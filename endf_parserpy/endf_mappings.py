from .logging_utils import logging, abbreviate_valstr, should_skip_logging_info
import re
from .tree_utils import (is_token, is_tree, get_name, get_value,
        get_child, get_child_names, get_child_value)
from .flow_control_utils import cycle_for_loop
from .endf_mapping_utils import get_varname, get_indexvars, eval_expr, varvalue_expr_conversion

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
        raise TypeError(f'Expected MAT {exp_mat} but encountered {cur_mat}')
    if exp_mf != 'MF' and int(exp_mf) != cur_mf:
        raise TypeError(f'Expected MF {exp_mf} but encountered {cur_mf}')
    if exp_mt != 'MT' and int(exp_mt) != cur_mt:
        raise TypeError(f'Expected MT {exp_mt} but encountered {cur_mt}')

def map_record_helper(expr_list, basekeys, record_dic, datadic, loop_vars, inverse):
    # these internal functions are hacks to allow for default names for some fields:
    # some fields in the ENDF language specification are optional and then no
    # Tree/Token is created for them but we still need to use their default names
    # in the mapping. For instance, the specification (xstable) after
    # [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable) is optional
    def get_varname_tmp(expr):
        return expr if isinstance(expr, str) else get_varname(expr)
    def get_indexvars_tmp(expr):
        return None if isinstance(expr, str) else get_indexvars(expr)
    def eval_expr_tmp(expr):
        # this is the same result as returned by eval_expr on an expr with just the variable name
        return eval_expr(expr) if not isinstance(expr, str) else (0, 1)
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
    indexvars_list = tuple(get_indexvars_tmp(t) for t in expr_list)
    expr_vvs = tuple((eval_expr_tmp(t) for i, t in enumerate(expr_list)))
    zipit = zip(basekeys, varnames, indexvars_list, expr_vvs)
    if not inverse:
        for sourcekey, targetkey, idxvars, expr_vv in zipit:
            # if the record specification contains a value,
            # hence targetkey is None, we check if the value
            # in the ENDF file is equal to that value and
            # bomb out if not. Except that, we don't do anything else,
            # as the fixed value can be written back during
            # the inverse transform from the record specification
            # in the ENDF recipe.
            if targetkey is None:
                assert expr_vv[1] == 0
                if record_dic[sourcekey] != expr_vv[0]:
                    raise ValueError(f'Expected {expr_vv[0]} in the ENDF file but got {record_dic[sourcekey]}')
            else:
                val = varvalue_expr_conversion_tmp(expr_vv, record_dic[sourcekey], inverse)
                if idxvars is None:
                    if targetkey in datadic and datadic[targetkey] != val:
                        raise ValueError( 'If the same variable appears in several record specifications ' +
                                          'in the ENDF recipe, the corresponding values ' +
                                          'in the ENDF file must be so that the variable evaluates to the ' +
                                         f'same value. This is not the case for {targetkey} which previously ' +
                                         f'was determined to be {datadic[targetkey]} but in the present ' +
                                         f'record would be determined to be {val}. Either the ENDF recipe ' +
                                          'is wrong or the ENDF file contains inconsistent data.')
                    datadic[targetkey] = val
                else:
                    # loop through indexvars, and initialize
                    # nested dictionaries with the indicies as keys
                    datadic.setdefault(targetkey, {})
                    curdic = datadic[targetkey]
                    for i, idxvar in enumerate(idxvars):
                        idx = loop_vars[idxvar]
                        if i < len(idxvars)-1:
                            curdic.setdefault(idx, {})
                            curdic = curdic[idx]
                    idx = loop_vars[idxvars[-1]]
                    curdic[idx] = val

        # we write out logging info the first time we encounter a variable
        tmp = tuple(v for v in varnames if v is not None)
        if not should_skip_logging_info(tmp, datadic):
            varvals = tuple(abbreviate_valstr(datadic[v]) for v in tmp)
            logging.info('Variable names in this record: ' + ', '.join([f'{v}: {vv}' for v, vv in zip(tmp, varvals)]))

        return datadic
    # inverse transform
    else:
        for sourcekey, targetkey, idxvars, expr_vv in zipit:
            if targetkey is None:
                assert expr_vv[1] == 0
                record_dic[sourcekey] = expr_vv[0]
            else:
                if idxvars is None:
                    val = datadic[targetkey]
                    finalval = varvalue_expr_conversion_tmp(expr_vv, val, inverse)
                    record_dic[sourcekey] = finalval
                else:
                    # loop through indexvars to descend
                    # into nested diciontary to retrieve value
                    curdic = datadic[targetkey]
                    for i, idxvar in enumerate(idxvars):
                        idx = loop_vars[idxvar]
                        if i < len(idxvars)-1:
                            curdic = curdic[idx]
                    idx = loop_vars[idxvars[-1]]
                    val = curdic[idx]
                    record_dic[sourcekey] = varvalue_expr_conversion_tmp(expr_vv, val, inverse)
        return record_dic
    raise ValueError('Tertium non datur')

def map_text_dic(text_line_node, text_dic={}, datadic={}, loop_vars={}, inverse=False):
    check_ctrl_spec(text_line_node, text_dic, datadic, inverse)
    expr_list = get_child(text_line_node, 'text_fields').children
    cn = ('HL',)
    return map_record_helper(expr_list, cn, text_dic, datadic, loop_vars, inverse)

