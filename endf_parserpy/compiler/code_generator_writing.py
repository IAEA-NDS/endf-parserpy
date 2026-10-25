############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################


from hashlib import md5
from .code_generator_core import generate_vardefs, generate_code_from_parsetree
from . import cpp_boilerplate
from . import cpp_boilerplate_writing
from .code_generator_core import (
    generate_cpp_parse_or_write_fun,
    generate_code_for_varassign,
)
from .code_generator_parsing_core import (
    generate_endf_dict_assignments,
)
from .code_generator_writing_core import (
    get_expr_value_using_endf_dict,
    contains_arithmetic,
    get_mat_from_mfmt_section,
    generate_section_writing_code,
)
from lark.lexer import Token
from .expr_utils.conversion import convert_to_exprtree
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from . import cpp_primitives as cpp
from .cpp_types import cpp_varops_assign
from .cpp_types import cpp_varaux
from . import endf2cpp_aux as aux
from .mode_management import (
    register_numeric_field_getter,
    register_text_field_getter,
    register_custom_int_field_getter,
    register_custom_int_row_binder,
    register_counter_field_getter,
    register_tab1_body_getter,
    register_tab2_body_getter,
    register_send_line_func,
    register_prepare_line_func,
    register_finalize_line_func,
    register_nested_element_hook,
    register_prepare_line_tape_func,
    register_finalize_line_tape_func,
    register_prepare_section_func,
    register_finalize_section_func,
    register_lookahead_tellg_statement,
    register_lookahead_seekg_statement,
    register_generate_expr_validation_func,
    register_lookahead_presence_check,
    register_lookahead_catch_clause,
    register_unused_arrays,
)
from .unused_arrays import find_unused_arrays
from .endf2cpp_aux import (
    get_numeric_field,
    get_text_field,
    get_tab1_body,
    get_tab2_body,
    get_custom_int_field,
    read_line_la,
    read_raw_line,
)
from .endf2cpp_aux_writing import (
    prepare_line_la,
    prepare_send_la,
    set_numeric_field,
    set_text_field,
    set_tab1_body,
    set_tab2_body,
    set_custom_int_field,
    write_section_verbatim,
    open_section,
    close_section,
)
from .lookahead_management import in_lookahead
from .variable_management import expand_abbreviation


def mf_mt_writefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"write_mf{mf}"
    return f"write_mf{mf}mt{mt}"


def _canonical_writefun_name(recipe):
    """Recipe-hash-derived canonical name for the writing side. See
    :func:`code_generator_parsing._canonical_parsefun_name` for the
    rationale and collision argument.
    """
    return "write_recipe_" + md5(recipe.encode()).hexdigest()[:16]


def _split_wrapper_names(entry):
    if isinstance(entry, (tuple, list)):
        return entry[0], entry[1]
    return entry, entry


def _writefun_forward_decl(ostream_name):
    return cpp.line(
        f"void {ostream_name}(std::ostream& cont, py::dict endf_dict, "
        "WritingOptions& write_opts);"
    )


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


_field_value_counter = [0]


def _reset_field_value_counter():
    _field_value_counter[0] = 0


def _bind_field_value(valcode):
    # The value of a field is needed twice, for writing the field and for
    # the assignment to the C++ variable(s) in the field. If it is retrieved
    # from the Python dictionary, it is retrieved once and stored in a local
    # variable whose name is returned (as the same str subclass as valcode).
    if "get_value(" not in valcode and "cpp_wacc_" not in valcode:
        return valcode, ""
    _field_value_counter[0] += 1
    name = f"cpp_wval_{_field_value_counter[0]}"
    code = cpp.statement(f"auto {name} = {valcode}")
    return type(valcode)(name), code


