############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

from .logging_utils import logging, abbreviate_valstr, should_skip_logging_info
import re
from .tree_utils import (is_token, is_tree, get_name, get_value,
        get_child, get_child_names, get_child_value, search_name)
from .flow_control_utils import cycle_for_loop
from .endf_mapping_utils import (get_varname, get_indexquants, eval_expr,
        varvalue_expr_conversion, open_section, close_section, get_indexvalue)
from .custom_exceptions import (
        UnexpectedControlRecordError,
        NumberMismatchError,
        InconsistentVariableAssignmentError,
        InvalidIntegerError,
        MoreListElementsExpectedError,
        UnconsumedListElementsError
    )
import numpy as np

def check_ctrl_spec(record_line_node, record_dic, datadic, inverse):
    ctrl_spec = get_child(record_line_node, 'ctrl_spec')
    dic = record_dic if not inverse else datadic
    # if MAT not found in local scope, scan the outer ones
    while not 'MAT' in dic and '__up' in dic:
        dic = dic['__up']
    cur_mat = dic['MAT']
    cur_mf  = dic['MF']
    cur_mt  = dic['MT']
    exp_mat = get_child_value(ctrl_spec, 'MAT_SPEC')
    exp_mf = get_child_value(ctrl_spec, 'MF_SPEC')
    exp_mt = get_child_value(ctrl_spec, 'MT_SPEC')
    if exp_mat != 'MAT' and int(exp_mat) != cur_mat:
        raise UnexpectedControlRecordError(
                f'Expected MAT {exp_mat} but encountered {cur_mat}')
    if exp_mf != 'MF' and int(exp_mf) != cur_mf:
        raise UnexpectedControlRecordError(
                f'Expected MF {exp_mf} but encountered {cur_mf}')
    if exp_mt != 'MT' and int(exp_mt) != cur_mt:
        raise UnexpectedControlRecordError(
                f'Expected MT {exp_mt} but encountered {cur_mt}')

