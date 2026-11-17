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

"""The C++ module with all flavors and the module names of the flavors
until release 0.18.

- The module endf_parserpy.cpp_parsers._flavors has one entry per build
  target, none for an alias.
- The released module names (endf6_ext, endf6, jendl, pendf, errorr,
  test) are deprecated shims: importing one issues a DeprecationWarning
  that names the importing code, and gives the entry of the module.
  gendf, aliases and frozen layout versions have no shim.
- An extension module of the old layout left in the package directory
  would be imported instead of a shim; the package warns about it, and
  setup.py removes such files when it builds the module.
"""

import importlib
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import endf_parserpy.cpp_parsers as cpp_parsers
from endf_parserpy import EndfParserCpp
from endf_parserpy.cpp_parsers import _historical_modules
from endf_parserpy.endf_recipes import (
    cpp_module_basename,
    list_endf_build_targets,
    list_endf_flavors,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
CPP_PARSERS_DIR = Path(cpp_parsers.__file__).parent

# the module names of the flavors in the releases until 0.18
HISTORICAL_MODULES = ("endf6_ext", "endf6", "jendl", "pendf", "errorr", "test")

# the functions of an entry of the module
ENTRY_FUNCTIONS = (
    "parse_endf",
    "parse_endf_file",
    "write_endf",
    "write_endf_file",
    "_bulk_body_info",
    "_line_read_counts",
)

# the file name of an extension module for this interpreter
SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[0]


def _flavors():
    return pytest.importorskip("endf_parserpy.cpp_parsers._flavors")


def _forget_module(monkeypatch, name):
    # import the module anew in this test; monkeypatch restores the
    # entries of sys.modules and the package attribute afterwards
    monkeypatch.delitem(sys.modules, "endf_parserpy.cpp_parsers." + name, False)
    monkeypatch.delattr(cpp_parsers, name, False)


# --- the module with all flavors ---------------------------------------


def test_cpp_module_has_one_entry_per_build_target():
    flavors = _flavors()
    targets = list_endf_build_targets()
    assert flavors._entries == tuple(cpp_module_basename(t) for t in targets)
    for alias in set(list_endf_flavors()) - set(targets):
        assert not hasattr(flavors, cpp_module_basename(alias))


@pytest.mark.parametrize("target", list_endf_build_targets())
def test_parser_uses_entry_of_build_target(target):
    flavors = _flavors()
    entry = getattr(flavors, cpp_module_basename(target))
    parser = EndfParserCpp(endf_format=target)
    assert parser._parse_endf is entry.parse_endf
    assert parser._write_endf_file is entry.write_endf_file
    # the documented access to the diagnostic functions of a parser
    assert importlib.import_module(parser._parse_endf.__module__) is entry
    for func in ENTRY_FUNCTIONS:
        assert callable(getattr(entry, func))


# --- the deprecated module names ---------------------------------------


def test_historical_module_names_of_package():
    assert _historical_modules.HISTORICAL_MODULES == HISTORICAL_MODULES
    assert set(_historical_modules.PER_FLAVOR_EXTENSION_MODULES) == set(
        HISTORICAL_MODULES
    ) | {"gendf"}


def test_no_shims_but_for_historical_names():
    # no shim for gendf (never released as a module of its own), the
    # aliases and the frozen layout versions
    modules = sorted(
        p.stem
        for p in CPP_PARSERS_DIR.glob("*.py")
        if not p.stem.startswith("_") and p.stem != "endf_parser_cpp"
    )
    assert modules == sorted(HISTORICAL_MODULES)
    for flavor in list_endf_flavors():
        name = cpp_module_basename(flavor)
        if name not in HISTORICAL_MODULES:
            assert not (CPP_PARSERS_DIR / f"{name}.py").exists()
    assert "gendf" in [cpp_module_basename(t) for t in list_endf_build_targets()]
    with pytest.raises(ImportError):
        importlib.import_module("endf_parserpy.cpp_parsers.gendf")


@pytest.mark.parametrize("name", HISTORICAL_MODULES)
def test_shim_warns_and_gives_entry(name, monkeypatch):
    flavors = _flavors()
    entry = getattr(flavors, name)
    target = [t for t in list_endf_build_targets() if cpp_module_basename(t) == name]
    _forget_module(monkeypatch, name)
    with pytest.warns(DeprecationWarning) as record:
        module = importlib.import_module("endf_parserpy.cpp_parsers." + name)
    assert module is entry
    for func in ENTRY_FUNCTIONS:
        assert getattr(module, func) is getattr(entry, func)
    parser = EndfParserCpp(endf_format=target[0])
    assert module.parse_endf is parser._parse_endf
    assert importlib.import_module(module.__name__) is module
    # one warning, which names the importing code and the replacements
    warnings = [w for w in record if issubclass(w.category, DeprecationWarning)]
    assert len(warnings) == 1
    assert warnings[0].filename == __file__
    message = str(warnings[0].message)
    assert message.startswith(
        f"The module endf_parserpy.cpp_parsers.{name} is deprecated"
    )
    assert f'EndfParserCpp(endf_format="{target[0]}")' in message
    assert "importlib.import_module(parser._parse_endf.__module__)" in message
    assert "_bulk_body_info" in message and "_line_read_counts" in message
    # imported once, the module is not executed again
    assert importlib.import_module("endf_parserpy.cpp_parsers." + name) is module


def test_shim_warning_names_import_statement(monkeypatch):
    flavors = _flavors()
    _forget_module(monkeypatch, "endf6_ext")
    with pytest.warns(DeprecationWarning) as record:
        from endf_parserpy.cpp_parsers import endf6_ext
    assert endf6_ext is flavors.endf6_ext
    assert [w.filename for w in record] == [__file__]
    _forget_module(monkeypatch, "jendl")
    with pytest.warns(DeprecationWarning) as record:
        import endf_parserpy.cpp_parsers.jendl
    assert [w.filename for w in record] == [__file__]
    assert endf_parserpy.cpp_parsers.jendl is flavors.jendl


# --- extension modules of the old layout -------------------------------


@pytest.mark.parametrize(
    "basename",
    [
        "endf6.cpython-311-x86_64-linux-gnu.so",
        "endf6_ext.cpython-39-darwin.so",
        "jendl.cp311-win_amd64.pyd",
        "pendf.abi3.so",
        "errorr.so",
        "test.pyd",
        "gendf.cpython-313-aarch64-linux-gnu.so",
    ],
)
def test_stale_extension_filename(basename):
    assert _historical_modules.is_stale_extension_filename(basename)


@pytest.mark.parametrize(
    "basename",
    [
        "_flavors.cpython-311-x86_64-linux-gnu.so",
        "_flavors.cp311-win_amd64.pyd",
        "endf6.py",
        "endf6.cpp",
        "_flavor_endf6.cpp",
        "endf6.so.bak",
        "endf6.cpython-311-x86_64-linux-gnu.so.tmp",
        "endf6_ext_0_19.cpython-311-x86_64-linux-gnu.so",
        "myflavor.cpython-311-x86_64-linux-gnu.so",
        "xendf6.so",
        "endf6.a.b.so",
    ],
)
def test_not_stale_extension_filename(basename):
    assert not _historical_modules.is_stale_extension_filename(basename)


def _make_files(directory, basenames):
    for basename in basenames:
        (directory / basename).write_bytes(b"")


def test_warning_names_stale_file(tmp_path):
    _make_files(
        tmp_path,
        [
            "endf6" + SUFFIX,
            "gendf" + SUFFIX,
            "_flavors" + SUFFIX,
            "endf6.py",
            "endf6.cpp",
            "myflavor" + SUFFIX,
        ],
    )
    expected = [str(tmp_path / ("endf6" + SUFFIX)), str(tmp_path / ("gendf" + SUFFIX))]
    assert _historical_modules.stale_extension_files(str(tmp_path)) == expected
    with pytest.warns(RuntimeWarning) as record:
        paths = _historical_modules.warn_stale_extension_files(str(tmp_path))
    assert paths == expected
    messages = [str(w.message) for w in record]
    assert len(messages) == 2
    for path, message in zip(expected, messages):
        assert message.startswith(f"The file {path} is the C++ extension module")


def test_package_directory_has_no_stale_files():
    assert _historical_modules.stale_extension_files() == []


def _load_setup_module():
    setup_py = REPO_ROOT / "setup.py"
    if not setup_py.exists():
        pytest.skip("setup.py is not available")
    pytest.importorskip("pybind11")
    spec = importlib.util.spec_from_file_location("_setup_under_test", setup_py)
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    return setup_module


def test_setup_removes_only_stale_files(tmp_path):
    setup_module = _load_setup_module()
    stale = [
        "endf6" + SUFFIX,
        "endf6_ext.cpython-39-x86_64-linux-gnu.so",
        "jendl.cp312-win_amd64.pyd",
        "gendf" + SUFFIX,
        "test.abi3.so",
    ]
    kept = [
        "_flavors" + SUFFIX,
        "endf6.py",
        "endf6.cpp",
        "_flavor_endf6.cpp",
        "myflavor" + SUFFIX,
        "endf6_ext_0_19" + SUFFIX,
        "notes.txt",
    ]
    _make_files(tmp_path, stale + kept)
    (tmp_path / ("pendf" + SUFFIX)).mkdir()  # not a file
    removed = setup_module.remove_stale_flavor_extensions(str(tmp_path))
    assert sorted(removed) == sorted(str(tmp_path / b) for b in stale)
    remaining = sorted(os.listdir(tmp_path))
    assert remaining == sorted(kept + ["pendf" + SUFFIX])
    assert setup_module.remove_stale_flavor_extensions(str(tmp_path)) == []
    assert setup_module.remove_stale_flavor_extensions(str(tmp_path / "no")) == []


def test_stale_file_in_package_is_warned_about(tmp_path):
    # a copy of the package (Python files only) with a dummy extension
    # module of the old layout: the package warns about it at import, and
    # Python imports it instead of the shim of the same name
    copy = tmp_path / "site"
    shutil.copytree(
        CPP_PARSERS_DIR.parent,
        copy / "endf_parserpy",
        ignore=shutil.ignore_patterns("*.cpp", "*.so", "*.pyd", "__pycache__"),
    )
    stale = copy / "endf_parserpy" / "cpp_parsers" / ("endf6" + SUFFIX)
    stale.write_bytes(b"")
    code = textwrap.dedent(
        """
        import warnings
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            import endf_parserpy
        for w in record:
            print(w.category.__name__, w.message)
        import importlib.util
        spec = importlib.util.find_spec("endf_parserpy.cpp_parsers.endf6")
        print("origin", spec.origin)
        """
    )
    env = dict(os.environ, PYTHONPATH=str(copy))
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    lines = res.stdout.splitlines()
    stale_warnings = [line for line in lines if line.startswith("RuntimeWarning")]
    assert stale_warnings == [
        f"RuntimeWarning The file {stale} is the C++ extension module `endf6` "
        "of a release before 0.19 of endf-parserpy, which now has one C++ "
        "module (endf_parserpy.cpp_parsers._flavors) for all flavors. Python "
        "imports this file for endf_parserpy.cpp_parsers.endf6 instead of the "
        "current code; delete it, or build the package again (setup.py "
        "removes such files when it builds the C++ module)."
    ]
    # the dummy file shadows the shim
    assert lines[-1] == f"origin {stale}"
