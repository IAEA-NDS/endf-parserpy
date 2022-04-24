from tree_utils import is_token, is_tree, get_name, get_value, get_child, get_child_names


def map_record_helper(expr_list, basekeys, record_dic, datadic, loop_vars, inverse):
    # these internal functions are hacks to allow for default names for some fields:
    # some fields in the ENDF language specification are optional and then no
    # Tree/Token is created for them but we still need to use their default names
    # in the mapping
    def get_varname_tmp(expr):
        return expr if isinstance(expr, str) else get_varname(expr)
    def get_indexvar_tmp(expr):
        return None if isinstance(expr, str) else get_indexvar(expr)

    vn = tuple((get_varname_tmp(t) for t in expr_list))
    newkeys = (eval_expr(t)[0] if vn[i] is None else vn[i]
            for i, t in enumerate(expr_list))
    indexvars = tuple(get_indexvar_tmp(t) for t in expr_list)
    #if 'table' in basekeys:
    #    import pdb; pdb.set_trace()
    if not inverse:
        zipit = zip(basekeys, newkeys, indexvars)
        dic = record_dic
        newdic = datadic
    else:
        zipit = zip(newkeys, basekeys, indexvars)
        dic = datadic
        newdic = record_dic

    for k1, k2, idxvar in zipit:
        if isinstance(k1, str) and isinstance(k2, str):
            if idxvar is None:
                newdic[k2] = dic[k1]
            elif not inverse:
                newdic.setdefault(k2, {})
                idx = loop_vars[idxvar]
                newdic[k2][idx] = dic[k1]
            else:
                idx = loop_vars[idxvar]
                newdic[k2] = dic[k1][idx]
        # case applies only for inverse mapping
        # forward case: if k2 is a float, it is not added as a key
        #               to resulting dictionary, consequently:
        # inverse case: k1 not part in the source dictionary,
        # (k1->k2)      but resulting dictionary is expected to
        # (k2->k1)      contain it as value of k2 (see forward case)
        elif inverse:
            assert idxvar is None
            if k1 not in dic:
                newdic[k2] = k1
            else:
                raise IndexError('Very strange, found a non-string key in dictionary')
        elif dic[k1] != k2:
            assert idxvar is None
            raise ValueError( 'Error while reading record ' +
                             f'expected {k2} but read {dic[k1]}')
    return newdic

def map_text_dic(text_line_node, text_dic={}, datadic={}, loop_vars={}, inverse=False):
    expr_list = get_child(text_line_node, 'text_fields').children
    cn = ('HL',)
    return map_record_helper(expr_list, cn, text_dic, datadic, loop_vars, inverse)

def map_head_dic(head_line_node, head_dic={}, datadic={}, loop_vars={}, inverse=False):
    expr_list = get_child(head_line_node, 'head_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, head_dic, datadic, loop_vars, inverse)

def map_cont_dic(cont_line_node, cont_dic={}, datadic={}, loop_vars={}, inverse=False):
    expr_list = get_child(cont_line_node, 'cont_fields').children
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, cont_dic, datadic, loop_vars, inverse)

def map_dir_dic(dir_line_node, dir_dic={}, datadic={}, loop_vars={}, inverse=False):
    expr_list = get_child(dir_line_node, 'dir_fields').children
    cn = ('L1', 'L2', 'N1', 'N2')
    return map_record_helper(expr_list, cn, dir_dic, datadic, loop_vars, inverse)

def map_tab1_dic(tab1_line_node, tab1_dic={}, datadic={}, loop_vars={}, inverse=False):
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

def get_conv_fact(expr):
    """Get conversion to get field value form variable."""
    vv = eval_expr(expr)
    return vv[0] / vv[1]

def eval_expr(expr):
    name = get_name(expr)
    if name == 'extvarname':
        return (0., 1.)
    elif name == 'NUMBER':
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
            assert v2[1] == 0
            return (v1[0]/v2[0], v1[1]/v2[0])
        elif name == 'addition':
            return (v1[0]+v2[0], v1[1]+v2[1])
        elif name == 'subtraction':
            return (v1[0]-v2[0], v1[1]-v2[1])
    else:
        assert len(expr.children) == 1
        return eval_expr(expr.children[0])

