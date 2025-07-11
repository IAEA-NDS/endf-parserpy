############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/23
# Last modified:   2025/07/11
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import os
from endf_parserpy.endf_recipes import (
    get_recipe_dict,
    list_endf_flavors,
)
from .endf2cpp import generate_cpp_module_code
from .cpp_boilerplate import generate_cmake_content


def create_cpp_parser_module(
    cpp_module_file, module_name, recipes=None, overwrite=False
):
    if not overwrite and os.path.exists(cpp_module_file):
        raise FileExistsError(f"file {cpp_module_file} exists already!")
    if recipes is None:
        recipes = get_recipe_dict("endf6-ext")
    cpp_module_code = generate_cpp_module_code(recipes, module_name)
    with open(cpp_module_file, "w") as f:
        f.write(cpp_module_code)


def create_cmake_file(project_path, module_name, overwrite=False):
    cmake_file = os.path.join(project_path, "CMakeLists.txt")
    if not overwrite and os.path.exists(cmake_file):
        raise FileExistsError(f"file {cmake_file} exists already!")
    cmake_content = generate_cmake_content(module_name)
    with open(cmake_file, "w") as f:
        f.write(cmake_content)


def create_project_files(
    project_path, module_name, recipes=None, path_exist_ok=False, overwrite_files=False
):
    if recipes is None:
        recipes = get_recipe_dict("endf6-ext")
    try:
        os.makedirs(project_path, exist_ok=path_exist_ok)
        os.makedirs(os.path.join(project_path, "build"), exist_ok=path_exist_ok)
    except FileExistsError:
        raise FileExistsError(f"the directory {project_path} exists already!")

    cpp_module_file = os.path.join(project_path, f"{module_name}.cpp")
    cmake_file = os.path.join(project_path, "CMakeLists.txt")

    create_cpp_parser_module(
        cpp_module_file, module_name, recipes, overwrite=overwrite_files
    )
    create_cmake_file(project_path, module_name, overwrite=overwrite_files)


def _prepare_cpp_parsers_subpackage(overwrite=False, only_filenames=False):
    endf_flavors = list_endf_flavors()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cpp_parsers_dir = os.path.join(script_dir, "../cpp_parsers")
    filenames = []
    for endf_flavor in endf_flavors:
        print(f"---- compilation of {endf_flavor} ----")
        module_name = endf_flavor.replace("-", "_")
        module_file = f"{module_name}.cpp"
        filenames.append(module_file)
        if only_filenames:
            continue
        cpp_module_path = os.path.join(cpp_parsers_dir, module_file)
        if not overwrite and os.path.exists(cpp_module_path):
            raise FileExistsError(f"The module {cpp_module_path} exists already!")
        recipe = get_recipe_dict(endf_flavor)
        create_cpp_parser_module(
            cpp_module_path, module_name, recipe, overwrite=overwrite
        )
    return filenames
