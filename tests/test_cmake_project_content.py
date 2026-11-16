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

"""Tests of the CMakeLists.txt written by create_project_files.

The file compiled the module without optimization: it gave
add_compile_options(-O3) after the target was created, where it has no
effect, and no build type. It also created the target as a SHARED
library, which pybind11 cannot build when it uses CMake's FindPython.
Release builds with GCC and Clang now start at -O1, as the package
build does, through the init value of the Release flags, so that a
level given by the user is kept.
"""

import re

from endf_parserpy.compiler.cpp_boilerplate import generate_cmake_content


def test_release_build_type_set_before_find_package():
    lines = generate_cmake_content("cpp_endf").splitlines()
    build_type = next(i for i, l in enumerate(lines) if "CMAKE_BUILD_TYPE Release" in l)
    find_package = next(i for i, l in enumerate(lines) if "find_package" in l)
    assert build_type < find_package
    # a build type given on the command line is kept
    condition = lines[build_type - 1]
    assert condition.startswith("if(NOT CMAKE_BUILD_TYPE")
    assert "CMAKE_CONFIGURATION_TYPES" in condition


def test_module_target_without_compile_options():
    content = generate_cmake_content("cpp_endf")
    assert "pybind11_add_module(cpp_endf MODULE cpp_endf.cpp)" in content
    assert "SHARED" not in content
    assert "add_compile_options" not in content


def test_release_flags_init_value_before_project():
    content = generate_cmake_content("cpp_endf")
    lines = content.splitlines()
    project = next(i for i, l in enumerate(lines) if l.startswith("project("))
    init = next(i for i, l in enumerate(lines) if "CMAKE_CXX_FLAGS_RELEASE_INIT" in l)
    override = next(
        i for i, l in enumerate(lines) if "CMAKE_USER_MAKE_RULES_OVERRIDE_CXX" in l
    )
    assert init < override < project
    assert 'set(CMAKE_CXX_FLAGS_RELEASE_INIT "-O1 -DNDEBUG")' in lines[init]
    # only for GCC and Clang, not for MSVC or clang-cl
    assert 'MATCHES "GNU|Clang"' in lines[init - 2]
    assert 'NOT CMAKE_CXX_SIMULATE_ID STREQUAL "MSVC"' in lines[init - 1]


def test_no_hard_coded_optimization_level():
    content = generate_cmake_content("cpp_endf")
    code = "\n".join(l for l in content.splitlines() if not l.startswith("#"))
    assert re.search(r"(add|target)_compile_options", code) is None
    assert "-O3" not in code
    assert code.count("-O1") == 1  # the init value only
