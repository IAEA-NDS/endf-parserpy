############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/12/07
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token


def is_token(tree):
    return type(tree) == Token


def is_tree(tree):
    return type(tree) == Tree


def get_name(tree, nofail=False):
    if type(tree) == Token:
        return str(tree.type)
    elif type(tree) == Tree:
        return str(tree.data)
    # instance check slower but kept for dealing OOP inheritance
    elif isinstance(tree, Tree):
        return str(tree.data)
    else:
        if nofail:
            return None
        else:
            raise TypeError(
                f"argument should have type Token or Tree " f"but has type {type(tree)}"
            )


def get_value(token):
    return token.value


def get_child_names(tree):
    return list(get_name(t) for t in tree.children)


def get_child(tree, name, nofail=False, idx=None):
    idx = 0 if idx is None else idx
    curidx = 0
    for child in tree.children:
        if get_name(child) == name:
            if idx == curidx:
                return child
            curidx += 1
    if nofail:
        return None
    else:
        raise IndexError(f"name {name} not found among child nodes")


def get_child_value(tree, name):
    for child in tree.children:
        if is_token(child):
            if get_name(child) == name:
                return child.value
    raise IndexError(f"child with name {name} not found")


def get_child_value_by_pos(tree, pos):
    ch = tree.children
    if pos >= 0 and pos < len(ch):
        if is_token(ch[pos]):
            return str(ch[pos])
    return None


def search_name(tree, name):
    if get_name(tree, nofail=True) == name:
        return True
    elif is_tree(tree):
        for curchild in tree.children:
            if search_name(curchild, name):
                return True
    return False


def retrieve_value(tree, name):
    if is_token(tree) and get_name(tree) == name:
        return get_value(tree)
    elif is_tree(tree):
        for child in tree.children:
            ret = retrieve_value(child, name)
            if ret is not None:
                return ret
    return None


def reconstruct_tree_str(tree):
    if type(tree) == Tree:
        curstr = ""
        for child in tree.children:
            curstr += reconstruct_tree_str(child)
            curstr += " "
        curstr = curstr[:-1]
        return curstr
    elif type(tree) == Token:
        return tree.value
    else:
        raise TypeError("neither token nor tree, what nightmare for a bee!")
