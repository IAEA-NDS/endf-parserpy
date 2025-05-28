############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.lexer import Token
from lark.tree import Tree
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.node_trafos import node2str
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


def logical_expr2cppstr(node, vardict):
    if isinstance(node, VariableToken):
        return get_cpp_extvarname(node, vardict)
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
        vs = get_variables_in_expr(expr1)
        vs.update(get_variables_in_expr(expr1))
        # sorting for deterministic code generation
        vs = sorted(vs)
        raw_logical_expr = (
            "("
            + "".join(
                [
                    logical_expr2cppstr(expr1, vardict),
                    str(relation),
                    logical_expr2cppstr(expr2, vardict),
                ]
            )
            + ")"
        )
        var_checks = []
        for v in vs:
            indices = [get_idxstr(v, i, vardict) for i in range(len(v.indices))]
            var_checks.append(did_read_var(v, vardict, indices))
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
    elif isinstance(node, Tree):
        return (
            "(" + "".join(logical_expr2cppstr(c, vardict) for c in node.children) + ")"
        )
    raise NotImplementedError("should not happen")


def expr2str_shiftidx(node, vardict, rawvars=False, vartypes=None):
    vartypes = {} if vartypes is None else vartypes
    if not isinstance(node, VariableToken):
        return node2str(node)
    if rawvars in (True, False):
        use_cpp_name = not rawvars
    else:
        use_cpp_name = node not in rawvars
    if use_cpp_name:
        varname = get_cpp_extvarname(node, vardict, vartypes)
    else:
        varname = str(node)
    return varname
