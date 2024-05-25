############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/25
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from . import cpp_primitives as cpp


def prepare_line(linevar, mat, mf, mt):
    code = cpp.statement(f"{linevar} = cpp_prepare_line({mat}, {mf}, {mt})")
    return code


def prepare_line_la(linevar, mat, mf, mt, lookahead):
    if lookahead:
        return ""
    return prepare_line(linevar, mat, mf, mt)


def prepare_send(linevar, mat, mf):
    code = cpp.statement(f"{linevar} = cpp_prepare_send({mat}, {mf})")
    return code


def prepare_send_la(linevar, mat, mf, lookahead):
    if lookahead:
        return ""
    return prepare_send(linevar, mat, mf)


def set_numeric_field(linevar, fieldpos, dtype, value):
    dtypestr = {float: "double", int: "int"}[dtype]
    code = cpp.statement(f"cpp_write_field<{dtypestr}>({linevar}, {fieldpos}, {value})")
    return code


def set_text_field(linevar, start, length, value):
    code = cpp.statement(f"{linevar}.replace({start}, {length}, {value})")
    return code


def set_custom_int_field(linevar, start_pos, length, value):
    code = cpp.statement(
        f"cpp_write_custom_int_field({linevar}, {start_pos}, {length}, {value})"
    )
    return code


def set_tab1_body(linevar, tab_body, mat, mf, mt):
    code = cpp.statement(f"write_tab1_body({linevar}, {tab_body}, {mat}, {mf}, {mt})")
    return code


def set_tab2_body(linevar, tab_body, mat, mf, mt):
    code = cpp.statement(f"write_tab2_body({linevar}, {tab_body}, {mat}, {mf}, {mt})")
    return code


def write_section_verbatim(ostreamvar, listobj):
    code = cpp.statement(f"write_section_verbatim({ostreamvar}, {listobj})")
    return code
