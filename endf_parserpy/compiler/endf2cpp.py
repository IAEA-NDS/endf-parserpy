############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from . import cpp_boilerplate
from .code_generator_core import (
    generate_cpp_parsefun,
)
from .code_generator_parsing import (
    _mf_mt_parsefun_name,
    generate_cpp_parsefun_wrappers_string,
    generate_cpp_parsefun_wrappers_file,
    generate_master_parsefun,
)


def generate_cpp_module_code(recipes, module_name):
    module_header = cpp_boilerplate.module_header()
    parsefuns_code = ""
    func_names = []
    recipefuns = {}
    for mf, mt_recipes in recipes.items():
        if isinstance(mt_recipes, str):
            print(f"MF: {mf}")
            func_name = _mf_mt_parsefun_name(mf, None)
            func_names.append(func_name)
            recipe = mt_recipes
            parsefuns_code += generate_cpp_parsefun(
                func_name + "_istream", recipe, mf=mf, mt=None
            )
            recipefuns[mf] = func_name
            continue
        for mt, recipe in mt_recipes.items():
            print(f"MF: {mf} MT: {mt}")
            func_name = _mf_mt_parsefun_name(mf, mt)
            func_names.append(func_name)
            mt_ = mt if mt != -1 else None
            parsefuns_code += generate_cpp_parsefun(
                func_name + "_istream", recipe, mf=mf, mt=mt_
            )
            curdic = recipefuns.setdefault(mf, {})
            curdic[mt] = func_name
    parsefun_wrappers_code1 = generate_cpp_parsefun_wrappers_string(
        func_names, ("ParsingOptions", "parse_opts")
    )
    parsefun_wrappers_code2 = generate_cpp_parsefun_wrappers_file(
        func_names, ("ParsingOptions", "parse_opts")
    )
    pybind_glue = cpp_boilerplate.register_cpp_parsefuns(func_names, module_name)
    # special case for the master function calling the other mf/mt parser funs
    master_parsefun_code = generate_master_parsefun("parse_endf_istream", recipefuns)
    parsefun_wrappers_code1 += generate_cpp_parsefun_wrappers_string(
        ["parse_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    parsefun_wrappers_code2 += generate_cpp_parsefun_wrappers_file(
        ["parse_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["parse_endf"],
        module_name,
        'py::arg("cont")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = false',
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["parse_endf_file"],
        module_name,
        'py::arg("filename")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = default_parsing_options()',
    )

    pybind_glue = cpp_boilerplate.register_pybind_module(module_name, pybind_glue)
    code = (
        module_header
        + parsefuns_code
        + master_parsefun_code
        + parsefun_wrappers_code1
        + parsefun_wrappers_code2
        + pybind_glue
    )
    return code
