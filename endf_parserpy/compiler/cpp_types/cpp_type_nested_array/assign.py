############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/22
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.recipe_parser.tree import Token
from endf_parserpy.utils.tree_utils import get_child
import endf_parserpy.compiler.cpp_primitives as cpp
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.node_checks import is_variable
from endf_parserpy.compiler.expr_utils.equation_utils import (
    contains_variable,
    get_variables_in_expr,
)
from endf_parserpy.compiler.expr_utils.tree_walkers import transform_nodes
from endf_parserpy.compiler.variable_management import (
    register_var,
    get_var_types,
    expand_abbreviation,
)
from endf_parserpy.compiler.node_checks import (
    is_list,
    is_loop,
    is_loop_head,
    is_for_loop,
    is_if_clause,
    is_section,
    is_repeat_loop,
)
from endf_parserpy.compiler.node_aux import (
    get_loopvar,
    get_loop_start,
    get_loop_stop,
)
from endf_parserpy.compiler.mode_management import (
    get_layout_recorder,
    get_nested_element_hook,
    get_unused_arrays,
)
from ..cpp_vartype_handling import has_loopvartype
from ..cpp_varaux import init_local_var_from_global_var
from ..cpp_dtype_aux import map_dtype
from .query import Query
from .auxiliary import get_ptr_varname, moveup_ptrassign
from endf_parserpy.compiler.unused_arrays import UnstoredAssignment
from endf_parserpy.utils.record_vectors import fixed_length_vector_arg


def _cpp_type(dtype, num_indices):
    if dtype == "intvec":
        # the values of an INTG record are the innermost level (rows),
        # see set_row and make_row_block of NestedArray
        return f"NestedArray<int, {num_indices + 1}>"
    return f"NestedArray<{map_dtype(dtype)}, {num_indices}>"


def _all_variables(expr):
    # the variables of an expression, also those in indices
    ret = set()
    for v in get_variables_in_expr(expr):
        ret.add(v)
        for idx in v.indices:
            ret.update(_all_variables(idx))
    return ret


def _prepare_dests(vartok, node, num_levels):
    # where the elements of the first num_levels levels are created
    dests = []
    limit_node = None
    for i in range(num_levels):
        limit_node = moveup_ptrassign(vartok, i, node, limit_node)
        dests.append(limit_node)
    return dests


def _is_scope_node(node):
    # sections and named LIST records have their own variables
    if is_section(node):
        return True
    return is_list(node) and get_child(node, "list_name", nofail=True) is not None


def _branches(node, scope):
    # the branch of each if-clause between the node and its scope
    ret = {}
    while node is not scope:
        parent = node.parent
        if is_if_clause(parent):
            ret[id(parent)] = id(node)
        node = parent
    return ret


def _occurs_elsewhere(node, vartok, site, branches):
    # whether the variable (same name and number of indices) occurs in
    # node apart from the site, also in indices, skipping the branches of
    # if-clauses that exclude the branch of the site
    if node is site:
        return False
    if isinstance(node, VariableToken):
        if str(node) == str(vartok) and len(node.indices) == len(vartok.indices):
            return True
        return any(_occurs_elsewhere(i, vartok, site, branches) for i in node.indices)
    if isinstance(node, Token):
        return False
    if node.data == "extvarname":
        # outside of expressions, variables are not converted to tokens
        name = get_child(node, "VARNAME")
        nidx = sum(1 for c in node.children if getattr(c, "data", None) == "indexquant")
        if str(name) == str(vartok) and nidx == len(vartok.indices):
            return True
    for child in node.children:
        if is_if_clause(node) and branches.get(id(node), id(child)) != id(child):
            # of a branch that excludes the branch of the site, only the
            # condition is considered (an else branch has none)
            if isinstance(child, Token):
                continue
            child = get_child(child, "if_head", nofail=True)
            if child is None:
                continue
        if _occurs_elsewhere(child, vartok, site, branches):
            return True
    return False


# nodes whose children are executed one after the other
_SEQUENCE_NODES = (
    "endf_recipe",
    "for_body",
    "repeat_body",
    "section_body",
    "if_body",
    "list_body",
    "list_line",
)
# nodes of records through which a field of a record is reached
_RECORD_PATH_NODES = (
    "code_token",
    "endf_line",
    "head_or_cont_line",
    "dir_line",
    "intg_line",
    "tab1_line",
    "tab2_line",
    "record_fields",
    "dir_fields",
    "intg_fields",
)
_TABLE_FIELDS = {"tab1_fields": (4, 5), "tab2_fields": (4,)}


