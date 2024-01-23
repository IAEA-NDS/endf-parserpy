############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

import traceback
from .tree_utils import (get_child, get_child_value, get_name,
        get_child_names, reconstruct_tree_str)
from .endf_mapping_utils import (
    eval_expr_without_unknown_var,
    get_indexvalue, get_indexquants, get_varname
)
from .logging_utils import write_info
from .custom_exceptions import (
    LoopVariableError, AbbreviationNameCollisionError,
    VariableNotFoundError, UnexpectedControlRecordError
)
from copy import deepcopy

def initialize_abbreviations(datadic):
    datadic['__abbrevs'] = set()

def introduce_abbreviation(tree, datadic):
    abbrevs = datadic.setdefault('__abbrevs', set())
    varname = get_child_value(tree, 'VARNAME')
    if varname in datadic:
        raise AbbreviationNameCollisionError(
            f'Abbreviation `{varname}` collides with an equally'
            'named variable or abbreviation defined earlier'
        )
    expr = get_child(tree, 'expr')
    abbrevs.add(varname)
    datadic[varname] = expr

def finalize_abbreviations(datadic):
    assert '__abbrevs' in datadic
    for abbrev in datadic['__abbrevs']:
        del datadic[abbrev]
    del datadic['__abbrevs']

def open_section(extvarname, datadic, loop_vars, create_missing):
    varname = get_varname(extvarname)
    indexquants = get_indexquants(extvarname)
    curdatadic = datadic
    datadic.setdefault(varname, {})
    datadic = datadic[varname]
    idcsstr_list = []
    if indexquants is not None:
        for idxquant in indexquants:
            idx = get_indexvalue(idxquant, loop_vars)
            idcsstr_list.append(str(idx))
            if create_missing:
                datadic.setdefault(idx, {})
            datadic = datadic[idx]
    # provide a pointer so that functions
    # can look for variable names in the outer scope
    datadic['__up'] = curdatadic
    write_info(f'Open section {varname}[' + ','.join(idcsstr_list) + ']')
    return datadic

def close_section(extvarname, datadic):
    varname = get_varname(extvarname)
    write_info(f'Close section {varname}')
    curdatadic = datadic
    datadic = datadic['__up']
    del curdatadic['__up']
    return datadic

def cycle_for_loop(tree, tree_handler, datadic, loop_vars,
                   loop_name='for_loop', head_name='for_head',  body_name='for_body'):
    assert tree.data == loop_name
    for_head = get_child(tree, head_name)
    varname = get_child_value(for_head, 'VARNAME')
    # determine range for loop counter
    start_expr = get_child(for_head, 'for_start')
    stop_expr = get_child(for_head, 'for_stop')
    start = eval_expr_without_unknown_var(start_expr, datadic, loop_vars)
    stop = eval_expr_without_unknown_var(stop_expr, datadic, loop_vars)
    if float(start) != int(start):
        raise LoopVariableError('Loop start index must evaluate to an integer')
    if float(stop) != int(stop):
        raise LoopVariableError('Loop stop index must evaluate to an integer')

    start = int(start)
    stop = int(stop)
    for_body = get_child(tree, body_name)
    if varname in loop_vars:
        raise LoopVariableError(
                f'The loop variable {varname} is already in use for another loop')
    write_info(f'Enter for loop (type {loop_name}) ' + reconstruct_tree_str(for_head) +
               f' (for_start: {start} and for_stop {stop})')
    for i in range(start, stop+1):
        loop_vars[varname] = i
        tree_handler(for_body)
    # if we don't enter the loop, then
    # the loop variable will not be set
    # and consequently we don't have to delete it
    if start <= stop:
        del(loop_vars[varname])
    write_info(f'Leave for loop (type {loop_name}) ' + reconstruct_tree_str(for_head) +
               f' (for_start: {start} and for_stop: {stop})')

def eval_if_condition(if_condition, datadic, loop_vars, missing_as_false=False):
    if len(if_condition.children) != 3:
        raise IndexError('if_condition must have three children')
    write_info('Dealing with the if_condition ' + reconstruct_tree_str(if_condition))
    left_expr = if_condition.children[0]
    cmpop = get_child_value(if_condition, 'IF_RELATION')
    right_expr = if_condition.children[2]
    try:
        left_val = eval_expr_without_unknown_var(left_expr, datadic, loop_vars)
        right_val = eval_expr_without_unknown_var(right_expr, datadic, loop_vars)
    except VariableNotFoundError as exc:
        if missing_as_false:
            return False
        else:
            raise exc
    write_info(f'Left side evaluates to {left_val} and right side to {right_val}')
    if ((cmpop == ">" and left_val > right_val) or
        (cmpop == "<" and left_val < right_val) or
        (cmpop =="<=" and left_val <= right_val) or
        (cmpop ==">=" and left_val >= right_val) or
        (cmpop =="!=" and left_val != right_val) or
        (cmpop =="==" and left_val == right_val)):
        return True
    else:
        return False

