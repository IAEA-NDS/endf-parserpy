############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/20
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
    register_prepare_line_func,
    register_finalize_line_func,
    register_prepare_line_tape_func,
    register_finalize_line_tape_func,
    register_prepare_section_func,
    register_finalize_section_func,
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
    set_numeric_field,
    set_text_field,
    set_tab1_body,
    set_tab2_body,
    set_custom_int_field,
)


def mf_mt_writefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"write_mf{mf}"
    return f"write_mf{mf}mt{mt}"


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


def _get_numeric_field_wrapper(node, idx, dtype, lookahead):
    valcode = get_numeric_field(idx, dtype, "parse_opts")
    code = ""
    if not lookahead:
        code += set_numeric_field("cpp_draft_line", idx, dtype, valcode)
    return valcode, code


def _get_text_field_wrapper(node, start, length, lookahead):
    valcode = get_text_field(start, length)
    code = ""
    if not lookahead:
        code += set_text_field("cpp_draft_line", start, length, valcode)
    return valcode, code


def _get_tab1_body_wrapper(xvar, yvar, nr, np, lookahead):
    tab1_body_data = get_tab1_body(xvar, yvar, nr, np, "mat", "mf", "mt", "parse_opts")
    valcode = "tab1_body"
    code = cpp.statement(f"{valcode} = {tab1_body_data}")
    if not lookahead:
        code += set_tab1_body("cpp_draft_line", valcode, "mat", "mf", "mt")
    return valcode, code


def _get_tab2_body_wrapper(nr, lookahead):
    tab2_body_data = get_tab2_body(nr, "mat", "mf", "mt", "parse_opts")
    valcode = "tab2_body"
    code = cpp.statement(f"{valcode} = {tab2_body_data}")
    code += cpp.statement('std::cout << "encounterd TAB2 body" << std::endl')
    if not lookahead:
        code += set_tab2_body("cpp_draft_line", valcode, "mat", "mf", "mt")
    return valcode, code


def _get_custom_int_field_wrapper(node, start, length, lookahead):
    valcode = get_custom_int_field(start, length)
    code = ""
    if not lookahead:
        code += set_custom_int_field("cpp_draft_line", start, length, valcode)
    return valcode, code


def _get_counter_field_wrapper(node, idx, lookahead):
    valcode = get_numeric_field(idx, int, "parse_opts")
    code = ""
    if not lookahead:
        code += set_numeric_field("cpp_draft_line", idx, int, valcode)
    return valcode, code


def _prepare_line_func_wrapper(lookahead):
    code = read_line_la("cpp_line", "mat", "mf", "mt", "parse_opts", lookahead)
    code += prepare_line_la("cpp_draft_line", "mat", "mf", "mt", lookahead)
    return code


def _finalize_line_func_wrapper(lookahead):
    if lookahead:
        return ""
    code = cpp.statement(
        'std::cout << "---------------------------------------" << std::endl'
    )
    code += cpp.statement('std::cout << "LINE: " << cpp_line << std::endl')
    code += cpp.statement('std::cout << "FINE: " << cpp_draft_line << std::endl')
    return code


def _prepare_line_tape_func_wrapper():
    return ""


def _finalize_line_tape_func_wrapper():
    return ""


def _prepare_section_func_wrapper(sectok, vardict):
    return ""


def _finalize_section_func_wrapper(sectok, vardict):
    return ""


