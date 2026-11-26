import importlib
import re


# The build targets: the flavors with a recipe dictionary of their own,
# each with the name of its folder in endf_parserpy/endf_recipes. The
# file __init__.py of the folder defines the recipe dictionary
# `endf_recipe_dictionary` of the flavor, and the module of the same
# name in endf_recipes/tape_structures its tape structure
# `TAPE_STRUCTURE` (see endf_parserpy.utils.tape_structure), so that the
# tape structure is read without the recipes. Both are imported when
# they are first needed (see _flavor_package and _tape_structure_spec),
# not with the package. The C++ code generator and setup.py create one
# entry per build target in the C++ module (see cpp_module_basename).
_FLAVOR_PACKAGES = {
    "endf6-ext": "endf6_ext",
    "endf6": "endf6",
    "jendl": "jendl",
    "pendf": "pendf",
    "errorr": "errorr",
    "gendf": "gendf",
    "test": "test",
}


def _flavor_package(target):
    """Import the folder of a build target and return the module."""
    return importlib.import_module("." + _FLAVOR_PACKAGES[target], __package__)


def _tape_structure_spec(target):
    """Import the tape structure module of a build target, return its spec."""
    name = ".tape_structures." + _FLAVOR_PACKAGES[target]
    return importlib.import_module(name, __package__).TAPE_STRUCTURE


# Layout versions and other names that stand for another flavor. An
# alias maps a name to a build target or to another alias. It has no
# recipes and no entry in the C++ module of its own.
#
# A layout version `<flavor>@<X.Y>` pins the layout of the dictionaries
# that the flavor gives in the release X.Y of endf-parserpy: the keys,
# their nesting, the shape of the arrays and the meaning of the values.
# The bare name of the flavor is always the latest layout. Every release
# X.Y adds `<flavor>@<X.Y>` for every flavor with layout versions, as an
# alias of the flavor. The checksums of the recipes of every version are
# stored in tests/test_layout_versions.py, whose guard test fails if the
# recipes of a version change. A change of the recipes that keeps the
# layout needs no new version: the failure message of the guard then
# gives the new checksum to store.
#
# Procedure when a change of the recipes of a flavor changes its layout
# (copy-on-write), e.g. a change of `endf6-ext` in the release 0.21 whose
# latest version is `endf6-ext@0.20`:
#
# 1. Create the folder `endf6_ext_0_20` of the frozen version with copies
#    of the current (unchanged) recipes of all MF/MT sections that the
#    change affects. Its `__init__.py` derives the recipe dictionary from
#    the flavor for the rest, as `jendl` does from `endf6`, and replaces
#    the recipes of these sections by the copies. Create
#    `tape_structures/endf6_ext_0_20.py` with a copy of the tape
#    structure of the flavor.
# 2. Move `endf6-ext@0.20` from `_ALIASES` to `_FLAVOR_PACKAGES`, as
#    `"endf6-ext@0.20": "endf6_ext_0_20"`, which makes it a build target
#    with its own entry in the C++ module, and let the earlier versions
#    with the same layout, e.g. `endf6-ext@0.19`, refer to it.
# 3. Change the recipes of `endf6-ext` and add the alias
#    `"endf6-ext@0.21": "endf6-ext"` with the release.
# 4. Store the checksum of `endf6-ext@0.21` in LAYOUT_CHECKSUMS of the
#    test: `pytest tests/test_layout_versions.py` fails for the new
#    version with the entry to add (name and checksum). Those of the
#    earlier versions stay as they are. Add the version to the table of
#    layout versions in the docs and to the CHANGELOG.
#
# Aliases that resolve to the changed flavor, e.g. `endf6@0.20` ->
# `endf6` for a change of `endf6`, are treated in the same way.
_ALIASES = {
    "endf6-ext@0.19": "endf6-ext",
    "endf6@0.19": "endf6",
}


_LAYOUT_VERSION_RE = re.compile(
    r"^(?P<flavor>[^@]+)@(?P<release>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))$"
)


def _release_key(name):
    """The release of a layout version as a tuple of integers."""
    release = _LAYOUT_VERSION_RE.match(name).group("release")
    return tuple(int(part) for part in release.split("."))