def determine_truthvalue(node, datadic, loop_vars, missing_as_false=False):
    name = get_name(node)
    if name == 'if_condition':
        return eval_if_condition(node, datadic, loop_vars, missing_as_false)
    elif name == 'comparison':
        # we strip away brackets because the information they
        # encode has already been considered in the tree generation process,
        # see grammar rule for "comparison" in endf_lark.py
        trimmed_children = [ch for ch in node.children
                                if get_name(ch) not in ('LPAR','RPAR')]
        if len(trimmed_children) != 1:
            raise ValueError('Exactly one child expected from "comparison" node')
        ch = trimmed_children[0]
        if get_name(ch) not in ('if_condition', 'disjunction'):
            raise ValueError('Child node must be either "if_condition" or "disjunction"')
        return determine_truthvalue(ch, datadic, loop_vars, missing_as_false)
    elif name == 'conjunction':
        # the following code is a bit messy because of the order of
        # conjunction and comparison in the "conjunction" rule and
        # that we want to avoid unnecessary evaluations of boolean expressions
        conj = get_child(node, 'conjunction', nofail=True)
        comp = get_child(node, 'comparison')
        if conj is not None:
            conj_truthval = determine_truthvalue(
                conj, datadic, loop_vars, missing_as_false
            )
            if conj_truthval is False:
                return False
        comp_truthval = determine_truthvalue(
            comp, datadic, loop_vars, missing_as_false
        )
        if conj is None:
            return comp_truthval
        else:
            return conj_truthval and comp_truthval
    elif name == 'disjunction':
        disj = get_child(node, 'disjunction', nofail=True)
        conj = get_child(node, 'conjunction')
        if disj is not None:
            disj_truthval = determine_truthvalue(
                disj, datadic, loop_vars, missing_as_false
            )
            if disj_truthval is True:
                return True
        conj_truthval = determine_truthvalue(
            conj, datadic, loop_vars, missing_as_false
        )
        if disj is None:
            return conj_truthval
        else:
            return disj_truthval or conj_truthval
    else:
        raise TypeError(f'Unsupported node type {name} encountered ' +
                         'while parsing boolean expression')


def evaluate_if_clause(
    tree, datadic, loop_vars, tree_handler=None,
    set_parser_state=None, get_parser_state=None, eval_body=True
):
    if_body = None
    first_if_statement = get_child(tree, 'if_statement')
    truthval = evaluate_if_statement(
        first_if_statement, datadic, loop_vars,
        tree_handler, set_parser_state, get_parser_state
    )
    if truthval is True:
        if_body = get_child(first_if_statement, 'if_body')
    else:
        elif_tree_list = [t for t in tree.children if get_name(t) == 'elif_statement']
        for elif_tree in elif_tree_list:
            truthval = evaluate_if_statement(
                elif_tree, datadic, loop_vars,
                tree_handler, set_parser_state, get_parser_state
            )
            if truthval is True:
                if_body = get_child(elif_tree, 'if_body')
                break

    if if_body is None and 'else_statement' in get_child_names(tree):
        else_tree = get_child(tree, 'else_statement')
        if_body = get_child(else_tree, 'if_body')

    if if_body is not None and eval_body:
        tree_handler(if_body)
    return if_body


def evaluate_if_statement(
    tree, datadic, loop_vars, tree_handler=None,
    set_parser_state=None, get_parser_state=None
):
    assert tree.data in ('if_statement', 'elif_statement', 'else_statement')
    if_head = get_child(tree, 'if_head')
    lookahead_option = get_child(tree, 'lookahead_option', nofail=True)
    should_perform_lookahead = (
        tree_handler is not None and lookahead_option and
        get_parser_state()['rwmode'] == 'read'
    )
    if should_perform_lookahead:
        datadic, loop_vars, orig_parser_state = perform_lookahead(
            tree, tree_handler, datadic, loop_vars,
            set_parser_state, get_parser_state
        )
    # evaluate the condition (with variables in datadic potentially
    # affected by the lookahead)
    write_info('Evaluate if head ' + reconstruct_tree_str(if_head))
    disj = get_child(if_head, 'disjunction')
    truthval = determine_truthvalue(
        disj, datadic, loop_vars, missing_as_false=True
    )
    if should_perform_lookahead:
        datadic, loop_vars = undo_lookahead_changes(
            datadic, loop_vars, orig_parser_state, set_parser_state
        )
    return truthval


def should_proceed(datadic, loop_vars, action_type):
    if '__lookahead' in loop_vars:
        if loop_vars['__lookahead'] == 0:
            return False
        elif action_type == 'endf_action':
            loop_vars['__lookahead'] -= 1
    return True


def perform_lookahead(tree, tree_handler, datadic, loop_vars,
                      set_parser_state, get_parser_state):
    if_head = get_child(tree, 'if_head')
    if_body = get_child(tree, 'if_body')
    orig_parser_state = get_parser_state()
    write_info('Start lookahead for if head ' + reconstruct_tree_str(if_head))
    lookahead_option = get_child(tree, 'lookahead_option', nofail=True)
    lookahead_expr = get_child(lookahead_option, 'expr')
    lookahead = eval_expr_without_unknown_var(lookahead_expr, datadic, loop_vars)
    if int(lookahead) != lookahead:
        raise ValueError( 'lookahead argument must evaluate to an integer' +
                         f'(got {lookahead})')
    lookahead = int(lookahead)

    if '__lookahead' in loop_vars:
        raise ValueError('Nested if statements with several ' +
                         'lookahead options are not allowed')

    # we want to save the state of the parser
    # before the lookahead to rewind it afterwards
    new_parser_state = deepcopy(orig_parser_state)
    # less strict parsing in lookahead.
    # problems will be captured later on (if requested by user)
    # when if body will be selected and executed
    new_parse_opts = new_parser_state['parse_opts']
    new_parse_opts['ignore_all_mismatches'] = True
    set_parser_state(new_parser_state)
    datadic = new_parser_state['datadic']
    loop_vars = new_parser_state['loop_vars']
    loop_vars['__lookahead'] = lookahead

    try:
        tree_handler(if_body)
    except UnexpectedControlRecordError:
        pass

    del(loop_vars['__lookahead'])
    return datadic, loop_vars, orig_parser_state


def undo_lookahead_changes(datadic, loop_vars, orig_parser_state,
                           set_parser_state):
    if orig_parser_state is not None:
        set_parser_state(orig_parser_state)
        datadic = orig_parser_state['datadic']
        loop_vars = orig_parser_state['loop_vars']
    return datadic, loop_vars
