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
        VariableInDenominatorError,
        SeveralUnboundVariablesError,
    )
from .math_utils import (math_add, math_sub,
        math_mul, math_div, math_neg)
import re

def open_section(extvarname, datadic, loop_vars):
    varname = get_varname(extvarname)
    indexquants = get_indexquants(extvarname)
    curdatadic = datadic
    datadic.setdefault(varname, {})
    datadic = datadic[varname]
    idcsstr_list = []
    if indexquants is not None:
        for idxquant in indexquants:
            idx = get_indexvalue(idxquant, loop_vars)
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

def get_varval(expr, datadic, loop_vars):
    name = get_name(expr)
    if name not in ('VARNAME', 'extvarname'):
        raise TypeError(f'node must be either of type VARNAME or extvarname but is {name}')

    varname = get_varname(expr)
    idxquants = get_indexquants(expr)

    if loop_vars is not None:
        if varname in datadic and varname in loop_vars:
            raise LoopVariableError(
                    f'the variable {varname} is both a loop variable and '
                     'a record variable, which is forbidden, check the recipe')
        if varname in loop_vars:
            return loop_vars[varname]

    while varname not in datadic and '__up' in datadic:
        datadic = datadic['__up']
    if varname not in datadic:
        raise VariableNotFoundError(f'variable {varname} not found')
    if idxquants is None:
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
        return val

def count_unassigned_vars(expr, datadic, loop_vars):
    if is_tree(expr) and get_name(expr) != 'extvarname':
        return sum([count_unassigned_vars(ch, datadic, loop_vars)
                    for ch in expr.children])
    elif is_tree(expr) or (is_token(expr) and get_name(expr) == 'VARNAME'):
        try:
            get_varval(expr, datadic, loop_vars)
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
    if is_token(expr) and get_name(expr) == 'VARNAME':
        return get_value(expr)
    else:
        return None

def get_indexquants(expr):
    idxquants = []
    for ch in expr.children:
        if is_tree(ch):
            varname = get_indexquants(ch)
            if varname is not None:
                idxquants.extend(varname)
        elif get_name(ch) in ('INDEXVAR', 'INDEXNUM'):
            idxquants.append(ch)
    return idxquants if len(idxquants) > 0 else None

def varvalue_expr_conversion(vv, val, inverse):
    # vv as returned by eval_expr
    if not inverse:
        # cast_int true means that we convert the result of a
        # division of two ints to int if possible
        return math_div(math_sub(val, vv[0]), vv[1], cast_int=True)
    else:
        return math_add(vv[0], math_mul(val, vv[1]))

def eval_expr_without_unknown_var(expr, datadic=None, loop_vars=None):
    ret = eval_expr(expr, datadic, loop_vars)
    if ret[1] != 0:
        raise VariableNotFoundError('Unknown variable in expression')
    return ret[0]

def eval_expr(expr, datadic=None, loop_vars=None):
    name = get_name(expr)
    # reminder: VARNAME is is a string of letters and number, e.g., foo1
    #           extvarname can contain an index specification, e.g., foo1[i]
    if name in ('VARNAME', 'extvarname'):
        if datadic is None:
            return (0, 1)
        else:
            # if datadic and variable exists in datadic
            # we substitute the variable name by its value
            try:
                val = get_varval(expr, datadic, loop_vars)
                return (val, 0)
            except VariableNotFoundError:
                return (0, 1)
            except UnavailableIndexError:
                return (0, 1)
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
        return (math_neg(v[0]), -v[1])
    elif name in ('addition', 'subtraction',
                'multiplication', 'division'):
        v1 = eval_expr(expr.children[0], datadic, loop_vars)
        # children[1] contains the operator symbol *,/,+,-
        v2 = eval_expr(expr.children[2], datadic, loop_vars)
        if name == 'multiplication':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                        'More than one unassigned variables must not appear ' +
                        'in an expression.')
            if v1[1] == 0:
                return (math_mul(v1[0], v2[0]),
                        math_mul(v1[0], v2[1]))
            else:
                return (math_mul(v1[0], v2[0]),
                        math_mul(v1[1], v2[0]))
        elif name == 'division':
            if v2[1] != 0:
                raise VariableInDenominatorError(
                        'A variable name must not appear in the denominator ' +
                        'of an expression.')
            vx = math_div(v1[0], v2[0], cast_int=True)
            vy = math_div(v1[1], v2[0], cast_int=True)
            return (vx, vy)
        # TODO: addition and subtraction would not fail
        #       for something like VAR1 + VAR2 with both
        #       variables unassigned; this would lead to
        #       wrong assignments upstream
        elif name == 'addition':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    'More than one unassigned variable must not appear ' +
                    'in an expression.')
            return (math_add(v1[0], v2[0]),
                    math_add(v1[1], v2[1]))
        elif name == 'subtraction':
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                        'More than one unassigned variable must not appear ' +
                        'in an expression.')
            return (math_sub(v1[0], v2[0]),
                    math_sub(v1[1], v2[1]))
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
