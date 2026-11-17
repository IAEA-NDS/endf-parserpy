############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/23
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import os
from endf_parserpy.endf_recipes import (
    get_recipe_dict,
    get_tape_structure,
    list_endf_build_targets,
    cpp_module_basename,
)
from endf_parserpy.utils.tape_structure import TapeStructure, check_recipes
from .endf2cpp import (
    generate_cpp_module_code,
    generate_cpp_flavor_code,
    generate_cpp_flavors_module_code,
    generate_shared_cpp_code,
)
from .cpp_boilerplate import generate_cmake_content


# the extension module with the functions of all build targets, one
# entry (submodule) per target (see _prepare_cpp_parsers_subpackage)
CPP_MODULE_NAME = "_flavors"
CPP_MODULE_FILENAME = f"{CPP_MODULE_NAME}.cpp"
FLAVOR_TU_PREFIX = "_flavor_"
SHARED_CPP_FILENAME = "_shared.cpp"
SHARED_CHUNK_PREFIX = "_shared_part_"


def _shared_chunk_filename(chunk_id):
    return f"{SHARED_CHUNK_PREFIX}{chunk_id:02d}.cpp"


def is_shared_chunk_filename(basename):
    return basename == SHARED_CPP_FILENAME or basename.startswith(SHARED_CHUNK_PREFIX)


def create_cpp_parser_module(
    cpp_module_file,
    module_name,
    recipes=None,
    overwrite=False,
    shared_registry=None,
    tape_structure=None,
):
    if not overwrite and os.path.exists(cpp_module_file):
        raise FileExistsError(f"file {cpp_module_file} exists already!")
    if recipes is None:
        recipes = get_recipe_dict("endf6-ext")
    # the tape structure of the recipes (ENDF-6 by default), which the
    # functions of the module use if their options give none; the recipes
    # must agree with it on the SEND records
    tape_structure = TapeStructure.from_spec(tape_structure)
    check_recipes(recipes, tape_structure)
    cpp_module_code = generate_cpp_module_code(
        recipes,
        module_name,
        shared_registry=shared_registry,
        tape_structure=tape_structure,
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
    project_path,
    module_name,
    recipes=None,
    path_exist_ok=False,
    overwrite_files=False,
    tape_structure=None,
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
        cpp_module_file,
        module_name,
        recipes,
        overwrite=overwrite_files,
        tape_structure=tape_structure,
    )
    create_cmake_file(project_path, module_name, overwrite=overwrite_files)


def _flavor_tu_filename(entry_name):
    return f"{FLAVOR_TU_PREFIX}{entry_name}.cpp"


def is_generated_tu_filename(basename):
    """Whether a file in ``cpp_parsers/`` is a translation unit that the
    build generates (and removes again before generating anew)."""
    return (
        is_shared_chunk_filename(basename)
        or basename == CPP_MODULE_FILENAME
        or (basename.startswith(FLAVOR_TU_PREFIX) and basename.endswith(".cpp"))
    )


def _prepare_cpp_parsers_subpackage(
    overwrite=False,
    only_filenames=False,
    dedup=True,
    num_shared_chunks=None,
):
    """Generate the C++ sources of the extension module with all flavors.

    The module ``endf_parserpy.cpp_parsers._flavors`` contains one
    entry (a submodule) per build target, named by
    ``cpp_module_basename``, with the functions ``parse_endf``,
    ``parse_endf_file``, ``write_endf`` and ``write_endf_file`` of the
    target. Aliases have no entry; they use the entry of their target.

    When ``dedup`` is True (default), parse and write function bodies
    that have an identical underlying ENDF recipe, specialized for the
    same MF/MT, across multiple flavors are emitted only once into shared
    translation unit(s).
    The code of each flavor (wrappers and dispatchers, which have the
    same names in every flavor) is placed into a namespace of its own,
    in a translation unit of its own (``_flavor_<entry>.cpp``); the
    module init is in ``_flavors.cpp``.

    Parameters
    ----------
    num_shared_chunks : Optional[int]
        Number of shared translation units to spread the canonical
        functions over so they can be compiled in parallel. ``None``
        (default) consults the ``INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS``
        environment variable, falling back to ``min(os.cpu_count(), 8)``.
        Set to ``1`` to keep the legacy single-``_shared.cpp`` layout.

    Returns
    -------
    list[str]
        The basenames of the translation units of the module, the
        flavors first, then the shared chunks, then the module init.
    """
    if num_shared_chunks is None:
        env_val = os.environ.get("INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS", "")
        try:
            num_shared_chunks = int(env_val) if env_val else min(os.cpu_count() or 1, 8)
        except ValueError:
            num_shared_chunks = min(os.cpu_count() or 1, 8)
    num_shared_chunks = max(num_shared_chunks, 1)

    # one entry per flavor with recipes of its own; the aliases, e.g.
    # layout versions without changes, use the entry of their flavor
    endf_flavors = list_endf_build_targets()
    entry_names = [cpp_module_basename(f) for f in endf_flavors]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cpp_parsers_dir = os.path.join(script_dir, "../cpp_parsers")
    flavor_filenames = [_flavor_tu_filename(e) for e in entry_names]
    filenames = list(flavor_filenames)
    if dedup:
        if num_shared_chunks == 1:
            filenames.append(SHARED_CPP_FILENAME)
        else:
            filenames.extend(
                _shared_chunk_filename(i) for i in range(num_shared_chunks)
            )
    filenames.append(CPP_MODULE_FILENAME)
    if only_filenames:
        return filenames

    # Remove the translation units left by any previous build. A
    # changed layout (different chunk count, dedup toggled off or other
    # flavors) would otherwise leave stale
    # files that the build picks up alongside the current ones, causing
    # duplicate-symbol link errors.
    if overwrite:
        for name in os.listdir(cpp_parsers_dir):
            if is_generated_tu_filename(name):
                os.remove(os.path.join(cpp_parsers_dir, name))

    def _write(basename, content):
        path = os.path.join(cpp_parsers_dir, basename)
        if not overwrite and os.path.exists(path):
            raise FileExistsError(f"The module {path} exists already!")
        with open(path, "w") as f:
            f.write(content)

    shared_registry = {} if dedup else None
    for endf_flavor, entry_name, filename in zip(
        endf_flavors, entry_names, flavor_filenames
    ):
        print(f"---- compilation of {endf_flavor} ----")
        recipe = get_recipe_dict(endf_flavor)
        code = generate_cpp_flavor_code(
            recipe,
            entry_name,
            shared_registry=shared_registry,
            tape_structure=get_tape_structure(endf_flavor),
        )
        _write(filename, code)
    _write(
        CPP_MODULE_FILENAME,
        generate_cpp_flavors_module_code(CPP_MODULE_NAME, entry_names),
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
            _write(basename, content)
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
