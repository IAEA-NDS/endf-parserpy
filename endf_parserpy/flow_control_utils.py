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
from .endf_mapping_utils import get_varname, get_indexvars, eval_expr
from .logging_utils import write_info


def cycle_for_loop(tree, tree_handler, datadic, loop_vars,
                   loop_name='for_loop', head_name='for_head',  body_name='for_body'):
    assert tree.data == loop_name
    for_head = get_child(tree, head_name)
    varname = get_child_value(for_head, 'VARNAME')
    # determine range for loop counter
    start_expr = get_child(for_head, 'for_start')
    stop_expr = get_child(for_head, 'for_stop')
    start = eval_expr(start_expr, datadic, loop_vars)[0]
    stop = eval_expr(stop_expr, datadic, loop_vars)[0]
    if float(start) != int(start):
        raise ValueError('Loop start index must evaluate to an integer')
    if float(stop) != int(stop):
        raise ValueError('Loop stop index must evaluate to an integer')
    start = int(start)
    stop = int(stop)
    for_body = get_child(tree, body_name)
    if varname in loop_vars:
        raise ValueError(f'The loop variable {varname} is already in use for another loop')
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

def eval_if_condition(if_condition, datadic, loop_vars):
    if len(if_condition.children) != 3:
        raise IndexError('if_condition must have three children')
    write_info('Dealing with the if_condition ' + reconstruct_tree_str(if_condition))
    left_expr = if_condition.children[0]
    cmpop = get_child_value(if_condition, 'IF_RELATION')
    right_expr = if_condition.children[2]
    left_val = eval_expr(left_expr, datadic, loop_vars)[0]
    right_val = eval_expr(right_expr, datadic, loop_vars)[0]
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

def determine_truthvalue(node, datadic, loop_vars):
    name = get_name(node)
    if name == 'if_condition':
        return eval_if_condition(node, datadic, loop_vars)
    elif name == 'comparison':
        if len(node.children) != 1:
            raise ValueError('Exactly one child expected from "comparison" node')
        ch = node.children[0]
        if get_name(ch) not in ('if_condition', 'disjunction'):
            raise ValueError('Child node must be either "if_condition" or "disjunction"')
        return determine_truthvalue(ch, datadic, loop_vars)
    elif name == 'conjunction':
        conj = get_child(node, 'conjunction', nofail=True)
        comp = get_child(node, 'comparison')
        comp_truthval = determine_truthvalue(comp, datadic, loop_vars)
        if conj is not None:
            conj_truthval = determine_truthvalue(conj, datadic, loop_vars)
            return (conj_truthval and comp_truthval)
        else:
            return comp_truthval
    elif name == 'disjunction':
        disj = get_child(node, 'disjunction', nofail=True)
        conj = get_child(node, 'conjunction')
        conj_truthval = determine_truthvalue(conj, datadic, loop_vars)
        if disj is not None:
            disj_truthval = determine_truthvalue(disj, datadic, loop_vars)
            return (disj_truthval or conj_truthval)
        else:
            return conj_truthval
    else:
        raise TypeError(f'Unsupported node type {name} encountered ' +
                         'while parsing boolean expression')

def evaluate_if_statement(tree, tree_handler, datadic, loop_vars,
                          dump_state, restore_state):
    assert tree.data == 'if_statement'
    if_head = get_child(tree, 'if_head')
    if_body = get_child(tree, 'if_body')
    lookahead_option = get_child(tree, 'lookahead_option', nofail=True)
    lookahead = 0
    if lookahead_option:
        lookahead_expr = get_child(lookahead_option, 'expr')
        lookahead = eval_expr(lookahead_expr, datadic, loop_vars)[0]
        if int(lookahead) != lookahead:
            raise ValueError( 'lookahead argument must evaluate to an integer' +
                             f'(got {lookahead})')
        lookahead = int(lookahead)

        if '__lookahead' in loop_vars:
            # NOTE: This error message will not appear because
            #       the lookahead is performed in a try clause.
            raise ValueError('Nested if statements with several ' +
                             'lookahead options are not allowed')

        # we want to save the state of the parser
        # before the lookahead to rewind it afterwards
        parser_state = dump_state()
        loop_vars['__lookahead'] = lookahead
        try:
            tree_handler(if_body)
        except:
            # we accept parsing failure
            # during lookahead, but print
            # the traceback for diagnostics
            write_info('Showing the stacktrace due to failure in lookahead...')
            traceback.print_exc()
            pass
        del(loop_vars['__lookahead'])

    # evaluate the condition (with variables in datadic potentially
    # affected by the lookahead)
    write_info('Evaluate if head ' + reconstruct_tree_str(if_head))
    disj = get_child(if_head, 'disjunction')
    try:
        truthval = determine_truthvalue(disj, datadic, loop_vars)
    except:
        # TODO: Improve the error handling. Ideally, we only want
        #       to assign the value False if any variable name
        #       in the if statement was not found but otherwise
        #       let this function fail.
        write_info('Showing the stacktrace due to failure in determination of if condition...')
        traceback.print_exc()
        truthval = False
    if truthval:
        write_info('Enter if body because ' + reconstruct_tree_str(if_head) + ' is true')
        if lookahead_option:
            restore_state(parser_state)
        tree_handler(if_body)
        write_info('Leave if body of if condition ' + reconstruct_tree_str(if_head))
    else:
        if lookahead_option:
            restore_state(parser_state)
        write_info('Skip if body because if condition ' + reconstruct_tree_str(if_head) + ' is false')

def should_proceed(tree, datadic, loop_vars, action_type):
    if action_type == 'endf_action':
        if '__lookahead' in loop_vars:
            if loop_vars['__lookahead'] == 0:
                return False
            else:
                loop_vars['__lookahead'] -= 1
    return True

