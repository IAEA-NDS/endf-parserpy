############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark import Lark
from lark.tree import Tree
from lark.lexer import Token
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.utils.tree_utils import get_child, get_name
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from .expr_utils.node_trafos import (
    node2str,
    replace_node,
)
from .expr_utils.tree_trafos import (
    reconstruct_endf_line_template,
    contains_variables,
    contains_desired_number,
    contains_potentially_inconsistent_variable,
)
from .expr_utils.equation_utils import (
    get_variables_in_expr,
    get_varassign_from_expr,
)
from . import cpp_primitives as cpp
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
    get_var_types,
    find_parent_dict,
)
from . import cpp_boilerplate
from . import cpp_boilerplate_reading
from . import endf2cpp_aux as aux
from .cpp_types import cpp_varops_query
from .cpp_types.cpp_varops_query import (
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
    is_repeat_loop,
    is_if_clause,
    is_abbreviation,
    is_stop,
)
from .node_aux import (
    simplify_expr_node,
    node_and_kids_to_ParseNode,
)
from .expr_utils.exceptions import (
    ModuloEquationError,
    MultipleVariableOccurrenceError,
    SeveralUnknownVariablesError,
)
from .mode_management import (
    get_numeric_field_getter,
    get_text_field_getter,
    get_tab1_body_getter,
    get_tab2_body_getter,
    get_custom_int_field_getter,
    get_counter_field_getter,
    get_send_line_func,
    get_prepare_line_func,
    get_finalize_line_func,
    get_prepare_line_tape_func,
    get_finalize_line_tape_func,
    get_prepare_section_func,
    get_finalize_section_func,
    get_lookahead_tellg_statement,
    get_lookahead_seekg_statement,
    get_generate_expr_validation_func,
)
from hashlib import md5


def generate_cpp_parse_or_write_fun(
    name,
    endf_recipe,
    mat=None,
    mf=None,
    mt=None,
    parser=None,
    vardict=None,
    fun_header=None,
    fun_footer=None,
    fun_setup=None,
):
    if vardict is None:
        raise TypeError("dictionary `vardict` must be provided")
    if parser is None:
        parser = Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)
    if fun_header is None:
        raise TypeError("must provide `fun_header` argument")
    if fun_footer is None:
        raise TypeError("must provide `fun_footer` argument")
    fun_setup = "" if fun_setup is None else fun_setup

    parsetree = parser.parse(endf_recipe)
    parsetree = transform_nodes(parsetree, simplify_expr_node)
    parsetree = transform_nodes_inplace(parsetree, node_and_kids_to_ParseNode)

    code = generate_code_from_parsetree(parsetree, vardict)

    # must be after traversing the tree because assign_exprstr_to_var
    # populates vardict and type info therein
    vardefs = generate_vardefs(vardict)
    fun_body = get_prepare_section_func(vardict)(None, vardict)
    fun_body += vardefs + fun_setup
    fun_body += get_prepare_line_tape_func(vardict)()
    fun_body += code
    fun_body += get_finalize_line_tape_func(vardict)()
    fun_body += get_finalize_section_func(vardict)(None, vardict)
    fun_body = cpp.indent_code(fun_body, cpp.INDENT)

    code = fun_header + fun_body + fun_footer
    md5_hash_recipe = md5(endf_recipe.encode()).hexdigest()
    md5_header = "\n\n"
    md5_header += "// MD5 hash of ENDF recipe underlying the following function: "
    md5_header += md5_hash_recipe
    md5_header += "\n"
    md5_hash_func = md5(code.encode()).hexdigest()
    md5_header += "// MD5 hash of the following function definition: "
    md5_header += md5_hash_func
    md5_header += "\n"
    return md5_header + code


