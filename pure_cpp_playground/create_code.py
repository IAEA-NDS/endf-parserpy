import sys

sys.path.insert(0, "..")
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.compiler.compiler import create_cpp_parser_module


recipes = get_recipe_dict("endf6-ext")
create_cpp_parser_module("parser.cpp", "pymodule", overwrite=True)
