############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2026/10/13
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from lark.lexer import Token
from lark.tree import Tree
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.node_trafos import (
    node2cppstr,
    cpp_operand,
    CppFloatValue,
)
from endf_parserpy.compiler.expr_utils.node_checks import (
    is_number,
    is_expr,
    is_minusexpr,
)
from endf_parserpy.compiler.expr_utils.tree_walkers import transform_nodes
from endf_parserpy.compiler.expr_utils.equation_utils import get_variables_in_expr
from endf_parserpy.compiler.node_checks import is_if_condition
from endf_parserpy.compiler.expr_utils.exceptions import VariableMissingError
from endf_parserpy.compiler.variable_management import find_parent_dict
import endf_parserpy.compiler.cpp_primitives as cpp
from .cpp_varaux import get_cpp_varname
from .cpp_type_information import (
    get_query_modules,
    get_assign_modules,
    get_vartype_modules,
)


def need_read_check(vartok, vardict, indices=None):
    if find_parent_dict(vartok, vardict) is None:
        return False
    if vartok.cpp_namespace is True:
        return False
    return True


def did_read_var(vartok, vardict, indices=None):
    if vartok.cpp_namespace is True:
        raise NotImplementedError(
            "read tracking not enabled for variables in cpp_namespace"
        )
    pardict = find_parent_dict(vartok, vardict)
    if pardict is None:
        return "false"
    idxstrs = None
    if indices is not None:
        idxstrs = []
        for i, idxtok in enumerate(vartok.indices):
            idxstrs.append(get_idxstr(vartok, i, vardict))
    for query in get_query_modules():
        if query.is_responsible(vartok, vardict):
            return query.did_read_var(vartok, vardict, idxstrs)
    raise TypeError(f"{vartok} has unknown type")


def get_cpp_extvarname(vartok, vardict, vartypes=None):
    vartypes = {} if vartypes is None else vartypes
    if find_parent_dict(vartok, vardict) is None:
        raise VariableMissingError(f"variable {vartok} missing/not encountered")
    vartype = vartypes.get(vartok, (None, None))
    dtype = vartype[0]
    specialtype = vartype[1]
    varname = get_cpp_varname(vartok, vardict, specialtype=specialtype, dtype=dtype)
    idxstrs = []
    for i, idxtok in enumerate(vartok.indices):
        idxstrs.append(get_idxstr(vartok, i, vardict, vartypes))
    for query in get_query_modules():
        if query.is_responsible(vartok, vardict):
            return query.assemble_extvarname(varname, idxstrs)
    raise TypeError(f"{vartok} has unknown datatype")


def get_cpp_objstr(tok, vardict, vartypes=None):
    vartypes = {} if vartypes is None else vartypes
    if isinstance(tok, VariableToken):
        return get_cpp_extvarname(tok, vardict, vartypes)
    elif is_number(tok):
        varname = str(tok)
        return varname
    raise NotImplementedError("evil programmer, what did you do?")


def get_idxstr(vartok, i, vardict, vartypes=None):
    vartypes = {} if vartypes is None else vartypes
    idxtok = vartok.indices[i]
    cpp_idxstr = transform_nodes(idxtok, expr2str_shiftidx, vardict, vartypes=vartypes)
    return cpp_idxstr


def _mark_float_value(varname):
    # values of float fields are of type EndfFloatCpp, see `cpp_operand`
    if _FLOAT_VARNAME.match(varname):
        return CppFloatValue(varname)
    return varname


_FLOAT_VARNAME = re.compile(r"^var_.+_[0-9]+d_double_")


def _contains_arithmetic(node):
    if isinstance(node, Tree):
        if node.data in _BINARY_OPERATORS:
            return True
        return any(_contains_arithmetic(c) for c in node.children)
    return False


def logical_expr2cppstr(node, vardict):
    if isinstance(node, VariableToken):
        return _mark_float_value(get_cpp_extvarname(node, vardict))
    elif is_minusexpr(node):
        # we assume that convert_to_expr_tree has been applied
        # and hence the "-" sign removed from the children of the minusexpr node
        child = node.children[0]
        return "-(" + logical_expr2cppstr(child, vardict) + ")"
    elif is_if_condition(node):
        # special treatment: if variables missing/not read,
        # logical condition should evaluate to false
        # reminder: if_condition: expr RELATION expr
        relation = node.children[1]
        expr1 = node.children[0]
        expr2 = node.children[2]
        assert is_expr(expr1)
        assert is_expr(expr2)
        # the variables on both sides of the relation must have been read
        vs = get_variables_in_expr(expr1)
        vs.update(get_variables_in_expr(expr2))
        # sorting for deterministic code generation
        vs = sorted(vs)
        lhs = logical_expr2cppstr(expr1, vardict)
        rhs = logical_expr2cppstr(expr2, vardict)
        if _contains_arithmetic(expr1) or _contains_arithmetic(expr2):
            # the result of arithmetic may be an exact fraction, which is
            # compared with a double, an int or another fraction
            lhs, rhs = cpp_operand(lhs), cpp_operand(rhs)
        raw_logical_expr = "(" + "".join([lhs, str(relation), rhs]) + ")"
        var_checks = []
        for v in vs:
            indices = [get_idxstr(v, i, vardict) for i in range(len(v.indices))]
            var_checks.append(did_read_var(v, vardict, indices))
        if len(var_checks) == 0:
            # comparison of constants, e.g. `0 == 1`
            return raw_logical_expr
        var_checks_expr = cpp.logical_and(var_checks)
        composite_check = cpp.logical_and([var_checks_expr, raw_logical_expr])
        return composite_check
    elif isinstance(node, Token):
        if node == "and":
            return "&&"
        elif node == "or":
            return "||"
        else:
            return str(node)
    elif isinstance(node, Tree) and node.data in _BINARY_OPERATORS:
        # the operator symbol is not necessarily retained as a child
        # in the parse tree, hence the operator is inferred from the
        # node type and the operands are the non-symbol children
        operands = [
            cpp_operand(logical_expr2cppstr(c, vardict))
            for c in node.children
            if not (isinstance(c, Token) and c in _OPERATOR_SYMBOLS)
        ]
        assert len(operands) == 2
        op = _BINARY_OPERATORS[node.data]
        if op in ("/", "%"):
            func = "cpp_div" if op == "/" else "cpp_mod"
            return f"{func}({operands[0]}, {operands[1]})"
        return "(" + op.join(operands) + ")"
    elif isinstance(node, Tree):
        parts = [logical_expr2cppstr(c, vardict) for c in node.children]
        code = "(" + "".join(parts) + ")"
        if len(parts) == 1 and isinstance(parts[0], CppFloatValue):
            return CppFloatValue(code)
        return code
    raise NotImplementedError("should not happen")


_BINARY_OPERATORS = {
    "addition": "+",
    "subtraction": "-",
    "multiplication": "*",
    "division": "/",
    "modulo": "%",
}

_OPERATOR_SYMBOLS = tuple(_BINARY_OPERATORS.values())


def expr2str_shiftidx(node, vardict, rawvars=False, vartypes=None):
    vartypes = {} if vartypes is None else vartypes
    if not isinstance(node, VariableToken):
        return node2cppstr(node)
    if rawvars in (True, False):
        use_cpp_name = not rawvars
    else:
        use_cpp_name = node not in rawvars
    if use_cpp_name:
        varname = _mark_float_value(get_cpp_extvarname(node, vardict, vartypes))
    elif str(node) == "cpp_float_val":
        # field value from which a float variable is solved
        varname = CppFloatValue(str(node))
    else:
        varname = str(node)
    return varname
