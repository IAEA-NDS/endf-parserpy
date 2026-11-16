############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/16
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Layout versions of the flavors and the guard against changing them.

A layout version, e.g. `endf6-ext@0.19`, pins the layout of the
dictionaries of a flavor. As long as the flavor keeps this layout, the
version is an alias of the flavor, without recipes or a C++ module of
its own (see endf_recipes/catalogue.py).

The guard stores a checksum of the recipes of every layout version and
fails if the recipes that a version resolves to change. The checksum is
computed from the parse trees of the recipes without the comments and
the line breaks, so that a change of a comment or of the spacing does not
change it.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.endf_recipes import (
    cpp_module_basename,
    get_layout_version,
    get_recipe_dict,
    list_endf_build_targets,
    list_endf_flavors,
    resolve_endf_flavor,
)
from endf_parserpy.endf_recipes import catalogue
from endf_parserpy.endf_recipes.catalogue import _LAYOUT_VERSION_RE, _resolve_aliases
from endf_parserpy.recipe_parser import Token, Tree, parse_recipe
from endf_parserpy.utils.debugging_utils import compare_objects


TESTDATA = Path(__file__).resolve().parent / "testdata"
REPO_ROOT = Path(__file__).resolve().parent.parent


# The checksums of the recipes of the layout versions (see the messages
# of _guard_report for what to do if one of them changes).
LAYOUT_CHECKSUMS = {
    "endf6-ext@0.19": "485ba0875adc6a983c6158c55b67f7a89423e4706f89f5bae1a2185ab8882e7c",
    "endf6@0.19": "a8d0b32409a04bfb1e30227e803a4ea77a356ef10a7db1a121ebb7090afee3c8",
}

# Whether a recipe fix that keeps the layout may also be applied to a
# frozen layout version, i.e. a version with recipes of its own
# ("backport"), or frozen versions stay as they are ("strict"). This is
# still to be decided; there is no frozen version yet. Fixes of the C++
# templates and of the code generator reach all versions in either case.
FROZEN_VERSION_POLICY = "backport"


def _canonical_tree(node):
    """The parse tree as nested lists, without comments and line breaks."""
    if isinstance(node, Tree):
        if node.data == "comment_block":
            return None
        children = [_canonical_tree(c) for c in node.children]
        children = [c for c in children if c is not None]
        # a statement that was only a comment
        if node.data == "code_token" and not children:
            return None
        return [str(node.data), children]
    assert isinstance(node, Token)
    if node.type == "NEWLINE":
        return None
    return [node.type, str(node)]