def _get_numeric_field_wrapper(node, idx, dtype, vardict):
    code = ""
    if not in_lookahead(vardict):
        # elements of arrays in loops with an accessor, see get_array_accessor
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", dtype, vardict, site=node
        )
        valcode = _convert_field_value(node, valcode, dtype, lenient=False)
        valcode, code = _bind_field_value(valcode)
        code += set_numeric_field("cpp_draft_line", idx, dtype, valcode, "write_opts")
    else:
        # defaults are used in lookahead for if-condition evaluation
        # NOTE: not ideal to use precoded values instead of dealing
        #       with missing variables directly, but the best solution
        #       I am able to come up with given the existing code structure.
        #       A variable whose value is a default is not marked as read,
        #       see _lookahead_presence_check_wrapper.
        defaults = {int: -99999, float: -99999.9}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", dtype, vardict, defaults
        )
        valcode = _convert_field_value(node, valcode, dtype, lenient=True)
    return valcode, code


def _convert_field_value(node, valcode, dtype, lenient):
    # The value of an expression with arithmetic may be an exact fraction
    # or a double; it is converted to the type of the field. An integer
    # field requires an integer, except within a lookahead (lenient).
    if not contains_arithmetic(convert_to_exprtree(node)):
        return valcode
    if dtype == int:
        func = "cpp_round_to_int" if lenient else "cpp_to_integer"
        return f"{func}({valcode})"
    if dtype == float:
        return f"cpp_to_double({valcode})"
    return valcode


def _get_text_field_wrapper(node, start, length, vardict, pad=False):
    # pad: the field has no length in the recipe and spans the remaining
    # text columns, so that a shorter value is padded with blanks
    code = ""
    if not in_lookahead(vardict):
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", str, vardict
        )
        code += set_text_field(
            "cpp_draft_line", start, length, valcode, str(VariableToken(node)), pad
        )
    else:
        defaults = {str: " " * 11}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", str, vardict, defaults
        )
    return valcode, code


def _get_tab1_body_wrapper(xvar, yvar, nr, np, vardict):
    code = ""
    valcode = "tab1_body"
    xvalue = get_expr_value_using_endf_dict(
        xvar, "cpp_index_shifter_store", "floatvec", vardict
    )
    yvalue = get_expr_value_using_endf_dict(
        yvar, "cpp_index_shifter_store", "floatvec", vardict
    )
    INTvar = VariableToken(Token("VARNAME", "INT"))
    INTvalue = get_expr_value_using_endf_dict(
        INTvar, "cpp_index_shifter_store", "intvec", vardict
    )
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    NBTvalue = get_expr_value_using_endf_dict(
        NBTvar, "cpp_index_shifter_store", "intvec", vardict
    )
    code += cpp.statement(f"{valcode}.X = {xvalue}")
    code += cpp.statement(f"{valcode}.Y = {yvalue}")
    code += cpp.statement(f"{valcode}.INT = {INTvalue}")
    code += cpp.statement(f"{valcode}.NBT = {NBTvalue}")
    if not in_lookahead(vardict):
        code += set_tab1_body(
            "cpp_draft_line", valcode, "mat", "mf", "mt", "linenum", "write_opts"
        )
    # all members of tab1_body are assigned anew before each use, so its
    # content can be moved to the variables of the record instead of copied
    return f"std::move({valcode})", code


def _get_tab2_body_wrapper(nr, vardict):
    code = ""
    valcode = "tab2_body"
    INTvar = VariableToken(Token("VARNAME", "INT"))
    INTvalue = get_expr_value_using_endf_dict(
        INTvar, "cpp_index_shifter_store", "intvec", vardict
    )
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    NBTvalue = get_expr_value_using_endf_dict(
        NBTvar, "cpp_index_shifter_store", "intvec", vardict
    )
    code += cpp.statement(f"{valcode}.INT = {INTvalue}")
    code += cpp.statement(f"{valcode}.NBT = {NBTvalue}")
    if not in_lookahead(vardict):
        code += set_tab2_body(
            "cpp_draft_line", valcode, "mat", "mf", "mt", "linenum", "write_opts"
        )
    # all members of tab2_body are assigned anew before each use, so its
    # content can be moved to the variables of the record instead of copied
    return f"std::move({valcode})", code


