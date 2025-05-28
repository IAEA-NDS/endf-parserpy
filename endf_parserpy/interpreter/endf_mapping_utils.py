############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import (
    is_tree,
    get_name,
    get_value,
    is_token,
    get_child,
    get_value,
)
from endf_parserpy.utils.math_utils import (
    math_add,
    math_sub,
    math_mul,
    math_div,
    math_mod,
    math_neg,
)
from .custom_exceptions import (
    VariableInDenominatorError,
    LoopVariableError,
    VariableNotFoundError,
    IndexVariableNotFoundError,
    UnavailableIndexError,
    InvalidIntegerError,
    SeveralUnboundVariablesError,
)
from .helpers import (
    list_set,
    list_setdefault,
    shift_indices,
)
import re


def get_indexvalue(expr, datadic, loop_vars, parse_opts, look_up):
    try:
        val = eval_expr_without_unknown_var(
            expr, datadic, loop_vars, parse_opts, look_up
        )
    except VariableNotFoundError as exc:
        raise exc.to_index_error() from exc
    if int(val) != val:
        raise InvalidIntegerError(
            f"Numbers in index specifications must be integer "
            f"but here we got {val}."
        )
    return val


def substitute_abbreviation(val, datadic, loop_vars, parse_opts, look_up):
    if not is_tree(val):
        return val
    assert get_name(val) == "expr"
    val = eval_expr_without_unknown_var(val, datadic, loop_vars, parse_opts, look_up)
    return val


def _get_array_value_in_dict_mode(varname, array_cont, idcs, raise_if_missing):
    curdic = array_cont
    for idx in idcs:
        if idx in curdic:
            curdic = curdic[idx]
        elif not raise_if_missing:
            return None
        else:
            raise UnavailableIndexError(
                f"index {idx} does not exist in array {varname}"
            )
    return curdic


def _get_array_value_in_list_mode(varname, array_cont, idcs, raise_if_missing):
    curlst = array_cont
    for idx in idcs:
        if idx >= 0 and idx < len(curlst):
            curlst = curlst[idx]
        elif not raise_if_missing:
            return None
        else:
            raise UnavailableIndexError(
                f"index {idx} does not exist in array {varname}"
            )
    return curlst


def get_array_value(
    varname, idxquants, datadic, loop_vars, parse_opts, raise_if_missing
):
    in_list_mode = parse_opts["internal_array_type"] == "list"
    array_obj = datadic[varname]
    idcs = [get_indexvalue(q, datadic, loop_vars, parse_opts, True) for q in idxquants]
    if in_list_mode:
        idcs = shift_indices(varname, idcs, datadic)
        return _get_array_value_in_list_mode(varname, array_obj, idcs, raise_if_missing)
    else:
        return _get_array_value_in_dict_mode(varname, array_obj, idcs, raise_if_missing)


def _set_array_value_in_dict_mode(
    varname, idxquants, value, datadic, loop_vars, parse_opts
):
    curdic = datadic.setdefault(varname, {})
    for idxquant in idxquants[:-1]:
        idx = get_indexvalue(idxquant, datadic, loop_vars, parse_opts, True)
        curdic = curdic.setdefault(idx, {})
    idx = get_indexvalue(idxquants[-1], datadic, loop_vars, parse_opts, True)
    curdic[idx] = value


def _set_array_value_in_list_mode(
    varname, idxquants, value, datadic, loop_vars, parse_opts
):
    idcs = [get_indexvalue(q, datadic, loop_vars, parse_opts, True) for q in idxquants]
    idcs = shift_indices(varname, idcs, datadic)
    curlist = datadic.setdefault(varname, [])
    for idx in idcs[:-1]:
        curlist = list_setdefault(curlist, idx, [])
    list_set(curlist, idcs[-1], value)


def set_array_value(varname, idxquants, value, datadic, loop_vars, parse_opts):
    in_list_mode = parse_opts["internal_array_type"] == "list"
    if not in_list_mode:
        _set_array_value_in_dict_mode(
            varname, idxquants, value, datadic, loop_vars, parse_opts
        )
    else:
        _set_array_value_in_list_mode(
            varname, idxquants, value, datadic, loop_vars, parse_opts
        )


def varname_or_extvarname_check(expr):
    name = get_name(expr, nofail=True)
    if name not in ("VARNAME", "extvarname"):
        raise TypeError(
            "node must be either of type `VARNAME` or `extvarname` "
            + f"but is of type `{name}`"
        )


