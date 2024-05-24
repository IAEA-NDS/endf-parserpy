############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/24
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


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
    generate_parse_or_read_verbatim,
)
from lark.lexer import Token
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
    register_counter_field_getter,
    register_tab1_body_getter,
    register_tab2_body_getter,
    register_send_line_func,
    register_prepare_line_func,
    register_finalize_line_func,
    register_prepare_line_tape_func,
    register_finalize_line_tape_func,
    register_prepare_section_func,
    register_finalize_section_func,
    register_lookahead_tellg_statement,
    register_lookahead_seekg_statement,
)
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
)
from .lookahead_management import in_lookahead


def mf_mt_writefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"write_mf{mf}"
    return f"write_mf{mf}mt{mt}"


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


def _get_numeric_field_wrapper(node, idx, dtype, vardict):
    code = ""
    if not in_lookahead(vardict):
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", dtype, vardict
        )
        code += set_numeric_field("cpp_draft_line", idx, dtype, valcode)
    else:
        # defaults are used in lookahead for if-condition evaluation
        # NOTE: not ideal to use precoded values instead of dealing
        #       with missing variables directly, but the best solution
        #       I am able to come up with given the existing code structure
        defaults = {int: -99999, float: -99999.9}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", dtype, vardict, defaults
        )
    return valcode, code


def _get_text_field_wrapper(node, start, length, vardict):
    code = ""
    if not in_lookahead(vardict):
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", str, vardict
        )
        code += set_text_field("cpp_draft_line", start, length, valcode)
    else:
        defaults = {str: " " * 11}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", str, vardict, defaults
        )
    return valcode, code


def _get_tab1_body_wrapper(xvar, yvar, nr, np, vardict):
    code = ""
    valcode = "tab1_body"
    xvalue = get_expr_value_using_endf_dict(
        xvar, "cpp_current_dict_tmp", "floatvec", vardict
    )
    yvalue = get_expr_value_using_endf_dict(
        yvar, "cpp_current_dict_tmp", "floatvec", vardict
    )
    INTvar = VariableToken(Token("VARNAME", "INT"))
    INTvalue = get_expr_value_using_endf_dict(
        INTvar, "cpp_current_dict_tmp", "intvec", vardict
    )
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    NBTvalue = get_expr_value_using_endf_dict(
        NBTvar, "cpp_current_dict_tmp", "intvec", vardict
    )
    code += cpp.statement(f"{valcode}.X = {xvalue}")
    code += cpp.statement(f"{valcode}.Y = {yvalue}")
    code += cpp.statement(f"{valcode}.INT = {INTvalue}")
    code += cpp.statement(f"{valcode}.NBT = {NBTvalue}")
    if not in_lookahead(vardict):
        code += set_tab1_body("cpp_draft_line", valcode, "mat", "mf", "mt")
    return valcode, code


def _get_tab2_body_wrapper(nr, vardict):
    code = ""
    valcode = "tab2_body"
    INTvar = VariableToken(Token("VARNAME", "INT"))
    INTvalue = get_expr_value_using_endf_dict(
        INTvar, "cpp_current_dict_tmp", "intvec", vardict
    )
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    NBTvalue = get_expr_value_using_endf_dict(
        NBTvar, "cpp_current_dict_tmp", "intvec", vardict
    )
    code += cpp.statement(f"{valcode}.INT = {INTvalue}")
    code += cpp.statement(f"{valcode}.NBT = {NBTvalue}")
    if not in_lookahead(vardict):
        code += set_tab2_body("cpp_draft_line", valcode, "mat", "mf", "mt")
    return valcode, code


def _get_custom_int_field_wrapper(node, start, length, vardict):
    code = ""
    if not in_lookahead(vardict):
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", int, vardict
        )
        code += set_custom_int_field("cpp_draft_line", start, length, valcode)
    else:
        defaults = {int: -99999}
        valcode = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", int, vardict, defaults
        )
    return valcode, code


def _get_counter_field_wrapper(node, idx, vardict):
    code = ""
    if not in_lookahead(vardict):
        pyobj = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", None, vardict
        )
        valcode = f"py::len({pyobj})"
        code += set_numeric_field("cpp_draft_line", idx, int, valcode)
    else:
        defaults = {int: -99999}
        pyobj = get_expr_value_using_endf_dict(
            node, "cpp_current_dict_tmp", None, vardict
        )
        valcode = f"py::len({pyobj})"
    return valcode, code


def _prepare_send_func_wrapper(vardict):
    code = prepare_send_la("cpp_draft_line", "mat", "mf", in_lookahead(vardict))
    return code


def _prepare_line_func_wrapper(vardict):
    code = prepare_line_la("cpp_draft_line", "mat", "mf", "mt", in_lookahead(vardict))
    return code


def _finalize_line_func_wrapper(vardict):
    if in_lookahead(vardict):
        return ""
    code = cpp.statement("cont << cpp_draft_line")
    return code