def map_head_dic(head_line_node, head_dic={}, datadic={}, loop_vars={}, inverse=False):
    check_ctrl_spec(head_line_node, head_dic, datadic, inverse)
    expr_list = get_child(head_line_node, 'head_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, head_dic, datadic, loop_vars, inverse)

def map_cont_dic(cont_line_node, cont_dic={}, datadic={}, loop_vars={}, inverse=False):
    check_ctrl_spec(cont_line_node, cont_dic, datadic, inverse)
    expr_list = get_child(cont_line_node, 'cont_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, cont_dic, datadic, loop_vars, inverse)

def map_dir_dic(dir_line_node, dir_dic={}, datadic={}, loop_vars={}, inverse=False):
    check_ctrl_spec(dir_line_node, dir_dic, datadic, inverse)
    expr_list = get_child(dir_line_node, 'dir_fields').children
    cn = ('L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, dir_dic, datadic, loop_vars, inverse)

def map_tab1_dic(tab1_line_node, tab1_dic={}, datadic={}, loop_vars={}, inverse=False):
    check_ctrl_spec(tab1_line_node, tab1_dic, datadic, inverse)
    tab1_fields = get_child(tab1_line_node, 'tab1_fields')
    tab1_cont_fields = get_child(tab1_fields, 'tab1_cont_fields')
    tab1_def_fields = get_child(tab1_fields, 'tab1_def').children
    if 'table_name' in get_child_names(tab1_line_node):
        tblname_expr = get_child(tab1_line_node, 'table_name')
        tblvarname = get_varname(tblname_expr)
    else:
        tblvarname = 'table'
    # deal with the mapping of the variable names in the table first
    cn = ('NBT', 'INT', 'X', 'Y')
    tab1_def_fields = get_child(tab1_fields, 'tab1_def').children
    expr_list = ['NBT', 'INT'] + list(tab1_def_fields)
    if not inverse:
        tbl_datadic = {}
        tbl_dic = tab1_dic['table']
    else:
        tbl_datadic = datadic[tblvarname]
        tbl_dic = {}
    tbl_ret = map_record_helper(expr_list, cn, tbl_dic, tbl_datadic,
                                loop_vars, inverse)
    # we remove NR and NP (last two elements) because redundant information
    # and not used by write_tab1 and read_tab1
    expr_list = tab1_cont_fields.children[:-2]
    cn = ('C1', 'C2', 'L1', 'L2', 'table')
    if 'table_name' in get_child_names(tab1_line_node):
        tblname_expr = get_child(tab1_line_node, 'table_name')
        expr_list.append(tblname_expr)
        tblvarname = get_varname(tblname_expr)
    else:
        expr_list.append('table')
        tblvarname = 'table'
    main_ret = map_record_helper(expr_list, cn, tab1_dic, datadic, loop_vars, inverse)
    # add the table dictionary to the main dictionary
    new_tblname = tblvarname if not inverse else 'table'
    main_ret[new_tblname] = tbl_ret
    return main_ret

def map_list_dic(list_line_node, list_dic={}, datadic={}, loop_vars={}, inverse=False,
                 run_instruction=None):
    # static variables for the recursive function
    val_idx = 0
    # we embed recurisve helper function here so that
    # it can see the variables list_dic, datadic and loop_vars.
    # helper function for map_list_dic to recursively parse the list_body
    def parse_list_body_node(node):
        nonlocal val_idx
        nonlocal list_dic
        node_type = get_name(node)

        if node_type == 'expr':
            # maybe a bit hacky and clunky, but the method can do the job
            # of assigning a value of the list body to the appropriate variable in datadic
            if not inverse:
                vals = list_dic['vals']
                map_record_helper([node], ('val',), {'val': vals[val_idx]}, datadic, loop_vars, inverse)
            else:
                list_val = map_record_helper([node], ('val',), {}, datadic, loop_vars, inverse)
                list_dic.setdefault('vals', [])
                list_dic['vals'].append(list_val['val'])

            val_idx += 1
            return
        if node_type == 'list_loop':
            cycle_for_loop(node, parse_list_body_node, datadic, loop_vars,
                           loop_name='list_loop', head_name='list_for_head',
                           body_name='list_body')
        elif is_tree(node) and node_type == 'list_body':
            for child in node.children:
                parse_list_body_node(child)
        # we are fine with a new line
        elif node_type == 'NEWLINE':
            return
        else:
            raise ValueError(f'A node of type {node_type} must not appear in a list_body')

    check_ctrl_spec(list_line_node, list_dic, datadic, inverse)
    expr_list = get_child(list_line_node, 'list_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2', 'vals')
    map_record_helper(expr_list, cn, list_dic, datadic, loop_vars, inverse)

    # parse the list body
    list_body_node = get_child(list_line_node, 'list_body')
    parse_list_body_node(list_body_node)
    if val_idx < len(list_dic['vals']):
        raise ValueError('Not all values in the list_body were consumed and ' +
                         'associated with variables in datadic')

    if not inverse:
        return datadic
    else:
        return list_dic