def _in_field(node, vartok):
    # whether vartok is in a field of a record reached from node without
    # passing a loop, an if-clause or a section, so that the field is read
    # each time node is executed
    if isinstance(node, Token):
        return False
    if node.data == "expr":
        return contains_variable(node, vartok)
    if node.data == "list_line":
        # the fields in the body of a named LIST record are variables
        # of its own scope
        named = get_child(node, "list_name", nofail=True) is not None
        return any(
            _in_field(c, vartok)
            for c in node.children
            if not isinstance(c, Token)
            and (c.data == "record_fields" or (c.data == "list_body" and not named))
        )
    if node.data in _TABLE_FIELDS:
        # the fields NR and NP of a TAB1 record and NR of a TAB2 record
        # are the sizes of its tables, not assignments of variables
        exprs = [
            c
            for c in get_child(node, "record_fields").children
            if not isinstance(c, Token) and c.data == "expr"
        ]
        skip = _TABLE_FIELDS[node.data]
        return any(_in_field(e, vartok) for i, e in enumerate(exprs) if i not in skip)
    if node.data in _RECORD_PATH_NODES or node.data == "list_body":
        return any(_in_field(c, vartok) for c in node.children)
    return False


def _is_read_before(vartok, loop):
    # whether a field with vartok is read each time before the loop
    curnode = loop
    while curnode.parent is not None:
        parent = curnode.parent
        if parent.data in _SEQUENCE_NODES:
            for child in parent.children:
                if child is curnode:
                    break
                if _in_field(child, vartok):
                    return True
        curnode = parent
    return False


def _only_in_expressions(node, vartok, in_expr=False):
    # whether vartok occurs in node only in expressions
    if isinstance(node, Token):
        return in_expr or node != vartok
    in_expr = in_expr or node.data == "expr"
    return all(_only_in_expressions(c, vartok, in_expr) for c in node.children)


def _is_checked_only(vartok, loop):
    # A scalar variable whose value is read from a field each time before
    # the loop is known when the loop starts; its fields in the loop are
    # then only checked against this value (by both parsers), so that
    # the variable does not change in the loop, provided it is not
    # redefined there in another way (e.g. as abbreviation)
    return (
        len(vartok.indices) == 0
        and _is_read_before(vartok, loop)
        and _only_in_expressions(loop, vartok)
    )


def _is_invariant_limit(lim, loopvars, outer, vardict):
    # whether the value of the expression lim, evaluated before the loop
    # outer, does not change in outer (see condition 5 of find_block)
    abbrevs = vardict.get("__abbrevs", {})
    for v in _all_variables(lim):
        if v in loopvars or v in abbrevs:
            return False
        if has_loopvartype(v, vardict):
            continue
        if not contains_variable(outer, v, filters=[is_loop_head]):
            continue
        if not _is_checked_only(v, outer):
            return False
    return True


def _is_block(vartok, node, block, outer, vardict, vector_arg=None):
    num_leading = len(vartok.indices) - len(block)
    loopvars = {get_loopvar(loop) for loop in block}
    # variables compared by name and number of indices (loop variables
    # have none), as in the walker of numpy_annotation
    loopvar_keys = {(str(v), 0) for v in loopvars}
    for idx in vartok.indices[:num_leading]:
        if any((str(v), len(v.indices)) in loopvar_keys for v in _all_variables(idx)):
            return False
    scope = node
    while scope.parent is not None and not _is_scope_node(scope):
        scope = scope.parent
    if _occurs_elsewhere(scope, vartok, node, _branches(node, scope)):
        return False
    leading = {
        str(idx)
        for idx in vartok.indices[:num_leading]
        if is_variable(idx) and len(idx.indices) == 0
    }
    curnode = outer.parent
    while curnode is not scope and curnode is not None:
        if is_loop(curnode) and str(get_loopvar(curnode)) not in leading:
            return False
        curnode = curnode.parent
    limits = [
        lim for loop in block for lim in (get_loop_start(loop), get_loop_stop(loop))
    ]
    if vector_arg is not None:
        # the length of the vector is a further limit of the block
        limits.append(vector_arg)
    for lim in limits:
        if not _is_invariant_limit(lim, loopvars, outer, vardict):
            return False
    if num_leading > 0:
        if _prepare_dests(vartok, node, num_leading)[-1] is not outer:
            return False
    return True


