import os
from .endf2cpp import generate_cpp_module_code
from .cpp_boilerplate import generate_cmake_content
from ..endf_recipes import endf_recipe_dictionary


def create_cpp_project_files(
    path, recipes=None, path_exist_ok=False, overwrite_files=False
):
    if recipes is None:
        recipes = endf_recipe_dictionary
    try:
        os.makedirs(path, exist_ok=path_exist_ok)
        os.makedirs(os.path.join(path, "build"), exist_ok=path_exist_ok)
    except FileExistsError:
        raise FileExistsError(f"the directory {path} exists already!")

    cpp_module_file = os.path.join(path, "cpp_parsefuns.cpp")
    cmake_file = os.path.join(path, "CMakeLists.txt")

    for f in (cmake_file, cpp_module_file):
        if overwrite_files is not True and os.path.exists(f):
            raise FileExistsError(f"file {f} exists!")

    cpp_module_code = generate_cpp_module_code(recipes)
    cmake_content = generate_cmake_content()

    with open(cpp_module_file, "w") as f:
        f.write(cpp_module_code)

    with open(cmake_file, "w") as f:
        f.write(cmake_content)
