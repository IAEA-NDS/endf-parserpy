from .endf6_ext import endf_recipe_dictionary as endf6_ext_recipes
from .endf6 import endf_recipe_dictionary as endf6_recipes
from .jendl import endf_recipe_dictionary as jendl_recipes
from .pendf import endf_recipe_dictionary as pendf_recipes
from .errorr import endf_recipe_dictionary as errorr_recipes
from .test import endf_recipe_dictionary as test_recipes


_FORMAT_DICT = {
    "endf6-ext": endf6_ext_recipes,
    "endf6": endf6_recipes,
    "jendl": jendl_recipes,
    "pendf": pendf_recipes,
    "errorr": errorr_recipes,
    "test": test_recipes,
}


def get_recipe_dict(format_spec):
    if format_spec not in _FORMAT_DICT:
        raise TypeError(
            f"There isn't any format specification "
            + "associated with the name `{format_spec}`"
        )
    return _FORMAT_DICT[format_spec]


def list_endf_flavors():
    return tuple(_FORMAT_DICT.keys())