def _prepare_line_tape_func_wrapper():
    # cpp_line not used but kept in order to avoid
    # rewritig the printing of error messages including template strings
    code = cpp.statement("std::string cpp_line")
    code += cpp.statement("std::string cpp_draft_line")
    code += cpp.statement("std::ostringstream cpp_output")
    return code


def _finalize_line_tape_func_wrapper():
    code = cpp.statement("std::cout << cpp_output.str()")
    return code


def _prepare_section_func_wrapper(sectok, vardict):
    if sectok is None:
        # initialization
        code = cpp.statement("py::dict cpp_parent_dict")
        code += cpp.statement("py::dict cpp_current_dict")
        code += cpp.statement("py::dict cpp_parent_dict_tmp")
        code += cpp.statement("py::dict cpp_current_dict_tmp = endf_dict")
        return code
    code = aux.open_section(
        sectok,
        vardict,
        current_dict="cpp_current_dict_tmp",
        parent_dict="cpp_parent_dict_tmp",
    )
    code += aux.open_section(sectok, vardict)
    return code


def _finalize_section_func_wrapper(sectok, vardict):
    code = generate_endf_dict_assignments(vardict)
    if sectok is None:
        return code
    code += aux.close_section(
        current_dict="cpp_current_dict_tmp", parent_dict="cpp_parent_dict_tmp"
    )
    code += aux.close_section()
    return code


def generate_cpp_writefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    vardict = {}
    register_numeric_field_getter(_get_numeric_field_wrapper, vardict)
    register_text_field_getter(_get_text_field_wrapper, vardict)
    register_tab1_body_getter(_get_tab1_body_wrapper, vardict)
    register_tab2_body_getter(_get_tab2_body_wrapper, vardict)
    register_custom_int_field_getter(_get_custom_int_field_wrapper, vardict)
    register_counter_field_getter(_get_counter_field_wrapper, vardict)
    register_send_line_func(_prepare_send_func_wrapper, vardict)
    register_prepare_line_func(_prepare_line_func_wrapper, vardict)
    register_finalize_line_func(_finalize_line_func_wrapper, vardict)
    register_prepare_line_tape_func(_prepare_line_tape_func_wrapper, vardict)
    register_finalize_line_tape_func(_finalize_line_tape_func_wrapper, vardict)
    register_prepare_section_func(_prepare_section_func_wrapper, vardict)
    register_finalize_section_func(_finalize_section_func_wrapper, vardict)
    register_lookahead_tellg_statement("", vardict)
    register_lookahead_seekg_statement("", vardict)

    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))

    ctrl_code = ""
    if mat is None:
        matval = get_expr_value_using_endf_dict(
            var_mat, "cpp_current_dict_tmp", int, vardict
        )
    else:
        matval = str(mat)
    if mf is None:
        mfval = get_expr_value_using_endf_dict(
            var_mf, "cpp_current_dict_tmp", int, vardict
        )
    else:
        mfval = str(mf)
    if mt is None:
        mtval = get_expr_value_using_endf_dict(
            var_mt, "cpp_current_dict_tmp", int, vardict
        )
    else:
        mtval = str(mt)

    ctrl_code += cpp.statement(f"int mat = {matval}")
    ctrl_code += cpp.statement(f"int mf = {mfval}")
    ctrl_code += cpp.statement(f"int mt = {mtval}")

    ctrl_code += generate_code_for_varassign(var_mat, vardict, matval, int)
    ctrl_code += generate_code_for_varassign(var_mf, vardict, mfval, int)
    ctrl_code += generate_code_for_varassign(var_mt, vardict, mtval, int)

    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mat, vardict)
    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mf, vardict)
    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mt, vardict)

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
    )


