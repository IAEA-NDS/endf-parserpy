############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# Variants of functions in endf_parserpy.utils.tree_utils for the
# recipe trees interpreted by EndfParserPy. Their results depend only
# on the tree node, and recipe trees are never modified, so each result
# is computed once and stored in the tree node.

from lark.tree import Tree
from endf_parserpy.utils.tree_utils import (
    reconstruct_tree_str as _reconstruct_tree_str_uncached,
    get_name,
    is_tree,
)


def reconstruct_tree_str(tree):
    """Same as tree_utils.reconstruct_tree_str."""
    if type(tree) == Tree:
        try:
            return tree._reconstructed_str
        except AttributeError:
            pass
        curstr = ""
        for child in tree.children:
            curstr += reconstruct_tree_str(child)
            curstr += " "
        curstr = curstr[:-1]
        tree._reconstructed_str = curstr
        return curstr
    return _reconstruct_tree_str_uncached(tree)


def search_name(tree, name):
    """Same as tree_utils.search_name."""
    if type(tree) == Tree:
        try:
            cache = tree._search_name_results
        except AttributeError:
            cache = tree._search_name_results = {}
        try:
            return cache[name]
        except KeyError:
            pass
        found = _search_name_uncached(tree, name)
        cache[name] = found
        return found
    return _search_name_uncached(tree, name)


def _search_name_uncached(tree, name):
    if get_name(tree, nofail=True) == name:
        return True
    elif is_tree(tree):
        for curchild in tree.children:
            if search_name(curchild, name):
                return True
    return False