def _layout_checksum(recipes):
    """The checksum of a recipe dictionary (SHA-256 of the parse trees)."""
    entries = []
    for mf in sorted(recipes):
        if isinstance(recipes[mf], str):
            entries.append([mf, None, _canonical_tree(parse_recipe(recipes[mf]))])
        else:
            for mt in sorted(recipes[mf]):
                tree = parse_recipe(recipes[mf][mt])
                entries.append([mf, mt, _canonical_tree(tree)])
    text = json.dumps(entries, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _changed_message(name, target, stored, found, frozen, policy):
    head = (
        f"The recipes of the layout version `{name}` have changed "
        f"(stored checksum {stored}, found {found}). "
    )
    if not frozen:
        return head + (
            f"`{name}` is an alias of the flavor `{target}`, so the change "
            f"is one of the recipes of `{target}`. If it changes the layout "
            "of the dictionaries (keys, nesting, array shape or the meaning "
            f"of a value), keep the previous recipes for `{name}` by the "
            "copy-on-write procedure in endf_recipes/catalogue.py and add "
            "the next version as alias; the checksum of "
            f"`{name}` then stays as it is. If the change keeps the "
            "layout, no version is added: replace the checksum of "
            f"`{name}` in LAYOUT_CHECKSUMS by '{found}'."
        )
    msg = head + (
        f"`{name}` is a frozen version with recipes of its own, which may "
        "also come from the flavor it derives from. A change of its layout "
        "is not allowed: undo the change, or, if it is a change of a recipe "
        f"that `{name}` takes over from its flavor, put a copy of the "
        f"previous recipe of this section into the folder of `{name}`."
    )
    if policy == "backport":
        msg += (
            " A fix that keeps the layout may be applied to frozen "
            f"versions: then replace the checksum of `{name}` in "
            f"LAYOUT_CHECKSUMS by '{found}'."
        )
    return msg


def _guard_report(flavors, targets, checksums, policy):
    """The messages of the guard, an empty list if nothing has changed.

    Parameters
    ----------
    flavors : dict
        Mapping of all names (flavors and aliases) to the names of their
        build targets.
    targets : dict
        Mapping of the build targets to their recipe dictionaries.
    checksums : dict
        The stored checksums of the layout versions.
    policy : str
        ``"backport"`` or ``"strict"`` (see FROZEN_VERSION_POLICY).
    """
    messages = []
    versions = [name for name in flavors if _LAYOUT_VERSION_RE.match(name)]
    for name in versions:
        target = flavors[name]
        found = _layout_checksum(targets[target])
        stored = checksums.get(name)
        if stored is None:
            messages.append(
                f"No checksum is stored for the layout version `{name}`: "
                f"add '{name}': '{found}' to LAYOUT_CHECKSUMS."
            )
        elif stored != found:
            frozen = _LAYOUT_VERSION_RE.match(target) is not None
            messages.append(
                _changed_message(name, target, stored, found, frozen, policy)
            )
    for name in checksums:
        if name not in versions:
            messages.append(
                f"A checksum is stored for `{name}`, which is not a layout "
                "version: remove it from LAYOUT_CHECKSUMS."
            )
    return messages


# the guard


def test_layout_versions_unchanged():
    flavors = {name: resolve_endf_flavor(name) for name in list_endf_flavors()}
    targets = {name: get_recipe_dict(name) for name in list_endf_build_targets()}
    messages = _guard_report(flavors, targets, LAYOUT_CHECKSUMS, FROZEN_VERSION_POLICY)
    assert not messages, "\n\n".join(messages)


def test_policy_is_known():
    assert FROZEN_VERSION_POLICY in ("backport", "strict")


# the checksum


RECIPE = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 6*NX, 0] CONT
SEND
"""


def test_checksum_ignores_comments_and_spacing():
    edited = """# the number of items
[MAT, MF,MT/ 0.0,0.0, 0, 0, 0, 0]HEAD

   # var NX: number of items divided by six
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 6 * NX, 0] CONT

SEND

