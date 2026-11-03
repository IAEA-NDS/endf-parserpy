############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from endf_parserpy.recipe_parser.tree import Token
from endf_parserpy.utils.tree_utils import get_name
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
    get_float_row_form,
)


def _template_literal(template):
    return template.replace("\n", r"\n")


def define_current_template(template):
    # when reading, cpp_template is ParsingOptions::current_template,
    # the template shown in error messages
    tmpl = _template_literal(template)
    code = cpp.statement(f'cpp_template = "{tmpl}"')
    return code


def define_record_body_template(template):
    # the template preceded by CPP_BODY_MARK (octal 001): the lines of the
    # body of a TAB1, TAB2 or LIST record are read (see ParsingOptions)
    tmpl = _template_literal(template)
    code = cpp.statement(f'cpp_template = "\\001{tmpl}"')
    return code


def read_raw_line(linevar):
    code = cpp.statement(f"cpp_read_raw_line({linevar}, cont)")
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
        f"cpp_read_line({linevar}, cont, {mat}, {mf}, {mt}, {parse_opts})"
    )
    return code


def read_line_la(linevar, mat, mf, mt, parse_opts, lookahead):
    if lookahead:
        return read_raw_line(linevar)
    else:
        return read_line(linevar, mat, mf, mt, parse_opts)


def get_mat_number(linevar):
    code = f"cpp_read_mat_number({linevar}.data())"
    return code


def get_mf_number(linevar):
    code = f"cpp_read_mf_number({linevar}.data())"
    return code


def get_mt_number(linevar):
    code = f"cpp_read_mt_number({linevar}.data())"
    return code


def get_int_field(idx, parse_opts):
    cpp_dtype = map_dtype(int)
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.data(), {idx}, {parse_opts})"
    return code


def get_custom_int_field(start_pos, length):
    code = f"cpp_read_custom_int_field(cpp_line.data(), {start_pos}, {length})"
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
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.data(), {fieldpos}, {parse_opts})"
    return code


_NUMERIC_FIELD_RE = re.compile(r"cpp_read_field<\w+>\(cpp_line\.data\(\), (\d+), \w+\)")


