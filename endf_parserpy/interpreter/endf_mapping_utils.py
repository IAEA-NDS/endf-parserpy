############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
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
    math_mul,
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
from fractions import Fraction
from endf_parserpy.utils.math_utils import EndfFloat, math_op
from endf_parserpy.utils.debugging_utils import TrackingDict


# Arithmetic of ENDF recipe expressions
#
# Expressions are evaluated exactly: integers and decimal literals are
# exact numbers, and a division of exact numbers gives an exact fraction
# (fractions.Fraction), e.g. 13/6. Only where an integer is needed (an
# integer field, a loop bound, an index) must the value be an integer.
# Values of float fields are floats (inexact); arithmetic with a float
# gives a float. The code generated for EndfParserCpp follows the same
# rules (see `cpp_templates/endf_rational.hpp`).


def _normalize(x):
    # a fraction that is an integer is represented as int
    if isinstance(x, Fraction) and x.denominator == 1:
        return x.numerator
    return x


def _is_exact(x):
    return isinstance(x, (int, Fraction)) and not isinstance(x, bool)


def _arith_number(x):
    # values of float fields (also EndfFloat) enter arithmetic as floats
    if isinstance(x, EndfFloat):
        return float(x)
    return x


def _scalar_div(x, y):
    x, y = _arith_number(x), _arith_number(y)
    if _is_exact(x) and _is_exact(y):
        return _normalize(Fraction(x) / Fraction(y))
    return x / y


def exact_div(x, y):
    return math_op(x, y, _scalar_div)


def exact_mod(x, y):
    return math_op(x, y, lambda a, b: _normalize(_arith_number(a) % _arith_number(b)))


def exact_op(x, y, op):
    return math_op(
        x, y, lambda a, b: _normalize(op(_arith_number(a), _arith_number(b)))
    )


def to_plain_number(x):
    """Convert an exact fraction to int (if integral) or float.

    Used for values leaving the expression evaluation, e.g. for writing
    a field. A non-integral fraction for an integer field then raises
    the usual error of the writer.
    """
    if isinstance(x, Fraction):
        x = _normalize(x)
        return float(x) if isinstance(x, Fraction) else x
    if isinstance(x, (list, tuple)) and any(isinstance(z, Fraction) for z in x):
        return type(x)(to_plain_number(z) for z in x)
    return x


def comparable_values(x, y):
    """Make two values comparable in the sense of the recipe language.

    A fraction compared with a float is converted to a float (Python
    would otherwise compare the exact value of the float).
    """

    def conv(a, other):
        if isinstance(a, Fraction) and not _is_exact(_arith_number(other)):
            return float(a)
        return a

    if hasattr(x, "__iter__") or hasattr(y, "__iter__"):
        return x, y
    return conv(x, y), conv(y, x)


def to_integer_solution(val, cast_int):
    """Convert the solution of an equation for an integer variable."""
    val = _normalize(val)
    if isinstance(val, int):
        return val
    if isinstance(val, Fraction):
        if cast_int:
            raise InvalidIntegerError(
                f"the solution {val} of the equation for an integer "
                + "variable is not an integer"
            )
        return float(val)
    rounded = round(val)
    if abs(val - rounded) <= max(1e-6, 1e-12 * abs(val)):
        return int(rounded)
    if cast_int:
        raise InvalidIntegerError(
            f"the solution {val} of the equation for an integer "
            + "variable is not an integer"
        )
    return val


# Results of the analysis of recipe tree nodes that depend only on the
# node itself (recipe trees are never modified) are computed once and
# stored in the node (Tree objects) or, for tokens, which do not accept
# new attributes, in dictionaries keyed by token type and value.
_token_literal_values = {}
_token_number_values = {}


