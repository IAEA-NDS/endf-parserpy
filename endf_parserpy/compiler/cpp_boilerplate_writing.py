############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/10/27
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


import importlib.resources
from . import cpp_primitives as cpp


def module_header_writing():
    with importlib.resources.open_text(
        "endf_parserpy.compiler.cpp_templates", "module_header_writing.hpp"
    ) as f:
        code = f.read()
    return code


def writefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        void {fun_name}(
          std::ostream& cont, py::dict endf_dict, WritingOptions &write_opts
        ) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          std::string cpp_template;
          double cpp_float_val;
          int cpp_nr_val;
          int cpp_np_val;
          Tab1Body tab1_body;
          Tab2Body tab2_body;
          bool list_mode = write_opts.array_type != "dict";
        """,
        -8,
    )
    # remove empty first line
    code = "\n".join(code.splitlines()[1:])
    return code


def writefun_footer():
    code = cpp.close_block()
    return code