def find_block(vartok, node, vardict):
    """Loops of the largest regular block of trailing indices.

    Returns the loops of the trailing indices (in the order of the
    indices), the outermost of them and, if the field is a vector of a
    length fixed before the record (see
    :mod:`endf_parserpy.utils.record_vectors`), which adds an innermost
    dimension to the block, the expression that determines the length
    (otherwise ``None``); or ``None`` if there is no block. The rule is
    the same as that of ``find_block`` in
    ``endf_parserpy.interpreter.numpy_annotation``, which explains it.
    """
    if node is None:
        return None
    vector_arg = fixed_length_vector_arg(node, lambda n: getattr(n, "parent", None))
    # a block has at least two dimensions
    min_loops = 2 if vector_arg is None else 1
    num_indices = len(vartok.indices)
    if num_indices < min_loops or get_var_types(vartok, vardict) is not None:
        return None
    names = [
        idx if is_variable(idx) and len(idx.indices) == 0 else None
        for idx in vartok.indices
    ]
    loops = []
    curnode = node.parent
    while curnode is not None and len(loops) < num_indices:
        # a block does not extend beyond an if-clause, a repeat loop or the
        # scope of a section or a named LIST record
        if is_if_clause(curnode) or is_repeat_loop(curnode) or _is_scope_node(curnode):
            break
        if is_for_loop(curnode) or curnode.data == "list_loop":
            loops.append(curnode)
        curnode = curnode.parent
    for rank in range(len(loops), min_loops - 1, -1):
        byvar = {str(get_loopvar(loop)): loop for loop in loops[:rank]}
        trailing = names[-rank:]
        if None in trailing or {str(v) for v in trailing} != set(byvar):
            continue
        block = tuple(byvar[str(v)] for v in trailing)
        if _is_block(vartok, node, block, loops[rank - 1], vardict, vector_arg):
            return block, loops[rank - 1], vector_arg
    return None


def _block_limits_code(block, vardict, vector_arg=None):
    # must be here to avoid a circular import error
    from endf_parserpy.compiler.code_generator_core import _loop_bound_code
    from ..cpp_varops_query import expr2str_shiftidx

    limits = []
    for loop in block:
        for lim in (get_loop_start(loop), get_loop_stop(loop)):
            lim = transform_nodes(lim.children[0], expand_abbreviation, vardict)
            limits.append(_loop_bound_code(lim, vardict))
    if vector_arg is not None:
        # the values of an INTG record, evaluated as by generate_code_for_intg
        ndigit = transform_nodes(vector_arg, expr2str_shiftidx, vardict)
        limits += ["0", f"cpp_intg_block_length({ndigit}) - 1"]
    return limits


def _pointer_levels(vardict):
    # number of leading levels with pointer variables per variable, shared
    # by all scopes of a generated function (stored with its basic
    # operations, which every copy of a scope shares); None if unknown
    curdict = vardict
    while "__basic_ops" not in curdict:
        if "__up" not in curdict:
            return None
        curdict = curdict["__up"]
    return curdict["__basic_ops"].setdefault("nested_array_pointer_levels", {})


def _prepared_per_iteration(vartok, node, num_leading):
    # Whether the element of each leading level i is prepared before the
    # loop of the index i+1, i.e. once in each iteration of the loop of
    # the index i, also if the loop of the index i+1 has no iterations.
    # Then the elements are prepared in the order of their indices without
    # gaps, so that prepare cannot fail (see unused_arrays).
    limit_node = None
    for i in range(num_leading):
        dest = moveup_ptrassign(vartok, i, node, limit_node)
        limit_node = dest
        if not is_loop(dest) or str(get_loopvar(dest)) != str(vartok.indices[i + 1]):
            return False
    return True


def _is_named_list_body(node, parent):
    return (
        is_list(parent)
        and node.data == "list_body"
        and get_child(parent, "list_name", nofail=True) is not None
    )


