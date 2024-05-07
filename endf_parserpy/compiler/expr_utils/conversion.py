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
from .tree_walkers import transform_nodes


class VariableToken(Token):
    def __new__(cls, node, cpp_namespace=False, inconsistent=False):
        if isinstance(node, VariableToken):
            inst = super().__new__(cls, "VARIABLE", node.value)
            inst.extvarname = node.extvarname
            inst.indices = node.indices
            inst.cpp_namespace = cpp_namespace
            inst.inconsistent = inconsistent
            return inst

        if isinstance(node, Token) and node.type in ("INDEXVAR", "VARNAME"):
            inst = super().__new__(cls, "VARIABLE", node.value)
            inst.extvarname = str(node)
            inst.indices = tuple()
            inst.cpp_namespace = cpp_namespace
            inst.inconsistent = inconsistent
            return inst

        if not isinstance(node, Tree) or node.data != "extvarname":
            raise TypeError("expect node type extvarname")

        idxquants = []
        all_tokens = node.scan_values(lambda v: isinstance(v, Token))
        for token in all_tokens:
            if token.type == "VARNAME":
                varname = token.value
            elif token.type == "INDEXNUM":
                idxquants.append(Token("NUMBER", token.value))
            elif token.type == "INDEXVAR":
                idxquants.append(VariableToken(token))

        varname_str = varname
        if len(idxquants) > 0:
            varname_str += "[" + ",".join(idxquants) + "]"
        inst = super().__new__(cls, "VARIABLE", varname)
        inst.extvarname = varname_str
        inst.indices = tuple(idxquants)
        inst.cpp_namespace = cpp_namespace
        inst.inconsistent = inconsistent
        return inst

    def __hash__(self):
        return hash((str(self), len(self.indices), self.cpp_namespace))


class DesiredNumberToken(Token):
    def __new__(cls, valuestr):
        inst = super().__new__(cls, "NUMBER", valuestr)
        return inst


def _simplify_token(token):
    if not isinstance(token, Token):
        return token
    if token.type == "DESIRED_NUMBER":
        return Token("NUMBER", token.value.rstrip("?"))
    # hack: VARIABLE is not part of the grammar but is introduced
    #       as a token type in VariableToken, therefore added
    elif token.type in ("VARNAME", "INDEXVAR", "INDEXNUM", "NUMBER", "VARIABLE"):
        return token
    return None


def _simplify_variable(node):
    if not isinstance(node, Tree):
        return node
    if node.data == "extvarname":
        return VariableToken(node)
    return node


def _simplify_tree(node):
    if not isinstance(node, Tree):
        return node
    skip_nodes = ("expr", "addpart", "mulpart", "bracketexpr", "inconsistent_varspec")
    if node.data in skip_nodes:
        assert len(node.children) == 1
        return node.children[0]
    return node


def convert_to_exprtree(tree):
    new_tree = transform_nodes(tree, _simplify_token)
    new_tree = transform_nodes(new_tree, _simplify_tree)
    new_tree = transform_nodes(new_tree, _simplify_variable)
    return new_tree