def _get_custom_int_field_wrapper(node, start, length, vardict, idx=None, row=None):
    code = ""
    if not in_lookahead(vardict):
        if row is not None:
            # element idx of the values retrieved by _custom_int_row_binder
            valcode = f"{row}[{idx}]"
        else:
            valcode = get_expr_value_using_endf_dict(
                node, "cpp_index_shifter_store", int, vardict, idx=idx
            )
            valcode, code = _bind_field_value(valcode)
        code += set_custom_int_field("cpp_draft_line", start, length, valcode)
    else:
        defaults = {int: -99999}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", int, vardict, defaults, idx=idx
        )
    return valcode, code


def _custom_int_row_binder(node, count, vardict):
    # The fields of an INTG record are filled with the elements of a
    # row of integers. The first `count` elements of the row are retrieved
    # once and stored in a local std::vector<int> whose name is returned,
    # so that the row is not retrieved from the Python dictionary again
    # for each field. None is returned if this is not applicable.
    if in_lookahead(vardict):
        return None, ""
    exprtree = transform_nodes(convert_to_exprtree(node), expand_abbreviation, vardict)
    if not isinstance(exprtree, VariableToken):
        return None, ""
    rowobj = get_expr_value_using_endf_dict(
        node, "cpp_index_shifter_store", None, vardict
    )
    if "get_value(" not in rowobj:
        return None, ""
    _field_value_counter[0] += 1
    name = f"cpp_wrow_{_field_value_counter[0]}"
    code = cpp.statement(
        f"std::vector<int> {name} = cpp_intg_row_values({rowobj}, {count})"
    )
    return name, code


def _get_counter_field_wrapper(node, idx, vardict):
    code = ""
    if not in_lookahead(vardict):
        pyobj = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", None, vardict
        )
        valcode = f"py::len({pyobj})"
        code += set_numeric_field("cpp_draft_line", idx, int, valcode, "write_opts")
    else:
        defaults = {int: -99999}
        pyobj = get_expr_value_using_endf_dict(
            node, "cpp_index_shifter_store", None, vardict
        )
        valcode = f"py::len({pyobj})"
    return valcode, code


def _lookahead_presence_check_wrapper(vartok):
    # In a lookahead, absent variables are substituted by default values
    # (see _get_numeric_field_wrapper). Such a variable must not count
    # as read, so that any comparison involving it in the if-condition
    # evaluates to false, in line with EndfParserPy, which treats
    # comparisons with variables missing in the dictionary as false.
    return f'cpp_index_shifter_store.has_value("{vartok}")'


def _prepare_send_func_wrapper(vardict):
    code = prepare_send_la(
        "cpp_draft_line", "mat", "mf", "write_opts", in_lookahead(vardict)
    )
    return code


def _prepare_line_func_wrapper(vardict):
    code = prepare_line_la(
        "cpp_draft_line",
        "mat",
        "mf",
        "mt",
        "linenum",
        "write_opts",
        in_lookahead(vardict),
    )
    return code


def _finalize_line_func_wrapper(vardict):
    if in_lookahead(vardict):
        return ""
    code = cpp.statement("cont << cpp_draft_line")
    return code


def _nested_element_func_wrapper(vartok, indices):
    # the start index of each level of a nested array with array_type="list"
    # is the first index of the loop that creates its elements, as in the
    # parsing code, also if an element remains empty (see IndexShifter)
    idcsarg = "std::vector<int>({" + ", ".join(indices) + "})"
    return cpp.statement(
        f'cpp_index_shifter_store.register_element("{vartok}", {idcsarg})'
    )


def _prepare_line_tape_func_wrapper():
    # cpp_line not used but kept in order to avoid
    # rewritig the printing of error messages including template strings
    code = cpp.statement("std::string cpp_line")
    code += cpp.statement("std::string cpp_draft_line")
    code += cpp.statement("int linenum = 0")
    # for the tape id line, indicated by mf=0 and mt=0, we want linenum = 0
    code += cpp.pureif(
        cpp.logical_and(["mf == 0", "mt == 0"]), cpp.statement("linenum = -1")
    )
    return code


def _finalize_line_tape_func_wrapper():
    return ""


