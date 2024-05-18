############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/18
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from . import cpp_boilerplate
from .code_generator_parsing import generate_all_cpp_parsefuns_code
from .code_generator_writing import generate_all_cpp_writefuns_code


def generate_cpp_module_code(recipes, module_name):
    parsefuns_code, parsefuns_pybind_glue = generate_all_cpp_parsefuns_code(
        recipes, module_name
    )
    writefuns_code, writefuns_pybind_glue = generate_all_cpp_writefuns_code(
        recipes, module_name
    )

    funs_code = parsefuns_code + writefuns_code
    pybind_glue = parsefuns_pybind_glue + writefuns_pybind_glue

    module_header = cpp_boilerplate.module_header()
    pybind_glue = cpp_boilerplate.register_pybind_module(module_name, pybind_glue)
    code = module_header + funs_code + pybind_glue
    return code
