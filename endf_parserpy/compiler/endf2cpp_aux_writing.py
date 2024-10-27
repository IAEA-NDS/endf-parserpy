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


from . import cpp_primitives as cpp
from .cpp_types.cpp_dtype_aux import map_dtype
from .cpp_types.cpp_varops_query import did_read_var, get_idxstr
from .cpp_types.cpp_varaux import check_variable


def prepare_line(linevar, mat, mf, mt, linenum, write_opts):
    code = cpp.statement(
        f"{linevar} = cpp_prepare_line({mat}, {mf}, {mt}, {linenum}, {write_opts})"
    )
    return code


def prepare_line_la(linevar, mat, mf, mt, linenum, write_opts, lookahead):
    if lookahead:
        return ""
    return prepare_line(linevar, mat, mf, mt, linenum, write_opts)


def prepare_send(linevar, mat, mf, write_opts):
    code = cpp.statement(f"{linevar} = cpp_prepare_send({mat}, {mf}, {write_opts})")
    return code


def prepare_send_la(linevar, mat, mf, write_opts, lookahead):
    if lookahead:
        return ""
    return prepare_send(linevar, mat, mf, write_opts)


def set_numeric_field(linevar, fieldpos, dtype, value, write_opts):
    cpp_dtype = map_dtype(dtype)
    code = cpp.statement(
        f"cpp_write_field<{cpp_dtype}>({linevar}, {fieldpos}, {value}, {write_opts})"
    )
    return code


def set_text_field(linevar, start, length, value):
    code = cpp.statement(f"{linevar}.replace({start}, {length}, {value})")
    return code


def set_custom_int_field(linevar, start_pos, length, value):
    code = cpp.statement(
        f"cpp_write_custom_int_field({linevar}, {start_pos}, {length}, {value})"
    )
    return code


def set_tab1_body(linevar, tab_body, mat, mf, mt, linenum, write_opts):
    code = cpp.statement(
        f"write_tab1_body({linevar}, {tab_body}, {mat}, {mf}, {mt}, {linenum}, {write_opts})"
    )
    return code


def set_tab2_body(linevar, tab_body, mat, mf, mt, linenum, write_opts):
    code = cpp.statement(
        f"write_tab2_body({linevar}, {tab_body}, {mat}, {mf}, {mt}, {linenum}, {write_opts})"
    )
    return code


def open_section(
    vartok, vardict, current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"
):
    check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices

    idxstrs = []
    for i, idxtok in enumerate(indices):
        curidxstr = get_idxstr(vartok, i, vardict)
        idxstrs.append(curidxstr)
    idcsarg = "std::vector<int>({" + ", ".join(idxstrs) + "})"

    code = ""
    code += cpp.statement(f"py::dict {parent_dict} = {current_dict}")
    code += cpp.statement(
        f"{current_dict} = "
        f'cpp_index_shifter_store.get_value("{secname}", {idcsarg}, py::dict())'
    )
    return code


def close_section(current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"):
    code = cpp.statement(f"{current_dict} = {parent_dict}")
    return code


def write_section_verbatim(ostreamvar, listobj, write_opts):
    code = cpp.statement(
        f"write_section_verbatim({ostreamvar}, {listobj}, {write_opts})"
    )
    return code
