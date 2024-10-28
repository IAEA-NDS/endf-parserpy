############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/10/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.lexer import Token
from .expr_utils.equation_utils import get_variables_in_expr
from .expr_utils.custom_nodes import VariableToken
from . import cpp_primitives as cpp
from .cpp_types.cpp_dtype_aux import map_dtype
from .cpp_types.cpp_varops_query import did_read_var, get_idxstr
from .cpp_types.cpp_varaux import check_variable, get_cpp_varname
from .lookahead_management import in_lookahead
from .mode_management import (
    get_prepare_line_func,
    get_numeric_field_getter,
    get_finalize_line_func,
)


def define_current_template(template):
    tmpl = template.replace("\n", r"\n")
    code = cpp.statement(f'cpp_template = "{tmpl}"')
    return code


def get_current_template():
    return "cpp_template"


def read_raw_line(linevar):
    code = cpp.statement(f"{linevar} = cpp_read_raw_line(cont)")
    return code


def read_send(mat, mf, parse_opts):
    code = cpp.statement(f"cpp_read_send(cont, {mat}, {mf}, {parse_opts})")
    return code


def is_fend(mat, parse_opts):
    return f"cpp_is_fend_record(cpp_line, {mat}, {parse_opts})"
    return code


def is_mend(parse_opts):
    return f"cpp_is_mend_record(cpp_line, {parse_opts})"


def is_tend(parse_opts):
    return f"cpp_is_tend_record(cpp_line, {parse_opts})"


def is_blank_line():
    return "cpp_is_blank_line(cpp_line)"


def read_line(linevar, mat, mf, mt, parse_opts):
    code = cpp.statement(
        f"{linevar} = cpp_read_line(cont, {mat}, {mf}, {mt}, {parse_opts})"
    )
    return code


def read_line_la(linevar, mat, mf, mt, parse_opts, lookahead):
    if lookahead:
        return read_raw_line(linevar)
    else:
        return read_line(linevar, mat, mf, mt, parse_opts)


def get_mat_number(linevar):
    code = f"cpp_read_mat_number({linevar}.c_str())"
    return code


def get_mf_number(linevar):
    code = f"cpp_read_mf_number({linevar}.c_str())"
    return code


def get_mt_number(linevar):
    code = f"cpp_read_mt_number({linevar}.c_str())"
    return code


def get_int_field(idx, parse_opts):
    cpp_dtype = map_dtype(int)
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.c_str(), {idx}, {parse_opts})"
    return code


def get_custom_int_field(start_pos, length):
    code = f"cpp_read_custom_int_field(cpp_line.c_str(), {start_pos}, {length})"
    return code


def get_int_vec(numel, parse_opts):
    cpp_dtype = map_dtype(int)
    code = cpp.statement(f"cpp_read_vec<{cpp_dtype}>(cont, {numel}, {parse_opts})")
    return code


def get_float_vec(nume, parse_opts):
    cpp_dtype = map_dtype(float)
    code = cpp.statement(f"cpp_read_vec<{cpp_dtype}>(cont, {numel}, {parse_opts})")
    return code


def get_numeric_field(fieldpos, dtype, parse_opts):
    cpp_dtype = map_dtype(dtype)
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.c_str(), {fieldpos}, {parse_opts})"
    return code


def get_text_field(start, length):
    code = f"cpp_line.substr({start}, {length})"
    return code


def _map_bool(boolexpr):
    return "true" if boolexpr else "false"


def validate_field(
    expected_value,
    actual_value,
    contains_variable,
    contains_desired_number,
    contains_inconsistent_varspec,
    exprstr,
    line_template,
    parse_opts,
):
    cont_var = _map_bool(contains_variable)
    cont_des_num = _map_bool(contains_desired_number)
    cont_incons_var = _map_bool(contains_inconsistent_varspec)
    code = cpp.statement(
        f"cpp_validate_field({expected_value}, {actual_value}, "
        + f" {cont_var}, {cont_des_num}, {cont_incons_var}, "
        + f"{exprstr},"
        + ("\n" + " " * cpp.INDENT if line_template else " ")
        + f"{line_template}, cpp_line, {parse_opts})"
    )
    return code


def get_tab1_body(xvar, yvar, nr, np, mat, mf, mt, parse_opts):
    code = f"read_tab1_body(cont, {nr}, {np}, {mat}, {mf}, {mt}, {parse_opts})"
    return code


def get_tab2_body(nr, mat, mf, mt, parse_opts):
    code = f"read_tab2_body(cont, {nr}, {mat}, {mf}, {mt}, {parse_opts})"
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
        f'cpp_index_shifter_store.setdefault("{secname}", {idcsarg}, py::dict())'
    )
    return code


def close_section(current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"):
    code = cpp.statement(f"{current_dict} = {parent_dict}")
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


def read_section_verbatim(tarvec, mat, mf, mt, cont, is_firstline, parse_opts):
    code = cpp.statement(
        f"{tarvec} = read_section_verbatim({mat}, {mf}, {mt}, {cont}, "
        + f"{is_firstline}, {parse_opts})"
    )
    return code


class ListBodyRecorder:

    @staticmethod
    def start_list_body_loop(npl_val, vardict):
        code = cpp.open_block()
        code += cpp.statement(f"int cpp_npl = {npl_val}", cpp.INDENT)
        code += cpp.statement("int cpp_i = 0", cpp.INDENT)
        code += cpp.statement("int cpp_j = 0", cpp.INDENT)
        code += cpp.indent_code(get_prepare_line_func(vardict)(vardict), cpp.INDENT)
        return code

    @staticmethod
    def finish_list_body_loop(vardict):
        code = cpp.indent_code(
            cpp.pureif(
                "cpp_i != cpp_npl",
                cpp.statement(
                    'throw std::runtime_error("not exactly NPL elements consumed")'
                ),
            ),
            cpp.INDENT,
        )
        code += cpp.close_block()
        code += get_finalize_line_func(vardict)(vardict)
        return code

    @staticmethod
    def get_element(node, vardict):
        valcode, addcode = get_numeric_field_getter(vardict)(
            node, "cpp_j", float, vardict
        )
        return valcode, addcode

    @staticmethod
    def update_counters_and_line(vardict):
        code = cpp.statement("cpp_i++")
        code += cpp.statement("cpp_j++")
        code += cpp.pureif(
            cpp.logical_and(["cpp_j > 5", "cpp_i < cpp_npl"]),
            cpp.concat(
                [
                    get_finalize_line_func(vardict)(vardict),
                    get_prepare_line_func(vardict)(vardict),
                    cpp.statement("cpp_j = 0"),
                ]
            ),
        )
        return code

    @staticmethod
    def indent(code):
        return cpp.indent_code(code, cpp.INDENT)
