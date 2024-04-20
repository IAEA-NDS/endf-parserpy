############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/04/20
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from lark import Lark
from ..tree_utils import get_child, get_name
from ..endf_lark import endf_recipe_grammar
from .expr_utils.conversion import VariableToken
from .expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from .expr_utils.node_trafos import node2str, replace_node
from . import cpp_primitives as cpp
from . import cpp_boilerplate
from . import endf2cpp_aux as aux
from .lookahead_management import (
    init_lookahead_counter,
    remove_lookahead_counter,
    decrease_lookahead_counter,
    in_lookahead,
    should_proceed,
)
from .variable_management import (
    register_abbreviation,
    unregister_abbreviations,
    expand_abbreviation,
    count_not_encountered_vars,
    register_var,
    unregister_var,
)
from .node_aux import (
    simplify_expr_node,
    node_and_kids_to_ParseNode,
    get_varassign_from_expr,
    get_variables_in_expr,
    expr2str_shiftidx,
    logical_expr2cppstr,
)
from .node_checks import (
    is_expr,
    is_send,
    is_head_or_cont,
    is_dir,
    is_tab1,
    is_tab2,
    is_list,
    is_text,
    is_intg,
    is_section,
    is_extvar,
    is_textplaceholder,
    is_for_loop,
    is_if_clause,
    is_abbreviation,
)


def generate_vardefs(vardict, save_state=False):
    code = cpp.comment("variable declarations")
    for vartok, dtype in vardict.items():
        if vartok.startswith("__"):
            continue
        code += aux.define_var(vartok, dtype, save_state=save_state)
    return code


def generate_endf_dict_assignments(vardict):
    code = cpp.comment("store data in Python dictionary")
    for vartok in vardict:
        if vartok.startswith("__"):
            continue
        code += aux.store_var_in_endf_dict2(vartok, vardict)
    return code


def generate_mark_vars_as_unread(vardict, prefix=""):
    code = cpp.comment("accept new variable state")
    for vartok in tuple(vardict):
        if vartok.startswith("__"):
            continue
        # loop variables are not read in from the file
        # so even in lookahead we neither want to remove
        # their type information nor mark them as unread
        # at the cpp level.
        if vardict[vartok] == "loopvartype":
            continue
        code += aux.mark_var_as_unread(vartok, prefix)
        unregister_var(vartok, vardict)
    return code


def generate_cpp_parsefun(name, endf_recipe, parser=None):
    if parser is None:
        parser = Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)
    parsetree = parser.parse(endf_recipe)
    parsetree = transform_nodes(parsetree, simplify_expr_node)
    parsetree = transform_nodes_inplace(parsetree, node_and_kids_to_ParseNode)
    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))
    vardict = {var_mat: int, var_mf: int, var_mt: int}

    code = generate_code_from_parsetree(parsetree, vardict)

    vardefs = generate_vardefs(vardict)
    ctrl_code = cpp.statement("std::streampos cpp_startpos = cont.tellg()")
    ctrl_code += aux.read_line()
    ctrl_code += aux.assign_exprstr_to_var(
        var_mat, "std::stoi(cpp_line.substr(66, 4))", vardict
    )
    ctrl_code += aux.assign_exprstr_to_var(
        var_mf, "std::stoi(cpp_line.substr(70, 2))", vardict
    )
    ctrl_code += aux.assign_exprstr_to_var(
        var_mt, "std::stoi(cpp_line.substr(72, 3))", vardict
    )
    ctrl_code += aux.store_var_in_endf_dict(var_mat, vardict)
    ctrl_code += aux.store_var_in_endf_dict(var_mf, vardict)
    ctrl_code += aux.store_var_in_endf_dict(var_mt, vardict)
    ctrl_code += cpp.statement("cont.seekg(cpp_startpos)")

    fun_header = cpp_boilerplate.parsefun_header(name)
    fun_footer = cpp.indent_code(generate_endf_dict_assignments(vardict), 4)
    fun_footer += cpp_boilerplate.parsefun_footer()
    fun_body = cpp.indent_code(vardefs + ctrl_code + code, 4)
    code = fun_header + fun_body + fun_footer
    return code


