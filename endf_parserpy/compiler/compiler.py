############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/23
# Last modified:   2026/11/16
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import os
from endf_parserpy.endf_recipes import (
    get_recipe_dict,
    list_endf_build_targets,
    cpp_module_basename,
)
from .endf2cpp import generate_cpp_module_code, generate_shared_cpp_code
from .cpp_boilerplate import generate_cmake_content


SHARED_CPP_FILENAME = "_shared.cpp"
SHARED_CHUNK_PREFIX = "_shared_part_"


def _shared_chunk_filename(chunk_id):
    return f"{SHARED_CHUNK_PREFIX}{chunk_id:02d}.cpp"


def is_shared_chunk_filename(basename):
    return basename == SHARED_CPP_FILENAME or basename.startswith(SHARED_CHUNK_PREFIX)


def create_cpp_parser_module(
    cpp_module_file, module_name, recipes=None, overwrite=False, shared_registry=None
):
    if not overwrite and os.path.exists(cpp_module_file):
        raise FileExistsError(f"file {cpp_module_file} exists already!")
    if recipes is None:
        recipes = get_recipe_dict("endf6-ext")
    cpp_module_code = generate_cpp_module_code(
        recipes, module_name, shared_registry=shared_registry
    )
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


def _prepare_cpp_parsers_subpackage(
    overwrite=False, only_filenames=False, dedup=True, num_shared_chunks=None
):
    """Generate per-flavor C++ pybind11 module sources.

    When ``dedup`` is True (default), parse and write function bodies
    that have an identical underlying ENDF recipe across multiple
    flavors are emitted only once into shared translation unit(s),
    which the build system compiles and links into each flavor's
    extension module via ``extra_objects``.

    Parameters
    ----------
    num_shared_chunks : Optional[int]
        Number of shared translation units to spread the canonical
        functions over so they can be compiled in parallel. ``None``
        (default) consults the ``INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS``
        environment variable, falling back to ``min(os.cpu_count(), 8)``.
        Set to ``1`` to keep the legacy single-``_shared.cpp`` layout.
    """
    if num_shared_chunks is None:
        env_val = os.environ.get("INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS", "")
        try:
            num_shared_chunks = int(env_val) if env_val else min(os.cpu_count() or 1, 8)
        except ValueError:
            num_shared_chunks = min(os.cpu_count() or 1, 8)
    num_shared_chunks = max(num_shared_chunks, 1)

    # one module per flavor with recipes of its own; the aliases, e.g.
    # layout versions without changes, use the module of their flavor
    endf_flavors = list_endf_build_targets()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cpp_parsers_dir = os.path.join(script_dir, "../cpp_parsers")
    flavor_filenames = [f"{cpp_module_basename(f)}.cpp" for f in endf_flavors]
    filenames = list(flavor_filenames)
    if dedup:
        if num_shared_chunks == 1:
            filenames.append(SHARED_CPP_FILENAME)
        else:
            filenames.extend(
                _shared_chunk_filename(i) for i in range(num_shared_chunks)
            )
    if only_filenames:
        return filenames

    # Remove shared translation units left by any previous build. A
    # changed layout (different chunk count, or dedup toggled off)
    # would otherwise leave stale _shared*.cpp files that the build
    # picks up alongside the current ones, causing duplicate-symbol
    # link errors.
    if overwrite:
        for name in os.listdir(cpp_parsers_dir):
            if is_shared_chunk_filename(name):
                os.remove(os.path.join(cpp_parsers_dir, name))

    shared_registry = {} if dedup else None
    for endf_flavor, module_file in zip(endf_flavors, flavor_filenames):
        print(f"---- compilation of {endf_flavor} ----")
        module_name = cpp_module_basename(endf_flavor)
        cpp_module_path = os.path.join(cpp_parsers_dir, module_file)
        if not overwrite and os.path.exists(cpp_module_path):
            raise FileExistsError(f"The module {cpp_module_path} exists already!")
        recipe = get_recipe_dict(endf_flavor)
        create_cpp_parser_module(
            cpp_module_path,
            module_name,
            recipe,
            overwrite=overwrite,
            shared_registry=shared_registry,
        )

    written_shared_files = []
    if dedup:
        chunks = generate_shared_cpp_code(shared_registry, num_chunks=num_shared_chunks)
        n_parse = len(shared_registry.get("parse", {}))
        n_write = len(shared_registry.get("write", {}))
        print(
            f"---- writing {len(chunks)} shared TU(s) with "
            f"{n_parse} parse + {n_write} write deduplicated functions ----"
        )
        for basename, content in chunks:
            shared_path = os.path.join(cpp_parsers_dir, basename)
            if not overwrite and os.path.exists(shared_path):
                raise FileExistsError(f"The module {shared_path} exists already!")
            with open(shared_path, "w") as f:
                f.write(content)
            written_shared_files.append(basename)
        # If fewer chunks were produced than requested (with fewer
        # functions than chunks), drop the missing names from the
        # returned filename list so downstream build steps don't try to
        # compile non-existent files.
        if num_shared_chunks > 1 and len(written_shared_files) != num_shared_chunks:
            shared_set = set(written_shared_files)
            filenames = [
                f
                for f in filenames
                if (not f.startswith(SHARED_CHUNK_PREFIX)) or f in shared_set
            ]
    return filenames
