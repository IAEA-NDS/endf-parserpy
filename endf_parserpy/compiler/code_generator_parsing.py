############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2025/07/07
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from .code_generator_core import generate_vardefs, generate_code_from_parsetree
from . import cpp_boilerplate
from . import cpp_boilerplate_reading
from .code_generator_core import (
    generate_cpp_parse_or_write_fun,
    generate_code_for_varassign,
)
from .code_generator_parsing_core import (
    generate_endf_dict_assignments,
    generate_parse_or_read_verbatim,
    generate_expr_validation,
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
    register_tab1_body_getter,
    register_tab2_body_getter,
    register_custom_int_field_getter,
    register_counter_field_getter,
    register_prepare_line_func,
    register_finalize_line_func,
    register_send_line_func,
    register_prepare_line_tape_func,
    register_finalize_line_tape_func,
    register_prepare_section_func,
    register_finalize_section_func,
    register_lookahead_tellg_statement,
    register_lookahead_seekg_statement,
    register_generate_expr_validation_func,
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
from .lookahead_management import in_lookahead


def mf_mt_parsefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"parse_mf{mf}"
    return f"parse_mf{mf}mt{mt}"


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


def _get_numeric_field_wrapper(node, idx, dtype, vardict):
    valcode = get_numeric_field(idx, dtype, "parse_opts")
    code = ""
    return valcode, code


def _get_text_field_wrapper(node, start, length, vardict):
    valcode = get_text_field(start, length)
    code = ""
    return valcode, code


def _get_tab1_body_wrapper(xvar, yvar, nr, np, vardict):
    valcode = get_tab1_body(xvar, yvar, nr, np, "mat", "mf", "mt", "parse_opts")
    code = ""
    return valcode, code


def _get_tab2_body_wrapper(nr, vardict):
    valcode = get_tab2_body(nr, "mat", "mf", "mt", "parse_opts")
    code = ""
    return valcode, code


def _get_custom_int_field_wrapper(node, start, length, vardict, idx=None):
    valcode = get_custom_int_field(start, length)
    code = ""
    return valcode, code


def _get_counter_field_wrapper(node, idx, vardict):
    valcode = get_numeric_field(idx, int, "parse_opts")
    code = ""
    return valcode, code


def _read_send_line_func_wrapper(vardict):
    code = aux.read_send("mat", "mf", "parse_opts")
    return code


def _prepare_line_func_wrapper(vardict):
    code = read_line_la(
        "cpp_line", "mat", "mf", "mt", "parse_opts", in_lookahead(vardict)
    )
    return code


def _finalize_line_func_wrapper(vardict):
    return ""


def _prepare_line_tape_func_wrapper():
    code = cpp.statement("std::string cpp_line")
    return code


def _finalize_line_tape_func_wrapper():
    return ""


def _prepare_section_func_wrapper(sectok, vardict):
    if sectok is None:
        # initialization
        code = cpp.statement("py::dict cpp_parent_dict")
        code += cpp.statement("py::dict cpp_current_dict")
        code += cpp.statement(
            "IndexShifterStore cpp_index_shifter_store(cpp_current_dict, list_mode)"
        )
        return code
    code = aux.open_section(sectok, vardict)
    code += cpp.statement(
        "IndexShifterStore cpp_index_shifter_store(cpp_current_dict, list_mode)"
    )
    return code


def _finalize_section_func_wrapper(sectok, vardict):
    code = generate_endf_dict_assignments(vardict)
    if sectok is None:
        return code
    code += aux.close_section()
    return code


def _generate_expr_validation_wrapper(actual_value, node, vardict):
    code = generate_expr_validation(actual_value, node, vardict)
    return code


def generate_cpp_parsefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    vardict = {}
    register_numeric_field_getter(_get_numeric_field_wrapper, vardict)
    register_text_field_getter(_get_text_field_wrapper, vardict)
    register_tab1_body_getter(_get_tab1_body_wrapper, vardict)
    register_tab2_body_getter(_get_tab2_body_wrapper, vardict)
    register_custom_int_field_getter(_get_custom_int_field_wrapper, vardict)
    register_counter_field_getter(_get_counter_field_wrapper, vardict)
    register_send_line_func(_read_send_line_func_wrapper, vardict)
    register_prepare_line_func(_prepare_line_func_wrapper, vardict)
    register_finalize_line_func(_finalize_line_func_wrapper, vardict)
    register_prepare_line_tape_func(_prepare_line_tape_func_wrapper, vardict)
    register_finalize_line_tape_func(_finalize_line_tape_func_wrapper, vardict)
    register_prepare_section_func(_prepare_section_func_wrapper, vardict)
    register_finalize_section_func(_finalize_section_func_wrapper, vardict)
    register_generate_expr_validation_func(_generate_expr_validation_wrapper, vardict)
    register_lookahead_tellg_statement(
        cpp.statement("std::streampos cpp_old_streampos = cont.tellg()"), vardict
    )
    register_lookahead_seekg_statement(
        cpp.statement("cont.seekg(cpp_old_streampos)"), vardict
    )

    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))

    ctrl_code = ""
    ctrl_code += cpp.statement("std::streampos cpp_startpos = cont.tellg()")
    ctrl_code += cpp.statement("std::string cpp_temp_line")
    ctrl_code += read_raw_line("cpp_temp_line")
    matval = aux.get_mat_number("cpp_temp_line") if mat is None else str(mat)
    mfval = aux.get_mf_number("cpp_temp_line") if mf is None else str(mf)
    mtval = aux.get_mt_number("cpp_temp_line") if mt is None else str(mt)
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

    fun_header = cpp_boilerplate_reading.parsefun_header(name)
    fun_footer = cpp_boilerplate_reading.parsefun_footer()
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