def _prepare_section_func_wrapper(sectok, vardict):
    if sectok is None:
        # initialization
        code = cpp.statement("py::dict cpp_parent_dict")
        code += cpp.statement("py::dict cpp_current_dict = endf_dict")
        code += cpp.statement(
            "IndexShifterStore cpp_index_shifter_store(cpp_current_dict, list_mode)"
        )
        return code
    code = open_section(
        sectok,
        vardict,
        current_dict="cpp_current_dict",
        parent_dict="cpp_parent_dict",
    )
    code += cpp.statement(
        "IndexShifterStore cpp_index_shifter_store(cpp_current_dict, list_mode)"
    )
    return code


def _finalize_section_func_wrapper(sectok, vardict):
    code = ""
    if sectok is None:
        return code
    code += close_section(
        current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"
    )
    return code


def _generate_expr_validation_wrapper(actual_value, node, vardict):
    return ""


def generate_cpp_writefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    _reset_field_value_counter()
    vardict = {}
    register_numeric_field_getter(_get_numeric_field_wrapper, vardict)
    register_text_field_getter(_get_text_field_wrapper, vardict)
    register_tab1_body_getter(_get_tab1_body_wrapper, vardict)
    register_tab2_body_getter(_get_tab2_body_wrapper, vardict)
    register_custom_int_field_getter(_get_custom_int_field_wrapper, vardict)
    register_custom_int_row_binder(_custom_int_row_binder, vardict)
    register_counter_field_getter(_get_counter_field_wrapper, vardict)
    register_send_line_func(_prepare_send_func_wrapper, vardict)
    register_prepare_line_func(_prepare_line_func_wrapper, vardict)
    register_finalize_line_func(_finalize_line_func_wrapper, vardict)
    register_nested_element_hook(_nested_element_func_wrapper, vardict)
    register_prepare_line_tape_func(_prepare_line_tape_func_wrapper, vardict)
    register_finalize_line_tape_func(_finalize_line_tape_func_wrapper, vardict)
    register_prepare_section_func(_prepare_section_func_wrapper, vardict)
    register_finalize_section_func(_finalize_section_func_wrapper, vardict)
    register_generate_expr_validation_func(_generate_expr_validation_wrapper, vardict)
    register_lookahead_presence_check(_lookahead_presence_check_wrapper, vardict)
    # When writing, the lookahead merely serves to evaluate the if-condition
    # with the data in the dictionary. If the records of a branch cannot be
    # evaluated with these data, e.g. because a variable of the branch is
    # absent and an expression depending on it cannot be handled, this is
    # no error: the branch simply does not apply. Variables of the
    # if-condition not available at this point are not marked as read,
    # see _lookahead_presence_check_wrapper, so the condition is false.
    register_lookahead_catch_clause("const std::exception& e", vardict)
    register_lookahead_tellg_statement("", vardict)
    register_lookahead_seekg_statement("", vardict)

    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))

    ctrl_code = ""
    if mat is None:
        matval = get_expr_value_using_endf_dict(
            var_mat, "cpp_index_shifter_store", int, vardict
        )
    else:
        matval = str(mat)
    if mf is None:
        mfval = get_expr_value_using_endf_dict(
            var_mf, "cpp_index_shifter_store", int, vardict
        )
    else:
        mfval = str(mf)
    if mt is None:
        mtval = get_expr_value_using_endf_dict(
            var_mt, "cpp_index_shifter_store", int, vardict
        )
    else:
        mtval = str(mt)

    ctrl_code += cpp.statement(f"int mat = {matval}")
    ctrl_code += cpp.statement(f"int mf = {mfval}")
    ctrl_code += cpp.statement(f"int mt = {mtval}")
    ctrl_code += cpp.statement(f'cpp_current_dict["MAT"] = mat')
    ctrl_code += cpp.statement(f'cpp_current_dict["MF"] = mf')
    ctrl_code += cpp.statement(f'cpp_current_dict["MT"] = mt')

    ctrl_code += generate_code_for_varassign(var_mat, vardict, matval, int)
    ctrl_code += generate_code_for_varassign(var_mf, vardict, mfval, int)
    ctrl_code += generate_code_for_varassign(var_mt, vardict, mtval, int)

    fun_header = cpp_boilerplate_writing.writefun_header(name)
    fun_footer = cpp_boilerplate_writing.writefun_footer()

    return generate_cpp_parse_or_write_fun(
        name,
        endf_recipe,
        mat,
        mf,
        mt,
        parser,
        vardict,
        fun_header=fun_header,
        fun_footer=fun_footer,
        fun_setup=ctrl_code,
        tree_analysis=_register_unused_arrays,
    )