def map_record_helper(expr_list, basekeys, record_dic, datadic, loop_vars, inverse, parse_opts=None):
    parse_opts = parse_opts if parse_opts is not None else {}
    fuzzy_matching = parse_opts.get('fuzzy_matching', False)
    ignore_zero_mismatch = parse_opts.get('ignore_zero_mismatch', True)

    # remove COMMA token because it is not relevant
    expr_list = [expr for expr in expr_list
            if not is_token(expr) or get_name(expr) != 'COMMA']

    # these internal functions are hacks to allow for default names for some fields:
    # some fields in the ENDF language specification are optional and then no
    # Tree/Token is created for them but we still need to use their default names
    # in the mapping. For instance, the specification (xstable) after
    # [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable) is optional
    def get_varname_tmp(expr):
        # the "not is_token(expr)" part is a hack because a Token seems to be regarded
        # as type "str" because isinstance(expr, str) evaluates to true for a Token
        return expr if isinstance(expr, str) and not is_token(expr)  else get_varname(expr)
    def get_indexquants_tmp(expr):
        return None if isinstance(expr, str) else get_indexquants(expr)
    def eval_expr_tmp(expr, datadic=None, loop_vars=None):
        # this is the same result as returned by eval_expr on an expr with just the variable name
        if not isinstance(expr, str):
            return eval_expr(expr, datadic, loop_vars)
        else:
            return (0, 1)
    def varvalue_expr_conversion_tmp(vv, val, inverse):
        # in the case of a tab1, the value of the variable (val) will be a list
        if isinstance(val, list):
            return [varvalue_expr_conversion(vv, x, inverse) for x in val]
        # in the case of a text record, it will be a string, which we return unaltered
        elif isinstance(val, str):
            return val
        # also if it is a dictionary, we return it unaltered
        elif isinstance(val, dict):
            return val
        # otherwise it is a number and we can convert back and forth (e.g., if N/6 in a record specification)
        else:
            return varvalue_expr_conversion(vv, val, inverse)

    varnames = tuple((get_varname_tmp(t) for t in expr_list))
    indexquants_list = tuple(get_indexquants_tmp(t) for t in expr_list)

    zipit = zip(basekeys, varnames, indexquants_list, expr_list)

    # TODO: Need to refactor the error message stuff
    def create_variable_exists_error_msg(varname, prev_val, cur_val):
        return ('If the same variable appears in several record specifications ' +
                'in the ENDF recipe, the corresponding values ' +
                'in the ENDF file must be so that the variable evaluates to the ' +
               f'same value. This is not the case for {varname} which previously ' +
               f'was determined to be {prev_val} but in the present ' +
               f'record would be determined to be {cur_val}. Either the ENDF recipe ' +
                'is wrong or the ENDF file contains inconsistent data. Note that ' +
               f'{varname} may be an array, in which case this statement would ' +
                'apply to one of the variables in that array')
    def create_variable_wrong_value_error_msg(realval, expval, sourcekey):
        return (f'Expected {expr_vv[0]} in the ENDF file but got {record_dic[sourcekey]}. '
                f'The value was encountered in a source field named {sourcekey}')

    if not inverse:
        for sourcekey, targetkey, idxquants, curexpr in zipit:

            expr_vv = eval_expr_tmp(curexpr, datadic, loop_vars)
            # if the record specification contains a value,
            # hence targetkey is None, we check if the value
            # in the ENDF file is equal to that value and
            # bomb out if not. Except that, we don't do anything else,
            # as the fixed value can be written back during
            # the inverse transform from the record specification
            # in the ENDF recipe.
            if targetkey is None:
                assert expr_vv[1] == 0

                if not ignore_zero_mismatch:
                    # if we have a DESIRED_NUMBER in the expression,
                    # we expect a certain number but we do not require it.
                    # with only NUMBER in the expression, any mismatch between
                    # our expectation and the number in the ENDF file will yield
                    # an error.
                    contains_desired_number = search_name(curexpr, 'DESIRED_NUMBER')
                    value_mismatch_occurred = record_dic[sourcekey] != expr_vv[0]
                    #msg = f'Expected {expr_vv[0]} in the ENDF file but got {record_dic[sourcekey]}'
                    msg = create_variable_wrong_value_error_msg(record_dic[sourcekey],
                                                                expr_vv[0], sourcekey)
                    if value_mismatch_occurred:
                        if contains_desired_number:
                            logging.warning(msg)
                        else:
                            raise NumberMismatchError(msg)
            else:
                inconsistency_allowed = is_tree(curexpr) and search_name(curexpr, 'inconsistent_varspec')
                # all variables in the current slot of the record
                # were already assigned so we just check for consistency
                if expr_vv[1] == 0:
                    if record_dic[sourcekey] != expr_vv[0]:
                        if not inconsistency_allowed:
                            if not fuzzy_matching:
                                mismatch_occurred = True
                            else:
                                mismatch_occurred = \
                                    not np.isclose(record_dic[sourcekey], expr_vv[0],
                                                   atol=1e-7, rtol=1e-5)
                            if mismatch_occurred:
                                raise InconsistentVariableAssignmentError(
                                         'The term with the values of the existing variables ' +
                                         f'evaluates to a value {expr_vv[0]} that is inconsistent ' +
                                         f'with the value {record_dic[sourcekey]} in the file ' +
                                         f'for slot {sourcekey}')
                # there is still a dangling variable but we can
                # solve the linear equation given in the slot to obtain its value
                else:
                    try:
                        val = varvalue_expr_conversion_tmp(expr_vv, record_dic[sourcekey], inverse)
                    except InvalidIntegerError as pexc:
                        raise InvalidIntegerError(str(pexc) + f' (variable {targetkey})')

                    if idxquants is None:
                        if targetkey in datadic:
                            prev_val = datadic[targetkey]
                            if not inconsistency_allowed:
                                if not fuzzy_matching:
                                    mismatch_occurred = prev_val != val
                                else:
                                    # NOTE: some files may contain small inconsistencies
                                    # which do not matter for all practical purposes, e.g., O-18 in FENDL 3.2.
                                    # we tolerate such small inconsistencies.
                                    mismatch_occurred = not np.isclose(prev_val, val, atol=1e-7, rtol=1e-5)
                                if mismatch_occurred:
                                    raise InconsistentVariableAssignmentError(
                                            create_variable_exists_error_msg(targetkey, prev_val, val))
                        else:
                            datadic[targetkey] = val
                    else:
                        # loop through indexvars, and initialize
                        # nested dictionaries with the indicies as keys
                        datadic.setdefault(targetkey, {})
                        curdic = datadic[targetkey]
                        for i, idxquant in enumerate(idxquants):
                            idx = get_indexvalue(idxquant, loop_vars)
                            if i < len(idxquants)-1:
                                curdic.setdefault(idx, {})
                                curdic = curdic[idx]
                        idx = get_indexvalue(idxquants[-1], loop_vars)
                        if idx in curdic:
                            prev_val = curdic[idx]
                            # NOTE: some files may contain small inconsistencies
                            # which do not matter for all practical purposes, e.g., O-18 in FENDL 3.2.
                            # we tolerate such small inconsistencies.
                            if not inconsistency_allowed:
                                if not fuzzy_matching:
                                    mismatch_occurred = prev_val != val
                                else:
                                    mismatch_occurred = not np.isclose(prev_val, val, atol=1e-7, rtol=1e-5)
                                if mismatch_occurred:
                                    raise InconsistentVariableAssignmentError(
                                            create_variable_exists_error_msg(targetkey, prev_val, val))
                        else:
                            curdic[idx] = val

        # we write out logging info the first time we encounter a variable
        tmp = tuple(v for v in varnames if v is not None)
        if not should_skip_logging_info(tmp, datadic):
            varvals = tuple(abbreviate_valstr(datadic[v]) for v in tmp)
            logging.info('Variable names in this record: ' + ', '.join([f'{v}: {vv}' for v, vv in zip(tmp, varvals)]))

        return datadic
    # inverse transform
    else:
        for sourcekey, targetkey, idxquants, curexpr in zipit:
            expr_vv = eval_expr_tmp(curexpr)
            if targetkey is None:
                assert expr_vv[1] == 0
                record_dic[sourcekey] = expr_vv[0]
            else:
                if idxquants is None:
                    val = datadic[targetkey]
                    finalval = varvalue_expr_conversion_tmp(expr_vv, val, inverse)
                    record_dic[sourcekey] = finalval
                else:
                    # loop through indexvars to descend
                    # into nested diciontary to retrieve value
                    curdic = datadic[targetkey]
                    for i, idxquant in enumerate(idxquants):
                        idx = get_indexvalue(idxquant, loop_vars)
                        if i < len(idxquants)-1:
                            curdic = curdic[idx]
                    idx = get_indexvalue(idxquants[-1], loop_vars)
                    val = curdic[idx]
                    record_dic[sourcekey] = varvalue_expr_conversion_tmp(expr_vv, val, inverse)
        return record_dic
    raise ValueError('Tertium non datur')