def generate_cpp_writefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    vardict = {}
    register_numeric_field_getter(_get_numeric_field_wrapper, vardict)
    register_text_field_getter(_get_text_field_wrapper, vardict)
    register_tab1_body_getter(_get_tab1_body_wrapper, vardict)
    register_tab2_body_getter(_get_tab2_body_wrapper, vardict)
    register_custom_int_field_getter(_get_custom_int_field_wrapper, vardict)
    register_counter_field_getter(_get_counter_field_wrapper, vardict)
    register_prepare_line_func(_prepare_line_func_wrapper, vardict)
    register_finalize_line_func(_finalize_line_func_wrapper, vardict)
    register_prepare_line_tape_func(_prepare_line_tape_func_wrapper, vardict)
    register_finalize_line_tape_func(_finalize_line_tape_func_wrapper, vardict)
    register_prepare_section_func(_prepare_section_func_wrapper, vardict)
    register_finalize_section_func(_finalize_section_func_wrapper, vardict)

    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))

    ctrl_code = ""
    ctrl_code += cpp.statement("std::streampos cpp_startpos = cont.tellg()")
    ctrl_code += read_raw_line("cpp_line")
    matval = aux.get_mat_number() if mat is None else str(mat)
    mfval = aux.get_mf_number() if mf is None else str(mf)
    mtval = aux.get_mt_number() if mt is None else str(mt)
    ctrl_code += cpp.statement(f"int mat = {matval}")
    ctrl_code += cpp.statement(f"int mf = {mfval}")
    ctrl_code += cpp.statement(f"int mt = {mtval}")
    ctrl_code += cpp.statement("cont.seekg(cpp_startpos)")

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
    body += cpp.statement("bool is_firstline = true")
    body += cpp.statement("std::streampos curpos")
    body += cpp.statement("py::dict mfmt_dict")
    body += cpp.statement("py::dict curdict")
    body += cpp.statement("int mat")
    body += cpp.statement("int mf")
    body += cpp.statement("int mt")
    body += cpp.statement("bool section_encountered = false")
    body += cpp.statement("int last_mat")
    body += cpp.statement("int last_mf")
    body += cpp.statement("int last_mt")
    body += cpp.statement("std::string cpp_line")
    body += cpp.statement("std::vector<std::string> verbatim_section")
    body += cpp.statement("bool found_tpid = false")
    body += cpp.statement("bool after_fend = false")
    body += cpp.statement("bool after_mend = false")
    body += cpp.statement("bool after_tend = false")
    body += cpp.statement("curpos = cont.tellg()")
    body += cpp.line("while (std::getline(cont, cpp_line)) {")
    matval = aux.get_custom_int_field(66, 4)
    mfval = aux.get_custom_int_field(70, 2)
    mtval = aux.get_custom_int_field(72, 3)
    body += cpp.statement(f"mat = {matval}", cpp.INDENT)
    body += cpp.statement(f"mf = {mfval}", cpp.INDENT)
    body += cpp.statement(f"mt = {mtval}", cpp.INDENT)

    conditions = []
    statements = []
    for mf, mfdic in recipefuns.items():
        sec_prep_code = cpp.call(
            "_check_end_records",
            "after_fend",
            "after_mend",
            "after_tend",
            "mat",
            "mf",
            "mt",
            "last_mat",
            "last_mf",
            "last_mt",
            "section_encountered",
            "found_tpid",
            "parse_opts",
        )
        sec_prep_code += cpp.statement("after_fend = false")
        sec_prep_code += cpp.statement("section_encountered = true")
        sec_prep_code += cpp.statement("cont.seekg(curpos)")

        if isinstance(mfdic, str):
            varname = _mf_mt_dict_varname(mf, None)
            funname = mfdic
            conditions.append(f"mf == {mf}")
            sec_read_code = generate_parse_or_read_verbatim(funname, "parse_opts")
            section_code = sec_prep_code + sec_read_code
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
                curcond = cpp.logical_and([curcond, "is_firstline"])
                # in case of MF=0/MT=0, we want to register that the tpid record has been read
                section_code += cpp.statement("found_tpid = true")

            sec_read_code = generate_parse_or_read_verbatim(funname, "parse_opts")
            section_code += sec_prep_code + sec_read_code
            statements.append(section_code)
            conditions.append(curcond)

    # if no parser function is registered for an MF/MT section
    # we read it in verbatim
    curcond = cpp.logical_and([f"mf != 0", "mt != 0"])
    curstat = aux.read_section_verbatim(
        "verbatim_section", "mat", "mf", "mt", "cont", "is_firstline", "parse_opts"
    )
    curstat += cpp_varaux.dict_assign("mfmt_dict", ["mf", "mt"], "verbatim_section")
    statements.append(curstat)
    conditions.append(curcond)

    # blank line treatment
    curcond = aux.is_blank_line()
    curstat = cpp.pureif(
        cpp.logical_not("parse_opts.ignore_blank_lines"),
        cpp.throw_runtime_error("Blank line detected"),
    )
    conditions.append(curcond)
    statements.append(curstat)

    # tend record treatment
    curcond = cpp.logical_and(["after_mend == true", aux.is_tend("parse_opts")])
    curstat = cpp.statement("after_mend = false")
    curstat += cpp.statement("after_tend = true")
    conditions.append(curcond)
    statements.append(curstat)
    # mend record treatment
    curcond = cpp.logical_and(["after_fend == true", aux.is_mend("parse_opts")])
    curstat = cpp.statement("after_fend = false")
    curstat = cpp.statement("after_mend = true")
    conditions.append(curcond)
    statements.append(curstat)
    # fend record treatment
    curcond = aux.is_fend("mat", "parse_opts")
    curstat = cpp.statement("after_fend = true")
    conditions.append(curcond)
    statements.append(curstat)

    # default branch
    errmsg = cpp.line("")
    errmsg += cpp.line(
        r'std::string("Invalid line encountered! This line is outside any MF/MT section.\n")',
        cpp.INDENT,
    )
    errmsg += cpp.line(r'+ "Line: " + cpp_line', cpp.INDENT)
    default_code = cpp.throw_runtime_error(errmsg, quote=False)

    body += cpp.indent_code(
        cpp.conditional_branches(conditions, statements, default=default_code)
    )
    body += cpp.statement("last_mat = mat", cpp.INDENT)
    body += cpp.statement("last_mf = mf", cpp.INDENT)
    body += cpp.statement("last_mt = mt", cpp.INDENT)
    body += cpp.statement("curpos = cont.tellg()", cpp.INDENT)
    body += cpp.statement("is_firstline = false", cpp.INDENT)
    body += cpp.close_block()
    body += cpp.statement("return mfmt_dict")

    args = (
        ("std::istream&", "cont"),
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", f"parse_opts=default_parsing_options()"),
    )
    code += cpp.function(name, body, "py::dict", *args)
    code += cpp.line("")
    return code


def generate_cpp_writefun_wrappers_string(writefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for p in writefuns:
        code += cpp.line(f"py::dict {p}(std::string& strcont{args_str}) {{")
        code += cpp.statement("std::istringstream iss(strcont)", cpp.INDENT)
        code += cpp.statement(f"return {p}_istream(iss{args_str2})", cpp.INDENT)
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
        code += cpp.line(f"py::dict {p}_file(std::string& filename{args_str}) {{")
        code += cpp.statement("std::ifstream inpfile(filename)", cpp.INDENT)
        code += cpp.indent_code(
            cpp.pureif(
                cpp.logical_not("inpfile.is_open()"),
                cpp.statement(
                    "throw std::ifstream::failure"
                    + '("failed to open file " + filename)'
                ),
            ),
            cpp.INDENT,
        )
        code += cpp.statement(f"return {p}_istream(inpfile{args_str2})", cpp.INDENT)
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
        'py::arg("cont")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = false',
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["write_endf_file"],
        module_name,
        'py::arg("filename")',
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
