from lark import Lark
from .endf_lark import endf_recipe_grammar
from .endf_recipes import endf_recipe_dictionary as recipe_dic
from .tree_utils import is_tree


def get_recipe_parser(recipe_grammar):
    return Lark(recipe_grammar, start='code_token',
                keep_all_tokens=True)


def get_recipe_parsetree(recipe, recipe_parser):
    return recipe_parser.parse(recipe)


def get_recipe_parsetree_dic():
    recipe_parser = get_recipe_parser(endf_recipe_grammar)
    tree_dic = {}
    for mf in recipe_dic:
        tree_dic.setdefault(mf, {})
        if isinstance(recipe_dic[mf], str):
            tree_dic[mf] = get_recipe_parsetree(recipe_dic[mf], recipe_parser)
        else:
            for mt in recipe_dic[mf]:
                tree_dic[mf][mt] = \
                        get_recipe_parsetree(recipe_dic[mf][mt], recipe_parser)
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
