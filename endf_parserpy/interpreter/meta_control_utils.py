############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import traceback
from endf_parserpy.utils.tree_utils import (
    get_child,
    get_child_value,
    get_name,
    get_child_names,
    reconstruct_tree_str,
)
from .endf_mapping_utils import (
    eval_expr_without_unknown_var,
    get_indexvalue,
    get_indexquants,
    get_varname,
)
from .lookahead_management import (
    perform_lookahead,
    undo_lookahead_changes,
)
from .logging_utils import write_info
from .custom_exceptions import (
    LoopVariableError,
    AbbreviationNameCollisionError,
    VariableNotFoundError,
    UnavailableIndexError,
    UnexpectedControlRecordError,
    MissingSectionError,
)
from .helpers import (
    shift_indices,
    list_setdefault,
)


def initialize_working_vars(datadic):
    datadic["__abbrevs"] = set()
    datadic["__startidcs"] = dict()


def introduce_abbreviation(tree, datadic):
    abbrevs = datadic.setdefault("__abbrevs", set())
    varname = get_child_value(tree, "VARNAME")
    if varname not in abbrevs and varname in datadic:
        raise AbbreviationNameCollisionError(
            f"Abbreviation `{varname}` collides with "
            "an equally named variable defined earlier"
        )
    expr = get_child(tree, "expr")
    abbrevs.add(varname)
    datadic[varname] = expr


def remove_working_vars(datadic):
    assert "__abbrevs" in datadic
    for abbrev in datadic["__abbrevs"]:
        del datadic[abbrev]
    del datadic["__abbrevs"]
    del datadic["__startidcs"]


def open_section(
    extvarname, datadic, loop_vars, parse_opts, create_missing, path=None, logger=None
):
    in_list_mode = parse_opts["internal_array_type"] == "list"
    varname = get_varname(extvarname)
    if path is not None:
        path += (varname,)
    indexquants = get_indexquants(extvarname)
    curdatadic = datadic
    if create_missing:
        if indexquants is None or not in_list_mode:
            datadic.setdefault(varname, {})
        else:
            datadic.setdefault(varname, [])
    try:
        datadic = datadic[varname]
    except KeyError:
        if indexquants is not None:
            msg = "Array of sections "
            section_type = "array of sections"
        else:
            msg = "Section "
            section_type = "section"
        msg += f"`{varname}` is missing in dictionary"
        raise MissingSectionError(msg, section_name=varname, section_type=section_type)

    idcsstr_list = []
    if indexquants is not None:
        idcs = [
            get_indexvalue(q, datadic, loop_vars, parse_opts, True) for q in indexquants
        ]
        if in_list_mode:
            idcs = shift_indices(varname, idcs, curdatadic)
        for i, idx in enumerate(idcs):
            idcsstr_list.append(str(idx))
            if create_missing:
                if in_list_mode:
                    new_el = [] if i + 1 < len(idcs) else {}
                    list_setdefault(datadic, idx, new_el)
                else:
                    datadic.setdefault(idx, {})
            try:
                datadic = datadic[idx]
            except KeyError:
                ext_secname = f"{varname}[" + ",".join(idcsstr_list) + "]"
                raise MissingSectionError(
                    f"Section `{ext_secname}` is missing in dictionary",
                    section_name=ext_secname,
                    section_type="section",
                )
            if path is not None:
                path += (idx,)
    # provide a pointer so that functions
    # can look for variable names in the outer scope
    datadic["__up"] = curdatadic
    write_info(logger, f"Open section {varname}[" + ",".join(idcsstr_list) + "]")
    if path is None:
        return datadic
    else:
        return datadic, path


def close_section(extvarname, datadic, logger=None):
    varname = get_varname(extvarname)
    write_info(logger, f"Close section {varname}")
    curdatadic = datadic
    datadic = datadic["__up"]
    del curdatadic["__up"]
    return datadic


