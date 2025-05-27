############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/07
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token


def _has_name(node, name):
    return (isinstance(node, Tree) and node.data == name) or (
        isinstance(node, Token) and node.type == name
    )


class DesiredNumberToken(Token):
    def __new__(cls, valuestr):
        inst = super().__new__(cls, "NUMBER", valuestr)
        return inst


class VariableToken(Token):
    def __new__(cls, node, cpp_namespace=False, inconsistent=False):
        if isinstance(node, VariableToken):
            inst = super().__new__(cls, "VARIABLE", node.value)
            inst.indices = node.indices
            inst.cpp_namespace = cpp_namespace
            inst.inconsistent = inconsistent
            return inst

        if isinstance(node, Token) and node.type in ("VARNAME",):
            inst = super().__new__(cls, "VARIABLE", node.value)
            inst.extvarname = str(node)
            inst.indices = tuple()
            inst.cpp_namespace = cpp_namespace
            inst.inconsistent = inconsistent
            return inst

        if not isinstance(node, Tree) or node.data != "extvarname":
            raise TypeError("expect node type extvarname")

        idxquants = []
        for curnode in node.children:
            if _has_name(curnode, "VARNAME"):
                varname = curnode.value
            elif _has_name(curnode, "indexquant"):
                expr_node = curnode.children[0]
                idxquants.append(expr_node)

        inst = super().__new__(cls, "VARIABLE", varname)
        inst.indices = tuple(idxquants)
        inst.cpp_namespace = cpp_namespace
        inst.inconsistent = inconsistent
        return inst

    def __hash__(self):
        return hash((str(self), len(self.indices), self.cpp_namespace))
