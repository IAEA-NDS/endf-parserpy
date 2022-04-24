from tree_utils import is_token, is_tree, get_name, get_value, get_child

def map_record_helper(oldkeys, newkeys, dic, inverse):
    newdic = {}
    zipit = zip(oldkeys, newkeys) if not inverse else zip(newkeys, oldkeys)
    for k1, k2 in zipit:
        if isinstance(k1, str) and isinstance(k2, str):
            newdic[k2] = dic[k1]
        # case applies only for inverse mapping
        # forward case: if k2 is a float, it is not added as a key
        #               to resulting dictionary, consequently:
        # inverse case: k1 not part in the source dictionary,
        # (k1->k2)      but resulting dictionary is expected to
        # (k2->k1)      contain it as value of k2 (see forward case)
        elif inverse:
            if k1 not in dic:
                newdic[k2] = k1
            else:
                raise IndexError('Very strange, found a non-string key in dictionary')
        elif dic[k1] != k2:
            raise ValueError( 'Error while reading record ' +
                             f'expected {k2} but read {dic[k1]}')
    return newdic

def map_head_to_dic(head_line_node, head_dic, inverse=False):
    head_fields = get_child(head_line_node, 'head_fields')
    vn = tuple((get_varname(t) for t in head_fields.children))
    vm = (eval_expr(t)[0] if vn[i] is None else vn[i]
            for i, t in enumerate(head_fields.children))
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(cn, vm, head_dic, inverse)

def map_cont_to_dic(cont_line_node, cont_dic, inverse=False):
    cont_fields = get_child(cont_line_node, 'cont_fields')
    vn = tuple((get_varname(t) for t in cont_fields.children))
    vm = (eval_expr(t)[0] if vn[i] is None else vn[i]
            for i, t in enumerate(cont_fields.children))
    cn = ('C1', 'C2', 'L1', 'L2', 'N1', 'N2')
    return map_record_helper(cn, vm, cont_dic, inverse)

def get_varname(expr):
    for ch in expr.children:
        if is_tree(ch):
            varname = get_varname(ch)
            if varname is not None:
                return varname
        elif get_name(ch) in 'CNAME':
            return get_value(ch)
    return None

def get_conv_fact(expr):
    """Get conversion to get field value form variable."""
    vv = eval_expr(expr)
    return vv[0] / vv[1]

def eval_expr(expr):
    name = get_name(expr)
    if name == 'CNAME':
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