def _decimal_literal_value(expr):
    # exact value of a literal (possibly negated or in brackets),
    # e.g. 0.1 is 1/10; None if expr is not a literal
    t = type(expr)
    if t is Tree:
        try:
            return expr._decimal_literal_value
        except AttributeError:
            pass
        value = _decimal_literal_value_uncached(expr)
        expr._decimal_literal_value = value
        return value
    elif t is Token:
        key = (expr.type, expr.value)
        try:
            return _token_literal_values[key]
        except KeyError:
            pass
        value = _decimal_literal_value_uncached(expr)
        _token_literal_values[key] = value
        return value
    return _decimal_literal_value_uncached(expr)


def _decimal_literal_value_uncached(expr):
    sign = 1
    while True:
        name = get_name(expr, nofail=True)
        if name in ("NUMBER", "DESIRED_NUMBER"):
            vstr = expr.value.rstrip("?").strip()
            return sign * _normalize(Fraction(vstr))
        if name == "minusexpr":
            sign = -sign
            expr = expr.children[1]
            continue
        if is_tree(expr):
            children = [
                c
                for c in expr.children
                if not (is_token(c) and get_name(c) in ("LPAR", "RPAR"))
            ]
            if len(children) == 1:
                expr = children[0]
                continue
        return None


def _arith_operand(expr, value):
    # value of an operand of an arithmetic operation, see the notes above
    literal = _decimal_literal_value(expr)
    if literal is not None:
        return (literal, 0, None)
    return (math_op(value[0], 0, lambda a, b: _arith_number(a)), value[1], value[2])


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


# Mapping types for which `idx in d` followed by `d[idx]` is equivalent to
# `d[idx]` raising KeyError for a missing key (also with respect to the
# recording of the access in TrackingDict and LookaheadDict objects).
_single_lookup_types = {dict, TrackingDict}


def _get_array_value_in_dict_mode(varname, array_cont, idcs, raise_if_missing):
    curdic = array_cont
    for idx in idcs:
        if type(curdic) in _single_lookup_types:
            # same as the general case below with a single lookup
            try:
                curdic = curdic[idx]
                continue
            except KeyError:
                pass
            if not raise_if_missing:
                return None
            raise UnavailableIndexError(
                f"index {idx} does not exist in array {varname}"
            )
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
    if type(expr) is Token and expr.type == "VARNAME":
        varname = expr.value
        idxquants = None
    else:
        try:
            varname, idxquants = expr._varname_and_indexquants
        except AttributeError:
            varname_or_extvarname_check(expr)
            varname = get_varname(expr)
            idxquants = get_indexquants(expr)
            expr._varname_and_indexquants = (varname, idxquants)

    # the membership test `varname in datadic` is done once per dictionary
    in_datadic = None
    if loop_vars is not None:
        in_datadic = varname in datadic
        if in_datadic and varname in loop_vars:
            raise LoopVariableError(
                f"the variable {varname} is both a loop variable and "
                "a record variable, which is forbidden, check the recipe"
            )
        if varname in loop_vars:
            return loop_vars[varname]

    orig_datadic = datadic
    if in_datadic is None:
        in_datadic = varname in datadic
    while not in_datadic and "__up" in datadic and look_up:
        datadic = datadic["__up"]
        in_datadic = varname in datadic
    if not in_datadic:
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
    t = type(expr)
    if t is Tree:
        try:
            return expr._varname
        except AttributeError:
            pass
        varname = None
        for ch in expr.children:
            varname = get_varname(ch)
            if varname is not None:
                break
        expr._varname = varname
        return varname
    elif t is Token:
        if get_name(expr) == "VARNAME":
            return get_value(expr)
    return None


def get_indexquants(expr):
    if not is_tree(expr):
        return None
    try:
        return expr._indexquants
    except AttributeError:
        pass
    idxquants = _get_indexquants_uncached(expr)
    expr._indexquants = idxquants
    return idxquants


