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

from .tree_utils import (is_tree, get_name, get_value, is_token,
        get_child, get_value)
from .logging_utils import write_info
from .custom_exceptions import (
        VariableInDenominatorError,
        LoopVariableError,
        VariableNotFoundError,
        UnavailableIndexError,
        InvalidIntegerError,
        SeveralUnboundVariablesError
    )
from .math_utils import (math_add, math_sub,
        math_mul, math_div, math_mod, math_neg)
import re

def get_indexvalue(token, loop_vars):
    tokname = get_name(token)
    tokval = get_value(token)
    if tokname == 'INDEXVAR':
        return loop_vars[tokval]
    elif tokname == 'INDEXNUM':
        try:
            idx = int(tokval)
        except ValueError as valerr:
            raise InvalidIntegerError(
                    f'Numbers in index specifications must be integer '
                     'but here we got {tokval}.')
        return idx
    else:
        raise TypeError(f'The token of type {tokname} is not allowed as index specification.')

def substitute_abbreviation(val, datadic, loop_vars, look_up):
    if not is_tree(val):
        return val
    assert get_name(val) == 'expr'
    val = eval_expr_without_unknown_var(
        val, datadic, loop_vars, look_up
    )
    return val

def get_varval(expr, datadic, loop_vars, look_up=True, eval_abbrev=True):
    name = get_name(expr, nofail=True)
    if name in ('VARNAME', 'extvarname'):
        varname = get_varname(expr)
        idxquants = get_indexquants(expr)
    else:
        raise TypeError(f'node must be either of type VARNAME or extvarname ' +
                        'but is {name} OR it must be at least a string with ' +
                        'the variable name')

    if loop_vars is not None:
        if varname in datadic and varname in loop_vars:
            raise LoopVariableError(
                    f'the variable {varname} is both a loop variable and '
                     'a record variable, which is forbidden, check the recipe')
        if varname in loop_vars:
            return loop_vars[varname]

    orig_datadic = datadic
    while (varname not in datadic and
           '__up' in datadic and look_up):
        datadic = datadic['__up']
    if varname not in datadic:
        raise VariableNotFoundError(f'variable {varname} not found')
    if idxquants is None:
        if eval_abbrev:
            return substitute_abbreviation(
                datadic[varname], orig_datadic, loop_vars, look_up
            )
        else:
            return datadic[varname]
    else:
        curdic = datadic[varname]
        for i, idxquant in enumerate(idxquants):
            idx = get_indexvalue(idxquant, loop_vars)
            if i < len(idxquants)-1:
                try:
                    curdic = curdic[idx]
                except Exception:
                    raise UnavailableIndexError(
                            f'index {idx} does not exist in array {varname}')
        idx = get_indexvalue(idxquants[-1], loop_vars)
        try:
            val = curdic[idx]
        except Exception:
            raise UnavailableIndexError(
                    f'index {idx} does not exist in array {varname}')
        if eval_abbrev:
            return substitute_abbreviation(val, orig_datadic, loop_vars, look_up)
        else:
            return val

def count_unassigned_vars(expr, datadic, loop_vars, look_up=True):
    if is_tree(expr) and get_name(expr) != 'extvarname':
        return sum([count_unassigned_vars(ch, datadic, loop_vars)
                    for ch in expr.children])
    elif is_tree(expr) or (is_token(expr) and get_name(expr) == 'VARNAME'):
        try:
            get_varval(expr, datadic, loop_vars, look_up)
        except VariableNotFoundError:
            return 1
        except UnavailableIndexError:
            return 1
        return 0
    else:
        return 0

def get_varname(expr):
    if is_tree(expr):
        for ch in expr.children:
            varname = get_varname(ch)
            if varname is not None:
                return varname
    elif is_token(expr):
        if get_name(expr) == 'VARNAME':
            return get_value(expr)

    return None

def get_indexquants(expr):
    if not is_tree(expr):
        return None
    idxquants = []
    for ch in expr.children:
        if is_tree(ch):
            varname = get_indexquants(ch)
            if varname is not None:
                idxquants.extend(varname)
        elif get_name(ch) in ('INDEXVAR', 'INDEXNUM'):
            idxquants.append(ch)
    return idxquants if len(idxquants) > 0 else None

