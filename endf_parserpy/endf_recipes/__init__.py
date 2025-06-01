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


def _populate_recipe_cache(clear_dir=False):
    """Populate the recipe_cache folder with compiled recipes

    This function is triggered by the installation procedure
    in ``build.py`` during package installation to convert the
    recipes into a parse tree using Lark and save them into
    a cache directory in ``recipe_cache``. This measure is
    undertaken as parsing can take a little bit and by caching
    the result, it does not need to be done everytime the
    ``EndfParser`` class is instantiated by the user.
    """
    import shutil
    import os
    from endf_parserpy.interpreter.endf_parser import EndfParser

    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipe_cache_dir = os.path.join(script_dir, "recipe_cache")
    if clear_dir:
        if os.path.exists(recipe_cache_dir):
            shutil.rmtree(recipe_cache_dir)
    os.makedirs(recipe_cache_dir, exist_ok=True)
    # it does not hurt to create an __init__ file to be sure
    # that the cache directory is created/copied during package installation
    initfile_path = os.path.join(recipe_cache_dir, "__init__.py")
    if not os.path.exists(initfile_path):
        with open(initfile_path, "w") as f:
            pass
    # instantiate parser for each endf flavor to create compiled recipe files
    endf_flavors = list_endf_flavors()
    for flavor in endf_flavors:
        print(f"Compiling ENDF recipe flavor {flavor}")
        EndfParser(endf_format=flavor, cache_dir=recipe_cache_dir)
