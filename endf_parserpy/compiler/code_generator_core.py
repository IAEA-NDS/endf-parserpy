############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .code_generator_parsing_core import (
    generate_code_for_varassign,
    generate_endf_dict_assignments,
)

from lark.tree import Tree
from lark.lexer import Token
from lark import Lark
from endf_parserpy.utils.tree_utils import get_child, get_name
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from .expr_utils.node_trafos import node2str
from .expr_utils.tree_trafos import reconstruct_endf_line_template
from . import cpp_primitives as cpp
from . import cpp_boilerplate
from .cpp_types import cpp_varops_query
from .cpp_types import cpp_varops_assign
from .cpp_types.cpp_type_scalar.auxiliary import init_readflag
from .lookahead_management import (
    init_lookahead_counter,
    remove_lookahead_counter,
    decrease_lookahead_counter,
    in_lookahead,
    should_proceed,
)
from .variable_management import (
    register_abbreviation,
    update_vardict,
    expand_abbreviation,
    register_var,
    unregister_var,
)
from . import endf2cpp_aux as aux
from .cpp_types.cpp_varops_query import (
    expr2str_shiftidx,
    logical_expr2cppstr,
)
from .node_aux import (
    simplify_expr_node,
    node_and_kids_to_ParseNode,
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
from .expr_utils.exceptions import (
    ModuloEquationError,
    MultipleVariableOccurrenceError,
    SeveralUnknownVariablesError,
)


def generate_vardefs(vardict, save_state=False):
    code = cpp.comment("variable declarations")
    for vartok in tuple(vardict.keys()):
        dtype = vardict[vartok]
        if vartok.startswith("__"):
            continue
        code += cpp_varops_assign.define_var(vartok, vardict, save_state=save_state)
    return code


def generate_cpp_parsefun(name, endf_recipe, mat=None, mf=None, mt=None, parser=None):
    if parser is None:
        parser = Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)
    parsetree = parser.parse(endf_recipe)
    parsetree = transform_nodes(parsetree, simplify_expr_node)
    parsetree = transform_nodes_inplace(parsetree, node_and_kids_to_ParseNode)

    vardict = {}

    ctrl_code = ""
    var_mat = VariableToken(Token("VARNAME", "MAT"))
    var_mf = VariableToken(Token("VARNAME", "MF"))
    var_mt = VariableToken(Token("VARNAME", "MT"))
    ctrl_code += cpp.statement("std::streampos cpp_startpos = cont.tellg()")
    ctrl_code += aux.read_raw_line()

    matval = aux.get_mat_number() if mat is None else str(mat)
    mfval = aux.get_mf_number() if mf is None else str(mf)
    mtval = aux.get_mt_number() if mt is None else str(mt)
    ctrl_code += cpp.statement(f"int mat = {matval}")
    ctrl_code += cpp.statement(f"int mf = {mfval}")
    ctrl_code += cpp.statement(f"int mt = {mtval}")
    ctrl_code += cpp.statement("cont.seekg(cpp_startpos)")
    ctrl_code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)

    ctrl_code += generate_code_for_varassign(var_mat, vardict, matval, int)
    ctrl_code += generate_code_for_varassign(var_mf, vardict, mfval, int)
    ctrl_code += generate_code_for_varassign(var_mt, vardict, mtval, int)

    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mat, vardict)
    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mf, vardict)
    ctrl_code += cpp_varops_assign.store_var_in_endf_dict(var_mt, vardict)
    ctrl_code += cpp.statement("cont.seekg(cpp_startpos)")

    code = generate_code_from_parsetree(parsetree, vardict)

    # must be after traversing the tree because assign_exprstr_to_var
    # populates vardict and type info therein
    vardefs = generate_vardefs(vardict)

    fun_header = cpp_boilerplate.parsefun_header(name)
    fun_footer = cpp.indent_code(generate_endf_dict_assignments(vardict), cpp.INDENT)
    fun_footer += cpp_boilerplate.parsefun_footer()
    fun_body = cpp.indent_code(vardefs + ctrl_code + code, cpp.INDENT)
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
    code += cpp.indent_code(vardef_code, cpp.INDENT)
    code += cpp.indent_code(body_code, cpp.INDENT)
    code += cpp.indent_code(generate_endf_dict_assignments(vardict), cpp.INDENT)
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
            cpp.statement("bool cpp_found_match = false", indent=cpp.INDENT),
        ]
    )
    new_vardict = vardict.copy()
    if_statement_code = generate_code_for_if_statement(if_statement, new_vardict)
    update_vardict(add_vardict, new_vardict)
    code += cpp.indent_code(if_statement_code, cpp.INDENT)
    for elif_statement in elif_statements:
        new_vardict = vardict.copy()
        code += cpp.indent_code(
            code=cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_for_if_statement(elif_statement, new_vardict),
            ),
            indent=cpp.INDENT,
        )
        update_vardict(add_vardict, new_vardict)
    if else_statement is not None:
        else_code = get_child(else_statement, "if_body")
        new_vardict = vardict.copy()
        code += cpp.indent_code(
            cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_from_parsetree(else_code, new_vardict),
            )
        )
        update_vardict(add_vardict, new_vardict)

    code += cpp.close_block()
    update_vardict(vardict, add_vardict)
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
                cpp.statement(
                    "std::streampos cpp_old_streampos = cont.tellg()", cpp.INDENT
                ),
            ]
        )

        la_body_code = generate_code_from_parsetree(if_body, vardict)
        logical_expr_str = logical_expr2cppstr(if_head, vardict)
        vardef_code = generate_vardefs(vardict, save_state=True)
        code += cpp.indent_code(
            cpp.block(
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
            )
        )
        if lookahead_option is not None:
            remove_lookahead_counter(vardict)
            vardict = orig_vardict
        code += cpp.indent_code(
            cpp.pureif(
                condition="cpp_found_match",
                code=generate_code_from_parsetree(if_body, vardict),
            )
        )
        code += cpp.close_block()
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
        valcode = aux.get_numeric_field(idx, dtype, "parse_opts")
        try:
            code += generate_code_for_varassign(
                child, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
        except (ModuloEquationError, MultipleVariableOccurrenceError) as exc:
            indexed_children.append(indexed_child)
            num_failures += 1
            if num_failures > 15:
                throw_cpp = True
        except SeveralUnknownVariablesError as exc:
            indexed_children.append(indexed_child)
            num_failures += 1
            if num_failures > 10:
                raise exc
    return code


def generate_code_for_text(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
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
        valcode = aux.get_text_field(ofs, length)
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

    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
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
    code += cpp.statement(f"cpp_intvec.push_back({valcode})", cpp.INDENT)
    code += cpp.close_block()
    code += generate_code_for_varassign(kij_expr, vardict, "cpp_intvec", "intvec")
    return cpp.open_block() + cpp.indent_code(code, cpp.INDENT) + cpp.close_block()


def generate_code_for_send(node, vardict):
    return aux.read_send("mat", "mf", "parse_opts")


def generate_code_for_cont(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
    record_fields = get_child(node, "record_fields")
    code += cpp.comment("read CONT record")
    code += generate_code_from_record_fields(record_fields, vardict)
    return code


def generate_code_for_dir(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
    record_fields = get_child(node, "dir_fields")
    code += cpp.comment("read TEXT record")
    code += generate_code_from_record_fields(record_fields, vardict, skip=(0, 1), ofs=2)
    return code


def generate_code_for_tab1(node, vardict):
    code = ""
    code += cpp.comment("read TAB1 record")
    template = reconstruct_endf_line_template(node)
    code += aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
    tab1_fields = get_child(node, "tab1_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab1_fields, "record_fields")
    tab1_def = get_child(tab1_fields, "tab1_def")

    code += generate_code_from_record_fields(record_fields, vardict, skip=(4, 5))

    if not should_proceed(vardict):
        return code
    # reading the tab body counts as one lookahead step
    decrease_lookahead_counter(vardict)

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    colnodes = [v for v in tab1_def.children if is_extvar(v)]
    assert len(colnodes) == 2
    xvar = VariableToken(colnodes[0])
    yvar = VariableToken(colnodes[1])
    nr = aux.get_int_field(4, "parse_opts")
    np = aux.get_int_field(5, "parse_opts")
    tabdata = aux.get_tab1_body(xvar, yvar, nr, np, "mat", "mf", "mt", "parse_opts")
    INTvar = VariableToken(Token("VARNAME", "INT"))
    NBTvar = VariableToken(Token("VARNAME", "NBT"))

    if sectok is not None:
        vardict = {"__up": vardict}

    assigncode = cpp.statement(f"Tab1Body tab_body = {tabdata}")
    assigncode += generate_code_for_varassign(xvar, vardict, "tab_body.X", "floatvec")
    assigncode += generate_code_for_varassign(yvar, vardict, "tab_body.Y", "floatvec")
    assigncode += generate_code_for_varassign(INTvar, vardict, "tab_body.INT", "intvec")
    assigncode += generate_code_for_varassign(NBTvar, vardict, "tab_body.NBT", "intvec")
    assigncode = cpp.block(assigncode)

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        dictassigns = generate_endf_dict_assignments(vardict)
        code += aux.open_section(sectok, vardict)
        code += cpp.indent_code(vardefs + assigncode + dictassigns)
        code += aux.close_section()
    else:
        code += assigncode
    return code


def generate_code_for_tab2(node, vardict):
    code = ""
    code += cpp.comment("read TAB2 record")
    template = reconstruct_endf_line_template(node)
    code += aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
    tab2_fields = get_child(node, "tab2_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab2_fields, "record_fields")

    code += generate_code_from_record_fields(record_fields, vardict, skip=(4,))

    if not should_proceed(vardict):
        return code
    # reading the tab body counts as one lookahead step
    decrease_lookahead_counter(vardict)

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    nr = aux.get_int_field(4, "parse_opts")
    tabdata = aux.get_tab2_body(nr, "mat", "mf", "mt", "parse_opts")
    INTvar = VariableToken(Token("VARNAME", "INT"))
    NBTvar = VariableToken(Token("VARNAME", "NBT"))

    if sectok is not None:
        vardict = {"__up": vardict}

    assigncode = cpp.statement(f"Tab2Body tab_body = {tabdata}")
    assigncode += generate_code_for_varassign(INTvar, vardict, "tab_body.INT", "intvec")
    assigncode += generate_code_for_varassign(NBTvar, vardict, "tab_body.NBT", "intvec")
    assigncode = cpp.block(assigncode)

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        dictassigns = generate_endf_dict_assignments(vardict)
        code += aux.open_section(sectok, vardict)
        code += cpp.indent_code(vardefs + assigncode + dictassigns)
        code += aux.close_section()
    else:
        code += assigncode
    return code


def generate_code_for_list(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = ""
    code += aux.define_current_template(template)
    code += aux.read_line_la("mat", "mf", "mt", "parse_opts", vardict)
    record_fields = get_child(node, "record_fields")
    code += cpp.comment("read LIST record")
    code += generate_code_from_record_fields(record_fields, vardict)
    if not should_proceed(vardict):
        return code
    # reading the list body is considered as one lookahead step
    decrease_lookahead_counter(vardict)

    list_name_node = get_child(node, "list_name", nofail=True)
    list_body_node = get_child(node, "list_body")
    sectok = None
    if list_name_node is not None:
        sectok = VariableToken(get_child(list_name_node, "extvarname"))
        vardict = {"__up": vardict}

    lbr = aux.ListBodyRecorder
    icode = lbr.start_list_body_loop("mat", "mf", "mt", "parse_opts")
    list_body_code = generate_code_for_list_body(list_body_node, vardict)
    icode += lbr.indent(list_body_code)
    icode += lbr.finish_list_body_loop()

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        dictassigns = generate_endf_dict_assignments(vardict)
        code += aux.open_section(sectok, vardict)
        code += cpp.indent_code(vardefs + icode + dictassigns)
        code += aux.close_section()
    else:
        code += icode
    return code


def generate_code_for_list_body(node, vardict):
    lbr = aux.ListBodyRecorder
    code = cpp.comment("read LIST body")
    for child in node.children:
        child_name = get_name(child)
        if child_name == "expr":
            current_value = lbr.get_element("parse_opts")
            code += generate_code_for_varassign(child, vardict, current_value, float)
            code += lbr.update_counters_and_line("mat", "mf", "mt", "parse_opts")
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
    if loopvar in vardict:
        raise TypeError(f"variable {loopvar} already declared")

    register_var(loopvar, "loopvartype", "Scalar", vardict, track_read=False)
    cpp_loopvar = cpp_varops_query.get_cpp_varname(loopvar, vardict)

    code = cpp.indent_code(
        rf"""
    for (int {cpp_loopvar} = {start_expr_str};
       {cpp_loopvar} <= {stop_expr_str}; {cpp_loopvar}++) {{
    """,
        -4,
    )
    code += cpp.indent_code(init_readflag(loopvar, val=True))
    body_code = parsefun(for_body, vardict)
    code += cpp.indent_code(body_code)
    code += cpp.close_block()
    unregister_var(loopvar, vardict)
    # add code propagated upward from downstream nodes
    code = node.precode + code
    return code