def get_all_extvarnames(expr):
    if not is_tree(expr):
        return []
    if get_name(expr) == 'extvarname':
        varname = None
        indices = []
        for ch in expr.children:
            child_name = get_name(ch)
            if child_name == 'VARNAME':
                varname = get_value(ch)
            elif child_name == 'indexquant':
                assert len(ch.children) == 1
                indexquant_child = ch.children[0]
                assert get_name(indexquant_child) in ('INDEXVAR', 'INDEXNUM')
                indices.append(get_value(indexquant_child))
            assert varname is not None
            return [(varname, tuple(indices))]

    varlist = []
    for ch in expr.children:
        varlist.extend(get_all_extvarnames(ch))
    return varlist

def varvalue_expr_conversion(vv, val, rwmode, cast_int=True):
    if vv[0] == 0 and vv[1] == 1:
        # vv[0] + vv[1]*varval = fieldvalue
        # so varval == fieldval
        return val
    # vv as returned by eval_expr
    if rwmode == 'read':
        # cast_int true means that we convert the result of a
        # division of two ints to int if possible
        return math_div(math_sub(val, vv[0]), vv[1], cast_int)
    else:
        return math_add(vv[0], math_mul(val, vv[1]))

def eval_expr_without_unknown_var(expr, datadic=None, loop_vars=None,
                                  look_up=True, cast_int=True):
    ret = eval_expr(expr, datadic, loop_vars, look_up, cast_int)
    if ret[1] != 0:
        unknown_varname = get_varname(ret[2])
        raise VariableNotFoundError(
                f'Unknown variable in expression ({unknown_varname})')
    return ret[0]

def eval_expr(expr, datadic=None, loop_vars=None, look_up=True, cast_int=True):
    name = get_name(expr, nofail=True)
    # reminder: VARNAME is is a string of letters and number, e.g., foo1
    #           extvarname can contain an index specification, e.g., foo1[i]
    if (name in ('VARNAME', 'extvarname')):
        if datadic is None:
            return (0, 1, expr)
        else:
            # if datadic and variable exists in datadic
            # we substitute the variable name by its value
            try:
                val = get_varval(expr, datadic, loop_vars, look_up, False)
                if is_tree(val) and get_name(val) == 'expr':
                    return eval_expr(
                        val, datadic, loop_vars, look_up, cast_int
                    )
                else:
                    return (val, 0, None)
            except VariableNotFoundError:
                return (0, 1, expr)
            except UnavailableIndexError:
                return (0, 1, expr)
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
        return (v, 0, None)
    elif name == 'minusexpr':
        v = eval_expr(expr.children[0], datadic, loop_vars, look_up, cast_int)
        return (math_neg(v[0]), -v[1], v[2])
    elif name in ('addition', 'subtraction',
                  'multiplication', 'modulo', 'division'):
        v1 = eval_expr(expr.children[0], datadic, loop_vars, look_up, cast_int)
        # children[1] contains the operator symbol *,/,+,-
        v2 = eval_expr(expr.children[2], datadic, loop_vars, look_up, cast_int)
        if name == 'multiplication':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                        'More than one unassigned variables must not appear ' +
                        'in an expression.')
            if v1[1] == 0:
                return (math_mul(v1[0], v2[0]),
                        math_mul(v1[0], v2[1]),
                        v2[2])
            else:
                return (math_mul(v1[0], v2[0]),
                        math_mul(v1[1], v2[0]),
                        v1[2])
        elif name == 'division':
            if v2[1] != 0:
                raise VariableInDenominatorError(
                        'A variable name must not appear in the denominator ' +
                        'of an expression.')
            vx = math_div(v1[0], v2[0], cast_int)
            vy = math_div(v1[1], v2[0], cast_int)
            return (vx, vy, v1[2])
        elif name == 'modulo':
            if v1[1] != 0 or v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    'Both x and y in the operation x % y (modulo) ' +
                    'must be known values. However, unbound variables' +
                    'are present in the expressions corresponding to x or y.')
            vx = math_mod(v1[0], v2[0], cast_int)
            return (vx, 0, None)
        elif name == 'addition':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    'More than one unassigned variable must not appear ' +
                    'in an expression.')
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            return (math_add(v1[0], v2[0]),
                    math_add(v1[1], v2[1]),
                    vexpr)
        elif name == 'subtraction':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                        'More than one unassigned variable must not appear ' +
                        'in an expression.')
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            return (math_sub(v1[0], v2[0]),
                    math_sub(v1[1], v2[1]),
                    vexpr)
    elif name == 'inconsistent_varspec':
        ch = get_child(expr, 'extvarname')
        return eval_expr(ch, datadic, loop_vars, look_up, cast_int)
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
        return eval_expr(
            trimmed_children[0], datadic, loop_vars, look_up, cast_int
        )
