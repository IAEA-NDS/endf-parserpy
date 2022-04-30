from .tree_utils import is_tree, get_name, get_value, is_token
import re

def get_varname(expr):
    if is_tree(expr):
        for ch in expr.children:
            varname = get_varname(ch)
            if varname is not None:
                return varname
    if is_token(expr) and get_name(expr) == 'VARNAME':
        return get_value(expr)
    else:
        return None

def get_indexvars(expr):
    idxvars = []
    for ch in expr.children:
        if is_tree(ch):
            varname = get_indexvars(ch)
            if varname is not None:
                return varname
        elif get_name(ch) in 'INDEXVAR':
            idxvars.append(get_value(ch))
    return idxvars if len(idxvars) > 0 else None

def varvalue_expr_conversion(vv, val, inverse):
    # vv as returned by eval_expr
    if not inverse:
        res = (val - vv[0]) / vv[1]
        # if all occuring quantities are integer,
        # we expect the result to be integer as well
        # (e.g., for counter fields, L1, L2, N1, N2)
        if isinstance(val, int) and isinstance(vv[0], int) and isinstance(vv[1], int):
            if int(res) != res:
                raise ValueError(f'fResult should be integer but obtained {res}')
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
        return (v, 0)
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

