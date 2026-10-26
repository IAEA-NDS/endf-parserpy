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

import warnings

from endf_parserpy.recipe_parser import get_recipe_parser as _get_parser
from endf_parserpy.utils.tree_utils import is_tree
from hashlib import md5


def get_string_hash(inpstr):
    return md5(inpstr.encode()).hexdigest()


def _warn_deprecated_cache_args(names):
    warnings.warn(
        f"the argument(s) {', '.join(f'`{n}`' for n in names)} are "
        "deprecated and have no effect: ENDF recipes are parsed when "
        "needed and not cached anymore",
        DeprecationWarning,
        stacklevel=3,
    )


def get_recipe_parser(recipe_grammar=None):
    """Return the parser for ENDF recipes.

    The argument ``recipe_grammar`` is deprecated and ignored; providing
    it emits a ``DeprecationWarning``. The returned object has a
    ``parse`` method that converts a recipe into a parse tree (see
    :mod:`endf_parserpy.recipe_parser`).
    """
    if recipe_grammar is not None:
        _warn_deprecated_cache_args(["recipe_grammar"])
    return _get_parser()


def get_recipe_parsetree(
    recipe, recipe_parser, grammar_hash=None, cache_dir=None, print_cache_info=None
):
    """Return the parse tree of an ENDF recipe.

    The arguments ``grammar_hash``, ``cache_dir`` and ``print_cache_info``
    are deprecated and ignored; providing them emits a
    ``DeprecationWarning``. Parse trees were cached in previous versions
    because parsing recipes was slow; they are now parsed when needed.
    """
    legacy = [
        name
        for name, value in [
            ("grammar_hash", grammar_hash),
            ("cache_dir", cache_dir),
            ("print_cache_info", print_cache_info),
        ]
        if value is not None
    ]
    if legacy:
        _warn_deprecated_cache_args(legacy)
    return recipe_parser.parse(recipe)


def get_recipe_parsetree_dic(recipe_dic, cache_dir=None, print_cache_info=None):
    """Return the parse trees of a (nested) dictionary of recipes.

    The arguments ``cache_dir`` and ``print_cache_info`` are deprecated
    and ignored; providing them emits a ``DeprecationWarning`` (see
    :func:`get_recipe_parsetree`).
    """
    legacy = [
        name
        for name, value in [
            ("cache_dir", cache_dir),
            ("print_cache_info", print_cache_info),
        ]
        if value is not None
    ]
    if legacy:
        _warn_deprecated_cache_args(legacy)
    parser = _get_parser()
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
