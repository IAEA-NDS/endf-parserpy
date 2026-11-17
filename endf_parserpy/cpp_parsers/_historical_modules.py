############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The module names of the flavors until release 0.18.

Until release 0.18, every flavor had a C++ extension module of its own,
e.g. ``endf_parserpy.cpp_parsers.endf6``. The functions of all flavors
are now in one module, ``endf_parserpy.cpp_parsers._flavors``, with an
entry (a submodule) per build target.

- The released module names (:data:`HISTORICAL_MODULES`) are kept as
  deprecated Python modules (shims) that stand for the entries of the
  module; :func:`deprecated_entry` is their code.
- An extension module of the old layout left in a source checkout (from
  an in-place build) would be imported instead of a shim, because Python
  prefers extension modules to Python files of the same name.
  :func:`warn_stale_extension_files` warns about such files when the
  package is imported; ``setup.py`` removes them when it builds the
  module (see :func:`is_stale_extension_filename`).
"""

import importlib
import importlib.machinery
import os
import re
import warnings

from endf_parserpy.utils.deprecation import warn_deprecated


# the C++ module of the package, with one entry per build target
CPP_MODULE = "endf_parserpy.cpp_parsers._flavors"

# the module names of the flavors in the releases until 0.18, which are
# kept as deprecated shims (aliases, frozen layout versions and later
# flavors have none)
HISTORICAL_MODULES = ("endf6_ext", "endf6", "jendl", "pendf", "errorr", "test")

# the C++ extension modules of the flavors before the module with all
# flavors: the historical ones and `gendf`, which was built as a module
# of its own in development versions only
PER_FLAVOR_EXTENSION_MODULES = HISTORICAL_MODULES + ("gendf",)

# the file name of an extension module of any Python version and
# platform, e.g. endf6.cpython-311-x86_64-linux-gnu.so, endf6.abi3.so,
# endf6.cp311-win_amd64.pyd or endf6.pyd
_EXTENSION_FILENAME = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\.[A-Za-z0-9_-]+)?\.(?:so|pyd)\Z"
)


def is_stale_extension_filename(basename):
    """Whether a file name is that of an extension module of the old
    layout (one module per flavor), for any Python version and platform.

    Only the file names of the modules in
    :data:`PER_FLAVOR_EXTENSION_MODULES` qualify, not that of the module
    with all flavors or of any other file.
    """
    match = _EXTENSION_FILENAME.match(basename)
    return match is not None and match.group("name") in PER_FLAVOR_EXTENSION_MODULES


def stale_extension_files(directory=None):
    """Return the paths of the extension modules of the old layout in
    ``directory`` that this interpreter would import (by the suffixes in
    ``importlib.machinery.EXTENSION_SUFFIXES``), sorted.

    ``directory`` defaults to the directory of this package.
    """
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))
    try:
        basenames = set(os.listdir(directory))
    except OSError:
        return []
    candidates = {
        name + suffix
        for name in PER_FLAVOR_EXTENSION_MODULES
        for suffix in importlib.machinery.EXTENSION_SUFFIXES
    }
    return [os.path.join(directory, b) for b in sorted(basenames & candidates)]


def warn_stale_extension_files(directory=None):
    """Issue a ``RuntimeWarning`` for each extension module of the old
    layout in ``directory`` (see :func:`stale_extension_files`).

    Returns the paths of the files warned about.
    """
    paths = stale_extension_files(directory)
    for path in paths:
        name = os.path.basename(path).split(".", 1)[0]
        warnings.warn(
            f"The file {path} is the C++ extension module `{name}` of a "
            "release before 0.19 of endf-parserpy, which now has one C++ "
            f"module ({CPP_MODULE}) for all flavors. Python imports "
            f"this file for endf_parserpy.cpp_parsers.{name} instead of "
            "the current code; delete it, or build the package again "
            "(setup.py removes such files when it builds the C++ module).",
            RuntimeWarning,
            stacklevel=2,
        )
    return paths


def _endf_format_of_entry(entry_name):
    from endf_parserpy.endf_recipes import (
        cpp_module_basename,
        list_endf_build_targets,
    )

    for target in list_endf_build_targets():
        if cpp_module_basename(target) == entry_name:
            return target
    return entry_name


def deprecated_entry(module_name):
    """The code of a shim: issue a ``DeprecationWarning`` that names the
    code importing the shim and return the entry of the module with all
    flavors that the shim stands for.

    Parameters
    ----------
    module_name : str
        The full name of the shim, e.g. ``endf_parserpy.cpp_parsers.endf6``.
    """
    entry_name = module_name.rsplit(".", 1)[-1]
    flavors = importlib.import_module(CPP_MODULE)
    endf_format = _endf_format_of_entry(entry_name)
    # attributed to the code importing the shim (an import statement or
    # importlib.import_module), see endf_parserpy.utils.deprecation
    warn_deprecated(
        f"The module {module_name} is deprecated and will be removed in a "
        "later release: the C++ functions of all flavors are now in one "
        "module. To parse and write, use "
        f'EndfParserCpp(endf_format="{endf_format}"); for the diagnostic '
        "functions _bulk_body_info and _line_read_counts, use "
        "importlib.import_module(parser._parse_endf.__module__) of such a "
        "parser."
    )
    return getattr(flavors, entry_name)