def _generate_code_for_varassign(
    vartok, node, vardict, valcode, dtype, throw_cpp=False
):
    try:
        vartok, expr = get_varassign_from_expr(vartok, node, vardict)
    except ModuloEquationError as exc:
        if not throw_cpp:
            raise exc
        exprstr = transform_nodes(node, node2str)
        return cpp.throw_runtime_error(
            f"The equation {exprstr}==value cannot be solved "
            + f"for {vartok} because the modulo operator is not "
            + "supported."
        )
    except MultipleVariableOccurrenceError as exc:
        if not throw_cpp:
            raise exc
        special_type = "Scalar" if len(vartok.indices) == 0 else "NestedVector"
        register_var(vartok, dtype, special_type, vardict)
        exprstr = transform_nodes(node, node2str)
        return cpp.throw_runtime_error(
            f"The equation {exprstr}==value cannot be solved "
            + f"for {vartok} because this variable could not "
            + "be isolated."
        )

    cpp_val_tok = Token("VARIABLE", "cpp_val")
    code = ""
    if expr == cpp_val_tok:
        code += cpp_varops_assign.assign_exprstr_to_var(
            vartok, valcode, dtype, vardict, node=node
        )
    else:
        if dtype == float:
            cpp_newval_tok = Token("VARNAME", "cpp_float_val")
        elif dtype == int:
            cpp_newval_tok = Token("VARNAME", "cpp_int_val")
        elif dtype == "intvec":
            cpp_newval_tok = Token("VARNAME", "cpp_intvec")
        elif dtype == "floatvec":
            cpp_newval_tok = Token("VARNAME", "cpp_floatvec")
        else:
            raise NotImplementedError(f"unknown node type {dtype}")
        cpp_newval_tok = VariableToken(cpp_newval_tok, cpp_namespace=True)
        expr = transform_nodes(expr, replace_node, cpp_val_tok, cpp_newval_tok)
        code += cpp_varops_assign.assign_exprstr_to_var(
            cpp_newval_tok,
            valcode,
            dtype,
            vardict,
            node=node,
        )
        exprstr = transform_nodes(
            expr, expr2str_shiftidx, vardict, rawvars=(cpp_newval_tok,)
        )
        code += cpp_varops_assign.assign_exprstr_to_var(
            vartok, exprstr, dtype, vardict, node=node
        )
    return code


