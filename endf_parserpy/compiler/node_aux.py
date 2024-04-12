############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from .expr_utils.node_trafos import node2str
from .expr_utils.conversion import convert_to_exprtree, VariableToken
from .expr_utils.node_checks import is_variable
from .expr_utils.equation_utils import solve_equation
from .node_checks import is_expr
from . import endf2cpp_aux as aux


def simplify_expr_node(node):
    if not is_expr(node):
        return node
    new_node = convert_to_exprtree(node)
    if not is_expr(new_node):
        new_node = Tree("expr", [new_node])
    return new_node


def get_varassign_from_expr(vartok, node, vardict):
    if is_expr(node):
        node = node.children[0]
    elif not isinstance(node, VariableToken):
        raise TypeError("expect `expr` node or VariableToken")
    lhs = node
    rhs = Token("VARIABLE", "cpp_val")
    vartok, expr = solve_equation(lhs, rhs, vartok)
    return vartok, expr


def get_variables_in_expr(node):
    if is_variable(node):
        return set((node,))
    varset = set()
    if isinstance(node, Tree):
        for child in node.children:
            curset = get_variables_in_expr(child)
            varset.update(curset)
    return varset


def logical_expr2cppstr(node, vardict):
    if isinstance(node, VariableToken):
        return aux.get_cpp_extvarname(node, vardict)
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


def expr2str_shiftidx(node, vardict, rawvars=False):
    if not isinstance(node, VariableToken):
        return node2str(node)
    if rawvars in (True, False):
        use_cpp_name = not rawvars
    else:
        use_cpp_name = node not in rawvars
    if use_cpp_name:
        varname = aux.get_cpp_extvarname(node, vardict)
    else:
        varname = str(node)
    return varname
