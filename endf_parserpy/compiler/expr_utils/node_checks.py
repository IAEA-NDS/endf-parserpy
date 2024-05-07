############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/07
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from .custom_nodes import DesiredNumberToken


def is_expr(node):
    return isinstance(node, Tree) and node.data == "expr"


def is_addition(node):
    return isinstance(node, Tree) and node.data == "addition"


def is_subtraction(node):
    return isinstance(node, Tree) and node.data == "subtraction"


def is_multiplication(node):
    return isinstance(node, Tree) and node.data == "multiplication"


def is_division(node):
    return isinstance(node, Tree) and node.data == "division"


def is_modulo(node):
    return isinstance(node, Tree) and node.data == "modulo"


def is_minusexpr(node):
    return isinstance(node, Tree) and node.data == "minusexpr"


def is_number(node):
    return isinstance(node, Token) and node.type == "NUMBER"


def is_variable(node):
    return isinstance(node, Token) and node.type == "VARIABLE"


def has_factor(node, factor):
    if is_multiplication(node):
        return factor in node.children
    return node == factor


def is_desired_number(node):
    return isinstance(node, DesiredNumberToken)


def is_inconsistent_variable(node):
    return is_variable(node) and node.inconsistent