def get_numeric_field_position(valcode):
    """Return the field position of code returned by
    :func:`get_numeric_field`, or -1 for any other code."""
    m = _NUMERIC_FIELD_RE.fullmatch(valcode)
    return int(m.group(1)) if m else -1


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
    parse_opts,
):
    cont_var = _map_bool(contains_variable)
    cont_des_num = _map_bool(contains_desired_number)
    cont_incons_var = _map_bool(contains_inconsistent_varspec)
    # the field of the value for error messages (-1 if not a single field)
    fieldnum = get_numeric_field_position(actual_value)
    code = cpp.statement(
        f"cpp_validate_field({expected_value}, {actual_value}, "
        + f" {cont_var}, {cont_des_num}, {cont_incons_var}, "
        + f"{exprstr},"
        + "\n"
        + " " * cpp.INDENT
        + f"{fieldnum}, {parse_opts})"
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


class FloatRowForm:
    """The row form of the reading of the body of a LIST record.

    The body is read in today's per-field form (each float value with
    ``cpp_read_field``) and, in a second copy, in the row form: the float
    fields of each line of the body are converted by one call of the row
    kernel selected when the module is loaded (``CppFloatRow`` in
    ``module_header_reading.hpp``), and each value is taken from the
    converted fields, or read with ``cpp_read_field`` if the kernel has
    left the field. The form is chosen once per record: the row form only
    if a row kernel is selected (``cpp_float_row_kernel``).

    The code of the body is generated once, with the statements of the row
    form (:attr:`declaration` and :attr:`conversion`, see
    :class:`ListBodyRecorder`); :meth:`select_form` derives both forms
    from it, so that the per-field form is exactly the code generated
    without the row form.
    """

    declaration = cpp.statement(
        "CppFloatRow cpp_row(cpp_float_row_kernel(), parse_opts)"
    )
    # after a line of the body is read, cpp_npl - cpp_i values remain
    conversion = cpp.statement("cpp_row.convert(cpp_line.data(), cpp_npl - cpp_i)")
    condition = "cpp_float_row_kernel() == nullptr"

    @staticmethod
    def _element_regex():
        # the reading of a float value of the body (see
        # ListBodyRecorder.get_element and get_numeric_field)
        cpp_dtype = re.escape(map_dtype(float))
        return re.compile(
            rf"\bcpp_read_field<({cpp_dtype})>\(cpp_line\.data\(\), cpp_j, (\w+)\)"
        )

    @classmethod
    def select_form(cls, code, with_row_form=True):
        """Return the code that reads the body of a LIST record in the form
        chosen at runtime, from the code ``code`` generated with the
        statements of the row form. Only the per-field form is returned if
        ``with_row_form`` is false or the body reads no float value with
        ``cpp_read_field``."""
        marks = (cls.declaration.strip(), cls.conversion.strip())
        lines = code.splitlines(keepends=True)
        per_field_code = "".join(s for s in lines if s.strip() not in marks)
        row_code, count = cls._element_regex().subn(
            r"cpp_read_row_field<\1>(cpp_row, cpp_line.data(), cpp_j, \2)", code
        )
        if count == 0 or not with_row_form:
            return per_field_code
        return cpp.ifelse(cls.condition, per_field_code, row_code)


class ListBodyRecorder:

    @staticmethod
    def _row_form(vardict):
        # the row form, if registered for the mode, except in a lookahead
        if in_lookahead(vardict):
            return None
        return get_float_row_form(vardict)

    @staticmethod
    def start_list_body_loop(npl_val, vardict):
        row_form = ListBodyRecorder._row_form(vardict)
        code = cpp.open_block()
        code += cpp.statement(f"int cpp_npl = {npl_val}", cpp.INDENT)
        code += cpp.statement("int cpp_i = 0", cpp.INDENT)
        code += cpp.statement("int cpp_j = 0", cpp.INDENT)
        if row_form is not None:
            code += cpp.indent_code(row_form.declaration, cpp.INDENT)
        # only read the first body line if the LIST is non-empty; an
        # NPL=0 LIST occupies its header line only, and an unconditional
        # read would consume the following record (e.g. the SEND)
        first_line_code = get_prepare_line_func(vardict)(vardict)
        if row_form is not None:
            first_line_code += row_form.conversion
        code += cpp.indent_code(
            cpp.pureif("cpp_npl > 0", first_line_code),
            cpp.INDENT,
        )
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
        # as the first body line, the last one only exists if the LIST is
        # non-empty; finalizing it unconditionally would write the header
        # line of an NPL=0 LIST a second time
        finalize_code = get_finalize_line_func(vardict)(vardict)
        if finalize_code:
            code += cpp.indent_code(
                cpp.pureif("cpp_npl > 0", finalize_code), cpp.INDENT
            )
        code += cpp.close_block()
        return code

    @staticmethod
    def select_form(code, list_body_node, vardict):
        # the code of the loop reading the body, from start_list_body_loop
        # to finish_list_body_loop, in the forms of the mode; the row form
        # only for a body with a loop (otherwise it reads a fixed number
        # of values, usually only a few)
        row_form = ListBodyRecorder._row_form(vardict)
        if row_form is None:
            return code
        with_loop = any(get_name(c) == "list_loop" for c in list_body_node.children)
        return row_form.select_form(code, with_loop)

    @staticmethod
    def get_element(node, vardict):
        # an element after the NPL elements of the body is an error, raised
        # before the field is accessed: the line of the NPL-th element is
        # the last line of the body and the field may lie beyond the six
        # fields of the line (cpp_j > 5), i.e. beyond the line
        code = cpp.pureif(
            "cpp_i >= cpp_npl", cpp.statement("cpp_throw_list_body_overrun(cpp_npl)")
        )
        valcode, addcode = get_numeric_field_getter(vardict)(
            node, "cpp_j", float, vardict
        )
        return valcode, code + addcode

    @staticmethod
    def update_counters_and_line(vardict):
        row_form = ListBodyRecorder._row_form(vardict)
        code = cpp.statement("cpp_i++")
        code += cpp.statement("cpp_j++")
        code += cpp.pureif(
            cpp.logical_and(["cpp_j > 5", "cpp_i < cpp_npl"]),
            cpp.concat(
                [
                    get_finalize_line_func(vardict)(vardict),
                    get_prepare_line_func(vardict)(vardict),
                    row_form.conversion if row_form is not None else "",
                    cpp.statement("cpp_j = 0"),
                ]
            ),
        )
        return code

    @staticmethod
    def indent(code):
        return cpp.indent_code(code, cpp.INDENT)