def generate_code_for_varassign(node, vardict, valcode, dtype, throw_cpp=False):
    code = ""
    node = transform_nodes_inplace(node, expand_abbreviation, vardict)
    exprstr = transform_nodes(node, node2str)
    variables = get_variables_in_expr(node)

    if len(variables) == 0:
        code += get_generate_expr_validation_func(vardict)(valcode, node, vardict)
        return code

    if aux.count_not_encountered_vars(node, vardict) > 1:
        raise SeveralUnknownVariablesError(
            f"more than one unencountered variables in {exprstr}"
        )

    # only try to solve for variables for which all remaining variables
    # have appeared before in recipe logic
    # NOTE: sorted() is introduced to make the program output
    #       deterministic/reproducible because iteration over
    #       sets is not stable over program runs.
    for v in sorted(variables):
        other_vars = sorted(variables.difference((v,)))
        some_other_unavail = any(
            find_parent_dict(w, vardict) is None for w in other_vars
        )
        if some_other_unavail:
            continue

        if cpp_varops_query.need_read_check(v, vardict, v.indices):
            # variable may read beore so we need to check
            # that at cpp runtime
            did_not_read_cond = aux.did_not_read_var(v, vardict, v.indices)
            assigncode = _generate_code_for_varassign(
                v, node, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
            validation_code = get_generate_expr_validation_func(vardict)(
                valcode, node, vardict
            )
            code += cpp.ifelse(
                condition=did_not_read_cond, code=assigncode, other_code=validation_code
            )
        else:
            # no possibility that variable has been read in beore
            # hence no checks necessary
            code += _generate_code_for_varassign(
                v, node, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
    return code


def generate_vardefs(vardict, save_state=False):
    code = cpp.comment("variable declarations")
    for vartok in tuple(vardict.keys()):
        dtype = vardict[vartok]
        if vartok.startswith("__"):
            continue
        code += cpp_varops_assign.define_var(vartok, vardict, save_state=save_state)
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
    elif is_repeat_loop(node):
        return generate_code_for_repeat_loop(node, vardict)
    elif is_if_clause(node):
        return generate_code_for_if_clause(node, vardict)
    elif is_section(node):
        return generate_code_for_section(node, vardict)
    elif is_stop(node):
        return generate_code_for_stop(node, vardict)

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
    inner_code = get_prepare_section_func(vardict)(sectok, vardict)
    inner_code += vardef_code
    inner_code += body_code
    inner_code += get_finalize_section_func(vardict)(sectok, vardict)
    code += cpp.block(inner_code)
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
                cpp.indent_code(get_lookahead_tellg_statement(vardict)),
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
                        cpp.trycatch(
                            la_body_code,
                            "const std::out_of_range& e",
                            cpp.comment("// accept failure in lookahead"),
                        ),
                        cpp.pureif(
                            condition=logical_expr_str,
                            code=cpp.statement("cpp_found_match = true"),
                        ),
                        get_lookahead_seekg_statement(vardict),
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
        valcode, addcode = get_numeric_field_getter(vardict)(child, idx, dtype, vardict)
        try:
            new_assigncode = generate_code_for_varassign(
                child, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
            code += addcode
            code += new_assigncode
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
    code += get_prepare_line_func(vardict)(vardict)
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
        valcode, addcode = get_text_field_getter(vardict)(v, ofs, length, vardict)
        code += addcode
        code += generate_code_for_varassign(vartok, vardict, valcode, dtype)
        ofs += length
    code += get_finalize_line_func(vardict)(vardict)
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
    code += get_prepare_line_func(vardict)(vardict)
    code += cpp.statement(f"int cpp_ndigit = {ndigit_exprstr}")
    code += cpp.pureif(
        cpp.logical_or(["cpp_ndigit < 2", "cpp_ndigit > 6"]),
        cpp.throw_runtime_error("invalid NDIGIT (must be between 2 and 6)"),
    )
    val_ii, addcode = get_custom_int_field_getter(vardict)(ii_expr, 0, 5, vardict)
    code += addcode
    val_jj, addcode = get_custom_int_field_getter(vardict)(jj_expr, 5, 5, vardict)
    code += addcode

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
    code += cpp.statement("int elpos = 0")
    code += cpp.line(
        "for (int cpp_i = cpp_start; cpp_i < cpp_end; cpp_i += cpp_step) {"
    )
    valcode, addcode = get_custom_int_field_getter(vardict)(
        kij_expr, "cpp_i", "cpp_step", vardict, idx="elpos"
    )
    code += addcode
    code += cpp.statement(f"cpp_intvec.push_back({valcode})", cpp.INDENT)
    code += cpp.statement("elpos++", cpp.INDENT)
    code += cpp.close_block()
    code += generate_code_for_varassign(kij_expr, vardict, "cpp_intvec", "intvec")
    code += get_finalize_line_func(vardict)(vardict)
    return cpp.open_block() + cpp.indent_code(code, cpp.INDENT) + cpp.close_block()


def generate_code_for_send(node, vardict):
    code = get_send_line_func(vardict)(vardict)
    code += get_finalize_line_func(vardict)(vardict)
    return code


def generate_code_for_cont(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += get_prepare_line_func(vardict)(vardict)
    code += cpp.comment("read CONT record")
    record_fields = get_child(node, "record_fields")
    code += generate_code_from_record_fields(record_fields, vardict)
    code += get_finalize_line_func(vardict)(vardict)
    return code


def generate_code_for_dir(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = aux.define_current_template(template)
    code += cpp.comment("read TEXT record")
    code += get_prepare_line_func(vardict)(vardict)
    record_fields = get_child(node, "dir_fields")
    code += generate_code_from_record_fields(record_fields, vardict, skip=(0, 1), ofs=2)
    code += get_finalize_line_func(vardict)(vardict)
    return code


def generate_code_for_tab1(node, vardict):
    code = ""
    template = reconstruct_endf_line_template(node)
    code += aux.define_current_template(template)
    tab1_fields = get_child(node, "tab1_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab1_fields, "record_fields")
    tab1_def = get_child(tab1_fields, "tab1_def")

    code += cpp.comment("read TAB1 record")
    code += get_prepare_line_func(vardict)(vardict)
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
    INTvar = VariableToken(Token("VARNAME", "INT"))
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    nr_vartok = VariableToken(Token("VARNAME", "cpp_nr_val"), cpp_namespace=True)
    np_vartok = VariableToken(Token("VARNAME", "cpp_np_val"), cpp_namespace=True)

    inner_code = ""
    if sectok is not None:
        vardict = {"__up": vardict}
        inner_code += get_prepare_section_func(vardict)(sectok, vardict)

    nr_val, addcode = get_counter_field_getter(vardict)(INTvar, 4, vardict)
    inner_code += addcode
    inner_code += cpp.statement(f"cpp_nr_val = {nr_val}")
    np_val, addcode = get_counter_field_getter(vardict)(xvar, 5, vardict)
    inner_code += addcode
    inner_code += cpp.statement(f"cpp_np_val = {np_val}")

    # we are done with the first control record line of the tab1 record
    inner_code += get_finalize_line_func(vardict)(vardict)

    # NOTE: the prepare line call is/should be handled by the code returned by get_tab1_body_getter
    tabdata, addcode = get_tab1_body_getter(vardict)(
        xvar, yvar, nr_vartok, np_vartok, vardict
    )
    inner_code += addcode

    assigncode = cpp.statement(f"Tab1Body tab_body = {tabdata}")
    assigncode += generate_code_for_varassign(xvar, vardict, "tab_body.X", "floatvec")
    assigncode += generate_code_for_varassign(yvar, vardict, "tab_body.Y", "floatvec")
    assigncode += generate_code_for_varassign(INTvar, vardict, "tab_body.INT", "intvec")
    assigncode += generate_code_for_varassign(NBTvar, vardict, "tab_body.NBT", "intvec")
    assigncode = cpp.block(assigncode)

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        inner_code += vardefs + assigncode
        inner_code += get_finalize_line_func(vardict)(vardict)
        inner_code += get_finalize_section_func(vardict)(sectok, vardict)
        code += cpp.block(inner_code)
    else:
        inner_code += assigncode
        inner_code += get_finalize_line_func(vardict)(vardict)
        code += inner_code
    return code


def generate_code_for_tab2(node, vardict):
    code = ""
    template = reconstruct_endf_line_template(node)
    code += aux.define_current_template(template)
    tab2_fields = get_child(node, "tab2_fields")
    table_name = get_child(node, "table_name", nofail=True)
    record_fields = get_child(tab2_fields, "record_fields")

    code += cpp.comment("read TAB2 record")
    code += get_prepare_line_func(vardict)(vardict)
    code += generate_code_from_record_fields(record_fields, vardict, skip=(4,))

    if not should_proceed(vardict):
        return code
    # reading the tab body counts as one lookahead step
    decrease_lookahead_counter(vardict)

    sectok = None
    if table_name is not None:
        sectok = VariableToken(get_child(table_name, "extvarname"))

    INTvar = VariableToken(Token("VARNAME", "INT"))
    NBTvar = VariableToken(Token("VARNAME", "NBT"))
    nr_vartok = VariableToken(Token("VARNAME", "cpp_nr_val"), cpp_namespace=True)

    inner_code = ""
    if sectok is not None:
        vardict = {"__up": vardict}
        inner_code += get_prepare_section_func(vardict)(sectok, vardict)

    nr_val, addcode = get_counter_field_getter(vardict)(INTvar, 4, vardict)
    inner_code += addcode
    inner_code += cpp.statement(f"cpp_nr_val = {nr_val}")

    # we are done with the first control record line of the tab2 record
    inner_code += get_finalize_line_func(vardict)(vardict)

    # NOTE: the prepare line call is/should be handled by the code returned by get_tab1_body_getter
    tabdata, addcode = get_tab2_body_getter(vardict)(nr_vartok, vardict)
    inner_code += addcode

    assigncode = cpp.statement(f"Tab2Body tab_body = {tabdata}")
    assigncode += generate_code_for_varassign(INTvar, vardict, "tab_body.INT", "intvec")
    assigncode += generate_code_for_varassign(NBTvar, vardict, "tab_body.NBT", "intvec")
    assigncode = cpp.block(assigncode)

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        inner_code += vardefs + assigncode
        inner_code += get_finalize_line_func(vardict)(vardict)
        inner_code += get_finalize_section_func(vardict)(sectok, vardict)
        code += cpp.block(inner_code)
    else:
        inner_code += assigncode
        inner_code += get_finalize_line_func(vardict)(vardict)
        code += inner_code
    return code


def generate_code_for_list(node, vardict):
    template = reconstruct_endf_line_template(node)
    code = ""
    code += aux.define_current_template(template)
    record_fields = get_child(node, "record_fields")

    code += get_prepare_line_func(vardict)(vardict)
    code += cpp.comment("read LIST record")
    code += generate_code_from_record_fields(record_fields, vardict)
    npl_node = get_child(record_fields, "expr", idx=4)
    npl_val, addcode = get_numeric_field_getter(vardict)(npl_node, 4, int, vardict)
    code += addcode
    code += get_finalize_line_func(vardict)(vardict)

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
    icode = lbr.start_list_body_loop(npl_val, vardict)
    list_body_code = generate_code_for_list_body(list_body_node, vardict)
    icode += lbr.indent(list_body_code)
    icode += lbr.finish_list_body_loop(vardict)

    if sectok is not None:
        vardefs = generate_vardefs(vardict)
        inner_code = get_prepare_section_func(vardict)(sectok, vardict)
        inner_code += vardefs + icode
        inner_code += get_finalize_section_func(vardict)(sectok, vardict)
        code += cpp.block(inner_code)
    else:
        code += icode
    return code


def generate_code_for_list_body(node, vardict):
    lbr = aux.ListBodyRecorder
    code = cpp.comment("read LIST body")
    for child in node.children:
        child_name = get_name(child)
        if child_name == "expr":
            current_value, addcode = lbr.get_element(child, vardict)
            code += addcode
            code += generate_code_for_varassign(child, vardict, current_value, float)
            code += lbr.update_counters_and_line(vardict)
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


def generate_code_for_repeat_loop(node, vardict):
    repeat_head = get_child(node, "repeat_head")
    repeat_body = get_child(node, "repeat_body")
    repeat_tail = get_child(node, "repeat_tail")
    until_cond = get_child(repeat_tail, "if_head")

    varassign = get_child(repeat_head, "repeat_varassign")
    loopvar_node = get_child(varassign, "VARNAME")
    start_expr_node = get_child(varassign, "expr")

    start_expr_node = transform_nodes(start_expr_node, expand_abbreviation, vardict)
    start_expr_str = transform_nodes(start_expr_node, expr2str_shiftidx, vardict)
    loopvar = VariableToken(loopvar_node)
    if loopvar in vardict:
        raise TypeError(f"variable {loopvar} already declared")

    register_var(loopvar, "loopvartype", "Scalar", vardict, track_read=False)
    cpp_loopvar = cpp_varops_query.get_cpp_varname(loopvar, vardict)

    code = cpp.indent_code(
        rf"""
    for (int {cpp_loopvar} = {start_expr_str};; {cpp_loopvar}++) {{
    """,
        -4,
    )
    code += cpp.indent_code(init_readflag(loopvar, val=True))
    body_code = generate_code_from_parsetree(repeat_body, vardict)
    # insert conditional break statement
    logical_expr_str = logical_expr2cppstr(until_cond, vardict)
    body_code += cpp.pureif(
        condition=logical_expr_str,
        code=cpp.statement("break"),
    )

    code += cpp.indent_code(body_code)
    code += cpp.close_block()
    unregister_var(loopvar, vardict)
    # add code propagated upward from downstream nodes
    code = node.precode + code
    return code


def generate_code_for_stop(node, vardict):
    stop_msg_outer_node = get_child(node, "escaped_stop_message")
    stop_msg_node = get_child(stop_msg_outer_node, "STOP_MESSAGE")
    stop_message = str(stop_msg_node)
    if '"' in stop_message:
        raise ValueError(
            'String in `stop` message must not contain double-quotes (`"`). '
            f"The invalid message: {stop_message}"
        )
    return cpp.throw_runtime_error(
        f"Encountered STOP instruction in recipe: {stop_message}"
    )