def generate_varname_str(expr, datadic, loop_vars, parse_opts, look_up):
    varname_or_extvarname_check(expr)
    node_name = get_name(expr)
    if node_name == "VARNAME":
        return get_value(expr)
    # we assume it is an extvarname node
    retstr = ""
    for child in expr.children:
        child_name = get_name(child)
        if child_name == "VARNAME":
            retstr += get_value(child)
        elif child_name == "indexquant":
            idxval = get_indexvalue(child, datadic, loop_vars, parse_opts, look_up)
            retstr += str(idxval)
        else:
            retstr += get_value(child)
    return retstr


def get_varval(
    expr,
    datadic,
    loop_vars,
    parse_opts,
    look_up=True,
    eval_abbrev=True,
    raise_if_missing=False,
):
    varname_or_extvarname_check(expr)
    varname = get_varname(expr)
    idxquants = get_indexquants(expr)

    if loop_vars is not None:
        if varname in datadic and varname in loop_vars:
            raise LoopVariableError(
                f"the variable {varname} is both a loop variable and "
                "a record variable, which is forbidden, check the recipe"
            )
        if varname in loop_vars:
            return loop_vars[varname]

    orig_datadic = datadic
    while varname not in datadic and "__up" in datadic and look_up:
        datadic = datadic["__up"]
    if varname not in datadic:
        if raise_if_missing:
            raise VariableNotFoundError(f"variable {varname} not found", varname)
        return None
    if idxquants is None:
        if eval_abbrev:
            return substitute_abbreviation(
                datadic[varname], orig_datadic, loop_vars, parse_opts, look_up
            )
        else:
            return datadic[varname]
    else:
        val = get_array_value(
            varname, idxquants, datadic, loop_vars, parse_opts, raise_if_missing
        )
        if val is None:
            return val
        # TODO: Can this if block be removed? Does it make sense to subsitute a name
        #       if is associated with an array name (hence has indices). Probably not.
        if eval_abbrev:
            return substitute_abbreviation(
                val, orig_datadic, loop_vars, parse_opts, look_up
            )
        else:
            return val


def set_varval(expr, datadic, loop_vars, value, parse_opts):
    varname_or_extvarname_check(expr)
    varname = get_varname(expr)
    idxquants = get_indexquants(expr)
    if idxquants is None:
        datadic[varname] = value
    else:
        set_array_value(varname, idxquants, value, datadic, loop_vars, parse_opts)


def count_unassigned_vars(expr, datadic, loop_vars, parse_opts, look_up=True):
    if is_tree(expr) and get_name(expr) != "extvarname":
        return sum(
            [count_unassigned_vars(ch, datadic, loop_vars) for ch in expr.children]
        )
    elif is_tree(expr) or (is_token(expr) and get_name(expr) == "VARNAME"):
        try:
            get_varval(expr, datadic, loop_vars, parse_opts, look_up)
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
        if get_name(expr) == "VARNAME":
            return get_value(expr)
    return None


def get_indexquants(expr):
    if not is_tree(expr):
        return None
    node_type = get_name(expr)
    if node_type in ("section_head", "list_name", "table_name"):
        expr = get_child(expr, "extvarname")
        node_type = get_name(expr)
    assert node_type == "extvarname"
    idxquants = []
    for ch in expr.children:
        if is_tree(ch) and get_name(ch) == "indexquant":
            child_expr = get_child(ch, "expr")
            idxquants.append(child_expr)
    return idxquants if len(idxquants) > 0 else None


def get_all_extvarnames(expr):
    if not is_tree(expr):
        return []
    if get_name(expr) == "extvarname":
        varname = None
        indices = []
        for ch in expr.children:
            child_name = get_name(ch)
            if child_name == "VARNAME":
                varname = get_value(ch)
            elif child_name == "indexquant":
                assert len(ch.children) == 1
                indexquant_child = ch.children[0]
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
    if rwmode == "read":
        # cast_int true means that we convert the result of a
        # division of two ints to int if possible
        return math_div(math_sub(val, vv[0]), vv[1], cast_int)
    else:
        return math_add(vv[0], math_mul(val, vv[1]))


def eval_expr_without_unknown_var(
    expr, datadic=None, loop_vars=None, parse_opts=None, look_up=True, cast_int=True
):
    ret = eval_expr(expr, datadic, loop_vars, parse_opts, look_up, cast_int, False)
    return ret[0]


