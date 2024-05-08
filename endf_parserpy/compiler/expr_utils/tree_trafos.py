############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/08
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from .tree_walkers import transform_nodes

from .node_checks import is_modulo, is_expr
from .node_trafos import (
    eliminate_subtraction,
    eliminate_minusexpr,
    factorout_division,
    flatten_multiplication,
    flatten_addition,
    expand_product,
    factorout_common,
    evaluate_int_ops,
    node_contains_variable,
    node_contains_desired_number,
    node_contains_potentially_inconsistent_variable,
    node2str,
)


def normalize_exprtree(tree):
    new_tree = transform_nodes(tree, eliminate_subtraction)
    new_tree = transform_nodes(new_tree, eliminate_minusexpr)
    new_tree = transform_nodes(new_tree, factorout_division)
    new_tree = transform_nodes(new_tree, flatten_multiplication)
    new_tree = transform_nodes(new_tree, flatten_addition)
    new_tree = transform_nodes(new_tree, expand_product)
    new_tree = transform_nodes(new_tree, flatten_addition)
    return new_tree


def simplify_for_readability(tree):
    new_tree = transform_nodes(tree, factorout_common)
    new_tree = transform_nodes(new_tree, flatten_multiplication)
    new_tree = transform_nodes(new_tree, flatten_addition)
    new_tree = transform_nodes(new_tree, evaluate_int_ops)
    return new_tree


def contains_desired_number(tree):
    return transform_nodes(tree, node_contains_desired_number)


def contains_potentially_inconsistent_variable(tree):
    return transform_nodes(tree, node_contains_potentially_inconsistent_variable)


def contains_variables(tree):
    return transform_nodes(tree, node_contains_variable)


def reconstruct_endf_line_template(tree):
    if is_expr(tree):
        return transform_nodes(tree, node2str)
    elif isinstance(tree, Tree):
        curstr = ""
        for child in tree.children:
            curstr += reconstruct_endf_line_template(child)
            curstr += " "
        curstr = curstr[:-1]
        return curstr
    elif isinstance(tree, Token):
        return tree.value
    else:
        raise TypeError("neither token nor tree, what nightmare for a bee!")
