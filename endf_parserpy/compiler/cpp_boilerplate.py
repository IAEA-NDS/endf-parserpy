############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from ..compat_wrappers.importlib_resources import open_text
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
    BUILD_INFO_MACROS,
    build_info_value,
)
from .cpp_boilerplate_writing import module_header_writing


# Free helper functions in the C++ boilerplate (templates and
# generators) are marked ``inline`` at source so the same boilerplate
# can be safely concatenated into both ``_shared.cpp`` and each flavor's
# ``.cpp``. When both are linked into the same .so, the relaxed-ODR
# semantics of ``inline`` avoid duplicate-symbol errors.
#
# When adding a new helper to ``cpp_templates/*.hpp`` (or to any function
# emitter in this package), mark it with the ``inline`` keyword. Class
# methods and template-class members are implicitly inline so they need
# no annotation.


def _module_header():
    code = ""
    with open_text("endf_parserpy.compiler.cpp_templates", "endf_rational.hpp") as f:
        code += f.read()
    with open_text("endf_parserpy.compiler.cpp_templates", "endf_float_cpp.hpp") as f:
        code += f.read()
    with open_text("endf_parserpy.compiler.cpp_templates", "index_shifter.hpp") as f:
        code += f.read()
    with open_text("endf_parserpy.compiler.cpp_templates", "module_header.hpp") as f:
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


def _register_cpp_funs(funs, docstring, extra_args):
    args_str = ", ".join(arg for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    code = ""
    for fun in funs:
        code += cpp.statement(f'm.def("{fun}", &{fun}, "{docstring}"{args_str})')
    return code


def register_cpp_parsefuns(parsefuns, *extra_args):
    return _register_cpp_funs(parsefuns, "parsing function", extra_args)


def register_cpp_writefuns(writefuns, *extra_args):
    return _register_cpp_funs(writefuns, "writing function", extra_args)


def generate_cmake_content(module_name):
    macros = BUILD_INFO_MACROS
    origin = build_info_value("cmake")
    code = cpp.indent_code(
        f"""
        cmake_minimum_required(VERSION 3.12)

        # With GCC and Clang, Release builds start at -O1 (instead of
        # CMake's -O3), as the package build does: much faster to compile.
        # CMake appends its own -O3 to an init value set here, so the
        # value is set in a file that CMake reads once the compiler is
        # known, before the flags are stored in the cache. MSVC keeps
        # its defaults (/O2). Another level can be chosen with, e.g.,
        #   cmake -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG" ..
        file(WRITE "${{CMAKE_BINARY_DIR}}/release_flags.cmake" [=[
        if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang"
           AND NOT CMAKE_CXX_SIMULATE_ID STREQUAL "MSVC")
          set(CMAKE_CXX_FLAGS_RELEASE_INIT "-O1 -DNDEBUG")
        endif()
        ]=])
        set(CMAKE_USER_MAKE_RULES_OVERRIDE_CXX
            "${{CMAKE_BINARY_DIR}}/release_flags.cmake")

        project({module_name})

        # Optimize unless another build type is given
        if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
          set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
        endif()

        find_package(pybind11 REQUIRED)

        # Create the Python extension module
        pybind11_add_module({module_name} MODULE {module_name}.cpp)

        set_property(TARGET {module_name} PROPERTY CXX_STANDARD 11)

        # The build information that the function _build_info of the
        # module reports: the origin, the build type and the optimization
        # flags of the build type, each as hexadecimal digits after "0x"
        # (string(HEX) needs CMake 3.18; with an older CMake, the module
        # reports "unknown"), which need no quoting with any generator
        if(CMAKE_VERSION VERSION_GREATER_EQUAL 3.18)
          if(CMAKE_CONFIGURATION_TYPES)
            set(build_info_configs ${{CMAKE_CONFIGURATION_TYPES}})
          else()
            set(build_info_configs ${{CMAKE_BUILD_TYPE}})
          endif()
          set(build_info_type "")
          set(build_info_optim "")
          foreach(build_info_config IN LISTS build_info_configs)
            string(TOUPPER "${{build_info_config}}" build_info_upper)
            separate_arguments(build_info_flags NATIVE_COMMAND
              "${{CMAKE_CXX_FLAGS}} ${{CMAKE_CXX_FLAGS_${{build_info_upper}}}}")
            set(build_info_optim_flags "")
            foreach(build_info_flag IN LISTS build_info_flags)
              if(build_info_flag MATCHES "^[-/]O")
                list(APPEND build_info_optim_flags "${{build_info_flag}}")
              endif()
            endforeach()
            list(JOIN build_info_optim_flags " " build_info_text)
            string(HEX "${{build_info_text}}" build_info_hex)
            string(APPEND build_info_optim
              "$<$<CONFIG:${{build_info_config}}>:0x${{build_info_hex}}>")
            string(HEX "${{build_info_config}}" build_info_hex)
            string(APPEND build_info_type
              "$<$<CONFIG:${{build_info_config}}>:0x${{build_info_hex}}>")
          endforeach()
          target_compile_definitions({module_name} PRIVATE
            {macros["origin"]}={origin}
            {macros["build_type"]}=${{build_info_type}}
            {macros["optimization_flags"]}=${{build_info_optim}})
        endif()
        """,
        -8,
    )
    return code
