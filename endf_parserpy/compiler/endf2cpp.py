############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/03/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
from lark import Lark
from ..tree_utils import get_child, get_name
from ..endf_lark import endf_recipe_grammar
from ..endf_recipes import endf_recipe_dictionary
from .expr_utils.conversion import (
    convert_to_exprtree,
    VariableToken,
)
from .expr_utils.tree_walkers import transform_nodes
from .expr_utils.node_checks import is_variable
from .expr_utils.node_trafos import node2str, replace_node
from endf_parserpy.compiler.expr_utils.equation_utils import solve_equation
from . import cpp_code_primitives as cpp


def is_code_token(node):
    return isinstance(node, Tree) and node.data == "code_token"


def is_expr(node):
    return isinstance(node, Tree) and node.data == "expr"


def is_head_or_cont(node):
    return isinstance(node, Tree) and node.data == "head_or_cont_line"


def is_dir(node):
    return isinstance(node, Tree) and node.data == "dir_line"


def is_tab1(node):
    return isinstance(node, Tree) and node.data == "tab1_line"


def is_tab2(node):
    return isinstance(node, Tree) and node.data == "tab2_line"


def is_list(node):
    return isinstance(node, Tree) and node.data == "list_line"


def is_text(node):
    return isinstance(node, Tree) and node.data == "text_line"


def is_section(node):
    return isinstance(node, Tree) and node.data == "section"


def is_extvar(node):
    return isinstance(node, Tree) and node.data == "extvarname"


def is_textplaceholder(node):
    return isinstance(node, Tree) and node.data == "textplaceholder"


def is_for_loop(node):
    return isinstance(node, Tree) and node.data == "for_loop"


def is_if_clause(node):
    return isinstance(node, Tree) and node.data == "if_clause"


def is_abbreviation(node):
    return isinstance(node, Tree) and node.data == "abbreviation"


def simplify_expr_node(node):
    if not is_expr(node):
        return node
    new_node = convert_to_exprtree(node)
    if not is_expr(new_node):
        new_node = Tree("expr", [new_node])
    return new_node


def logical_expr2cppstr(node, vardict):
    if isinstance(node, VariableToken):
        return cpp.get_cpp_extvarname(node, vardict)
    elif isinstance(node, Token):
        if node == "and":
            return "&&"
        elif node == "or":
            return "||"
        else:
            return str(node)
    elif isinstance(node, Tree):
        return (
            "(" + "".join(logical_expr2cppstr(c, vardict) for c in node.children) + ")"
        )
    raise NotImplementedError("should not happen")


def expr2str_shiftidx(node, vardict, rawvars=False):
    if not isinstance(node, VariableToken):
        return node2str(node)
    if rawvars in (True, False):
        use_cpp_name = not rawvars
    else:
        use_cpp_name = node not in rawvars
    if use_cpp_name:
        varname = cpp.get_cpp_extvarname(node, vardict)
    else:
        varname = str(node)
    return varname


def expand_abbreviation(node, vardict):
    if not is_variable(node):
        return node
    if "__abbrevs" not in vardict:
        return node
    abbrevs = vardict["__abbrevs"]
    if node not in abbrevs:
        return node
    return abbrevs[node].children[0]


def get_variables_in_expr(node):
    if is_variable(node):
        return set((node,))
    varset = set()
    if isinstance(node, Tree):
        for child in node.children:
            curset = get_variables_in_expr(child)
            varset.update(curset)
    return varset


def register_abbreviation(node, vardict):
    vartok = VariableToken(get_child(node, "VARNAME"))
    expr = get_child(node, "expr")
    abbrevs = vardict.setdefault("__abbrevs", {})
    abbrevs[vartok] = expr


def unregister_abbreviations(vardict):
    if "__abbrevs" in vardict:
        del vardict["__abbrevs"]


def did_encounter_var(vartok, vardict):
    while vartok not in vardict and "__up" in vardict:
        vardict = vardict["__up"]
    return vartok in vardict