def _creation_loop(vartok, level, node, ptr_dest):
    # The loop before which the element of the leading level `level` of a
    # nested array is created, so that it exists (possibly empty) also if
    # the loop of the next index has no iterations: the loop of the index
    # level+1, if the indices up to level+1 are the variables of enclosing
    # for or LIST loops, the loop of each index enclosing that of the next
    # one, and no if-clause lies between that loop and the assignment.
    # None if no such loop exists, or if the element is already prepared
    # in that loop or further out (ptr_dest, see moveup_ptrassign), i.e.
    # once in each of its iterations. The search stops at a section or a
    # named LIST record, which have their own variables.
    names = [str(idx) for idx in vartok.indices[: level + 2]]
    target = None
    pos = level + 1
    cur = node
    while cur.parent is not None and pos >= 0:
        parent = cur.parent
        if is_section(parent) or _is_named_list_body(cur, parent):
            break
        if target is None and is_if_clause(parent):
            return None
        if (is_for_loop(parent) or parent.data == "list_loop") and str(
            get_loopvar(parent)
        ) == names[pos]:
            if target is None:
                target = parent
            pos -= 1
        cur = parent
    if target is None or pos >= 0:
        return None
    # skip if the element is already prepared in the target loop or a loop
    # around it
    cur = target
    while cur is not None:
        if cur is ptr_dest:
            return None
        cur = cur.parent
    return target


def _index_loop(vartok, pos, node):
    # The loop whose variable is the index pos of the variable and that
    # encloses the assignment (node) without an if-clause, a repeat loop,
    # a section or a named LIST record in between; other loops may lie in
    # between. None if the index is not a variable without indices or
    # there is no such loop.
    idx = vartok.indices[pos]
    if not is_variable(idx) or len(idx.indices) != 0:
        return None
    cur = node
    while cur.parent is not None:
        parent = cur.parent
        if (
            is_section(parent)
            or _is_named_list_body(cur, parent)
            or is_if_clause(parent)
            or is_repeat_loop(parent)
        ):
            return None
        if (is_for_loop(parent) or parent.data == "list_loop") and str(
            get_loopvar(parent)
        ) == str(idx):
            return parent
        cur = parent
    return None


def _loops_between(node, loop):
    # the loops enclosing node up to and including loop
    ret = []
    cur = node.parent
    while cur is not None:
        if is_loop(cur):
            ret.append(cur)
        if cur is loop:
            break
        cur = cur.parent
    return ret


def _scope_of(node):
    scope = node
    while scope.parent is not None and not _is_scope_node(scope):
        scope = scope.parent
    return scope


def _limits_invariant(loop, loopvars, vardict):
    # whether the bounds of the loop do not change while it is executed
    return all(
        _is_invariant_limit(lim, loopvars, loop, vardict)
        for lim in (get_loop_start(loop), get_loop_stop(loop))
    )


def _filled_in_one_execution(vartok, level, node, loop, loopvars, vardict):
    # Whether the children of an element of the level `level` created in
    # the loop are all set in the execution of the loop in which it is
    # created: each loop around the loop (up to the scope) has a leading
    # index of the element as variable, so that another execution of the
    # loop belongs to another element, and the leading indices do not
    # change in the loop except with the loops inside it.
    leading = vartok.indices[: level + 1]
    names = {str(idx) for idx in leading if is_variable(idx) and len(idx.indices) == 0}
    scope = _scope_of(node)
    cur = loop.parent
    while cur is not None and cur is not scope:
        if is_repeat_loop(cur):
            return False
        if is_loop(cur) and str(get_loopvar(cur)) not in names:
            return False
        cur = cur.parent
    loopvar = get_loopvar(loop)
    inner = {str(v) for v in loopvars if str(v) != str(loopvar)}
    for idx in leading:
        for v in _all_variables(idx):
            if str(v) in inner:
                continue
            if not _is_invariant_limit(v, {loopvar}, loop, vardict):
                return False
    return True


def _reservation_loop(vartok, level, node, vardict):
    # The loop that sets the children of the elements of the level `level`
    # of a nested array (the variable itself for level -1), whose number
    # is reserved (see _reserve_code): the loop of the index level+1 (see
    # _index_loop) whose bounds do not change while it is executed. None
    # if there is no such loop.
    loop = _index_loop(vartok, level + 1, node)
    if loop is None or loop.loop_bounds is None:
        return None
    loopvars = {get_loopvar(lp) for lp in _loops_between(node, loop)}
    if not _limits_invariant(loop, loopvars, vardict):
        return None
    return loop, loopvars