def _get_indexquants_uncached(expr):
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
        # The solution is computed exactly. Solved from an integer field,
        # the variable is an integer; cast_int false (within a lookahead)
        # means that a solution that is not an integer is accepted.
        res = exact_div(exact_op(val, vv[0], lambda a, b: a - b), vv[1])
        if isinstance(val, int):
            return to_integer_solution(res, cast_int)
        return to_plain_number(res)
    else:
        return math_add(vv[0], math_mul(val, vv[1]))


_EVAL_EXPR_NODE_NAMES = (
    "VARNAME",
    "extvarname",
    "NUMBER",
    "DESIRED_NUMBER",
    "minusexpr",
    "addition",
    "subtraction",
    "multiplication",
    "modulo",
    "division",
    "inconsistent_varspec",
)


def _get_eval_target(tree):
    # Follow the nodes that eval_expr passes on to their single child
    # (last branch of eval_expr) and store the node reached in the tree.
    target = tree
    while type(target) is Tree and get_name(target) not in _EVAL_EXPR_NODE_NAMES:
        ch_first = target.children[0]
        ch_last = target.children[-1]
        if (
            is_token(ch_first)
            and get_name(ch_first) == "LPAR"
            and is_token(ch_last)
            and get_name(ch_last) == "RPAR"
        ):
            trimmed_children = target.children[1:-1]
        else:
            trimmed_children = target.children
        assert len(trimmed_children) == 1
        target = trimmed_children[0]
    tree._eval_target = target
    return target


def _eval_number_token(expr):
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
    t = type(expr)
    if t is Tree:
        # skip nodes that only enclose a single expression (e.g. in brackets)
        try:
            expr = expr._eval_target
        except AttributeError:
            expr = _get_eval_target(expr)
        t = type(expr)
    if t is Token:
        name = str(expr.type)
    elif t is Tree:
        name = str(expr.data)
    else:
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
        key = (name, expr.value)
        try:
            return _token_number_values[key]
        except KeyError:
            pass
        value = _eval_number_token(expr)
        _token_number_values[key] = value
        return value
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
        v = _arith_operand(expr.children[1], v)
        return (exact_op(v[0], -1, lambda a, b: a * b), _normalize(-v[1]), v[2])
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
        v1 = _arith_operand(expr.children[0], v1)
        v2 = _arith_operand(expr.children[2], v2)
        if name == "multiplication":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variables must not appear "
                    + "in an expression."
                )
            mul = lambda a, b: a * b
            if v1[1] == 0:
                return (exact_op(v1[0], v2[0], mul), exact_op(v1[0], v2[1], mul), v2[2])
            else:
                return (exact_op(v1[0], v2[0], mul), exact_op(v1[1], v2[0], mul), v1[2])
        elif name == "division":
            if v2[1] != 0:
                raise VariableInDenominatorError(
                    "A variable name must not appear in the denominator "
                    + "of an expression."
                )
            # exact fractions instead of the requirement that a division
            # of integers be exact, see the notes on the arithmetic above
            vx = exact_div(v1[0], v2[0])
            vy = exact_div(v1[1], v2[0])
            return (vx, vy, v1[2])
        elif name == "modulo":
            if v1[1] != 0 or v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "Both x and y in the operation x % y (modulo) "
                    + "must be known values. However, unbound variables"
                    + "are present in the expressions corresponding to x or y."
                )
            vx = exact_mod(v1[0], v2[0])
            return (vx, 0, None)
        elif name == "addition":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variable must not appear "
                    + "in an expression."
                )
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            add = lambda a, b: a + b
            return (exact_op(v1[0], v2[0], add), exact_op(v1[1], v2[1], add), vexpr)
        elif name == "subtraction":
            if v1[1] != 0 and v2[1] != 0:
                raise SeveralUnboundVariablesError(
                    "More than one unassigned variable must not appear "
                    + "in an expression."
                )
            vexpr = v1[2] if v1[1] != 0 else v2[2]
            sub = lambda a, b: a - b
            return (exact_op(v1[0], v2[0], sub), exact_op(v1[1], v2[1], sub), vexpr)
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
