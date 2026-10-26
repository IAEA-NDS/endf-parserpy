############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/12/07
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.recipe_parser import get_recipe_parser as _get_parser
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.utils.tree_utils import is_tree
from hashlib import md5


def get_string_hash(inpstr):
    return md5(inpstr.encode()).hexdigest()


def get_recipe_parser(recipe_grammar):
    """Return the parser for ENDF recipes.

    The argument ``recipe_grammar`` is ignored; it is kept for
    compatibility. The returned object has a ``parse`` method that
    converts a recipe into a parse tree (see
    :mod:`endf_parserpy.recipe_parser`).
    """
    return _get_parser()


def get_recipe_parsetree(
    recipe, recipe_parser, grammar_hash, cache_dir, print_cache_info
):
    """Return the parse tree of an ENDF recipe.

    The arguments ``grammar_hash``, ``cache_dir`` and ``print_cache_info``
    are ignored. Parse trees were cached in previous versions because
    parsing recipes was slow; they are now parsed when needed.
    """
    return recipe_parser.parse(recipe)


def get_recipe_parsetree_dic(recipe_dic, cache_dir, print_cache_info):
    """Return the parse trees of a (nested) dictionary of recipes.

    The arguments ``cache_dir`` and ``print_cache_info`` are ignored
    (see :func:`get_recipe_parsetree`).
    """
    parser = get_recipe_parser(endf_recipe_grammar)
    tree_dic = {}
    for mf in recipe_dic:
        tree_dic.setdefault(mf, {})
        if isinstance(recipe_dic[mf], str):
            tree_dic[mf] = parser.parse(recipe_dic[mf])
        else:
            for mt in recipe_dic[mf]:
                tree_dic[mf][mt] = parser.parse(recipe_dic[mf][mt])
    return tree_dic


def get_responsible_recipe_parsetree(tree_dic, mf, mt):
    if mf in tree_dic:
        if is_tree(tree_dic[mf]):
            return tree_dic[mf]
        elif mt in tree_dic[mf] and is_tree(tree_dic[mf][mt]):
            return tree_dic[mf][mt]
        elif (-1) in tree_dic[mf] and is_tree(tree_dic[mf][-1]):
            return tree_dic[mf][-1]
    return None


def get_responsible_recipe_parsefun(parsefun_dic, mf, mt):
    d = parsefun_dic
    if mf in parsefun_dic:
        if callable(d[mf]):
            return d[mf]
        elif mt in d[mf] and callable(d[mf][mt]):
            return d[mf][mt]
        elif (-1) in d[mf] and callable(d[mf][-1]):
            return d[mf][-1]
    return None
