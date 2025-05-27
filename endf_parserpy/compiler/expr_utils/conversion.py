############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from .tree_walkers import transform_nodes
from .custom_nodes import (
    VariableToken,
    DesiredNumberToken,
)


def _simplify_token(token):
    if not isinstance(token, Token):
        return token
    if token.type == "DESIRED_NUMBER":
        return DesiredNumberToken(token.value.rstrip("?"))
    # hack: VARIABLE is not part of the grammar but is introduced
    #       as a token type in VariableToken, therefore added
    elif token.type in ("VARNAME", "NUMBER", "VARIABLE"):
        return token
    return None


def _simplify_variable(node):
    if not isinstance(node, Tree):
        return node
    if node.data == "extvarname":
        return VariableToken(node)
    elif node.data == "inconsistent_varspec":
        # due to bottom-up conversion by transform_nodes
        # we expect here a VariableToken
        child = node.children[0]
        assert isinstance(child, VariableToken)
        return VariableToken(
            child, cpp_namespace=child.cpp_namespace, inconsistent=True
        )
    return node


def _simplify_tree(node):
    if not isinstance(node, Tree):
        return node
    skip_nodes = ("expr", "addpart", "mulpart", "bracketexpr")
    if node.data in skip_nodes:
        assert len(node.children) == 1
        return node.children[0]
    return node


def convert_to_exprtree(tree):
    new_tree = transform_nodes(tree, _simplify_token)
    new_tree = transform_nodes(new_tree, _simplify_tree)
    new_tree = transform_nodes(new_tree, _simplify_variable)
    return new_tree