def generate_code_from_parsetree(node, vardict):
    if not should_proceed(vardict):
        return ""

    if is_send(node):
        return generate_code_for_send(node, vardict)
    elif is_head_or_cont(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_cont(node, vardict)
    elif is_dir(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_dir(node, vardict)
    elif is_tab1(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_tab1(node, vardict)
    elif is_tab2(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_tab2(node, vardict)
    elif is_list(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_list(node, vardict)
    elif is_text(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_text(node, vardict)
    elif is_intg(node):
        decrease_lookahead_counter(vardict)
        return generate_code_for_intg(node, vardict)
    elif is_abbreviation(node):
        register_abbreviation(node, vardict)
    elif is_for_loop(node):
        return generate_code_for_loop(node, vardict)
    elif is_if_clause(node):
        return generate_code_for_if_clause(node, vardict)
    elif is_section(node):
        return generate_code_for_section(node, vardict)

    code = ""
    if isinstance(node, Tree):
        for child in node.children:
            code += generate_code_from_parsetree(child, vardict)
    return code


def _generate_code_for_section(sectok, section_body, vardict, parsefun):
    pardict = vardict
    vardict = {"__up": pardict}
    body_code = parsefun(section_body, vardict)
    vardef_code = generate_vardefs(vardict)
    code = cpp.comment(f"open section {sectok}")
    code += aux.open_section(sectok, vardict)
    code += cpp.indent_code(vardef_code, 4)
    code += cpp.indent_code(body_code, 4)
    code += cpp.indent_code(generate_endf_dict_assignments(vardict), 4)
    code += aux.close_section()
    vardict = pardict
    return code


def generate_code_for_section(node, vardict):
    section_head = get_child(node, "section_head")
    section_body = get_child(node, "section_body")
    extvarname = get_child(section_head, "extvarname")
    sectok = VariableToken(extvarname)
    code = _generate_code_for_section(
        sectok, section_body, vardict, generate_code_from_parsetree
    )
    return code


def generate_code_for_loop(node, vardict):
    for_head = get_child(node, "for_head")
    for_body = get_child(node, "for_body")
    loopvar_node = get_child(for_head, "VARNAME")
    start_expr_node = get_child(get_child(for_head, "for_start"), "expr").children[0]
    stop_expr_node = get_child(get_child(for_head, "for_stop"), "expr").children[0]
    parsefun = generate_code_from_parsetree
    code = _generate_code_for_loop(
        node, vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
    )
    return code


def generate_code_for_if_clause(node, vardict):
    add_vardict = {}
    if_statement = get_child(node, "if_statement")
    elif_statements = [c for c in node.children if get_name(c) == "elif_statement"]
    else_statement = get_child(node, "else_statement", nofail=True)
    code = cpp.concat(
        [
            cpp.comment("evaluate if-elif-else clause"),
            cpp.open_block(),
            cpp.statement("bool cpp_found_match = false", indent=4),
        ]
    )
    new_vardict = vardict.copy()
    if_statement_code = generate_code_for_if_statement(if_statement, new_vardict)
    add_vardict.update(new_vardict)
    code += cpp.indent_code(if_statement_code, 4)
    for elif_statement in elif_statements:
        new_vardict = vardict.copy()
        code += cpp.indent_code(
            code=cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_for_if_statement(elif_statement, new_vardict),
            ),
            indent=4,
        )
        add_vardict.update(new_vardict)
    if else_statement is not None:
        else_code = get_child(else_statement, "if_body")
        new_vardict = vardict.copy()
        code += cpp.indent_code(
            code=cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_from_parsetree(else_code, new_vardict),
            ),
            indent=4,
        )
        add_vardict.update(new_vardict)

    code += cpp.close_block()
    if "__up" in add_vardict:
        del add_vardict["__up"]
    unregister_abbreviations(add_vardict)
    vardict.update(add_vardict)
    return code


def generate_code_for_if_statement(node, vardict):
    if_head = get_child(node, "if_head")
    if_body = get_child(node, "if_body")
    lookahead_option = get_child(node, "lookahead_option", nofail=True)
    if in_lookahead(vardict) or lookahead_option is not None:
        if in_lookahead(vardict) and lookahead_option is not None:
            raise TypeError("nested lookahead is not possible")
        orig_vardict = vardict
        vardict = orig_vardict.copy()

    if lookahead_option is not None:
        la_expr = get_child(lookahead_option, "expr")
        la_expr_str = transform_nodes(la_expr.children[0], node2str)
        la_steps = int(la_expr_str)
        init_lookahead_counter(la_steps, vardict)

    code = ""
    if in_lookahead(vardict):
        code = cpp.concat(
            [
                cpp.comment("if statement evaluation with lookahead"),
                cpp.open_block(),
                cpp.statement("std::streampos cpp_old_streampos = cont.tellg()", 4),
            ]
        )

        la_body_code = generate_code_from_parsetree(if_body, vardict)
        logical_expr_str = logical_expr2cppstr(if_head, vardict)
        vardef_code = generate_vardefs(vardict, save_state=True)
        code += cpp.indent_code(
            code=cpp.block(
                cpp.concat(
                    [
                        vardef_code,
                        la_body_code,
                        cpp.pureif(
                            condition=logical_expr_str,
                            code=cpp.statement("cpp_found_match = true"),
                        ),
                        cpp.statement("cont.seekg(cpp_old_streampos)"),
                    ]
                )
            ),
            indent=4,
        )
        remove_lookahead_counter(vardict)
        if lookahead_option is not None:
            vardict = orig_vardict
        code += cpp.indent_code(
            code=cpp.pureif(
                condition="cpp_found_match",
                code=generate_code_from_parsetree(if_body, vardict),
            ),
            indent=4,
        )
        code += "}\n"
    else:
        logical_expr_str = logical_expr2cppstr(if_head, vardict)
        code += cpp.pureif(
            condition=logical_expr_str,
            code=cpp.concat(
                [
                    cpp.comment("if statement evaluation"),
                    cpp.statement("cpp_found_match = true"),
                    generate_code_from_parsetree(if_body, vardict),
                ]
            ),
        )

    code = cpp.pureif(condition="! cpp_found_match", code=code)
    return code


def _generate_code_for_varassign(
    vartok, node, vardict, valcode, dtype, throw_cpp=False
):
    try:
        vartok, expr = get_varassign_from_expr(vartok, node, vardict)
    except Exception as exc:
        exprstr = transform_nodes(node, node2str)
        errmsg = (
            f"except for {vartok}, all variables appearing "
            + "in the recipe field expression are available but not able "
            + f"to solve the equation {exprstr}==value for {vartok}"
        )
        if throw_cpp:
            return cpp.throw_runtime_error(errmsg)
        raise exc

    cpp_val_tok = Token("VARIABLE", "cpp_val")
    code = ""
    if expr == cpp_val_tok:
        code += aux.assign_exprstr_to_var(vartok, valcode, vardict, node=node)
    else:
        if dtype == float:
            cpp_newval_tok = Token("VARNAME", "cpp_float_val")
        elif dtype == int:
            cpp_newval_tok = Token("VARNAME", "cpp_int_val")
        elif dtype == "intvec":
            cpp_newval_tok = Token("VARNAME", "cpp_intvec")
        else:
            raise NotImplementedError(f"unknown node type {dtype}")
        cpp_newval_tok = VariableToken(cpp_newval_tok)
        expr = transform_nodes(expr, replace_node, cpp_val_tok, cpp_newval_tok)
        code += aux.assign_exprstr_to_var(
            cpp_newval_tok,
            valcode,
            vardict,
            use_cpp_name=False,
            mark_as_read=False,
            node=node,
        )
        exprstr = transform_nodes(
            expr, expr2str_shiftidx, vardict, rawvars=(cpp_newval_tok,)
        )
        code += aux.assign_exprstr_to_var(vartok, exprstr, vardict, node=node)

    register_var(vartok, dtype, vardict)
    return code


def generate_code_for_varassign(
    node, vardict, valcode, dtype, throw_cpp=False, noassign_code=""
):
    code = ""
    node = transform_nodes_inplace(node, expand_abbreviation, vardict)
    variables = get_variables_in_expr(node)
    if count_not_encountered_vars(node, vardict) > 1:
        raise IndexError("more than one unencountered variables")
    if len(variables) == 0:
        # NOTE: consistency checking could be done here
        return noassign_code

    exprstr = transform_nodes(node, node2str)
    code = cpp.conditional_branches(
        conditions=[aux.did_not_read_var(v, v.indices) for v in variables],
        codes=[
            cpp.concat(
                [
                    cpp.pureif(
                        condition=aux.any_unread_vars(variables.difference((v,))),
                        code=cpp.throw_runtime_error(
                            "some of the required variables "
                            + f"""{", ".join(variables.difference((v,)))} """
                            + f"to solve the equation {exprstr}=val "
                            + f"for variable {v} are missing"
                        ),
                    ),
                    _generate_code_for_varassign(
                        v, node, vardict, valcode, dtype, throw_cpp=throw_cpp
                    ),
                ]
            )
            for v in variables
        ],
    )
    return code


def generate_code_from_record_fields(node, vardict, skip=None, ofs=0):
    code = ""
    num_failures = 0
    expr_list = [c for c in node.children if is_expr(c)]
    indexed_children = list(enumerate(expr_list))
    throw_cpp = False
    while len(indexed_children) > 0:
        indexed_child = indexed_children.pop(0)
        idx, child = indexed_child
        idx += ofs
        if not is_expr(child):
            continue
        if skip is not None and idx in skip:
            continue
        dtype = float if idx < 2 else int
        valcode = aux.get_numeric_field(idx, dtype)
        try:
            code += generate_code_for_varassign(
                child, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
        except Exception as exc:
            indexed_children.append(indexed_child)
            num_failures += 1
            if num_failures > 10:
                throw_cpp = True
            elif throw_cpp:
                raise exc
    return code


def generate_code_for_text(node, vardict):
    code = aux.read_line()
    text_fields = get_child(node, "text_fields")
    tphs = [v for v in text_fields.children if is_textplaceholder(v)]
    ofs = 0
    is_first = True
    for i, tph in enumerate(tphs):
        v = get_child(tph, "extvarname", nofail=True)
        txtlen = get_child(tph, "TEXTLENGTH", nofail=True)
        if is_first:
            is_first = False
        elif txtlen is None:
            raise TypeError("several textplaceholder must have TEXTLENGTH")
        if v is None:
            if txtlen is None:
                raise TypeError("somthing strange happened")
            ofs += int(txtlen)
            continue
        length = int(txtlen) if txtlen is not None else 66
        vartok = VariableToken(v)
        dtype = str
        register_var(vartok, dtype, vardict)
        valcode = aux.get_text_field(vartok, ofs, length, vardict)
        code += generate_code_for_varassign(vartok, vardict, valcode, dtype)
        ofs += length
    return code


def generate_code_for_intg(node, vardict):
    ndigit_expr = get_child(get_child(node, "ndigit_expr"), "expr")
    ndigit_exprstr = transform_nodes(ndigit_expr, expr2str_shiftidx, vardict)
    intg_fields = get_child(node, "intg_fields")
    intg_fields_kids = [f for f in intg_fields.children if is_expr(f)]
    ii_expr = intg_fields_kids[0]
    jj_expr = intg_fields_kids[1]
    kij_expr = intg_fields_kids[2]

    code = aux.read_line()
    code += cpp.statement(f"int cpp_ndigit = {ndigit_exprstr}")
    code += cpp.pureif(
        cpp.logical_or(["cpp_ndigit < 2", "cpp_ndigit > 6"]),
        cpp.throw_runtime_error("invalid NDIGIT (must be between 2 and 6)"),
    )
    val_ii = aux.get_custom_int_field(0, 5)
    val_jj = aux.get_custom_int_field(5, 5)
    code += generate_code_for_varassign(ii_expr, vardict, val_ii, int)
    code += generate_code_for_varassign(jj_expr, vardict, val_jj, int)
    code += cpp.statement("int cpp_step = cpp_ndigit + 1")
    code += cpp.statement("int cpp_end = 65")
    code += cpp.statement("int cpp_start")
    code += cpp.ifelse(
        "cpp_ndigit <= 5",
        cpp.statement("cpp_start = 11"),
        cpp.statement("cpp_start = 10"),
    )
    code += cpp.statement("std::vector<int> cpp_intvec")
    code += cpp.line(
        "for (int cpp_i = cpp_start; cpp_i < cpp_end; cpp_i += cpp_step) {"
    )
    valcode = aux.get_custom_int_field("cpp_i", "cpp_step")
    code += cpp.statement(f"cpp_intvec.push_back({valcode})", 4)
    code += cpp.close_block()
    code += generate_code_for_varassign(kij_expr, vardict, "cpp_intvec", "intvec")
    return cpp.open_block() + cpp.indent_code(code, 4) + cpp.close_block()


def generate_code_for_send(node, vardict):
    return aux.read_send()


def generate_code_for_cont(node, vardict):
    code = aux.read_line()
    record_fields = get_child(node, "record_fields")
    code += cpp.comment("read CONT record")
    code += generate_code_from_record_fields(record_fields, vardict)
    return code


def generate_code_for_dir(node, vardict):
    code = aux.read_line()
    record_fields = get_child(node, "dir_fields")
    code += cpp.comment("read TEXT record")
    code += generate_code_from_record_fields(record_fields, vardict, skip=(0, 1), ofs=2)
    return code


def generate_code_for_tab1(node, vardict):
    code = "\n// read TAB1 record\n"
    code += aux.read_line()
    tab1_fields = get_child(node, "tab1_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab1_fields, "record_fields")
    tab1_def = get_child(tab1_fields, "tab1_def")

    code += generate_code_from_record_fields(record_fields, vardict, skip=(4, 5))

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    colnodes = [v for v in tab1_def.children if is_extvar(v)]
    assert len(colnodes) == 2
    xvar = VariableToken(colnodes[0])
    yvar = VariableToken(colnodes[1])
    if not in_lookahead(vardict):
        if sectok is None:
            code += aux.read_tab_body(xvar, yvar)
        else:
            code += aux.open_section(sectok, vardict)
            body_code = aux.read_tab_body(xvar, yvar)
            code += cpp.indent_code(body_code, 4)
            code += aux.close_section()
    return code


def generate_code_for_tab2(node, vardict):
    code = "\n// read TAB2 record\n"
    code += aux.read_line()
    tab2_fields = get_child(node, "tab2_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab2_fields, "record_fields")

    code += generate_code_from_record_fields(record_fields, vardict, skip=(4,))

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    if not in_lookahead(vardict):
        if sectok is None:
            code += aux.read_tab_body(None, None)
        else:
            code += aux.open_section(sectok, vardict)
            body_code = aux.read_tab_body(None, None)
            code += cpp.indent_code(body_code, 4)
            code += aux.close_section()
    return code


def generate_code_for_list(node, vardict):
    code = aux.read_line()
    record_fields = get_child(node, "record_fields")
    code += cpp.comment("read LIST record")
    code += generate_code_from_record_fields(record_fields, vardict)
    if not should_proceed(vardict):
        return code
    list_body_node = get_child(node, "list_body")
    code += cpp.open_block()
    code += cpp.statement(f"int cpp_npl = {aux.get_int_field(4)}", 4)
    values = aux.get_float_vec("cpp_npl")
    code += cpp.statement(f"cpp_floatvec = {values}", 4)
    code += cpp.statement("int cpp_j = 0", 4)
    list_body_code = generate_code_for_list_body(list_body_node, vardict)
    code += cpp.indent_code(list_body_code, 4)
    code += cpp.close_block()
    decrease_lookahead_counter(vardict)
    return code


def generate_code_for_list_body(node, vardict):
    code = cpp.comment("read LIST body")
    for child in node.children:
        child_name = get_name(child)
        if child_name == "expr":
            code += generate_code_for_varassign(
                child,
                vardict,
                "cpp_floatvec[cpp_j++]",
                float,
                noassign_code=cpp.statement("cpp_j++"),
            )
        elif child_name == "list_loop":
            code += generate_code_for_list_loop(child, vardict)
        elif child_name == "LINEPADDING":
            raise NotImplementedError("LINEPADDING not implemented")
    return code


def generate_code_for_list_loop(node, vardict):
    for_head = get_child(node, "list_for_head")
    for_body = get_child(node, "list_body")
    loopvar_node = get_child(for_head, "VARNAME")
    start_expr_node = get_child(get_child(for_head, "for_start"), "expr").children[0]
    stop_expr_node = get_child(get_child(for_head, "for_stop"), "expr").children[0]
    parsefun = generate_code_for_list_body
    code = _generate_code_for_loop(
        node, vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
    )
    return code


def _generate_code_for_loop(
    node, vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
):
    start_expr_node = transform_nodes(start_expr_node, expand_abbreviation, vardict)
    stop_expr_node = transform_nodes(stop_expr_node, expand_abbreviation, vardict)
    start_expr_str = transform_nodes(start_expr_node, expr2str_shiftidx, vardict)
    stop_expr_str = transform_nodes(stop_expr_node, expr2str_shiftidx, vardict)
    loopvar = VariableToken(loopvar_node)
    cpp_loopvar = aux.get_cpp_varname(loopvar)
    if loopvar in vardict:
        raise TypeError(f"variable {loopvar} already declared")
    register_var(loopvar, "loopvartype", vardict)

    code = cpp.indent_code(
        rf"""
    for (int {cpp_loopvar} = {start_expr_str};
         {cpp_loopvar} <= {stop_expr_str}; {cpp_loopvar}++) {{
    """,
        -4,
    )
    code += cpp.indent_code(aux.init_readflag(loopvar, val=True), 4)
    body_code = parsefun(for_body, vardict)
    code += cpp.indent_code(body_code, 4)
    code += "}\n"
    unregister_var(loopvar, vardict)
    # add code propagated upward from downstream nodes
    code = node.precode + code
    return code


def _mf_mt_parsefun_name(mf, mt):
    if mt is None or mt == -1:
        return f"parse_mf{mf}"
    return f"parse_mf{mf}mt{mt}"


def _mf_mt_dict_varname(mf, mt):
    if mt is None or mt == -1:
        return f"mf{mf}_dict"
    return f"mf{mf}_mt{mt}_dict"


def generate_master_parsefun(name, recipefuns):
    header = cpp.line(f"py::dict {name}(std::istream& cont) {{")
    footer = cpp.statement("return mfmt_dict", 4)
    footer += cpp.close_block()
    body = ""
    body += cpp.statement("bool is_firstline = true")
    body += cpp.statement("std::streampos curpos")
    body += cpp.statement("py::dict mfmt_dict")
    body += cpp.statement("py::dict curdict")
    body += cpp.statement("int mf")
    body += cpp.statement("int mt")
    body += cpp.statement("std::string cpp_line")
    body += cpp.statement("curpos = cont.tellg()")
    body += cpp.line("while (std::getline(cont, cpp_line)) {")
    body += cpp.statement("mf = std::stoi(cpp_line.substr(70, 2))", 4)
    body += cpp.statement("mt = std::stoi(cpp_line.substr(72, 3))", 4)

    conditions = []
    statements = []
    for mf, mfdic in recipefuns.items():
        if isinstance(mfdic, str):
            varname = _mf_mt_dict_varname(mf, None)
            funname = mfdic
            conditions.append(f"mf == {mf}")
            curstat = cpp.statement("cont.seekg(curpos)")
            curstat += aux.dict_assign(
                "mfmt_dict", ["mf", "mt"], f"{funname}_istream(cont)"
            )
            statements.append(curstat)
            continue
        for mt in reversed(sorted(mfdic.keys())):
            funname = mfdic[mt]
            varname = _mf_mt_dict_varname(mf, mt)
            if mt == -1:
                curcond = f"mf == {mf}"
            else:
                curcond = f"mf == {mf} && mt == {mt}"
            if mt == 0 and mt == 0:
                curcond = cpp.logical_and([curcond, "is_firstline"])
            curstat = cpp.statement("cont.seekg(curpos)")
            curstat += aux.dict_assign(
                "mfmt_dict", ["mf", "mt"], f"{funname}_istream(cont)"
            )
            statements.append(curstat)
            conditions.append(curcond)
    body += cpp.indent_code(cpp.conditional_branches(conditions, statements), 4)
    body += cpp.statement("curpos = cont.tellg()", 4)
    body += cpp.statement("is_firstline = false", 4)
    body += cpp.close_block()
    code = cpp.line("") + header + cpp.indent_code(body, 4) + footer + cpp.line("")
    return code


def generate_cpp_parsefun_wrappers_string(parsefuns):
    code = ""
    for p in parsefuns:
        code += cpp.line(f"py::dict {p}(std::string& strcont) {{")
        code += cpp.statement("std::istringstream iss(strcont)", 4)
        code += cpp.statement(f"return {p}_istream(iss)", 4)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_cpp_parsefun_wrappers_file(parsefuns):
    code = ""
    for p in parsefuns:
        code += cpp.line(f"py::dict {p}_file(std::string& filename) {{")
        code += cpp.statement("std::ifstream inpfile(filename)", 4)
        code += cpp.statement(f"return {p}_istream(inpfile)", 4)
        code += cpp.close_block()
        code += cpp.line("")
    return code


def generate_cpp_module_code(recipes):
    module_header = cpp_boilerplate.module_header()
    parsefuns_code = ""
    func_names = []
    recipefuns = {}
    for mf, mt_recipes in recipes.items():
        if isinstance(mt_recipes, str):
            func_name = _mf_mt_parsefun_name(mf, None)
            func_names.append(func_name)
            recipe = mt_recipes
            parsefuns_code += generate_cpp_parsefun(func_name + "_istream", recipe)
            recipefuns[mf] = func_name
            continue
        for mt, recipe in mt_recipes.items():
            print((mf, mt))
            func_name = _mf_mt_parsefun_name(mf, mt)
            func_names.append(func_name)
            parsefuns_code += generate_cpp_parsefun(func_name + "_istream", recipe)
            curdic = recipefuns.setdefault(mf, {})
            curdic[mt] = func_name
    master_parsefun_code = generate_master_parsefun("parse_endf_istream", recipefuns)
    func_names.append("parse_endf")
    parsefun_wrappers_code1 = generate_cpp_parsefun_wrappers_string(func_names)
    parsefun_wrappers_code2 = generate_cpp_parsefun_wrappers_file(func_names)
    func_names.append("parse_endf_file")
    pybind_glue = cpp_boilerplate.register_cpp_parsefuns(func_names)
    code = (
        module_header
        + parsefuns_code
        + master_parsefun_code
        + parsefun_wrappers_code1
        + parsefun_wrappers_code2
        + pybind_glue
    )
    return code
