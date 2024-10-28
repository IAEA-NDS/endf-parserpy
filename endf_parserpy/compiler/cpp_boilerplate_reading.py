############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/10/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import importlib.resources
from . import cpp_primitives as cpp


def module_header_reading():
    with importlib.resources.open_text(
        "endf_parserpy.compiler.cpp_templates", "module_header_reading.hpp"
    ) as f:
        code = f.read()

    return code


def register_reading_options():
    code = r"""
    // static bool parsing_options_registered = false;
    // if (! parsing_options_registered) {
    //   py::class_<ParsingOptions>(m, "ParsingOptions")
    //     .def(py::init<>())
    //     .def_readwrite("ignore_number_mismatch", &ParsingOptions::ignore_number_mismatch)
    //     .def_readwrite("ignore_zero_mismatch", &ParsingOptions::ignore_zero_mismatch)
    //     .def_readwrite("ignore_varspec_mismatch", &ParsingOptions::ignore_varspec_mismatch)
    //     .def_readwrite("accept_spaces", &ParsingOptions::accept_spaces)
    //     .def_readwrite("ignore_blank_lines", &ParsingOptions::ignore_blank_lines)
    //     .def_readwrite("ignore_send_records", &ParsingOptions::ignore_send_records)
    //     .def_readwrite("ignore_missing_tpid", &ParsingOptions::ignore_missing_tpid)
    //     .def_readwrite("validate_control_records", &ParsingOptions::validate_control_records);
    //   parsing_options_registered = true;
    // }
    """
    return cpp.indent_code(code, -4)


def parsefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        py::dict {fun_name}(
          std::istream& cont, ParsingOptions &parse_opts
        ) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          std::string cpp_template;
          double cpp_float_val;
          int cpp_nr_val;
          int cpp_np_val;
          bool list_mode = parse_opts.array_type != "dict";
        """,
        -8,
    )
    # remove empty first line
    code = "\n".join(code.splitlines()[1:])
    return code


def parsefun_footer():
    code = cpp.statement("return cpp_current_dict", cpp.INDENT)
    code += cpp.close_block()
    return code
