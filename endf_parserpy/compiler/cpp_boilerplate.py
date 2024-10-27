############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/10/27
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import importlib.resources
from . import cpp_primitives as cpp
from .cpp_types.cpp_type_information import get_vartype_definitions
from .cpp_types.cpp_vartype_handling import (
    construct_vartype_dtype_enum,
    construct_vartype2str_func,
    construct_vartype_validation_func,
)
from .cpp_boilerplate_reading import (
    register_reading_options,
    module_header_reading,
)
from .cpp_boilerplate_writing import module_header_writing


def _module_header():
    code = ""
    with importlib.resources.open_text(
        "endf_parserpy.compiler.cpp_templates", "endf_float_cpp.hpp"
    ) as f:
        code += f.read()
    with importlib.resources.open_text(
        "endf_parserpy.compiler.cpp_templates", "index_shifter.hpp"
    ) as f:
        code += f.read()
    with importlib.resources.open_text(
        "endf_parserpy.compiler.cpp_templates", "module_header.hpp"
    ) as f:
        code += f.read()
    return code


def module_header():
    code = cpp.line("#define PYTHON_COMPILE")
    code += _module_header()
    code += module_header_reading()
    code += module_header_writing()
    code += cpp.line("")
    code += construct_vartype_dtype_enum()
    code += cpp.line("")
    code += construct_vartype2str_func()
    code += cpp.line("")
    code += construct_vartype_validation_func()
    for vartype_definition in get_vartype_definitions():
        code += vartype_definition
    return code


def register_pybind_module(module_name, inner_code):
    code = cpp.line("") + cpp.line("")
    code += cpp.line(f"PYBIND11_MODULE({module_name}, m) {{")
    code += cpp.indent_code(register_reading_options(), cpp.INDENT)
    code += cpp.indent_code(inner_code, cpp.INDENT)
    code += cpp.close_block()
    return code


def register_cpp_parsefuns(parsefuns, module_name, *extra_args):
    args_str = ", ".join(arg for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    code = ""
    for parsefun in parsefuns:
        curcode = cpp.statement(
            f'm.def("{parsefun}", &{parsefun}, "parsing function"{args_str})'
        )
        code += curcode
    return code


def generate_cmake_content(module_name):
    code = cpp.indent_code(
        f"""
        cmake_minimum_required(VERSION 3.12)
        project({module_name})

        find_package(pybind11 REQUIRED)

        # Create the C++ executable
        pybind11_add_module({module_name} SHARED {module_name}.cpp)

        add_compile_options(-O3)
        set_property(TARGET {module_name} PROPERTY CXX_STANDARD 11)
        """,
        -8,
    )
    return code