def _register_unused_arrays(parsetree, vardict):
    # the values of these variables are not stored when writing
    register_unused_arrays(find_unused_arrays(parsetree), vardict)


def generate_master_writefun(name, recipefuns):
    code = ""
    body = ""
    body += cpp.statement("int mat")
    body += cpp.statement("int mf")
    body += cpp.statement("int mt")
    body += cpp.statement("int last_mat = -9999")
    body += cpp.statement("int last_mf = -9999")
    body += cpp.statement("int last_mt = -9999")
    body += cpp.statement("bool section_encountered = false")
    body += cpp.statement("bool found_tpid = false")
    body += cpp.statement("auto d = py::reinterpret_borrow<py::dict>(endf_dict)")
    body += cpp.statement('py::object mf_keys = d.attr("keys")()')
    # sort the mf keys
    body += cpp.statement("std::vector<int> sorted_mf_keys")
    body += cpp.line("for (auto mf_key : mf_keys) {")
    body += cpp.statement("sorted_mf_keys.push_back(py::cast<int>(mf_key))", cpp.INDENT)
    body += cpp.close_block()
    body += cpp.statement("std::sort(sorted_mf_keys.begin(), sorted_mf_keys.end())")
    body += cpp.statement("std::map<int, std::vector<int>> sorted_mfmt_keys")
    # sort the mt keys
    body += cpp.line("for (auto mf_key : sorted_mf_keys) {")
    body += cpp.statement(
        'py::object mt_keys = d[py::cast(mf_key)].attr("keys")()', cpp.INDENT
    )
    body += cpp.statement("std::vector<int> sorted_mt_keys")
    body += cpp.line("for (auto mt_key : mt_keys) {", cpp.INDENT)
    body += cpp.statement(
        "sorted_mt_keys.push_back(py::cast<int>(mt_key))", 2 * cpp.INDENT
    )
    body += cpp.indent_code(cpp.close_block(), cpp.INDENT)
    body += cpp.statement(
        "std::sort(sorted_mt_keys.begin(), sorted_mt_keys.end())", cpp.INDENT
    )
    body += cpp.statement("sorted_mfmt_keys[mf_key] = sorted_mt_keys", cpp.INDENT)
    body += cpp.close_block()
    # iterate through the sorted mf/mt combinations
    body += cpp.line("for (auto mf_key : sorted_mf_keys) {")
    body += cpp.statement("py::dict mf_dict = d[py::cast(mf_key)]", cpp.INDENT)
    body += cpp.statement(
        "std::vector<int> sorted_mt_keys = sorted_mfmt_keys[mf_key]", cpp.INDENT
    )
    body += cpp.line("for (auto mt_key : sorted_mt_keys) {", cpp.INDENT)
    body += cpp.statement(
        "py::object mt_dict = mf_dict[py::cast(mt_key)]", 2 * cpp.INDENT
    )
    body += cpp.statement(f"mf = mf_key", 2 * cpp.INDENT)
    body += cpp.statement(f"mt = mt_key", 2 * cpp.INDENT)

    # skip section if it shouldn't be parsed
    body += cpp.indent_code(
        cpp.pureif(
            cpp.logical_not(aux.should_parse_section("mf", "mt", "exclude", "include")),
            cpp.statement("continue"),
        ),
        2 * cpp.INDENT,
    )

    # add FEND record if required
    body += cpp.indent_code(
        cpp.pureif(
            cpp.logical_and(
                ["section_encountered", "mf != last_mf", "mf != 0", "last_mf != 0"]
            ),
            cpp.statement("cont << cpp_prepare_send(mat, 0, write_opts)"),
        ),
        2 * cpp.INDENT,
    )

    conditions = []
    statements = []
    for mf, mfdic in recipefuns.items():
        if isinstance(mfdic, str):
            varname = _mf_mt_dict_varname(mf, None)
            funname = mfdic
            conditions.append(f"mf == {mf}")
            section_code = generate_section_writing_code(funname, "write_opts")
            matval = get_mat_from_mfmt_section("mt_dict")
            section_code += cpp.statement(f"mat = {matval}")
            section_code += cpp.statement("section_encountered = true")
            statements.append(section_code)
            continue
        for mt in reversed(sorted(mfdic.keys())):
            funname = mfdic[mt]
            varname = _mf_mt_dict_varname(mf, mt)
            section_code = ""
            if mt == -1:
                curcond = f"mf == {mf}"
            else:
                curcond = f"mf == {mf} && mt == {mt}"
            if mt == 0 and mt == 0:
                # in case of MF=0/MT=0, we want to register that the tpid record has been read
                section_code += cpp.statement("found_tpid = true")

            section_code = generate_section_writing_code(funname, "write_opts")
            matval = get_mat_from_mfmt_section("mt_dict")
            section_code += cpp.statement(f"mat = {matval}")
            section_code += cpp.statement("section_encountered = true")
            statements.append(section_code)
            conditions.append(curcond)

    # if no writing function registered for an MF/MT function,
    # the section must be given as a py::list of strings
    default_code = write_section_verbatim(
        "cont",
        "py::cast<py::list>(endf_dict[py::cast(mf)][py::cast(mt)])",
        "write_opts",
    )

    body += cpp.indent_code(
        cpp.conditional_branches(conditions, statements, default=default_code),
        2 * cpp.INDENT,
    )

    body += cpp.statement("last_mat = mat", 2 * cpp.INDENT)
    body += cpp.statement("last_mf = mf", 2 * cpp.INDENT)
    body += cpp.statement("last_mt = mt", 2 * cpp.INDENT)
    body += cpp.indent_code(cpp.close_block(), cpp.INDENT)
    body += cpp.close_block()

    # add FEND, MEND and TEND record at the very end
    body += cpp.statement("cont << cpp_prepare_send(mat, 0, write_opts)")
    body += cpp.statement("cont << cpp_prepare_send(0, 0, write_opts)")
    body += cpp.statement("cont << cpp_prepare_send(-1, 0, write_opts, false)")

    args = (
        ("std::ostream&", "cont"),
        ("py::dict", "endf_dict"),
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("WritingOptions", f"write_opts=default_writing_options()"),
    )
    code += cpp.function(name, body, "void", *args)
    code += cpp.line("")
    return code


