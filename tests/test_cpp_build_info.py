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

"""Tests of the build information of the C++ module (``_build_info``).

The build gives the origin, the build type and the optimization flags as
compile definitions with the text in hexadecimal digits, which need no
quoting on any command line; the compiler and the C++ standard come from
the macros of the compiler.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from endf_parserpy.compiler.cpp_boilerplate import generate_cmake_content
from endf_parserpy.compiler.cpp_boilerplate_reading import (
    BUILD_INFO_MACROS,
    build_info_value,
    register_diagnostic_functions,
    register_reading_options,
)
from endf_parserpy.compiler.endf2cpp import generate_cpp_flavors_module_code


REPO_ROOT = Path(__file__).resolve().parent.parent

FIELDS = (
    "compiler",
    "compiler_version",
    "cplusplus",
    "cpp_standard",
    "ndebug",
    "origin",
    "build_type",
    "optimization_flags",
    "optimization",
)


def test_build_info_value_is_a_preprocessing_number():
    assert build_info_value("-O1") == "0x2d4f31"
    assert build_info_value("/O2") == "0x2f4f32"
    assert build_info_value("") == "0x"
    value = build_info_value('-O3 -DX="a b"')
    assert value.startswith("0x")
    assert all(c in "0123456789abcdef" for c in value[2:])


def test_build_info_in_both_module_inits():
    assert 'm.def("_build_info"' in register_reading_options()
    assert 'm.def("_build_info"' in register_diagnostic_functions()
    # once in the module with all flavors, where the diagnostic functions
    # are defined for the module and each entry
    code = generate_cpp_flavors_module_code("_flavors", ["a", "b"])
    assert code.count('m.def("_build_info"') == 1
    for macro in BUILD_INFO_MACROS.values():
        assert f"#ifdef {macro}" in code


def test_cmake_content_gives_the_build_info():
    content = generate_cmake_content("cpp_endf")
    assert "target_compile_definitions(cpp_endf PRIVATE" in content
    assert f"{BUILD_INFO_MACROS['origin']}={build_info_value('cmake')}" in content
    assert f"{BUILD_INFO_MACROS['build_type']}=${{build_info_type}}" in content
    assert f"{BUILD_INFO_MACROS['optimization_flags']}=${{build_info_optim}}" in (
        content
    )
    assert "string(HEX" in content
    assert "VERSION_GREATER_EQUAL 3.18" in content


def _setup_module():
    setup_py = REPO_ROOT / "setup.py"
    if not setup_py.exists():
        pytest.skip("setup.py is not available")
    pytest.importorskip("pybind11")
    spec = importlib.util.spec_from_file_location("_setup_build_info", setup_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decode(value):
    assert value.startswith("0x")
    return bytes.fromhex(value[2:]).decode("utf-8")


def test_setup_build_info_macros_gcc():
    setup = _setup_module()
    compiler = SimpleNamespace(
        compiler_type="unix",
        compiler_so=["gcc", "-DNDEBUG", "-g", "-O2", "-Wall", "-O3"],
    )
    ext = SimpleNamespace(extra_compile_args=["-std=c++11", "-O1"])
    macros = dict(setup.build_info_macros(compiler, ext, False))
    assert _decode(macros[BUILD_INFO_MACROS["optimization_flags"]]) == "-O2 -O3 -O1"
    assert _decode(macros[BUILD_INFO_MACROS["build_type"]]) == "Release"
    assert _decode(macros[BUILD_INFO_MACROS["origin"]]) in ("setup.py", "cibuildwheel")


def test_setup_build_info_macros_msvc(monkeypatch):
    setup = _setup_module()
    monkeypatch.setenv("CIBUILDWHEEL", "1")
    compiler = SimpleNamespace(
        compiler_type="msvc",
        initialized=True,
        compile_options=["/nologo", "/O2", "/W3", "/GL", "/DNDEBUG", "/MD"],
        compile_options_debug=["/nologo", "/Od", "/MDd", "/Zi"],
    )
    ext = SimpleNamespace(extra_compile_args=["-std=c++11", "/O2"])
    macros = dict(setup.build_info_macros(compiler, ext, False))
    assert _decode(macros[BUILD_INFO_MACROS["optimization_flags"]]) == "/O2 /O2"
    assert _decode(macros[BUILD_INFO_MACROS["origin"]]) == "cibuildwheel"
    macros = dict(setup.build_info_macros(compiler, ext, True))
    assert _decode(macros[BUILD_INFO_MACROS["optimization_flags"]]) == "/Od /O2"
    assert _decode(macros[BUILD_INFO_MACROS["build_type"]]) == "Debug"


def test_build_info_of_the_module():
    flavors = pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    info = flavors._build_info()
    assert set(info) == set(FIELDS)
    for field in FIELDS:
        assert info[field] not in ("", None), field
    assert info["compiler"] in ("gcc", "clang", "apple-clang", "clang-cl", "msvc")
    assert info["cplusplus"] >= 201103
    assert info["cpp_standard"].startswith("C++")
    # a module built by setup.py or cibuildwheel gives its origin and flags
    assert info["origin"] in ("setup.py", "cibuildwheel")
    assert info["build_type"] in ("Release", "Debug")
    flags = info["optimization_flags"].split()
    assert flags and info["optimization"] == flags[-1]
    assert info["optimization"][:2] in ("-O", "/O")
    # the same for every entry
    for entry in flavors._entries:
        assert getattr(flavors, entry)._build_info() == info
