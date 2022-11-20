from lark import Lark
from .endf_lark import endf_recipe_grammar
from .endf_recipes import endf_recipe_dictionary as recipe_dic


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
