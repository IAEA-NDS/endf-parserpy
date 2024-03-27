############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/03/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from .tree_walkers import transform_nodes
from .node_checks import is_addition, is_multiplication
from .node_trafos import (
    eliminate_subtraction,
    eliminate_minusexpr,
    flatten_multiplication,
    flatten_addition,
    extract_factor,
)
from .tree_trafos import normalize_exprtree, simplify_for_readability


def contains_variable(node, vartok):
    if isinstance(node, Token):
        return node == vartok
    return any(contains_variable(c, vartok) for c in node.children)


def _move_constants_to_rhs(lhs, rhs, vartok):
    if not is_addition(lhs):
        return lhs, rhs
    new_lhs_terms = []
    new_rhs = rhs
    for child in lhs.children:
        if contains_variable(child, vartok):
            new_lhs_terms.append(child)
        else:
            new_rhs = Tree("subtraction", [new_rhs, child])
    if len(new_lhs_terms) == 0:
        new_lhs = Token("NUMBER", "0")
    elif len(new_lhs_terms) == 1:
        new_lhs = new_lhs_terms[0]
    else:
        new_lhs = Tree("addition", new_lhs_terms)
    new_rhs = transform_nodes(new_rhs, eliminate_subtraction)
    new_rhs = transform_nodes(new_rhs, eliminate_minusexpr)
    new_rhs = transform_nodes(new_rhs, flatten_multiplication)
    new_rhs = transform_nodes(new_rhs, flatten_addition)
    return new_lhs, new_rhs


def _move_constfact_to_rhs(lhs, rhs, vartok):
    if not is_multiplication(lhs):
        if lhs == vartok:
            return lhs, rhs
        raise TypeError(f"lhs does not contain {vartok}")

    const_factors = []
    var_factors = []
    for child in lhs.children:
        if not contains_variable(child, vartok):
            const_factors.append(child)
        else:
            var_factors.append(child)

    if len(var_factors) != 1:
        raise TypeError(f"variable {vartok} expected to appear exactly once")
    else:
        rhs_divisor = Tree("multiplication", const_factors)

    new_lhs = var_factors[0]
    new_rhs = Tree("division", [rhs, rhs_divisor])
    return new_lhs, new_rhs


def solve_equation(lhs, rhs, vartok):
    new_lhs = normalize_exprtree(lhs)
    new_rhs = normalize_exprtree(rhs)
    new_lhs, new_rhs = _move_constants_to_rhs(new_lhs, new_rhs, vartok)
    if new_lhs != vartok:
        new_lhs = extract_factor(new_lhs, vartok)
    new_lhs, new_rhs = _move_constfact_to_rhs(new_lhs, new_rhs, vartok)
    new_lhs = simplify_for_readability(new_lhs)
    new_rhs = simplify_for_readability(new_rhs)
    return new_lhs, new_rhs
