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
"""

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
