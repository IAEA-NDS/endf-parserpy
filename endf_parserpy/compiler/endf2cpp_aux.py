############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/05
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .expr_utils.equation_utils import get_variables_in_expr
from . import cpp_primitives as cpp
from .cpp_types.cpp_varops_query import did_read_var
from .cpp_types.cpp_varaux import check_variable, get_cpp_varname


def read_send():
    code = cpp.statement("cpp_read_send(cont)")
    return code


def read_line():
    code = cpp.statement("cpp_line = cpp_read_line(cont)")
    return code


def get_int_field(idx):
    code = f"cpp_read_field<int>(cpp_line.c_str(), {idx})"
    return code


def get_custom_int_field(start_pos, length):
    code = f"cpp_read_custom_int_field(cpp_line.c_str(), {start_pos}, {length})"
    return code


def get_int_vec(numel):
    code = cpp.statement("cpp_read_vec<int>(cont, {numel})")
    return code


def get_float_vec(numel):
    code = cpp.statement(f"cpp_read_vec<double>(cont, {numel})")
    return code


def get_numeric_field(fieldpos, dtype):
    dtypestr = {float: "double", int: "int"}[dtype]
    code = f"cpp_read_field<{dtypestr}>(cpp_line.c_str(), {fieldpos})"
    return code


def get_text_field(start, length):
    code = f"cpp_line.substr({start}, {length})"
    return code


def get_tab1_body(xvar, yvar, nr, np):
    code = cpp.statement(f"read_tab1_body(cont, {nr}, {np})")
    return code


def get_tab2_body(nr):
    code = cpp.statement(f"read_tab2_body(cont, {nr})")
    return code


def open_section(vartok, vardict):
    check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices
    code = cpp.indent_code(
        f"""
    {{
        py::dict cpp_parent_dict = cpp_current_dict;
        if (! cpp_parent_dict.contains("{secname}")) {{
          cpp_parent_dict["{secname}"] = py::dict();
        }}
        py::dict cpp_current_dict = cpp_parent_dict["{secname}"];
        """,
        -4,
    )
    for idx in indices:
        cpp_idxstr = get_cpp_varname(idx, vardict)
        idxstr = f"py::cast({cpp_idxstr})"
        code += cpp.indent_code(
            f"""
        if (! cpp_current_dict.contains({idxstr})) {{
          cpp_current_dict[{idxstr}] = py::dict();
        }}
        cpp_current_dict = cpp_current_dict[{idxstr}];
        """,
            -4,
        )
    return code


def close_section():
    code = cpp.statement("cpp_current_dict = cpp_parent_dict", cpp.INDENT)
    code += cpp.close_block()
    return code


def did_not_read_var(vartok, vardict, indices=None):
    return "(! " + did_read_var(vartok, vardict, indices) + ")"


def any_unread_vars(vartoks, vardict, glob=False):
    if glob:
        return cpp.logical_or(did_not_read_var(v, vardict) for v in vartoks)
    else:
        return cpp.logical_or(did_not_read_var(v, vardict, v.indices) for v in vartoks)


def did_encounter_var(vartok, vardict):
    while vartok not in vardict and "__up" in vardict:
        vardict = vardict["__up"]
    return vartok in vardict


def count_not_encountered_vars(node, vardict):
    varset = get_variables_in_expr(node)
    return sum(not did_encounter_var(v, vardict) for v in varset)


def should_parse_section(mf, mt, exclude, include):
    return f"should_parse_section({mf}, {mt}, {exclude}, {include})"


def should_not_parse_section(mf, mt, exclude, include):
    return cpp.logical_not(should_parse_section(mf, mt, exclude, include))


def read_section_verbatim(tarvec, mf, mt, cont, is_firstline):
    code = cpp.statement(
        f"{tarvec} = read_section_verbatim({mf}, {mt}, {cont}, {is_firstline})"
    )
    return code