def cycle_for_loop(
    tree,
    tree_handler,
    datadic,
    loop_vars,
    parse_opts,
    loop_name="for_loop",
    head_name="for_head",
    body_name="for_body",
    logger=None,
):
    assert tree.data == loop_name
    for_head = get_child(tree, head_name)
    varname = get_child_value(for_head, "VARNAME")
    # determine range for loop counter
    start_expr = get_child(for_head, "for_start")
    stop_expr = get_child(for_head, "for_stop")
    start = eval_expr_without_unknown_var(start_expr, datadic, loop_vars, parse_opts)
    stop = eval_expr_without_unknown_var(stop_expr, datadic, loop_vars, parse_opts)
    if float(start) != int(start):
        raise LoopVariableError("Loop start index must evaluate to an integer")
    if float(stop) != int(stop):
        raise LoopVariableError("Loop stop index must evaluate to an integer")

    start = int(start)
    stop = int(stop)
    for_body = get_child(tree, body_name)
    if varname in loop_vars:
        raise LoopVariableError(
            f"The loop variable {varname} is already in use for another loop"
        )
    write_info(
        logger,
        f"Enter for loop (type {loop_name}) "
        + reconstruct_tree_str(for_head)
        + f" (for_start: {start} and for_stop {stop})",
    )
    for i in range(start, stop + 1):
        loop_vars[varname] = i
        tree_handler(for_body)
    # if we don't enter the loop, then
    # the loop variable will not be set
    # and consequently we don't have to delete it
    if start <= stop:
        del loop_vars[varname]
    write_info(
        logger,
        f"Leave for loop (type {loop_name}) "
        + reconstruct_tree_str(for_head)
        + f" (for_start: {start} and for_stop: {stop})",
    )


def cycle_repeat_loop(
    tree,
    tree_handler,
    datadic,
    loop_vars,
    parse_opts,
    logger=None,
):
    assert tree.data == "repeat_loop"
    repeat_head = get_child(tree, "repeat_head")
    varassign = get_child(repeat_head, "repeat_varassign")
    varname = get_child_value(varassign, "VARNAME")
    start_expr = get_child(varassign, "expr")
    start = eval_expr_without_unknown_var(start_expr, datadic, loop_vars, parse_opts)

    if float(start) != int(start):
        raise LoopVariableError("Loop start index must evaluate to an integer")

    start = int(start)
    repeat_body = get_child(tree, "repeat_body")
    if varname in loop_vars:
        raise LoopVariableError(
            f"The loop variable {varname} is already in use for another loop"
        )
    write_info(
        logger,
        f"Enter repeat/until loop "
        + reconstruct_tree_str(repeat_head)
        + f" (start value of {varname}: {start}",
    )

    repeat_tail = get_child(tree, "repeat_tail")
    until_cond = get_child(get_child(repeat_tail, "if_head"), "disjunction")

    loopvar = start
    while True:
        loop_vars[varname] = loopvar
        tree_handler(repeat_body)
        until_cond_truthval = determine_truthvalue(
            until_cond,
            datadic,
            loop_vars,
            parse_opts,
            missing_as_false=False,
            logger=logger,
        )
        if until_cond_truthval:
            break
        loopvar += 1

    del loop_vars[varname]
    write_info(
        logger,
        f"Leave repeat/until loop"
        + reconstruct_tree_str(repeat_head)
        + f" ({varname} start: {start} and stop: {loopvar})",
    )


def eval_if_condition(
    if_condition, datadic, loop_vars, parse_opts, missing_as_false=False, logger=None
):
    if len(if_condition.children) != 3:
        raise IndexError("if_condition must have three children")
    write_info(
        logger, "Dealing with the if_condition " + reconstruct_tree_str(if_condition)
    )
    left_expr = if_condition.children[0]
    cmpop = get_child_value(if_condition, "IF_RELATION")
    right_expr = if_condition.children[2]
    try:
        left_val = eval_expr_without_unknown_var(
            left_expr, datadic, loop_vars, parse_opts
        )
        right_val = eval_expr_without_unknown_var(
            right_expr, datadic, loop_vars, parse_opts
        )
    except (VariableNotFoundError, UnavailableIndexError):
        if missing_as_false:
            return False
        raise
    write_info(
        logger, f"Left side evaluates to {left_val} and right side to {right_val}"
    )
    if (
        (cmpop == ">" and left_val > right_val)
        or (cmpop == "<" and left_val < right_val)
        or (cmpop == "<=" and left_val <= right_val)
        or (cmpop == ">=" and left_val >= right_val)
        or (cmpop == "!=" and left_val != right_val)
        or (cmpop == "==" and left_val == right_val)
    ):
        return True
    else:
        return False