def _resolve_aliases(targets, aliases):
    """Map every name to the name of its build target.

    Parameters
    ----------
    targets : dict
        The build targets, mapping their names to the names of their
        folders.
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
        cycle of aliases, or if a layout version `<flavor>@<X.Y>` stands
        for another flavor.
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
    for name in list(targets) + list(aliases):
        m = _LAYOUT_VERSION_RE.match(name)
        if m is None:
            continue
        target = resolved[name]
        target_m = _LAYOUT_VERSION_RE.match(target)
        target_flavor = target_m.group("flavor") if target_m else target
        if target_flavor != m.group("flavor"):
            raise ValueError(
                f"the layout version `{name}` stands for `{target}`, "
                f"which is neither `{m.group('flavor')}` nor one of its "
                "layout versions"
            )
    return resolved


_RESOLVED = _resolve_aliases(_FLAVOR_PACKAGES, _ALIASES)


def resolve_endf_flavor(format_spec):
    """Return the name of the flavor whose recipes a name stands for.

    For a layout version that is an alias, e.g. ``endf6-ext@0.19`` as long
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
        The name of the flavor whose recipes and entry in the C++ module
        are used.
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
    now, e.g. ``endf6-ext@0.19`` for ``endf6-ext``, or ``None`` if the
    flavor has no layout versions. If several versions have this layout,
    the one of the latest release is returned. A layout version is
    returned as is.

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
            versions.append((_release_key(name), name))
    return max(versions)[1] if versions else None


def get_recipe_dict(format_spec):
    """Return the recipe dictionary of a flavor or a layout version."""
    return _flavor_package(resolve_endf_flavor(format_spec)).endf_recipe_dictionary


def get_tape_structure(format_spec):
    """Return the tape structure of a flavor or a layout version.

    Returns
    -------
    TapeStructure
        The resolved tape structure (see
        :class:`~endf_parserpy.TapeStructure`) of the flavor whose recipes
        the name stands for.
    """
    from ..utils.tape_structure import TapeStructure

    target = resolve_endf_flavor(format_spec)
    ts = _TAPE_STRUCTURES.get(target)
    if ts is None:
        ts = TapeStructure.from_spec(_tape_structure_spec(target))
        _TAPE_STRUCTURES[target] = ts
    return ts


# the resolved tape structures of the build targets (see get_tape_structure)
_TAPE_STRUCTURES = {}


def list_endf_flavors():
    """Return the names that can be given as ``endf_format``.

    The names of the flavors are followed by those of the layout
    versions and other aliases.
    """
    return tuple(_RESOLVED.keys())


def cpp_module_basename(format_spec):
    """Return the name of the entry of a build target in the C++ module.

    The characters ``-``, ``@`` and ``.``, which a Python identifier
    cannot contain, are replaced by ``_``, e.g. ``endf6_ext`` for
    ``endf6-ext`` and ``endf6_ext_0_20`` for a frozen layout version
    ``endf6-ext@0.20``. The entry is a submodule of
    ``endf_parserpy.cpp_parsers._flavors`` and its code is in the C++
    namespace ``endf_flavor_<name>``.
    """
    return format_spec.replace("-", "_").replace("@", "_").replace(".", "_")


def _check_entry_names(targets):
    """Check that the build targets have distinct, valid entry names.

    The mapping by :func:`cpp_module_basename` is not injective (e.g.
    ``a-b`` and ``a_b`` both give ``a_b``), and in the C++ module with
    all flavors, an entry of the same name would silently replace the
    functions of another target.

    Raises
    ------
    ValueError
        If two build targets have the same entry name, or an entry name
        is not a Python identifier or starts with ``_`` (which is
        reserved for other names of the module, e.g. ``_entries``).
    """
    seen = {}
    for name in targets:
        entry = cpp_module_basename(name)
        if not entry.isidentifier() or entry.startswith("_"):
            raise ValueError(
                f"the build target `{name}` gives the entry name `{entry}` "
                "in the C++ module, which is not an identifier without a "
                "leading underscore"
            )
        if entry in seen:
            raise ValueError(
                f"the build targets `{seen[entry]}` and `{name}` give the "
                f"same entry name `{entry}` in the C++ module"
            )
        seen[entry] = name


_check_entry_names(_FLAVOR_PACKAGES)


def list_endf_build_targets():
    """Return the names of the flavors with recipes of their own.

    Each of them has an entry in the C++ module.
    """
    return tuple(_FLAVOR_PACKAGES.keys())