def _created_in_loop_reservable(vartok, level, node, loop, loopvars, vardict):
    # An element created inside the loop that sets its children gets the
    # reservation when it is created if it is created only at this
    # assignment (the variable occurs nowhere else in its scope) and all
    # its children are set in the same execution of the loop.
    scope = _scope_of(node)
    if _occurs_elsewhere(scope, vartok, node, _branches(node, scope)):
        return False
    return _filled_in_one_execution(vartok, level, node, loop, loopvars, vardict)


def _encloses(outer, node):
    # whether node is outer or inside it
    while node is not None:
        if node is outer:
            return True
        node = node.parent
    return False


def _reserve_code(arrname, loop):
    # The capacity of the list arrname (ending with . or ->) for the
    # children set by the loop, reserved before the loop; the bounds are
    # evaluated in the same order as by the loop. The reservation does not
    # change the elements.
    start, stop = loop.loop_bounds
    return cpp.block(
        cpp.statement(f"int cpp_first = {start}")
        + cpp.statement(f"{arrname}reserve(cpp_first, {stop})")
    )


def _reserve_at_creation_code(ptrname, loop):
    # The capacity of the element just prepared (ptrname) for the children
    # set by the loop, which encloses the preparation, reserved if the
    # element is new (empty); the bounds have the values with which the
    # loop started (see _limits_invariant).
    start, stop = loop.loop_bounds
    return cpp.pureif(
        f"{ptrname}->empty()",
        cpp.statement(f"int cpp_first = {start}")
        + cpp.statement(f"{ptrname}->reserve(cpp_first, {stop})"),
    )


