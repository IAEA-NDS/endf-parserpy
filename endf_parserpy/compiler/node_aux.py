############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from typing import Optional, Union
from lark.tree import Tree
from lark.tree import _Leaf_T, Branch, Meta  # for type checking
from lark.lexer import Token
from endf_parserpy.utils.tree_utils import get_name, get_child
from .expr_utils.conversion import convert_to_exprtree
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.node_checks import is_variable
from .expr_utils.equation_utils import solve_equation
from .node_checks import is_expr
from . import endf2cpp_aux as aux


class ParseNode(Tree):

    parent: Union[Tree, None]

    def __init__(
        self,
        data: str,
        children: "List[Branch[_Leaf_T]]",
        meta: Optional[Meta] = None,
        parent: Optional[Tree] = None,
    ):
        super().__init__(data, children, meta)
        self.parent = parent
        self.precode = ""
        self._trackid = id(self)

    def __deepcopy__(self, memo):
        raise NotImplementedError("deepcopy not implemented")

    def copy(self):
        node_copy = super().copy()
        node_copy.parent = self.parent
        node_copy.precode = self.precode
        node_copy._trackid = self._trackid
        return node_copy

    def append_precode(self, code):
        self.precode += code

    def check_my_identity(self):
        if self._trackid != id(self):
            raise TypeError("Damn, I lost my identity!")
        for c in self.children:
            if isinstance(c, ParseNode):
                if c.parent is not self:
                    raise TypeError("My children get my identity wrong")


def node_and_kids_to_ParseNode(node):
    if not isinstance(node, Tree):
        return node
    new_node = ParseNode(node.data, [], node._meta)
    new_children = []
    for c in node.children:
        if type(c) == Tree:
            new_child = ParseNode(c.data, c.children, c._meta, parent=new_node)
        elif type(c) == ParseNode:
            new_child = c
            new_child.parent = new_node
        else:
            new_child = c
        new_children.append(new_child)
    new_node.children = new_children
    return new_node


def simplify_expr_node(node):
    if not is_expr(node):
        return node
    new_node = convert_to_exprtree(node)
    if not is_expr(new_node):
        new_node = Tree("expr", [new_node])
    return new_node


def get_loop_head(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_head")
    elif node_name == "list_loop":
        return get_child(node, "list_for_head")
    elif node_name == "repeat_loop":
        return get_child(node, "repeat_head")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_body")
    elif node_name == "list_loop":
        return get_child(node, "list_body")
    elif node_name == "repeat_loop":
        return get_child(node, "repeat_body")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loopvar(node):
    node = get_loop_head(node)
    if get_name(node) == "repeat_head":
        node = get_child(node, "repeat_varassign")
    return VariableToken(get_child(node, "VARNAME"))


def get_loop_start(node):
    node = get_loop_head(node)
    if get_name(node) == "repeat_head":
        return get_child(get_child(node, "repeat_varassign"), "expr")
    return get_child(get_child(node, "for_start"), "expr")


def get_loop_stop(node):
    node = get_loop_head(node)
    if get_name(node) == "repeat_head":
        return None
    return get_child(get_child(node, "for_stop"), "expr")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "list_loop":
        return get_child(node, "list_body")
    elif node_name == "for_loop":
        return get_child(node, "for_body")
    elif node_name == "repeat_loop":
        return get_child(node, "repeat_body")
    else:
        raise TypeError("not a loop node")