def _call_writefun(callcode):
    """Call a writing function; an error message is escaped (see
    cpp_rethrow_escaped)."""
    code = cpp.line("try {")
    code += cpp.statement(callcode, cpp.INDENT)
    code += cpp.line("} catch (const py::error_already_set&) {")
    code += cpp.statement("throw", cpp.INDENT)
    code += cpp.line("} catch (const std::runtime_error& cpp_exc) {")
    code += cpp.statement("cpp_rethrow_escaped(cpp_exc)", cpp.INDENT)
    code += cpp.close_block()
    return code


def generate_cpp_writefun_wrappers_string(writefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for entry in writefuns:
        outer, inner = _split_wrapper_names(entry)
        code += cpp.line(f"py::str {outer}(py::dict endf_dict{args_str}) {{")
        code += cpp.statement("std::ostringstream oss", cpp.INDENT)
        code += cpp.indent_code(
            _call_writefun(f"{inner}_ostream(oss, endf_dict{args_str2})"), cpp.INDENT
        )
        # each byte becomes the character with the same code
        code += cpp.statement("return cpp_bytes_to_pystr(oss.str())", cpp.INDENT)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_cpp_writefun_wrappers_file(writefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for entry in writefuns:
        outer, inner = _split_wrapper_names(entry)
        code += cpp.line(
            f"void {outer}_file(std::string& filename, py::dict endf_dict{args_str}) {{"
        )
        code += cpp.statement(
            "std::ofstream outfile(filename, std::ios::binary)", cpp.INDENT
        )
        code += cpp.indent_code(
            cpp.pureif(
                cpp.logical_not("outfile.is_open()"),
                cpp.statement(
                    "throw std::ofstream::failure"
                    + '("failed to open file " + filename)'
                ),
            ),
            cpp.INDENT,
        )
        code += cpp.indent_code(
            _call_writefun(f"{inner}_ostream(outfile, endf_dict{args_str2})"),
            cpp.INDENT,
        )
        code += cpp.statement("outfile.close()", cpp.INDENT)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_all_cpp_writefuns_code(recipes, module_name, shared_registry=None):
    """Mirror of :func:`code_generator_parsing.generate_all_cpp_parsefuns_code`
    for the write side. With ``shared_registry`` provided, deduplicate
    write_recipe_<hash>_ostream bodies across flavors into _shared.cpp.
    """
    dedup = shared_registry is not None
    writefuns_code = ""
    wrapper_entries = []
    recipefuns = {}
    forward_decls_seen = set()
    if dedup:
        write_reg = shared_registry.setdefault("write", {})

    def _route(recipe, outer_name, mf, mt_):
        nonlocal writefuns_code
        if not dedup:
            writefuns_code += generate_cpp_writefun(
                outer_name + "_ostream", recipe, mf=mf, mt=mt_
            )
            return outer_name
        recipe_hash = md5(recipe.encode()).hexdigest()
        canonical = _canonical_writefun_name(recipe)
        canonical_ostream = canonical + "_ostream"
        if recipe_hash not in write_reg:
            write_reg[recipe_hash] = (
                canonical,
                generate_cpp_writefun(canonical_ostream, recipe, mf=mf, mt=mt_),
            )
        if canonical_ostream not in forward_decls_seen:
            writefuns_code += _writefun_forward_decl(canonical_ostream)
            forward_decls_seen.add(canonical_ostream)
        return canonical

    for mf, mt_recipes in recipes.items():
        if isinstance(mt_recipes, str):
            print(f"MF: {mf}")
            outer_name = mf_mt_writefun_name(mf, None)
            inner_name = _route(mt_recipes, outer_name, mf=mf, mt_=None)
            wrapper_entries.append((outer_name, inner_name))
            recipefuns[mf] = inner_name
            continue
        for mt, recipe in mt_recipes.items():
            print(f"MF: {mf} MT: {mt}")
            outer_name = mf_mt_writefun_name(mf, mt)
            mt_ = mt if mt != -1 else None
            inner_name = _route(recipe, outer_name, mf=mf, mt_=mt_)
            wrapper_entries.append((outer_name, inner_name))
            curdic = recipefuns.setdefault(mf, {})
            curdic[mt] = inner_name

    writefun_wrappers_code1 = generate_cpp_writefun_wrappers_string(
        wrapper_entries, ("WritingOptions", "write_opts")
    )
    writefun_wrappers_code2 = generate_cpp_writefun_wrappers_file(
        wrapper_entries, ("WritingOptions", "write_opts")
    )
    # special case for the master function calling the other mf/mt parser funs
    master_writefun_code = generate_master_writefun("write_endf_ostream", recipefuns)
    writefun_wrappers_code1 += generate_cpp_writefun_wrappers_string(
        ["write_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("WritingOptions", "write_opts"),
    )
    writefun_wrappers_code2 += generate_cpp_writefun_wrappers_file(
        ["write_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("WritingOptions", "write_opts"),
    )
    pybind_glue = ""
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["write_endf"],
        module_name,
        'py::arg("endf_dict")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("WritingOptions") = false',
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["write_endf_file"],
        module_name,
        'py::arg("filename")',
        'py::arg("endf_dict")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("write_opts") = default_writing_options()',
    )

    all_writefun_codes = (
        writefuns_code
        + master_writefun_code
        + writefun_wrappers_code1
        + writefun_wrappers_code2
    )
    return all_writefun_codes, pybind_glue