def count_not_encountered_vars(node, vardict):
    varset = get_variables_in_expr(node)
    return sum(not did_encounter_var(v, vardict) for v in varset)


def register_var(vartok, dtype, vardict):
    vardict[vartok] = dtype


def unregister_var(vartok, vardict):
    if vartok.startswith("__"):
        raise TypeError("not a valid variable")
    del vardict[vartok]


def generate_vardefs(vardict, save_state=False):
    code = "\n// variable declarations\n"
    for vartok, dtype in vardict.items():
        if vartok.startswith("__"):
            continue
        code += cpp.define_var(vartok, dtype, save_state=save_state)
    return code


def generate_mark_vars_as_unread(vardict, prefix=""):
    code = "// accept new variable state\n"
    for vartok in tuple(vardict):
        if vartok.startswith("__"):
            continue
        code += cpp.mark_var_as_unread(vartok, prefix)
        unregister_var(vartok, vardict)
    return code


def get_varassign_from_expr(vartok, node, vardict):
    if is_expr(node):
        node = node.children[0]
    elif not isinstance(node, VariableToken):
        raise TypeError("expect `expr` node or VariableToken")
    lhs = node
    rhs = Token("VARIABLE", "cpp_val")
    vartok, expr = solve_equation(lhs, rhs, vartok)
    return vartok, expr


def generate_cpp_parsefun(name, endf_recipe, parser=None):
    if parser is None:
        parser = Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)
    parsetree = parser.parse(endf_recipe)
    parsetree = transform_nodes(parsetree, simplify_expr_node)
    vardict = dict()
    code = generate_code_from_parsetree(parsetree, vardict)
    vardefs = generate_vardefs(vardict)
    fun_header = cpp.parsefun_header(name)
    fun_footer = cpp.parsefun_footer()
    fun_body = cpp.align_code(vardefs + code, 4)
    code = fun_header + fun_body + fun_footer
    return code


def find_parent_dict(vartok, vardict):
    d = vardict
    while vartok not in d and "__up" in d:
        d = d["__up"]
    if vartok in d:
        return d
    return None