def eval_expr(
    expr,
    datadic=None,
    loop_vars=None,
    parse_opts=None,
    look_up=True,
    cast_int=True,
    accept_missing=True,
):
    name = get_name(expr, nofail=True)
    # reminder: VARNAME is is a string of letters and number, e.g., foo1
    #           extvarname can contain an index specification, e.g., foo1[i]
    if name in ("VARNAME", "extvarname"):
        if datadic is None:
            return (0, 1, expr)
        else:
            # if datadic and variable exists in datadic
            # we substitute the variable name by its value
            val = get_varval(
                expr, datadic, loop_vars, parse_opts, look_up, False, not accept_missing
            )
            if val is None:
                return (0, 1, expr)
            elif is_tree(val) and get_name(val) == "expr":
                return eval_expr(
                    val,
                    datadic,
                    loop_vars,
                    parse_opts,
                    look_up,
                    cast_int,
                    accept_missing,
                )
            else:
                return (val, 0, None)

    elif name == "NUMBER" or name == "DESIRED_NUMBER":
        vstr = expr.value
        # a desired number is suffixed by a question mark
        # so we strip that away before proceeding
        vstr = vstr.rstrip("?")
        # if it was an integer, we preserve this quality
        if re.match("^ *[0-9]+ *$", vstr):
            v = int(vstr)
        else:
            v = float(vstr)
        return (v, 0, None)
    elif name == "minusexpr":
        v = eval_expr(
            expr.children[1],
            datadic,
            loop_vars,
            parse_opts,
            look_up,
            cast_int,
            accept_missing,
        )
        return (math_neg(v[0]), -v[1], v[2])
    elif name in ("addition", "subtraction", "multiplication", "modulo", "division"):
        v1 = eval_expr(
            expr.children[0],
            datadic,
            loop_vars,
            parse_opts,
            look_up,
            cast_int,
            accept_missing,
        )
        # children[1] contains the operator symbol *,/,+,-
        v2 = eval_expr(
            expr.children[2],
            datadic,
            loop_vars,
            parse_opts,
            look_up,
            cast_int,
            accept_missing,
        )
        if name == "multiplication":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variables must not appear "
                    + "in an expression."
                )
            if v1[1] == 0:
                return (math_mul(v1[0], v2[0]), math_mul(v1[0], v2[1]), v2[2])
            else:
                return (math_mul(v1[0], v2[0]), math_mul(v1[1], v2[0]), v1[2])
        elif name == "division":
            if v2[1] != 0:
                raise VariableInDenominatorError(
                    "A variable name must not appear in the denominator "
                    + "of an expression."
                )
            vx = math_div(v1[0], v2[0], cast_int)
            vy = math_div(v1[1], v2[0], cast_int)
            return (vx, vy, v1[2])
        elif name == "modulo":
            if v1[1] != 0 or v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "Both x and y in the operation x % y (modulo) "
                    + "must be known values. However, unbound variables"
                    + "are present in the expressions corresponding to x or y."
                )
            vx = math_mod(v1[0], v2[0], cast_int)
            return (vx, 0, None)
        elif name == "addition":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variable must not appear "
                    + "in an expression."
                )
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            return (math_add(v1[0], v2[0]), math_add(v1[1], v2[1]), vexpr)
        elif name == "subtraction":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variable must not appear "
                    + "in an expression."
                )
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            return (math_sub(v1[0], v2[0]), math_sub(v1[1], v2[1]), vexpr)
    elif name == "inconsistent_varspec":
        ch = get_child(expr, "extvarname")
        return eval_expr(
            ch, datadic, loop_vars, parse_opts, look_up, cast_int, accept_missing
        )
    else:
        # we remove enclosing brackets if present
        ch_first = expr.children[0]
        ch_last = expr.children[-1]
        if (
            is_token(ch_first)
            and get_name(ch_first) == "LPAR"
            and is_token(ch_last)
            and get_name(ch_last) == "RPAR"
        ):
            trimmed_children = expr.children[1:-1]
        else:
            trimmed_children = expr.children
        assert len(trimmed_children) == 1
        return eval_expr(
            trimmed_children[0],
            datadic,
            loop_vars,
            parse_opts,
            look_up,
            cast_int,
            accept_missing,
        )
