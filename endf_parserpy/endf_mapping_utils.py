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

from .tree_utils import is_tree, get_name, get_value, is_token, get_child
from .logging_utils import write_info
import re

def open_section(extvarname, datadic, loop_vars):
    varname = get_varname(extvarname)
    indexvars = get_indexvars(extvarname)
    curdatadic = datadic
    datadic.setdefault(varname, {})
    datadic = datadic[varname]
    idcsstr_list = []
    if indexvars is not None:
        for idxvar in indexvars:
            idx = loop_vars[idxvar]
            idcsstr_list.append(str(idx))
            datadic.setdefault(idx, {})
            datadic = datadic[idx]
    # provide a pointer so that functions
    # can look for variable names in the outer scope
    datadic['__up'] = curdatadic
    write_info(f'Open section {varname}[' + ','.join(idcsstr_list) + ']')
    return datadic

def close_section(extvarname, datadic):
    varname = get_varname(extvarname)
    write_info(f'Close section {varname}')
    curdatadic = datadic
    datadic = datadic['__up']
    del curdatadic['__up']
    return datadic

def get_varval(expr, datadic, loop_vars):
    name = get_name(expr)
    if name not in ('VARNAME', 'extvarname'):
        raise TypeError(f'node must be either of type VARNAME or extvarname but is {name}')

    varname = get_varname(expr)
    idxvars = get_indexvars(expr)

    if loop_vars is not None:
        if varname in datadic and varname in loop_vars:
            raise IndexError(f'the variable {varname} is both a loop variable and '
                              'a record variable, which is forbidden, check the recipe')
        if varname in loop_vars:
            return loop_vars[varname]

    while varname not in datadic and '__up' in datadic:
        datadic = datadic['__up']
    if varname not in datadic:
        raise IndexError(f'variable {varname} not found')
    if idxvars is None:
        return datadic[varname]
    else:
        curdic = datadic[varname]
        for i, idxvar in enumerate(idxvars):
            idx = loop_vars[idxvar]
            if i < len(idxvars)-1:
                curdic = curdic[idx]
        idx = loop_vars[idxvar[-1]]
        val = curdic[idx]
        return val

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

def eval_expr(expr, datadic=None, loop_vars=None):
    name = get_name(expr)
    # reminder: VARNAME is is a string of letters and number, e.g., foo1
    #           extvarname can contain an index specification, e.g., foo1[i]
    if name in ('VARNAME', 'extvarname'):
        if datadic is None:
            return (0, 1)
        else:
            # if datadic is given, we substitute the variable name by its value
            val = get_varval(expr, datadic, loop_vars)
            return (val, 0)
    elif name == 'NUMBER' or name == 'DESIRED_NUMBER':
        vstr = expr.value
        # a desired number is suffixed by a question mark
        # so we strip that away before proceeding
        vstr = vstr.rstrip('?')
        # if it was an integer, we preserve this quality
        if re.match('^ *[0-9]+ *$', vstr):
            v = int(vstr)
        else:
            v = float(vstr)
        return (v, 0)
    elif name == 'minusexpr':
        v = eval_expr(expr.children[0], datadic, loop_vars)
        return (-v[0], -v[1])
    elif name in ('addition', 'subtraction',
                'multiplication', 'division'):
        v1 = eval_expr(expr.children[0], datadic, loop_vars)
        # children[1] contains the operator symbol *,/,+,-
        v2 = eval_expr(expr.children[2], datadic, loop_vars)
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
    elif name == 'inconsistent_varspec':
        ch = get_child(expr, 'extvarname')
        return eval_expr(ch, datadic, loop_vars)
    else:
        # we remove enclosing brackets if present
        ch_first = expr.children[0]
        ch_last = expr.children[-1]
        if (is_token(ch_first) and get_name(ch_first) == 'LPAR' and
            is_token(ch_last) and get_name(ch_last) == 'RPAR'):
            trimmed_children = expr.children[1:-1]
        else:
            trimmed_children = expr.children
        assert len(trimmed_children) == 1
        return eval_expr(trimmed_children[0], datadic, loop_vars)

