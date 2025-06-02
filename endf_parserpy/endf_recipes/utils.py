def defdic(dic, index, recipe):
    """store recipe in nested dictionary"""
    curdic = dic
    for idx in index[:-1]:
        curdic = curdic.setdefault(idx, {})
    curdic[index[-1]] = recipe


def _populate_recipe_cache(clear_dir=False):
    """Populate the recipe_cache folder with compiled recipes

    This function is triggered by the installation procedure
    in ``build.py`` during package installation to convert the
    recipes into a parse tree using Lark and save them into
    a cache directory in ``recipe_cache``. This measure is
    undertaken as parsing can take a little bit and by caching
    the result, it does not need to be done everytime the
    ``EndfParserPy`` class is instantiated by the user.
    """
    import shutil
    import os
    from endf_parserpy.interpreter.endf_parser import EndfParserPy
    from .catalogue import list_endf_flavors

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
        EndfParserPy(endf_format=flavor, cache_dir=recipe_cache_dir)
