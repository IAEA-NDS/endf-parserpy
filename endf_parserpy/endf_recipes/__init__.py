import importlib

from .catalogue import (
    get_recipe_dict,
    get_tape_structure,
    list_endf_flavors,
    list_endf_build_targets,
    resolve_endf_flavor,
    get_layout_version,
    cpp_module_basename,
)
from .catalogue import _FLAVOR_PACKAGES


# The folders of the flavors (e.g. endf6) are imported when they are
# first needed (see catalogue.py), or when accessed as attributes of
# this package (PEP 562).
def __getattr__(name):
    if name in _FLAVOR_PACKAGES.values():
        return importlib.import_module("." + name, __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_FLAVOR_PACKAGES.values()))
