############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/05/25
# Last modified:   2025/05/22
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from copy import deepcopy
from endf_parserpy.utils.tree_utils import (
    reconstruct_tree_str,
)
from .endf_mapping_utils import (
    get_child,
    eval_expr_without_unknown_var,
)
from .logging_utils import write_info


def should_proceed(datadic, loop_vars, action_type):
    if "__lookahead" in loop_vars:
        if loop_vars["__lookahead"] == 0:
            return False
        elif action_type == "endf_action":
            loop_vars["__lookahead"] -= 1
    return True


def perform_lookahead(
    tree,
    tree_handler,
    datadic,
    loop_vars,
    parse_opts,
    set_parser_state,
    get_parser_state,
    logger=None,
):
    if_head = get_child(tree, "if_head")
    if_body = get_child(tree, "if_body")
    orig_parser_state = get_parser_state()
    write_info(logger, "Start lookahead for if head " + reconstruct_tree_str(if_head))
    lookahead_option = get_child(tree, "lookahead_option", nofail=True)
    lookahead_expr = get_child(lookahead_option, "expr")
    lookahead = eval_expr_without_unknown_var(
        lookahead_expr, datadic, loop_vars, parse_opts
    )
    if int(lookahead) != lookahead:
        raise ValueError(
            "lookahead argument must evaluate to an integer" + f"(got {lookahead})"
        )
    lookahead = int(lookahead)

    if "__lookahead" in loop_vars:
        raise ValueError(
            "Nested if statements with several " + "lookahead options are not allowed"
        )

    # we want to save the state of the parser
    # before the lookahead to rewind it afterwards
    new_parser_state = deepcopy(orig_parser_state)
    # less strict parsing in lookahead.
    # problems will be captured later on (if requested by user)
    # when if body will be selected and executed
    new_parse_opts = new_parser_state["parse_opts"]
    new_parse_opts["ignore_all_mismatches"] = True
    set_parser_state(new_parser_state)
    datadic = new_parser_state["datadic"]
    loop_vars = new_parser_state["loop_vars"]
    loop_vars["__lookahead"] = lookahead

    try:
        tree_handler(if_body)
    except UnexpectedControlRecordError:
        pass

    del loop_vars["__lookahead"]
    return datadic, loop_vars, orig_parser_state


def undo_lookahead_changes(datadic, loop_vars, orig_parser_state, set_parser_state):
    if orig_parser_state is not None:
        set_parser_state(orig_parser_state)
        datadic = orig_parser_state["datadic"]
        loop_vars = orig_parser_state["loop_vars"]
    return datadic, loop_vars