def _generate_check_end_records_fun(funname):
    checker_body = ""

    end_record_checks = cpp.pureif(
        cpp.logical_or(["after_mend == true", "after_tend == true"]),
        cpp.throw_runtime_error("No MF/MT section allowed after MEND/TEND record"),
    )
    end_record_checks += cpp.pureif(
        cpp.logical_and(["after_fend == true", "section_encountered == false"]),
        cpp.throw_runtime_error(
            "FEND record without preceding MF/MT section encountered"
        ),
    )
    end_record_checks += cpp.pureif(
        cpp.logical_and(["after_fend == true", "last_mf >= mf"]),
        cpp.throw_runtime_error("MF sections must be in ascending order"),
    )

    tpid_record_check = cpp.pureif(
        cpp.logical_and(
            ["found_tpid == false", "parse_opts.ignore_missing_tpid == false"]
        ),
        cpp.throw_runtime_error("Tape ID (TPID) record missing in first line"),
    )

    checker_body = cpp.pureif(
        "parse_opts.ignore_send_records == false", end_record_checks
    )
    checker_body += tpid_record_check

    args = (
        ("bool", "after_fend"),
        ("bool", "after_mend"),
        ("bool", "after_tend"),
        ("bool", "mat"),
        ("bool", "mf"),
        ("bool", "mt"),
        ("bool", "last_mat"),
        ("bool", "last_mf"),
        ("bool", "last_mt"),
        ("bool", "section_encountered"),
        ("bool", "found_tpid"),
        ("ParsingOptions", "parse_opts"),
    )

    checker_fun = cpp.function(funname, checker_body, "void", *args)
    return checker_fun