def init_lookahead_counter(steps, vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    if pardic is not None:
        TypeError("already in lookahead")
    vardict["__lookahead"] = steps


def remove_lookahead_counter(vardict):
    if "__lookahead" not in vardict:
        raise TypeError("call at end of lookahead")
    if vardict["__lookahead"] != 0:
        raise IndexError("implementation error of lookahead")
    del vardict["__lookahead"]


def decrease_lookahead_counter(vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    if pardic is not None:
        pardic["__lookahead"] -= 1


def in_lookahead(vardict):
    return find_parent_dict("__lookahead", vardict) is not None


def should_proceed(vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    return pardic is None or pardic["__lookahead"] > 0


def generate_code_from_parsetree(node, vardict):
    if not should_proceed(vardict):
        return ""

    if is_head_or_cont(node):
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
    code = f"\n// open section {sectok}"
    code += cpp.open_section(sectok, vardict)
    code += cpp.align_code(vardef_code, 4)
    code += cpp.align_code(body_code, 4)
    code += cpp.close_section()
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
        vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
    )
    return code


def generate_code_for_if_clause(node, vardict):
    add_vardict = {}
    if_statement = get_child(node, "if_statement")
    elif_statements = [c for c in node.children if get_name(c) == "elif_statement"]
    else_statement = get_child(node, "else_statement", nofail=True)
    code = cpp.align_code(
        """
    // evaluate if-elif-else clause
    {
        bool cpp_found_match = false;
    """,
        -4,
    )
    new_vardict = vardict.copy()
    if_statement_code = generate_code_for_if_statement(if_statement, new_vardict)
    add_vardict.update(new_vardict)
    code += cpp.align_code(if_statement_code, 4)
    for elif_statement in elif_statements:
        new_vardict = vardict.copy()
        code += cpp.align_code(
            cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_for_if_statement(elif_statement, new_vardict),
            ),
            4,
        )
        add_vardict.update(new_vardict)
        code += cpp.align_code(if_statement_code, 8)
    if else_statement is not None:
        else_code = get_child(else_statement, "if_body")
        new_vardict = vardict.copy()
        code += cpp.align_code(
            cpp.pureif(
                condition="! cpp_found_match",
                code=generate_code_from_parsetree(else_code, new_vardict),
            ),
            4,
        )
        add_vardict.update(new_vardict)

    code += "}\n"
    if "__up" in add_vardict:
        del add_vardict["__up"]
    unregister_abbreviations(add_vardict)
    vardict.update(add_vardict)
    return code


def generate_code_for_if_statement(node, vardict):
    if_head = get_child(node, "if_head")
    if_body = get_child(node, "if_body")
    lookahead_option = get_child(node, "lookahead_option", nofail=True)
    if lookahead_option is not None:
        la_expr = get_child(lookahead_option, "expr")
        la_expr_str = transform_nodes(la_expr.children[0], node2str)
        la_steps = int(la_expr_str)
        init_lookahead_counter(la_steps, vardict)

    code = ""
    if in_lookahead(vardict):
        code += cpp.align_code(
            """
        // if statement evaluation with lookahead
        {
            int cpp_old_linenum = cpp_linenum;
        """,
            -8,
        )
        la_body_code = generate_code_from_parsetree(if_body, vardict)
        logical_expr_str = logical_expr2cppstr(if_head, vardict)
        vardef_code = generate_vardefs(vardict, save_state=True)
        code += cpp.align_code(
            cpp.block(
                cpp.concat(
                    [
                        vardef_code,
                        la_body_code,
                        cpp.pureif(
                            condition=logical_expr_str,
                            code=cpp.concat(
                                [
                                    "cpp_found_match = true;",
                                    generate_mark_vars_as_unread(vardict),
                                ]
                            ),
                        ),
                        "cpp_linenum = cpp_old_linenum;",
                    ]
                )
            ),
            4,
        )
        remove_lookahead_counter(vardict)
        code += cpp.align_code(
            cpp.pureif(
                condition="cpp_found_match",
                code=generate_code_from_parsetree(if_body, vardict),
            ),
            4,
        )
        code += "}\n"
    else:
        logical_expr_str = logical_expr2cppstr(if_head, vardict)
        code += cpp.pureif(
            condition=logical_expr_str,
            code=cpp.concat(
                [
                    "// if statement evaluation",
                    "cpp_found_match = true;",
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
        code += cpp.assign_exprstr_to_var(vartok, valcode, vardict)
    else:
        if dtype == float:
            cpp_newval_tok = Token("VARNAME", "cpp_float_val")
        elif dtype == int:
            cpp_newval_tok = Token("VARNAME", "cpp_int_val")
        else:
            raise NotImplementedError(f"unknown node type {dtype}")
        cpp_newval_tok = VariableToken(cpp_newval_tok)
        expr = transform_nodes(expr, replace_node, cpp_val_tok, cpp_newval_tok)
        code += cpp.assign_exprstr_to_var(
            cpp_newval_tok, valcode, vardict, use_cpp_name=False, mark_as_read=False
        )
        exprstr = transform_nodes(
            expr, expr2str_shiftidx, vardict, rawvars=(cpp_newval_tok,)
        )
        code += cpp.assign_exprstr_to_var(vartok, exprstr, vardict)

    if not in_lookahead(vardict):
        code += cpp.store_var_in_endf_dict(vartok, vardict)
    register_var(vartok, dtype, vardict)
    return code


def generate_code_for_varassign(node, vardict, valcode, dtype, throw_cpp=False):
    code = ""
    node = transform_nodes(node, expand_abbreviation, vardict)
    variables = get_variables_in_expr(node)
    if count_not_encountered_vars(node, vardict) > 1:
        raise IndexError("more than one unencountered variables")
    if len(variables) == 0:
        # NOTE: consistency checking could be done here
        return cpp.line(valcode)

    exprstr = transform_nodes(node, node2str)
    code = cpp.conditional_branches(
        conditions=[cpp.did_not_read_var(v) for v in variables],
        codes=[
            cpp.concat(
                [
                    cpp.pureif(
                        condition=cpp.any_unread_vars(variables.difference((v,))),
                        code=cpp.throw_runtime_error(
                            "some of the required variables "
                            + f"""{", ".join(variables.difference((v,)))} """
                            + f"to solve the equation {exprstr}=val "
                            + f"for variable {v} are missing"
                        ),
                    ),
                    cpp.pureif(
                        condition=cpp.logical_not(cpp.did_var_mem_allocation(v)),
                        code=cpp.concat(
                            [
                                cpp.comment(
                                    "do memory allocation for variable if not yet done"
                                ),
                                # cpp.allocate_var_mem(v, vardict)  not working right now
                            ]
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
        valcode = cpp.get_numeric_field(idx, dtype)
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
    code = cpp.read_line()
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
        valcode = cpp.get_text_field(vartok, ofs, length, vardict)
        code += generate_code_for_varassign(vartok, vardict, valcode, dtype)
        if not in_lookahead(vardict):
            code += cpp.store_var_in_endf_dict(vartok, vardict)
        ofs += length
    return code


def generate_code_for_cont(node, vardict):
    code = cpp.read_line()
    record_fields = get_child(node, "record_fields")
    code += "\n// read CONT record\n"
    code += generate_code_from_record_fields(record_fields, vardict)
    return code


def generate_code_for_dir(node, vardict):
    code = cpp.read_line()
    record_fields = get_child(node, "dir_fields")
    code += "\n// read TEXT record\n"
    code += generate_code_from_record_fields(record_fields, vardict, skip=(0, 1), ofs=2)
    return code


def generate_code_for_tab1(node, vardict):
    code = "\n// read TAB1 record\n"
    code += cpp.read_line()
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
            code += cpp.read_tab_body(xvar, yvar)
        else:
            code += cpp.open_section(sectok, vardict)
            body_code = cpp.read_tab_body(xvar, yvar)
            code += cpp.align_code(body_code, 4)
            code += cpp.close_section()
    return code


def generate_code_for_tab2(node, vardict):
    code = "\n// read TAB2 record\n"
    code += cpp.read_line()
    tab2_fields = get_child(node, "tab2_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab2_fields, "record_fields")

    code += generate_code_from_record_fields(record_fields, vardict, skip=(4,))

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    if not in_lookahead(vardict):
        if sectok is None:
            code += cpp.read_tab_body(None, None)
        else:
            code += cpp.open_section(sectok, vardict)
            body_code = cpp.read_tab_body(None, None)
            code += cpp.align_code(body_code, 4)
            code += cpp.close_section()
    return code


def generate_code_for_list(node, vardict):
    code = cpp.read_line()
    record_fields = get_child(node, "record_fields")
    code += "\n// read LIST record\n"
    code += generate_code_from_record_fields(record_fields, vardict)
    if not should_proceed(vardict):
        return code
    list_body_node = get_child(node, "list_body")
    code += cpp.align_code(
        """
    {
        int cpp_npl = cpp_read_int_field(*cpp_lineptr, 4);
        cpp_floatvec = cpp_read_float_vec(cpp_lines, cpp_npl, cpp_linenum);
        int cpp_j = 0;
    """,
        -4,
    )
    list_body_code = generate_code_for_list_body(list_body_node, vardict)
    code += cpp.align_code(list_body_code, 4)
    code += cpp.align_code(
        """
    }
    """,
        -4,
    )
    decrease_lookahead_counter(vardict)
    return code


def generate_code_for_list_body(node, vardict):
    code = "\n// read LIST body\n"
    for child in node.children:
        child_name = get_name(child)
        if child_name == "expr":
            code += generate_code_for_varassign(
                child, vardict, "cpp_floatvec[cpp_j++]", float
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
        vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
    )
    return code


def _generate_code_for_loop(
    vardict, parsefun, for_body, loopvar_node, start_expr_node, stop_expr_node
):
    start_expr_node = transform_nodes(start_expr_node, expand_abbreviation, vardict)
    stop_expr_node = transform_nodes(stop_expr_node, expand_abbreviation, vardict)
    start_expr_str = transform_nodes(start_expr_node, expr2str_shiftidx, vardict)
    stop_expr_str = transform_nodes(stop_expr_node, expr2str_shiftidx, vardict)
    loopvar = VariableToken(loopvar_node)
    cpp_loopvar = cpp.get_cpp_varname(loopvar)
    if loopvar in vardict:
        raise TypeError(f"variable {loopvar} already declared")
    dtype = (start_expr_str, stop_expr_str)
    register_var(loopvar, dtype, vardict)

    code = cpp.align_code(
        rf"""
    for (int {cpp_loopvar} = {start_expr_str};
         {cpp_loopvar} <= {stop_expr_str}; {cpp_loopvar}++) {{
    """,
        -4,
    )
    body_code = parsefun(for_body, vardict)
    code += cpp.align_code(body_code, 4)
    code += "}\n"
    unregister_var(loopvar, vardict)
    return code


def generate_cpp_module_code():
    module_header = cpp.module_header()
    parsefuns_code = ""
    parsefuns_code += generate_cpp_parsefun(
        "parse_mf1mt451", endf_recipe_dictionary[1][451]
    )
    parsefuns_code += generate_cpp_parsefun(
        "parse_mf2mt151", endf_recipe_dictionary[2][151]
    )
    parsefuns_code += generate_cpp_parsefun("parse_mf3", endf_recipe_dictionary[3])
    parsefuns_code += generate_cpp_parsefun("parse_mf4", endf_recipe_dictionary[4])
    parsefuns_code += generate_cpp_parsefun("parse_mf5", endf_recipe_dictionary[5])
    parsefuns_code += generate_cpp_parsefun("parse_mf6", endf_recipe_dictionary[6])
    parsefuns_code += generate_cpp_parsefun("parse_mf10", endf_recipe_dictionary[10])
    parsefuns_code += generate_cpp_parsefun("parse_mf12", endf_recipe_dictionary[12])
    parsefuns_code += generate_cpp_parsefun("parse_mf14", endf_recipe_dictionary[14])
    parsefuns_code += generate_cpp_parsefun("parse_mf15", endf_recipe_dictionary[15])
    parsefuns_code += generate_cpp_parsefun("parse_mf33", endf_recipe_dictionary[33])
    pybind_glue = cpp.register_cpp_parsefuns(
        (
            "parse_mf1mt451",
            "parse_mf2mt151",
            "parse_mf3",
            "parse_mf4",
            "parse_mf5",
            "parse_mf6",
            "parse_mf10",
            "parse_mf12",
            "parse_mf14",
            "parse_mf15",
            "parse_mf33",
        )
    )
    code = module_header + parsefuns_code + pybind_glue
    return code


def generate_cmake_content():
    code = cpp.align_code(
        """
    cmake_minimum_required(VERSION 3.12)
    project(cpp_parsefuns)

    find_package(pybind11 REQUIRED)

    # Create the C++ executable
    pybind11_add_module(cpp_parsefuns SHARED cpp_parsefuns.cpp)

    # Link against Python libraries
    # target_link_libraries(example PRIVATE Python::Python)
    set_property(TARGET cpp_parsefuns PROPERTY CXX_STANDARD 11)
    """,
        -4,
    )
    return code