def determine_truthvalue(
    node, datadic, loop_vars, parse_opts, missing_as_false=False, logger=None
):
    name = get_name(node)
    if name == "if_condition":
        return eval_if_condition(
            node, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
        )
    elif name == "comparison":
        # we strip away brackets because the information they
        # encode has already been considered in the tree generation process,
        # see grammar rule for "comparison" in endf_recipes/endf_lark_ebnf.py
        trimmed_children = [
            ch for ch in node.children if get_name(ch) not in ("LPAR", "RPAR")
        ]
        if len(trimmed_children) != 1:
            raise ValueError('Exactly one child expected from "comparison" node')
        ch = trimmed_children[0]
        if get_name(ch) not in ("if_condition", "disjunction"):
            raise ValueError(
                'Child node must be either "if_condition" or "disjunction"'
            )
        return determine_truthvalue(
            ch, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
        )
    elif name == "conjunction":
        # the following code is a bit messy because of the order of
        # conjunction and comparison in the "conjunction" rule and
        # that we want to avoid unnecessary evaluations of boolean expressions
        conj = get_child(node, "conjunction", nofail=True)
        comp = get_child(node, "comparison")
        if conj is not None:
            conj_truthval = determine_truthvalue(
                conj, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
            )
            if conj_truthval is False:
                return False
        comp_truthval = determine_truthvalue(
            comp, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
        )
        if conj is None:
            return comp_truthval
        else:
            return conj_truthval and comp_truthval
    elif name == "disjunction":
        disj = get_child(node, "disjunction", nofail=True)
        conj = get_child(node, "conjunction")
        if disj is not None:
            disj_truthval = determine_truthvalue(
                disj, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
            )
            if disj_truthval is True:
                return True
        conj_truthval = determine_truthvalue(
            conj, datadic, loop_vars, parse_opts, missing_as_false, logger=logger
        )
        if disj is None:
            return conj_truthval
        else:
            return disj_truthval or conj_truthval
    else:
        raise TypeError(
            f"Unsupported node type {name} encountered "
            + "while parsing boolean expression"
        )


def evaluate_if_clause(
    tree,
    datadic,
    loop_vars,
    parse_opts,
    tree_handler=None,
    set_parser_state=None,
    get_parser_state=None,
    eval_body=True,
    logger=None,
):
    if_body = None
    first_if_statement = get_child(tree, "if_statement")
    truthval = evaluate_if_statement(
        first_if_statement,
        datadic,
        loop_vars,
        parse_opts,
        tree_handler,
        set_parser_state,
        get_parser_state,
        logger=logger,
    )
    if truthval is True:
        if_body = get_child(first_if_statement, "if_body")
    else:
        elif_tree_list = [t for t in tree.children if get_name(t) == "elif_statement"]
        for elif_tree in elif_tree_list:
            truthval = evaluate_if_statement(
                elif_tree,
                datadic,
                loop_vars,
                parse_opts,
                tree_handler,
                set_parser_state,
                get_parser_state,
                logger=logger,
            )
            if truthval is True:
                if_body = get_child(elif_tree, "if_body")
                break

    if if_body is None and "else_statement" in get_child_names(tree):
        else_tree = get_child(tree, "else_statement")
        if_body = get_child(else_tree, "if_body")

    if if_body is not None and eval_body:
        tree_handler(if_body)
    return if_body


def evaluate_if_statement(
    tree,
    datadic,
    loop_vars,
    parse_opts,
    tree_handler=None,
    set_parser_state=None,
    get_parser_state=None,
    logger=None,
):
    assert tree.data in ("if_statement", "elif_statement", "else_statement")
    if_head = get_child(tree, "if_head")
    lookahead_option = get_child(tree, "lookahead_option", nofail=True)
    should_perform_lookahead = (
        tree_handler is not None
        and lookahead_option
        and get_parser_state()["rwmode"] == "read"
    )
    if should_perform_lookahead:
        datadic, loop_vars, orig_parser_state = perform_lookahead(
            tree,
            tree_handler,
            datadic,
            loop_vars,
            parse_opts,
            set_parser_state,
            get_parser_state,
            logger=logger,
        )
    # evaluate the condition (with variables in datadic potentially
    # affected by the lookahead)
    write_info(logger, "Evaluate if head " + reconstruct_tree_str(if_head))
    disj = get_child(if_head, "disjunction")
    truthval = determine_truthvalue(
        disj, datadic, loop_vars, parse_opts, missing_as_false=True, logger=logger
    )
    if should_perform_lookahead:
        datadic, loop_vars = undo_lookahead_changes(
            datadic, loop_vars, orig_parser_state, set_parser_state
        )
    return truthval
