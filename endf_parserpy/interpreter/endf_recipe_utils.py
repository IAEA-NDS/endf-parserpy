############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/12/07
# Last modified:   2025/05/31
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark import Lark
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.utils.tree_utils import is_tree
import importlib.resources
from platformdirs import user_cache_dir
from hashlib import md5
import os
import pickle


DISPLAYED_CACHE_INFO = False
RECIPE_CACHE_PKG = "endf_parserpy.endf_recipes.recipe_cache"


def get_string_hash(inpstr):
    return md5(inpstr.encode()).hexdigest()


def get_recipe_parser(recipe_grammar):
    return Lark(recipe_grammar, start="endf_recipe", keep_all_tokens=True)


def get_recipe_parsetree(
    recipe, recipe_parser, grammar_hash, cache_dir, print_cache_info
):
    recipe_hash = get_string_hash(recipe)
    filename = get_string_hash(grammar_hash + recipe_hash) + ".pkl"

    # try to retrieve compiled recipe from recipe cache
    # populated during package installation (see build.py)
    if importlib.resources.is_resource(RECIPE_CACHE_PKG, filename):
        with importlib.resources.open_binary(RECIPE_CACHE_PKG, filename) as f:
            recipe_parsetree = pickle.load(f)
            return recipe_parsetree

    if cache_dir is False:
        return recipe_parser.parse(recipe)

    if cache_dir is None:
        cache_dir = user_cache_dir("endf_parserpy", "gschnabel")
        global DISPLAYED_CACHE_INFO
        if print_cache_info and not DISPLAYED_CACHE_INFO:
            print(
                f"Compiled ENDF recipes are cached in {cache_dir}\n"
                + "Specify `cache_dir=False` to disable the creation "
                + "and use of a cache directory.\n"
                + "Alternatively, pass a path as `cache_dir` argument.\n"
                + "To suppress this message, specify `print_cache_info=False`."
            )
            DISPLAYED_CACHE_INFO = True

    filepath = os.path.join(cache_dir, filename)
    if not os.path.exists(filepath):
        os.makedirs(cache_dir, exist_ok=True)
        recipe_parsetree = recipe_parser.parse(recipe)
        with open(filepath, "wb") as fw:
            pickle.dump(recipe_parsetree, fw, protocol=4)
    else:
        with open(filepath, "rb") as fr:
            recipe_parsetree = pickle.load(fr)
    return recipe_parsetree


def get_recipe_parsetree_dic(recipe_dic, cache_dir, print_cache_info):
    recipe_parser = get_recipe_parser(endf_recipe_grammar)
    grammar_hash = get_string_hash(endf_recipe_grammar)
    tree_dic = {}
    for mf in recipe_dic:
        tree_dic.setdefault(mf, {})
        if isinstance(recipe_dic[mf], str):
            tree_dic[mf] = get_recipe_parsetree(
                recipe_dic[mf], recipe_parser, grammar_hash, cache_dir, print_cache_info
            )
        else:
            for mt in recipe_dic[mf]:
                tree_dic[mf][mt] = get_recipe_parsetree(
                    recipe_dic[mf][mt],
                    recipe_parser,
                    grammar_hash,
                    cache_dir,
                    print_cache_info,
                )
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
