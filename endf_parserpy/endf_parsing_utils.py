import re
from .tree_utils import (is_token, is_tree, get_name, get_value,
        get_child, get_child_names, get_child_value)

def check_ctrl_spec(record_line_node, record_dic, datadic, inverse):
    ctrl_spec = get_child(record_line_node, 'ctrl_spec')
    dic = record_dic if not inverse else datadic
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
    def get_indexvar_tmp(expr):
        return None if isinstance(expr, str) else get_indexvar(expr)
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
    indexvars = tuple(get_indexvar_tmp(t) for t in expr_list)
    expr_vvs = tuple((eval_expr_tmp(t) for i, t in enumerate(expr_list)))
    zipit = zip(basekeys, varnames, indexvars, expr_vvs)
    if not inverse:
        for sourcekey, targetkey, idxvar, expr_vv in zipit:
            # if the record specification contains a value,
            # hence targetkey is None, we check if the value
            # in the ENDF file is equal to that value and
            # bomb out if not. Other than that, we don't do anything,
            # as the fixed value can be written back during
            # the inverse transform from the record specification.
            if targetkey is None:
                assert expr_vv[1] == 0
                if record_dic[sourcekey] != expr_vv[0]:
                    raise ValueError(f'Expected {expr_vv[0]} in the ENDF file but got {record_dic[sourcekey]}')
            else:
                val = varvalue_expr_conversion_tmp(expr_vv, record_dic[sourcekey], inverse)
                if not idxvar:
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
                    idx = loop_vars[idxvar]
                    datadic.setdefault(targetkey, {})
                    datadic[targetkey][idx] = val
        return datadic
    # inverse transform
    else:
        for sourcekey, targetkey, idxvar, expr_vv in zipit:
            if targetkey is None:
                assert expr_vv[1] == 0
                record_dic[sourcekey] = expr_vv[0]
            else:
                if not idxvar:
                    val = datadic[targetkey]
                    finalval = varvalue_expr_conversion_tmp(expr_vv, val, inverse)
                    record_dic[sourcekey] = finalval
                else:
                    idx = loop_vars[idxvar]
                    val = datadic[targetkey][idx]
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
    check_ctrl_spec(list_line_node, list_dic, datadic, inverse)
    expr_list = get_child(list_line_node, 'list_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2', 'vals')
    expr_list.append('vals')
    # here we go through the list elements to get the list
    if run_instruction is None:
        raise TypeError('argument run_instruction must be provided')
    assert '__in_list_body' not in loop_vars
    loop_vars['__in_list_body'] = True
    list_body_node = get_child(list_line_node, 'list_body')
    # this is the run_instruction function of the BasicEndfParser class
    # to deal with the recursive traversal of the tree.
    # the run_instruction function in the  general BasicEndfParser class
    # also needs to ensure that nothing is parsed that does not belong
    # into the body of the list. for this reason we set the variable
    # __in_list_body here that can be used in the BasicEndfParser class.
    # NOTE: This coupling between the code here and the the code in the
    # BasicEndfParser class is certainly not beautiful and does not help
    # code readability, but inlining the logic produces too many lines
    run_instruction(list_body_node)
    del loop_vars['__in_list_body']
    ret_dic = map_record_helper(expr_list, cn, list_dic, datadic, loop_vars, inverse)
    return ret_dic

# helper function for map_list_dic to recursively parse the list_body
def parse_list_body_node(node):
    pass
    # if loop statement, recurse
    # otherwise we expect an expr object where we extract the

def get_varname(expr):
    for ch in expr.children:
        if is_tree(ch):
            varname = get_varname(ch)
            if varname is not None:
                return varname
        elif get_name(ch) in 'VARNAME':
            return get_value(ch)
    return None

def get_indexvar(expr):
    for ch in expr.children:
        if is_tree(ch):
            varname = get_indexvar(ch)
            if varname is not None:
                return varname
        elif get_name(ch) in 'INDEXVAR':
            return get_value(ch)
    return None

def varvalue_expr_conversion(vv, val, inverse):
    # vv as returned by eval_expr
    if not inverse:
        res = (val - vv[0]) / vv[1]
        # if all occuring quantities are integer,
        # we expect the result to be integer as well
        # (e.g., for counter fields, L1, L2, N1, N2)
        if isinstance(val, int) and isinstance(vv[0], int) and isinstance(vv[1], int):
            if int(res) != res:
                raise ValueError('Result should be integer')
            return int(res)
        else:
            return res
    else:
        return vv[0] + val*vv[1]

def eval_expr(expr):
    name = get_name(expr)
    # reminder: VARNAME is is a string of letters and number, e.g., foo1
    #           extvarname can contain an index specification, e.g., foo1[i]
    if name in ('VARNAME', 'extvarname'):
        return (0, 1)
    elif name == 'NUMBER':
        # if it was an integer, we preserve this quality
        vstr = expr.value
        if re.match('^ *[0-9]+ *$', vstr):
            v = int(expr.value)
        else:
            v = float(expr.value)
        return (v, 0.)
    elif name == 'minusexpr':
        v = eval_expr(expr.children[0])
        return (-v[0], -v[1])
    elif name in ('addition', 'subtraction',
                'multiplication', 'division'):
        v1 = eval_expr(expr.children[0])
        v2 = eval_expr(expr.children[1])
        if name == 'multiplication':
            assert v1[1] == 0 or v2[1] == 0
            if v1[1] == 0:
                return (v1[0]*v2[0], v1[0]*v2[1])
            else:
                return (v1[0]*v2[0], v1[1]*v2[0])
        elif name == 'division':
            if v2[1] != 0:
                raise ValueError('A variable name must not appear in the denominator ' +
                                 'of an expression.')
            vx = v1[0]/v2[0]
            vy = v1[1]/v2[0]
            # divisions of two ints yield by default float in Python
            # if the division of two ints evaluate to an integer,
            # we want to preserve the int type
            if isinstance(v2[0], int):
                if isinstance(v1[0], int) and int(vx) == vx:
                    vx = int(vx)
                if isinstance(v1[1], int) and int(vy) == vy:
                    vy = int(vy)
            return (vx, vy)
        elif name == 'addition':
            return (v1[0]+v2[0], v1[1]+v2[1])
        elif name == 'subtraction':
            return (v1[0]-v2[0], v1[1]-v2[1])
    else:
        assert len(expr.children) == 1
        return eval_expr(expr.children[0])