"""
    assert _layout_checksum({2: {1: RECIPE}}) == _layout_checksum({2: {1: edited}})


@pytest.mark.parametrize(
    "edited",
    [
        RECIPE.replace("NX", "NY"),
        RECIPE.replace("6*NX", "NX"),
        RECIPE.replace("0, 6*NX", "6*NX, 0"),
        RECIPE.replace("0.0, 0.0, 0, 0, 6*NX", "0.0, 0.0, 0, 0, 6*NX[1]"),
    ],
)
def test_checksum_detects_changes(edited):
    assert _layout_checksum({2: {1: RECIPE}}) != _layout_checksum({2: {1: edited}})


def test_checksum_depends_on_sections():
    assert _layout_checksum({2: {1: RECIPE}}) != _layout_checksum({2: {2: RECIPE}})
    assert _layout_checksum({2: {1: RECIPE}}) != _layout_checksum({2: RECIPE})


# the catalogue of flavors


def test_versions_are_aliases():
    for name in ("endf6-ext@0.19", "endf6@0.19"):
        assert name in list_endf_flavors()
        assert name not in list_endf_build_targets()
    assert resolve_endf_flavor("endf6-ext@0.19") == "endf6-ext"
    assert resolve_endf_flavor("endf6@0.19") == "endf6"
    assert get_recipe_dict("endf6-ext@0.19") is get_recipe_dict("endf6-ext")
    assert get_recipe_dict("endf6@0.19") is get_recipe_dict("endf6")


def test_list_endf_flavors_keeps_the_flavors():
    flavors = ("endf6-ext", "endf6", "jendl", "pendf", "errorr", "gendf", "test")
    assert list_endf_build_targets() == flavors
    assert list_endf_flavors()[: len(flavors)] == flavors
    assert set(list_endf_flavors()) == set(flavors) | {"endf6-ext@0.19", "endf6@0.19"}
    for name in flavors:
        assert resolve_endf_flavor(name) == name


def test_get_layout_version():
    assert get_layout_version("endf6-ext") == "endf6-ext@0.19"
    assert get_layout_version("endf6") == "endf6@0.19"
    assert get_layout_version("endf6-ext@0.19") == "endf6-ext@0.19"
    assert get_layout_version("endf6@0.19") == "endf6@0.19"
    assert get_layout_version("jendl") is None
    assert get_layout_version("test") is None


def test_get_layout_version_latest_release(monkeypatch):
    resolved = dict(
        catalogue._RESOLVED,
        **{"endf6-ext@0.20": "endf6-ext", "endf6-ext@0.9": "endf6-ext"},
    )
    monkeypatch.setattr(catalogue, "_RESOLVED", resolved)
    assert get_layout_version("endf6-ext") == "endf6-ext@0.20"
    assert get_layout_version("endf6-ext@0.9") == "endf6-ext@0.9"


@pytest.mark.parametrize(
    "name, match",
    [
        ("endf6@0.19", True),
        ("endf6-ext@1.0", True),
        ("endf6@v1", False),
        ("endf6@0.19.1", False),
        ("endf6@0.019", False),
        ("endf6-v1", False),
    ],
)
def test_layout_version_names(name, match):
    assert (_LAYOUT_VERSION_RE.match(name) is not None) == match


def test_cpp_module_basename():
    assert cpp_module_basename("endf6-ext") == "endf6_ext"
    assert cpp_module_basename("endf6-ext@0.20") == "endf6_ext_0_20"
    assert cpp_module_basename("endf6") == "endf6"


def test_unknown_name():
    with pytest.raises(TypeError, match="`endf6-ext@9.99`"):
        get_recipe_dict("endf6-ext@9.99")
    with pytest.raises(TypeError, match="`endf6-ext@9.99`"):
        resolve_endf_flavor("endf6-ext@9.99")


def test_resolve_aliases_chain():
    targets = {"a": {}, "b": {}}
    aliases = {"a@0.19": "a", "a@0.20": "a@0.19", "b@0.19": "b"}
    resolved = _resolve_aliases(targets, aliases)
    assert resolved == {"a": "a", "b": "b", "a@0.19": "a", "a@0.20": "a", "b@0.19": "b"}
    assert list(resolved) == ["a", "b", "a@0.19", "a@0.20", "b@0.19"]


@pytest.mark.parametrize(
    "aliases, message",
    [
        ({"a@0.1": "x"}, "`a@0.1` refers to `x`"),
        ({"a@0.1": "a@0.2", "a@0.2": "x"}, "`a@0.2` refers to `x`"),
        ({"a@0.1": "a@0.1"}, "cycle of aliases: a@0.1 -> a@0.1"),
        (
            {"a@0.1": "a@0.2", "a@0.2": "a@0.1"},
            "cycle of aliases: a@0.1 -> a@0.2 -> a@0.1",
        ),
        ({"x@0.1": "a@0.1", "a@0.1": "a@0.2", "a@0.2": "a@0.1"}, "cycle of aliases"),
        ({"a": "a"}, "`a` is also the name of a build target"),
        ({"b@0.1": "a"}, "the layout version `b@0.1` stands for `a`"),
    ],
)
def test_resolve_aliases_rejects(aliases, message):
    with pytest.raises(ValueError, match=message):
        _resolve_aliases({"a": {}}, aliases)


def test_build_has_no_module_for_aliases():
    # the extension modules of setup.py, which are the same as before the
    # layout versions were introduced
    setup_py = REPO_ROOT / "setup.py"
    if not setup_py.exists():
        pytest.skip("setup.py is not available")
    pytest.importorskip("pybind11")
    spec = importlib.util.spec_from_file_location("_setup_under_test", setup_py)
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    ext_modules = setup_module.generate_ext_module_list("yes", None)
    names = [ext.name for ext in ext_modules]
    assert names == [
        "endf_parserpy.cpp_parsers.endf6_ext",
        "endf_parserpy.cpp_parsers.endf6",
        "endf_parserpy.cpp_parsers.jendl",
        "endf_parserpy.cpp_parsers.pendf",
        "endf_parserpy.cpp_parsers.errorr",
        "endf_parserpy.cpp_parsers.gendf",
        "endf_parserpy.cpp_parsers.test",
    ]


# the parsers with a layout version that is an alias


ALIAS_CASES = [
    ("endf6-ext@0.19", "endf6-ext", "dec-094_Pu_244.endf"),
    ("endf6-ext@0.19", "endf6-ext", "tsl_Al.endf"),
    ("endf6@0.19", "endf6", "dec-094_Pu_244.endf"),
    ("endf6@0.19", "endf6", "tsl_Al.endf"),
]


@pytest.mark.parametrize("version, flavor, filename", ALIAS_CASES)
def test_python_parser_with_alias(version, flavor, filename):
    path = str(TESTDATA / filename)
    dict_version = EndfParserPy(endf_format=version).parsefile(path)
    dict_flavor = EndfParserPy(endf_format=flavor).parsefile(path)
    compare_objects(dict_version, dict_flavor)


def _cpp_module(flavor):
    name = "endf_parserpy.cpp_parsers." + cpp_module_basename(flavor)
    return pytest.importorskip(name)


@pytest.mark.parametrize(
    "version, flavor, filename",
    ALIAS_CASES + [("endf6-ext@0.19", "endf6-ext", "n_2925_29-Cu-63.endf")],
)
def test_cpp_parser_with_alias(version, flavor, filename):
    module = _cpp_module(flavor)
    path = str(TESTDATA / filename)
    parser_version = EndfParserCpp(endf_format=version)
    parser_flavor = EndfParserCpp(endf_format=flavor)
    assert parser_version._parse_endf is module.parse_endf
    assert parser_version._parse_endf_file is module.parse_endf_file
    assert parser_version._write_endf is module.write_endf
    assert parser_version._write_endf_file is module.write_endf_file
    dict_version = parser_version.parsefile(path)
    compare_objects(dict_version, parser_flavor.parsefile(path))
    assert parser_version.write(dict_version) == parser_flavor.write(dict_version)


def test_cpp_parser_error_names_both_flavors(monkeypatch):
    resolved = dict(catalogue._RESOLVED, **{"nomodule@0.19": "nomodule"})
    monkeypatch.setattr(catalogue, "_RESOLVED", resolved)
    with pytest.raises(ImportError) as exc_info:
        EndfParserCpp(endf_format="nomodule@0.19")
    message = str(exc_info.value)
    assert "`nomodule@0.19`, which stands for the flavor `nomodule`" in message
    assert "endf_parserpy.cpp_parsers.nomodule)" in message


def test_cpp_parser_unknown_name():
    with pytest.raises(ImportError, match="`no-such-flavor`"):
        EndfParserCpp(endf_format="no-such-flavor")


@pytest.mark.parametrize("no_cpp", [False, True])
def test_cli_accepts_layout_version(monkeypatch, capsys, no_cpp):
    from endf_parserpy.cli.cmd import cli_interface

    if not no_cpp:
        _cpp_module("endf6-ext")
    path = str(TESTDATA / "dec-094_Pu_244.endf")
    argv = ["endf-cli", "validate", "--endf_format", "endf6-ext@0.19", path]
    if no_cpp:
        argv.append("--no-cpp")
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc_info:
        cli_interface()
    assert exc_info.value.code == 0
    assert f"ok - {path}" in capsys.readouterr().out


def test_cli_parser_with_layout_version():
    from endf_parserpy.cli.cmd_utils import add_common_cmd_parser_args, get_endf_parser

    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap)
    args = vars(ap.parse_args(["--endf_format", "endf6@0.19", "--no-cpp"]))
    parser = get_endf_parser(args)
    assert isinstance(parser, EndfParserPy)
    path = str(TESTDATA / "dec-094_Pu_244.endf")
    compare_objects(
        parser.parsefile(path), EndfParserPy(endf_format="endf6").parsefile(path)
    )


# copy-on-write, demonstrated on a copy of the test flavor: a breaking
# change of the recipe of MF2/MT1, which renames the variable NX to NITEMS


def _cont(n1, mt, seq):
    ints = "".join(f"{v:11d}" for v in (0, 0, n1, 0))
    return " 0.000000+0 0.000000+0" + ints + f"   1 2{mt:3d}{seq:5d}"


SECTION_MF2_MT1 = "\n".join([_cont(0, 1, 1), _cont(18, 1, 2), _cont(0, 0, 99999)])


def _demo_catalogue(targets, aliases):
    """A catalogue as in catalogue.py: build targets and resolved names."""
    return targets, _resolve_aliases(targets, aliases)


def _demo_parse(targets, resolved, name):
    recipes = targets[resolved[name]]
    parser = EndfParserPy(
        recipes=recipes, ignore_missing_tpid=True, ignore_send_records=True
    )
    return parser.parse(SECTION_MF2_MT1)[2][1]


def test_copy_on_write_demo():
    current = deepcopy(get_recipe_dict("test"))
    old_recipe = current[2][1]
    assert "6*NX" in old_recipe
    # the state before the change: the releases 0.19 and 0.20 have the
    # same layout, so demo@0.19 and demo@0.20 are aliases of demo
    aliases = {"demo@0.19": "demo", "demo@0.20": "demo"}
    targets, resolved = _demo_catalogue({"demo": current}, aliases)
    checksums = {name: _layout_checksum(current) for name in aliases}
    assert _guard_report(resolved, targets, checksums, "strict") == []
    for name in aliases:
        assert _demo_parse(targets, resolved, name)["NX"] == 3

    # the breaking change, made on the flavor only, is reported
    changed = deepcopy(current)
    changed[2][1] = old_recipe.replace("NX", "NITEMS")
    targets, resolved = _demo_catalogue({"demo": changed}, aliases)
    for policy in ("backport", "strict"):
        messages = _guard_report(resolved, targets, checksums, policy)
        assert len(messages) == 2
        assert "`demo@0.20` is an alias of the flavor `demo`" in messages[1]
        assert "copy-on-write" in messages[1]

    # copy-on-write in the release 0.21: demo@0.20 gets a copy of the
    # previous recipe of MF2/MT1 and derives from the flavor for the rest,
    # as jendl from endf6; it becomes a build target, demo@0.19 refers to
    # it, and demo@0.21 is the new alias of demo
    frozen = deepcopy(changed)
    frozen[2][1] = old_recipe
    targets, resolved = _demo_catalogue(
        {"demo": changed, "demo@0.20": frozen},
        {"demo@0.19": "demo@0.20", "demo@0.21": "demo"},
    )
    checksums["demo@0.21"] = _layout_checksum(changed)
    assert _guard_report(resolved, targets, checksums, "strict") == []
    assert list(targets) == ["demo", "demo@0.20"]
    assert resolved["demo@0.19"] == "demo@0.20"
    assert resolved["demo@0.21"] == "demo"
    # the frozen versions keep the old layout, the bare name has the new one
    assert _demo_parse(targets, resolved, "demo@0.19")["NX"] == 3
    assert _demo_parse(targets, resolved, "demo@0.20")["NX"] == 3
    assert "NX" not in _demo_parse(targets, resolved, "demo")
    assert _demo_parse(targets, resolved, "demo")["NITEMS"] == 3
    assert _demo_parse(targets, resolved, "demo@0.21")["NITEMS"] == 3


def test_guard_on_frozen_version_depends_on_policy():
    current = deepcopy(get_recipe_dict("test"))
    frozen = deepcopy(current)
    targets, resolved = _demo_catalogue(
        {"demo": current, "demo@0.20": frozen}, {"demo@0.21": "demo"}
    )
    checksums = {
        "demo@0.20": _layout_checksum(frozen),
        "demo@0.21": _layout_checksum(current),
    }
    # a change of a recipe of the frozen version
    frozen[2][2] = frozen[2][2].replace(
        "SEND", "[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] CONT\nSEND"
    )
    backport = _guard_report(resolved, targets, checksums, "backport")
    strict = _guard_report(resolved, targets, checksums, "strict")
    assert len(backport) == len(strict) == 1
    assert "`demo@0.20` is a frozen version" in strict[0]
    assert "replace the checksum" in backport[0]
    assert "replace the checksum" not in strict[0]


def test_guard_reports_missing_and_extra_checksums():
    current = get_recipe_dict("test")
    targets, resolved = _demo_catalogue({"demo": current}, {"demo@0.19": "demo"})
    messages = _guard_report(resolved, targets, {"demo@0.77": "0"}, "backport")
    assert len(messages) == 2
    assert "No checksum is stored for the layout version `demo@0.19`" in messages[0]
    assert "`demo@0.77`, which is not a layout version" in messages[1]
