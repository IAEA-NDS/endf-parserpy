import re
from .endf6_ext import endf_recipe_dictionary as endf6_ext_recipes
from .endf6 import endf_recipe_dictionary as endf6_recipes
from .jendl import endf_recipe_dictionary as jendl_recipes
from .pendf import endf_recipe_dictionary as pendf_recipes
from .errorr import endf_recipe_dictionary as errorr_recipes
from .test import endf_recipe_dictionary as test_recipes


# The build targets: the flavors with a recipe dictionary of their own.
# The C++ code generator and setup.py create one C++ module per entry.
_FORMAT_DICT = {
    "endf6-ext": endf6_ext_recipes,
    "endf6": endf6_recipes,
    "jendl": jendl_recipes,
    "pendf": pendf_recipes,
    "errorr": errorr_recipes,
    "test": test_recipes,
}


# Layout versions and other names that stand for another flavor. An
# alias maps a name to a build target or to another alias. It has no
# recipes and no C++ module of its own.
#
# A layout version `<flavor>-v<N>` pins the layout of the dictionaries
# produced for a flavor: the keys, their nesting, the shape of the arrays
# and the meaning of the values. N is increased only by a change of this
# layout, not by a fix of a recipe that keeps it. The bare name of the
# flavor is always the latest version. The checksums of the recipes of
# every version are stored in tests/test_layout_versions.py.
#
# Procedure when a change of the recipes of a flavor changes its layout
# (copy-on-write), e.g. a change of the flavor `endf6-ext` whose latest
# version is `endf6-ext-v1`:
#
# 1. Create the folder `endf6_ext_v1` of the frozen version with copies
#    of the current (unchanged) recipes of all MF/MT sections that the
#    change affects. Its `__init__.py` derives the recipe dictionary from
#    the flavor for the rest, as `jendl` does from `endf6`, and replaces
#    the recipes of these sections by the copies.
# 2. Move `endf6-ext-v1` from `_ALIASES` to `_FORMAT_DICT`, which makes
#    it a build target with its own C++ module.
# 3. Change the recipes of `endf6-ext` and add the alias
#    `"endf6-ext-v2": "endf6-ext"`.
# 4. Store the checksum of `endf6-ext-v2` in the test; the one of
#    `endf6-ext-v1` stays as it is. Add the version to the table of
#    layout versions in the docs and to the CHANGELOG.
#
# Aliases that resolve to the changed flavor, e.g. `endf6-v1` -> `endf6`
# for a change of `endf6`, are treated in the same way.
_ALIASES = {
    "endf6-ext-v1": "endf6-ext",
    "endf6-v1": "endf6",
}


_LAYOUT_VERSION_RE = re.compile(r"^(?P<flavor>.+)-v(?P<num>[1-9][0-9]*)$")


def _resolve_aliases(targets, aliases):
    """Map every name to the name of its build target.

    Parameters
    ----------
    targets : dict
        The build targets, mapping their names to recipe dictionaries.
    aliases : dict
        Mapping of alias names to build targets or other aliases.

    Returns
    -------
    dict
        Mapping of all names, the build targets first, in the order of
        ``targets`` and ``aliases``, to the name of a build target.

    Raises
    ------
    ValueError
        If an alias has the name of a build target, refers to a name
        that is neither a build target nor an alias, or is part of a
        cycle of aliases.
    """
    resolved = {name: name for name in targets}
    for name in aliases:
        if name in targets:
            raise ValueError(f"the alias `{name}` is also the name of a build target")
    for name in aliases:
        chain = [name]
        current = aliases[name]
        while current not in targets:
            if current not in aliases:
                raise ValueError(
                    f"the alias `{chain[-1]}` refers to `{current}`, "
                    "which is neither a flavor nor an alias"
                )
            if current in chain:
                cycle = " -> ".join(chain + [current])
                raise ValueError(f"cycle of aliases: {cycle}")
            chain.append(current)
            current = aliases[current]
        resolved[name] = current
    return resolved


_RESOLVED = _resolve_aliases(_FORMAT_DICT, _ALIASES)


def resolve_endf_flavor(format_spec):
    """Return the name of the flavor whose recipes a name stands for.

    For a layout version that is an alias, e.g. ``endf6-ext-v1`` as long
    as it has the layout of the latest ``endf6-ext``, this is the name of
    the flavor (``endf6-ext``); for the name of a flavor with recipes of
    its own, the name itself.

    Parameters
    ----------
    format_spec : str
        A name returned by :func:`list_endf_flavors`.

    Returns
    -------
    str
        The name of the flavor whose recipes and C++ module are used.
    """
    if format_spec not in _RESOLVED:
        raise TypeError(
            "There isn't any format specification "
            + f"associated with the name `{format_spec}`"
        )
    return _RESOLVED[format_spec]


def get_layout_version(format_spec):
    """Return the layout version that a name currently gives.

    The name of the layout version that can be passed as ``endf_format``
    to keep the layout of the dictionaries that ``format_spec`` gives
    now, e.g. ``endf6-ext-v1`` for ``endf6-ext``, or ``None`` if the
    flavor has no layout versions. A layout version is returned as is.

    Parameters
    ----------
    format_spec : str
        A name returned by :func:`list_endf_flavors`.

    Returns
    -------
    str or None
        The name of the layout version.
    """
    target = resolve_endf_flavor(format_spec)
    if _LAYOUT_VERSION_RE.match(format_spec):
        return format_spec
    versions = []
    for name, name_target in _RESOLVED.items():
        m = _LAYOUT_VERSION_RE.match(name)
        if m and m.group("flavor") == format_spec and name_target == target:
            versions.append((int(m.group("num")), name))
    return max(versions)[1] if versions else None


def get_recipe_dict(format_spec):
    """Return the recipe dictionary of a flavor or a layout version."""
    return _FORMAT_DICT[resolve_endf_flavor(format_spec)]


def list_endf_flavors():
    """Return the names that can be given as ``endf_format``.

    The names of the flavors are followed by those of the layout
    versions and other aliases.
    """
    return tuple(_RESOLVED.keys())


def list_endf_build_targets():
    """Return the names of the flavors with recipes and a C++ module of their own."""
    return tuple(_FORMAT_DICT.keys())
