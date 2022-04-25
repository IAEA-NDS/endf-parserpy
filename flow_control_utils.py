from tree_utils import get_child, get_child_value, get_child_names
from endf_parsing_utils import get_varname, get_indexvar, eval_expr

def eval_expr_with_var(expr, datadic, loop_vars):
    v = eval_expr(expr)
    # check if variable in expression
    if v[1] != 0:
        varname = get_varname(expr)
        if varname not in datadic:
            raise ValueError(f'variable {varname} not found in datadic')
        indexvar = get_indexvar(expr)
        if indexvar is None:
            return v[0] + v[1] * datadic[varname]
        else:
            if indexvar not in loop_vars:
                raise ValueError(f'index variable {indexvar} not found in loop_vars')
            idx = loop_vars[indexvar]
            return v[0] + v[1] * datadic[varname][indexvar]
    else:
        return v[0]

def cycle_for_loop(tree, tree_handler, datadic, loop_vars):
    assert tree.data == 'for_loop'
    for_head = get_child(tree, 'for_head')
    varname = get_child_value(for_head, 'VARNAME')
    # determine range for loop counter
    start_expr = get_child(for_head, 'for_start')
    stop_expr = get_child(for_head, 'for_stop')
    start = eval_expr_with_var(start_expr, datadic, loop_vars)
    stop = eval_expr_with_var(stop_expr, datadic, loop_vars)
    assert float(start) == int(start)
    assert float(stop) == int(stop)
    start = int(start)
    stop = int(stop)
    for_body = get_child(tree, 'for_body')
    assert varname not in loop_vars
    for i in range(start, stop+1):
        loop_vars[varname] = i
        tree_handler(for_body)
    del(loop_vars[varname])

def evaluate_if_statement(tree, tree_handler, datadic, loop_vars,
                          dump_state, restore_state):
    assert tree.data == 'if_statement'
    if_condition = get_child(tree, 'if_condition')
    if_body = get_child(tree, 'if_body')
    lookahead_option = get_child(tree, 'lookahead_option', nofail=True)
    lookahead = 0
    if lookahead_option:
        lookahead_expr = get_child(lookahead_option, 'expr')
        lookahead = eval_expr_with_var(lookahead_expr, datadic, loop_vars)
        if int(lookahead) != lookahead:
            raise ValueError( 'lookahead argument must evaluate to an integer' +
                             f'(got {lookahead})')
        lookahead = int(lookahead)
        if '__lookahead' in loop_vars:
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
            # during lookahead
            pass
        del(loop_vars['__lookahead'])

    # evaluate the condition (with variables in datadic potentially
    # affected by the lookahead)
    assert len(if_condition.children) == 3
    left_expr = if_condition.children[0]
    cmpop = get_child_value(if_condition, 'IF_RELATION')
    right_expr = if_condition.children[2]
    left_val = eval_expr_with_var(left_expr, datadic, loop_vars)
    right_val = eval_expr_with_var(right_expr, datadic, loop_vars)
    if ((cmpop == ">" and left_val > right_val) or
        (cmpop == "<" and left_val < right_val) or
        (cmpop =="<=" and left_val <= right_val) or
        (cmpop ==">=" and left_val >= right_val) or
        (cmpop =="!=" and left_val != right_val) or
        (cmpop =="==" and left_val == right_val)):

        if lookahead_option:
            restore_state(parser_state)
        tree_handler(if_body)
    else:
        if lookahead_option:
            restore_state(parser_state)


def should_proceed(tree, datadic, loop_vars, action_type):
    if action_type == 'endf_action':
        if '__lookahead' in loop_vars:
            if loop_vars['__lookahead'] == 0:
                return False
            else:
                loop_vars['__lookahead'] -= 1
    return True

