############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/16
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from .code_generator_core import generate_vardefs, generate_code_from_parsetree
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
from .mode_management import register_numeric_field_getter
from .endf2cpp_aux import get_numeric_field


def mf_mt_parsefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"parse_mf{mf}"
    return f"parse_mf{mf}mt{mt}"


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


def _get_numeric_field_wrapper(node, idx, dtype, lookahead):
    valcode = get_numeric_field(idx, dtype, "parse_opts")
    code = ""
    return valcode, code


def generate_cpp_parsefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    vardict = {}
    register_numeric_field_getter(_get_numeric_field_wrapper, vardict)
    return generate_cpp_parse_or_write_fun(
        name, endf_recipe, mat, mf, mt, parser, vardict
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
        code += cpp.statement("std::ifstream inpfile(filename)", cpp.INDENT)
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