def generate_master_parsefun(name, recipefuns):
    code = ""
    code += cpp.line("")
    code += _generate_check_end_records_fun("_check_end_records")
    code += cpp.line("")

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
        sec_prep_code += cpp.pureif("mt != 0", cpp.statement("is_firstline = false"))

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
    curcond = cpp.logical_and([aux.is_blank_line(), "after_tend == false"])
    curstat = cpp.pureif(
        cpp.logical_not("parse_opts.ignore_blank_lines"),
        cpp.throw_runtime_error(
            "Blank line detected: Correct file or use `ignore_blank_lines` option"
        ),
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


def generate_cpp_parsefun_wrappers_string(parsefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for p in parsefuns:
        code += cpp.line(f"py::dict {p}(std::string& strcont{args_str}) {{")
        code += cpp.statement("std::istringstream iss(strcont)", cpp.INDENT)
        code += cpp.statement(f"return {p}_istream(iss{args_str2})", cpp.INDENT)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_cpp_parsefun_wrappers_file(parsefuns, *extra_args):
    args_str = ", ".join(arg[0] + " " + arg[1] for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    args_str2 = ", ".join(arg[1] for arg in extra_args)
    args_str2 = ", " + args_str2 if args_str2 != "" else args_str2
    code = ""
    for p in parsefuns:
        code += cpp.line(f"py::dict {p}_file(std::string& filename{args_str}) {{")
        code += cpp.statement(
            "std::ifstream inpfile(filename, std::ios::binary)", cpp.INDENT
        )
        code += cpp.pureif(
            cpp.logical_not("inpfile.is_open()"),
            cpp.statement(
                "throw std::ifstream::failure" + '("failed to open file " + filename)'
            ),
        )
        code += cpp.statement(f"return {p}_istream(inpfile{args_str2})", cpp.INDENT)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_all_cpp_parsefuns_code(recipes, module_name):
    parsefuns_code = ""
    func_names = []
    recipefuns = {}
    for mf, mt_recipes in recipes.items():
        if isinstance(mt_recipes, str):
            print(f"MF: {mf}")
            func_name = mf_mt_parsefun_name(mf, None)
            func_names.append(func_name)
            recipe = mt_recipes
            parsefuns_code += generate_cpp_parsefun(
                func_name + "_istream", recipe, mf=mf, mt=None
            )
            recipefuns[mf] = func_name
            continue
        for mt, recipe in mt_recipes.items():
            print(f"MF: {mf} MT: {mt}")
            func_name = mf_mt_parsefun_name(mf, mt)
            func_names.append(func_name)
            mt_ = mt if mt != -1 else None
            parsefuns_code += generate_cpp_parsefun(
                func_name + "_istream", recipe, mf=mf, mt=mt_
            )
            curdic = recipefuns.setdefault(mf, {})
            curdic[mt] = func_name
    parsefun_wrappers_code1 = generate_cpp_parsefun_wrappers_string(
        func_names, ("ParsingOptions", "parse_opts")
    )
    parsefun_wrappers_code2 = generate_cpp_parsefun_wrappers_file(
        func_names, ("ParsingOptions", "parse_opts")
    )
    # special case for the master function calling the other mf/mt parser funs
    master_parsefun_code = generate_master_parsefun("parse_endf_istream", recipefuns)
    parsefun_wrappers_code1 += generate_cpp_parsefun_wrappers_string(
        ["parse_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    parsefun_wrappers_code2 += generate_cpp_parsefun_wrappers_file(
        ["parse_endf"],
        ("py::object", "exclude"),
        ("py::object", "include"),
        ("ParsingOptions", "parse_opts"),
    )
    pybind_glue = ""
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["parse_endf"],
        module_name,
        'py::arg("cont")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = false',
    )
    pybind_glue += cpp_boilerplate.register_cpp_parsefuns(
        ["parse_endf_file"],
        module_name,
        'py::arg("filename")',
        'py::arg("exclude") = py::none()',
        'py::arg("include") = py::none()',
        'py::arg("parse_opts") = default_parsing_options()',
    )

    all_parsefun_codes = (
        parsefuns_code
        + master_parsefun_code
        + parsefun_wrappers_code1
        + parsefun_wrappers_code2
    )
    return all_parsefun_codes, pybind_glue
