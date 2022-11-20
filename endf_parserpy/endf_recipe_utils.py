from lark import Lark
from .endf_lark import endf_recipe_grammar
from .endf_recipes import endf_recipe_dictionary as recipe_dic
from .tree_utils import is_tree


def get_recipe_parsetree_dic():
    endf_recipe_grammar_parser = Lark(endf_recipe_grammar, start='code_token',
                                      keep_all_tokens=True)
    tree_dic = {}
    for mf in recipe_dic:
        tree_dic.setdefault(mf, {})
        if isinstance(recipe_dic[mf], str):
            tree_dic[mf] = endf_recipe_grammar_parser.parse(recipe_dic[mf])
        else:
            for mt in recipe_dic[mf]:
                tree_dic[mf][mt] = \
                        endf_recipe_grammar_parser.parse(recipe_dic[mf][mt])

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