def map_text_dic(text_line_node, text_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(text_line_node, text_dic, datadic, inverse)
    expr_list = get_child(text_line_node, 'text_fields').children
    cn = ('HL',)
    return map_record_helper(expr_list, cn, text_dic, datadic, loop_vars, inverse, parse_opts)

def map_head_dic(head_line_node, head_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(head_line_node, head_dic, datadic, inverse)
    expr_list = get_child(head_line_node, 'head_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, head_dic, datadic, loop_vars, inverse, parse_opts)

def map_cont_dic(cont_line_node, cont_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(cont_line_node, cont_dic, datadic, inverse)
    expr_list = get_child(cont_line_node, 'cont_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, cont_dic, datadic, loop_vars, inverse, parse_opts)

def map_dir_dic(dir_line_node, dir_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(dir_line_node, dir_dic, datadic, inverse)
    expr_list = get_child(dir_line_node, 'dir_fields').children
    cn = ('L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, dir_dic, datadic, loop_vars, inverse, parse_opts)

def map_intg_dic(intg_line_node, intg_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(intg_line_node, intg_dic, datadic, inverse)
    expr_list = get_child(intg_line_node, 'intg_fields').children
    cn = ('II', 'JJ', 'KIJ')
    return map_record_helper(expr_list, cn, intg_dic, datadic, loop_vars, inverse, parse_opts)

def map_tab2_dic(tab2_line_node, tab2_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(tab2_line_node, tab2_dic, datadic, inverse)
    tab2_fields = get_child(tab2_line_node, 'tab2_fields')
    tab2_cont_fields = get_child(tab2_fields, 'tab2_cont_fields')
    # tab2_def_fields contains the name of the Z variable
    # we don't need it because the following TAB1/LIST records
    # contain the name of this variable at position of C2
    tab2_def_fields = get_child(tab2_fields, 'tab2_def').children
    tab2_name_node = get_child(tab2_line_node, 'table_name', nofail=True)
    # open section if desired
    if tab2_name_node is not None:
        datadic = open_section(tab2_name_node, datadic, loop_vars)
    # deal with the mapping of the variable names in the table first
    cn = ('NBT', 'INT')
    tab2_def_fields = get_child(tab2_fields, 'tab2_def').children
    expr_list = ['NBT', 'INT']
    tbl_dic = {} if inverse else tab2_dic['table']
    tbl_ret = map_record_helper(expr_list, cn, tbl_dic, datadic, loop_vars, inverse, parse_opts)
    # close section if desired
    if tab2_name_node is not None:
        datadic = close_section(tab2_name_node, datadic)
    # we remove NR because we can infer it from the length of the NBT array
    # we keep NZ because it contains the number of following TAB1/LIST records
    # NOTE: -(2+1) because a comma separates NR and NZ
    expr_list = tab2_cont_fields.children[:-3] + tab2_cont_fields.children[-1:]
    cn = ('C1', 'C2', 'L1', 'L2','N2')
    main_ret = map_record_helper(expr_list, cn, tab2_dic, datadic, loop_vars, inverse, parse_opts)
    if inverse:
        main_ret['table'] = tbl_ret
    return main_ret

def map_tab1_dic(tab1_line_node, tab1_dic={}, datadic={}, loop_vars={}, inverse=False, parse_opts=None):
    check_ctrl_spec(tab1_line_node, tab1_dic, datadic, inverse)
    tab1_fields = get_child(tab1_line_node, 'tab1_fields')
    tab1_cont_fields = get_child(tab1_fields, 'tab1_cont_fields')
    tab1_def_fields = get_child(tab1_fields, 'tab1_def').children
    tab1_name_node = get_child(tab1_line_node, 'table_name', nofail=True)

    # open section if desired
    if tab1_name_node is not None:
        datadic = open_section(tab1_name_node, datadic, loop_vars)
    # deal with the mapping of the variable names in the table first
    cn = ('NBT', 'INT', 'X', 'Y')
    tab1_def_fields = get_child(tab1_fields, 'tab1_def').children
    # remove the slash
    tab1_def_fields = [field for field in tab1_def_fields if get_name(field) != 'SLASH']
    expr_list = ['NBT', 'INT'] + list(tab1_def_fields)
    tbl_dic = {} if inverse else tab1_dic['table']
    tbl_ret = map_record_helper(expr_list, cn, tbl_dic, datadic, loop_vars, inverse, parse_opts)
    # close section if desired
    if tab1_name_node is not None:
        datadic = close_section(tab1_name_node, datadic)
    # we remove NR and NP (last two elements) because redundant information
    # and not used by write_tab1 and read_tab1 (2+1 because a comma separates NR and NP)
    expr_list = tab1_cont_fields.children[:-3]
    cn = ('C1', 'C2', 'L1', 'L2')
    main_ret = map_record_helper(expr_list, cn, tab1_dic, datadic, loop_vars, inverse, parse_opts)
    if inverse:
        main_ret['table'] = tbl_ret
    return main_ret

def map_list_dic(list_line_node, list_dic={}, datadic={}, loop_vars={}, inverse=False,
                 run_instruction=None, parse_opts=None):
    val_idx = 0
    # we embed recurisve helper function here so that
    # it can see the variables list_dic, datadic and loop_vars.
    # helper function for map_list_dic to recursively parse the list_body
    def parse_list_body_node(node):
        nonlocal val_idx
        nonlocal list_dic
        node_type = get_name(node)

        if node_type == 'expr':
            if not inverse:
                vals = list_dic['vals']
                numvals = len(vals)
                if val_idx >= numvals:
                    raise MoreListElementsExpectedError(
                            f'All {numvals} values in the list body present in the ENDF file ' +
                             'have already been consumed. ' +
                             'You may check the index specifications of your list body. ')
                # maybe a bit hacky and clunky, but the method can do the job
                # of assigning a value of the list body to the appropriate variable in datadic
                map_record_helper([node], ('val',), {'val': vals[val_idx]}, datadic, loop_vars, inverse, parse_opts)
            else:
                list_val = map_record_helper([node], ('val',), {}, datadic, loop_vars, inverse, parse_opts)
                list_dic.setdefault('vals', [])
                list_dic['vals'].append(list_val['val'])

            val_idx += 1
            return

        # sometimes the expectation is that within a list body (list in LIST record)
        # a line must be padded with zeros until the end before a new subrecord
        # starts on the next line
        elif node_type == 'LINEPADDING':
            num_skip_elems = (6 - val_idx % 6) % 6
            if not inverse:
                # we do nothing here because we only need to skip some
                # elements, what we do afterwards
                pass
            else:
                list_dic['vals'].extend([0.0]*num_skip_elems)
            # skip over the elements
            val_idx = val_idx + num_skip_elems
            return

        elif node_type == 'list_loop':
            cycle_for_loop(node, parse_list_body_node, datadic, loop_vars,
                           loop_name='list_loop', head_name='list_for_head',
                           body_name='list_body')

        elif is_tree(node) and node_type == 'list_body':
            for child in node.children:
                parse_list_body_node(child)

        # we are fine with a new line and a comma
        elif node_type in ('NEWLINE', 'COMMA'):
            return
        else:
            raise ValueError(f'A node of type {node_type} must not appear in a list_body')

    check_ctrl_spec(list_line_node, list_dic, datadic, inverse)
    expr_list = get_child(list_line_node, 'list_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2', 'vals')
    map_record_helper(expr_list, cn, list_dic, datadic, loop_vars, inverse, parse_opts)

    # enter subsection if demanded
    list_name_node = get_child(list_line_node, 'list_name', nofail=True)
    if list_name_node is not None:
        datadic = open_section(list_name_node, datadic, loop_vars)
    # parse the list body
    list_body_node = get_child(list_line_node, 'list_body')
    parse_list_body_node(list_body_node)
    # close subsection if opened
    if list_name_node is not None:
        datadic = close_section(list_name_node, datadic)

    numels_in_list = len(list_dic['vals'])
    if val_idx < numels_in_list:
        raise UnconsumedListElementsError(
                f'Not all values in the list_body were consumed and '
                 'associated with variables in datadic '
                f'(read {val_idx} out of {numels_in_list})')
    if inverse:
        return list_dic
    else:
        return datadic