class Assign:

    def define_var(vartok, vardict, save_state=False):
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtype = next(v[0] for v in vartypes if v[1] == specialtype)
        num_indices = len(vartok.indices)
        varname = Query.get_cpp_varname(vartok, vardict)
        code = ""
        if save_state:
            code += init_local_var_from_global_var(
                varname, _cpp_type(dtype, num_indices)
            )
        else:
            code += cpp.statement(f"{_cpp_type(dtype, num_indices)} {varname}")
        levels = _pointer_levels(vardict)
        num_ptrs = num_indices - 1
        if levels is not None:
            num_ptrs = levels.get((str(vartok), num_indices), 0)
        for i in range(num_ptrs):
            ptrtype = _cpp_type(dtype, num_indices - i - 1)
            code += cpp.statement(f"{ptrtype}* {get_ptr_varname(vartok, i)}")
        return code

    def assign_exprstr_to_var(vartok, indices, exprstr, dtype, vardict, node):
        if len(indices) == 0:
            return False
        block = find_block(vartok, node, vardict)
        register_var(vartok, dtype, "NestedArray", vardict)
        cpp_varname = Query.get_cpp_varname(vartok, vardict, dtype=dtype)
        num_indices = len(indices)
        num_leading = num_indices - 1 if block is None else num_indices - len(block[0])
        # the values of an INTG record are a row, an innermost level
        rows = dtype == "intvec"
        layout_recorder = get_layout_recorder(vardict)
        nested_element_hook = get_nested_element_hook(vardict)
        levels = _pointer_levels(vardict)
        if levels is not None:
            key = (str(vartok), num_indices)
            levels[key] = max(levels.get(key, 0), num_leading)
        # the values of an unused array are not stored (writing), only the
        # elements are registered with the index bookkeeping as before
        unused = (
            node is not None
            and str(vartok) in get_unused_arrays(vardict)
            and _prepared_per_iteration(vartok, node, num_leading)
        )
        code = ""
        ptrvar_old = cpp_varname
        limit_node = None
        # the levels whose elements are lists (not blocks) of children
        # set by the loop of the next index, see _reservation_loop
        num_lists = num_leading if block is None else num_leading - 1
        for i in range(num_leading):
            ptrvar_new = get_ptr_varname(vartok, i)
            dot = "." if i == 0 else "->"
            new_code = ""
            if not unused:
                new_code = cpp.statement(
                    f"{ptrvar_new} = {ptrvar_old}{dot}prepare({indices[i]})"
                )
            if node is not None:
                destnode = moveup_ptrassign(vartok, i, node, limit_node)
                limit_node = destnode
                creation = _creation_loop(vartok, i, node, destnode)
                reservation = None
                if not unused and i < num_lists:
                    reservation = _reservation_loop(vartok, i, node, vardict)
                if reservation is not None:
                    loop, loopvars = reservation
                    loop.check_my_identity()
                    if _encloses(destnode, loop):
                        # the element is known before the loop
                        loop.append_loop_setup(_reserve_code(f"{ptrvar_new}->", loop))
                    elif creation is not loop and _created_in_loop_reservable(
                        vartok, i, node, loop, loopvars, vardict
                    ):
                        new_code += _reserve_at_creation_code(ptrvar_new, loop)
            if nested_element_hook is not None:
                new_code += nested_element_hook(vartok, indices[: i + 1])
            if node is not None:
                if destnode is not node:
                    destnode.check_my_identity()
                    destnode.append_precode(new_code)
                    if layout_recorder is not None:
                        layout_recorder.record_pointer_preparation(
                            vartok, i, destnode, node
                        )
                else:
                    code += new_code
                # the element is created (empty) before the loop of the
                # next index if the preparation above stays inside it,
                # e.g. because the variable occurs elsewhere in that loop,
                # so that a loop without iterations leaves no gap
                if creation is not None:
                    create_code = ""
                    if not unused:
                        chain = "".join(
                            f"{'.' if k == 0 else '->'}prepare({indices[k]})"
                            for k in range(i + 1)
                        )
                        create_code = cpp.statement(f"{cpp_varname}{chain}")
                    if nested_element_hook is not None:
                        create_code += nested_element_hook(vartok, indices[: i + 1])
                    creation.check_my_identity()
                    creation.append_precode(create_code)
                    if (
                        reservation is not None
                        and reservation[0] is creation
                        and not _encloses(destnode, creation)
                    ):
                        # the element is created right before the loop
                        creation.append_loop_setup(
                            _reserve_code(f"{cpp_varname}{chain}->", creation)
                        )
                    if layout_recorder is not None:
                        layout_recorder.record_pointer_preparation(
                            vartok, i, creation, node
                        )
            else:
                code += new_code
            ptrvar_old = ptrvar_new
        if unused:
            return UnstoredAssignment(code)
        dot = "." if num_leading == 0 else "->"
        if node is not None and num_lists >= 0:
            # the variable itself (level -1) is the list of the children
            # set by the loop of its first index
            reservation = _reservation_loop(vartok, -1, node, vardict)
            if reservation is not None:
                loop = reservation[0]
                loop.check_my_identity()
                loop.append_loop_setup(_reserve_code(f"{cpp_varname}.", loop))
        if block is None:
            setter = "set_row" if rows else "set"
            code += cpp.statement(
                f"{ptrvar_old}{dot}{setter}({indices[-1]}, {exprstr})"
            )
            return code
        loops, outer, vector_arg = block
        limits = ", ".join(_block_limits_code(loops, vardict, vector_arg))
        maker = "make_block" if vector_arg is None else "make_row_block"
        outer.append_precode(cpp.statement(f"{ptrvar_old}{dot}{maker}({limits})"))
        if layout_recorder is not None:
            rank = len(loops) + (0 if vector_arg is None else 1)
            layout_recorder.record_block(vartok, num_leading, outer, node, rank)
        trailing = ", ".join(indices[num_leading:])
        deref = cpp_varname if num_leading == 0 else f"(*{ptrvar_old})"
        if rows:
            code += cpp.statement(f"{deref}.set_block_row({exprstr}, {trailing})")
        else:
            code += cpp.statement(f"{deref}({trailing}) = {exprstr}")
        return code

    def get_layout(vartok, vardict):
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtype = next(v[0] for v in vartypes if v[1] == specialtype)
        return (specialtype, dtype, len(vartok.indices))

    def store_var_in_endf_dict2(vartok, vardict):
        src_varname = Query.get_cpp_varname(vartok, vardict)
        assigncode = cpp.statement(
            f'cpp_current_dict["{vartok}"] = {src_varname}.to_pyobj(list_mode, numpy_ints, numpy_floats)'
        )
        code = cpp.pureif(Query.did_read_var(vartok, vardict), assigncode)
        return code