def generate_master_writefun(name, recipefuns):
    code = ""
    body = ""
    body += cpp.statement("int mat")
    body += cpp.statement("int mf")
    body += cpp.statement("int mt")
    body += cpp.statement("int last_mat")
    body += cpp.statement("int last_mf")
    body += cpp.statement("int last_mt")
    body += cpp.statement("bool found_tpid = false")
    # body += cpp.line("while (std::getline(cont, cpp_line)) {")
    body += cpp.statement("auto d = py::reinterpret_borrow<py::dict>(endf_dict)")
    body += cpp.statement('py::object mf_keys = d.attr("keys")()')
    body += cpp.line("for (auto mf_key : mf_keys) {")
    body += cpp.statement("int mf_key_int = py::cast<int>(mf_key)", cpp.INDENT)
    body += cpp.statement("py::dict mf_dict = d[py::cast(mf_key_int)]", cpp.INDENT)
    body += cpp.statement('py::object mt_keys = mf_dict.attr("keys")()', cpp.INDENT)
    body += cpp.line("for (auto mt_key : mt_keys) {", cpp.INDENT)
    body += cpp.statement("int mt_key_int = py::cast<int>(mt_key)", 2 * cpp.INDENT)
    body += cpp.statement(
        "py::dict mt_dict = mf_dict[py::cast(mt_key_int)]", 2 * cpp.INDENT
    )
    body += cpp.statement(f"mf = mf_key_int", 2 * cpp.INDENT)
    body += cpp.statement(f"mt = mt_key_int", 2 * cpp.INDENT)

    conditions = []
    statements = []
    for mf, mfdic in recipefuns.items():
        if isinstance(mfdic, str):
            varname = _mf_mt_dict_varname(mf, None)
            funname = mfdic
            conditions.append(f"mf == {mf}")
            section_code = generate_parse_or_read_verbatim(funname, "parse_opts")
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

            section_code = generate_parse_or_read_verbatim(funname, "parse_opts")
            statements.append(section_code)
            conditions.append(curcond)

    # TODO
    default_code = ""

    body += cpp.indent_code(
        cpp.conditional_branches(conditions, statements, default=default_code),
        2 * cpp.INDENT,
    )

    # curstat += cpp.statement("std::cout << cpp_prepare_send(mat, 0)")
    # curstat += cpp.statement("std::cout << cpp_prepare_send(0, 0)")
    # curstat += cpp.statement("std::cout << cpp_prepare_send(-1, 0)")

    body += cpp.statement("last_mat = mat", 2 * cpp.INDENT)
    body += cpp.statement("last_mf = mf", 2 * cpp.INDENT)
    body += cpp.statement("last_mt = mt", 2 * cpp.INDENT)
    body += cpp.indent_code(cpp.close_block(), cpp.INDENT)
    body += cpp.close_block()

    args = (
        ("std::ostream&", "cont"),
        ("py::dict", "endf_dict"),
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", f"parse_opts=default_parsing_options()"),
    )
    code += cpp.function(name, body, "void", *args)
    code += cpp.line("")
    return code


def generate_cpp_writefun_wrappers_string(writefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for p in writefuns:
        code += cpp.line(f"std::string {p}(py::dict endf_dict{args_str}) {{")
        code += cpp.statement("std::ostringstream oss", cpp.INDENT)
        code += cpp.statement(f"{p}_istream(oss, endf_dict{args_str2})", cpp.INDENT)
        code += cpp.statement("return oss.str()")
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_cpp_writefun_wrappers_file(writefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for p in writefuns:
        code += cpp.line(
            f"void {p}_file(std::string& filename, py::dict endf_dict{args_str}) {{"
        )
        code += cpp.statement("std::ofstream outfile(filename)", cpp.INDENT)
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
        code += cpp.statement(f"{p}_istream(outfile, endf_dict{args_str2})", cpp.INDENT)
        code += cpp.statement("outfile.close()")
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_all_cpp_writefuns_code(recipes, module_name):
    writefuns_code = ""
    func_names = []
    recipefuns = {}
    for mf, mt_recipes in recipes.items():
        if isinstance(mt_recipes, str):
            print(f"MF: {mf}")
            func_name = mf_mt_writefun_name(mf, None)
            func_names.append(func_name)
            recipe = mt_recipes
            writefuns_code += generate_cpp_writefun(
                func_name + "_istream", recipe, mf=mf, mt=None
            )
            recipefuns[mf] = func_name
            continue
        for mt, recipe in mt_recipes.items():
            print(f"MF: {mf} MT: {mt}")
            func_name = mf_mt_writefun_name(mf, mt)
            func_names.append(func_name)
            mt_ = mt if mt != -1 else None
            writefuns_code += generate_cpp_writefun(
                func_name + "_istream", recipe, mf=mf, mt=mt_
            )
            curdic = recipefuns.setdefault(mf, {})
            curdic[mt] = func_name
    writefun_wrappers_code1 = generate_cpp_writefun_wrappers_string(
        func_names, ("ParsingOptions", "parse_opts")
    )
    writefun_wrappers_code2 = generate_cpp_writefun_wrappers_file(
        func_names, ("ParsingOptions", "parse_opts")
    )
    # special case for the master function calling the other mf/mt parser funs
    master_writefun_code = generate_master_writefun("write_endf_istream", recipefuns)
    writefun_wrappers_code1 += generate_cpp_writefun_wrappers_string(
        ["write_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    writefun_wrappers_code2 += generate_cpp_writefun_wrappers_file(
        ["write_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    pybind_glue = ""
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["write_endf"],
        module_name,
        'py::arg("endf_dict")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = false',
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["write_endf_file"],
        module_name,
        'py::arg("filename")',
        'py::arg("endf_dict")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = default_parsing_options()',
    )

    all_writefun_codes = (
        writefuns_code
        + master_writefun_code
        + writefun_wrappers_code1
        + writefun_wrappers_code2
    )
    return all_writefun_codes, pybind_glue
