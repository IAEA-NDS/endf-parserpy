############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from endf_parserpy.recipe_parser.tree import Token, Tree
from endf_parserpy.utils.tree_utils import get_child, get_name
from .expr_utils.equation_utils import get_variables_in_expr
from .expr_utils.custom_nodes import VariableToken
from . import cpp_primitives as cpp
from .cpp_types.cpp_dtype_aux import map_dtype
from .cpp_types.cpp_varops_query import did_read_var, get_idxstr
from .cpp_types.cpp_varaux import check_variable, get_cpp_varname
from .lookahead_management import in_lookahead
from .variable_management import expand_abbreviation
from .expr_utils.tree_walkers import transform_nodes
from .mode_management import (
    get_prepare_line_func,
    get_numeric_field_getter,
    get_finalize_line_func,
    get_list_bulk_form,
    get_list_bulk_recorder,
)


def _template_literal(template):
    return template.replace("\n", r"\n")


def define_current_template(template):
    # when reading, cpp_template is ParsingOptions::current_template,
    # the template shown in error messages
    tmpl = _template_literal(template)
    code = cpp.statement(f'cpp_template = "{tmpl}"')
    return code


def define_record_body_template(template):
    # the template preceded by CPP_BODY_MARK (octal 001): the lines of the
    # body of a TAB1, TAB2 or LIST record are read (see ParsingOptions)
    tmpl = _template_literal(template)
    code = cpp.statement(f'cpp_template = "\\001{tmpl}"')
    return code


def read_raw_line(linevar):
    code = cpp.statement(f"cpp_read_raw_line({linevar}, cont)")
    return code


def read_send(mat, mf, parse_opts):
    code = cpp.statement(f"cpp_read_send(cont, {mat}, {mf}, {parse_opts})")
    return code


def is_fend(mat, parse_opts):
    return f"cpp_is_fend_record(cpp_line, {mat}, {parse_opts})"
    return code


def is_mend(parse_opts):
    return f"cpp_is_mend_record(cpp_line, {parse_opts})"


def is_tend(parse_opts):
    return f"cpp_is_tend_record(cpp_line, {parse_opts})"


def is_blank_line():
    return "cpp_is_blank_line(cpp_line)"


def read_line(linevar, mat, mf, mt, parse_opts):
    code = cpp.statement(
        f"cpp_read_line({linevar}, cont, {mat}, {mf}, {mt}, {parse_opts})"
    )
    return code


def read_line_la(linevar, mat, mf, mt, parse_opts, lookahead):
    if lookahead:
        return read_raw_line(linevar)
    else:
        return read_line(linevar, mat, mf, mt, parse_opts)


def get_mat_number(linevar):
    code = f"cpp_read_mat_number({linevar}.data())"
    return code


def get_mf_number(linevar):
    code = f"cpp_read_mf_number({linevar}.data())"
    return code


def get_mt_number(linevar):
    code = f"cpp_read_mt_number({linevar}.data())"
    return code


def get_int_field(idx, parse_opts):
    cpp_dtype = map_dtype(int)
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.data(), {idx}, {parse_opts})"
    return code


def get_custom_int_field(start_pos, length):
    code = f"cpp_read_custom_int_field(cpp_line.data(), {start_pos}, {length})"
    return code


def get_int_vec(numel, parse_opts):
    cpp_dtype = map_dtype(int)
    code = cpp.statement(f"cpp_read_vec<{cpp_dtype}>(cont, {numel}, {parse_opts})")
    return code


def get_float_vec(nume, parse_opts):
    cpp_dtype = map_dtype(float)
    code = cpp.statement(f"cpp_read_vec<{cpp_dtype}>(cont, {numel}, {parse_opts})")
    return code


def get_numeric_field(fieldpos, dtype, parse_opts):
    cpp_dtype = map_dtype(dtype)
    code = f"cpp_read_field<{cpp_dtype}>(cpp_line.data(), {fieldpos}, {parse_opts})"
    return code


_NUMERIC_FIELD_RE = re.compile(r"cpp_read_field<\w+>\(cpp_line\.data\(\), (\d+), \w+\)")


def get_numeric_field_position(valcode):
    """Return the field position of code returned by
    :func:`get_numeric_field`, or -1 for any other code."""
    m = _NUMERIC_FIELD_RE.fullmatch(valcode)
    return int(m.group(1)) if m else -1


def get_text_field(start, length):
    code = f"cpp_line.substr({start}, {length})"
    return code


def _map_bool(boolexpr):
    return "true" if boolexpr else "false"


def validate_field(
    expected_value,
    actual_value,
    contains_variable,
    contains_desired_number,
    contains_inconsistent_varspec,
    exprstr,
    parse_opts,
):
    cont_var = _map_bool(contains_variable)
    cont_des_num = _map_bool(contains_desired_number)
    cont_incons_var = _map_bool(contains_inconsistent_varspec)
    # the field of the value for error messages (-1 if not a single field)
    fieldnum = get_numeric_field_position(actual_value)
    # a value of the body of a LIST record (cpp_i is its index in the
    # body): delivered by CppListBody (see list_body_field) or read from
    # the current line (field cpp_j); only used for a tolerated mismatch
    body_args = ""
    if actual_value.startswith("cpp_body."):
        body_args = ", &cpp_body, cpp_i"
    elif _BODY_FIELD_RE.search(actual_value):
        body_args = ", nullptr, cpp_i"
    code = cpp.statement(
        f"cpp_validate_field({expected_value}, {actual_value}, "
        + f" {cont_var}, {cont_des_num}, {cont_incons_var}, "
        + f"{exprstr},"
        + "\n"
        + " " * cpp.INDENT
        + f"{fieldnum}, {parse_opts}{body_args})"
    )
    return code


# the reading of a field of the body of a LIST record in the per-field
# form (see cpp_read_field and ListBodyRecorder)
_BODY_FIELD_RE = re.compile(r"\(cpp_line\.data\(\), cpp_j, ")


def get_tab1_body(xvar, yvar, nr, np, mat, mf, mt, parse_opts):
    code = f"read_tab1_body(cont, {nr}, {np}, {mat}, {mf}, {mt}, {parse_opts})"
    return code


def get_tab2_body(nr, mat, mf, mt, parse_opts):
    code = f"read_tab2_body(cont, {nr}, {mat}, {mf}, {mt}, {parse_opts})"
    return code


def open_section(
    vartok, vardict, current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"
):
    check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices

    idxstrs = []
    for i, idxtok in enumerate(indices):
        curidxstr = get_idxstr(vartok, i, vardict)
        idxstrs.append(curidxstr)
    idcsarg = "std::vector<int>({" + ", ".join(idxstrs) + "})"

    code = ""
    code += cpp.statement(f"py::dict {parent_dict} = {current_dict}")
    code += cpp.statement(
        f"{current_dict} = "
        f'cpp_index_shifter_store.setdefault("{secname}", {idcsarg}, py::dict())'
    )
    return code


def close_section(current_dict="cpp_current_dict", parent_dict="cpp_parent_dict"):
    code = cpp.statement(f"{current_dict} = {parent_dict}")
    return code


def did_not_read_var(vartok, vardict, indices=None):
    return "(! " + did_read_var(vartok, vardict, indices) + ")"


def any_unread_vars(vartoks, vardict, glob=False):
    if glob:
        return cpp.logical_or(did_not_read_var(v, vardict) for v in vartoks)
    else:
        return cpp.logical_or(did_not_read_var(v, vardict, v.indices) for v in vartoks)


def did_encounter_var(vartok, vardict):
    while vartok not in vardict and "__up" in vardict:
        vardict = vardict["__up"]
    return vartok in vardict


def count_not_encountered_vars(node, vardict):
    varset = get_variables_in_expr(node)
    return sum(not did_encounter_var(v, vardict) for v in varset)


def should_parse_section(mf, mt, exclude, include):
    return f"should_parse_section({mf}, {mt}, {exclude}, {include})"


def should_not_parse_section(mf, mt, exclude, include):
    return cpp.logical_not(should_parse_section(mf, mt, exclude, include))


def read_section_verbatim(tarvec, mat, mf, mt, cont, is_firstline, parse_opts):
    code = cpp.statement(
        f"{tarvec} = read_section_verbatim({mat}, {mf}, {mt}, {cont}, "
        + f"{is_firstline}, {parse_opts})"
    )
    return code


def list_body_field(dtype, fieldpos, parse_opts):
    # the value cpp_i of the body of a LIST record decoded by CppListBody,
    # the field fieldpos of the current line (read if not decoded)
    cpp_dtype = map_dtype(dtype)
    code = (
        f"cpp_body.field<{cpp_dtype}>(cpp_i, cpp_line.data(), {fieldpos}, "
        + f"{parse_opts})"
    )
    return code


def list_body_next_line(linevar, mat, mf, mt, parse_opts):
    # the reading of the next line of the body of a LIST record decoded by
    # CppListBody (only lines not read by it are read)
    code = cpp.statement(
        f"cpp_body.next_line({linevar}, cont, {mat}, {mf}, {mt}, {parse_opts})"
    )
    return code


def _all_variable_keys(expr):
    # names and numbers of indices of the variables of an expression, also
    # of those in indices
    keys = set()
    for v in get_variables_in_expr(expr):
        keys.add((str(v), len(v.indices)))
        for idx in v.indices:
            keys.update(_all_variable_keys(idx))
    return keys


def _same_variable(a, b):
    return str(a) == str(b) and len(a.indices) == len(b.indices)


class _ListStore:
    # a store of a value into an array, as reported by the assignment code
    # (cpp_type_nested_array/assign.py): the kind ("list": set, "block":
    # operator(), "row": the values of an INTG record), the container (a
    # list ending with "." or "->", or a block), the C++ code and the
    # expressions of the indices of the store, whether other code (e.g. the
    # preparation of an element) precedes it in the code of the
    # assignment, and the preparations of elements in that code (the code
    # and the expression of the index of each), if it has no other
    # statements (None otherwise)
    def __init__(
        self, vartok, kind, container, indices, index_exprs, preceded, preparations
    ):
        self.vartok = vartok
        self.kind = kind
        self.container = container
        self.indices = list(indices)
        self.index_exprs = list(index_exprs)
        self.preceded = preceded
        self.preparations = None if preparations is None else list(preparations)


class _ListElement:
    # an element of the body of a LIST record in the bulk pass: how it is
    # read (see _classify_list_element in code_generator_core.py), its
    # code, the stores and the code of the type of the variable reported
    # while the code was generated
    def __init__(self, classification):
        self.kind, detail = classification
        self.vartok = detail if self.kind == "assign" else None
        self.reason = detail if self.kind == "other" else None
        self.code = None
        self.stores = []
        self.type_codes = []


class _ListLoop:
    # a loop of the body of a LIST record as generated in the bulk pass:
    # its C++ variable, its bounds, its setup code (the code placed before
    # the loop, see ParseNode) and the declaration of the read flag of its
    # variable at the start of an iteration
    def __init__(self, node):
        self.variable = node.loop_variable
        self.bounds = node.loop_bounds
        self.setup = node.precode + node.loop_setup
        self.readflag = node.loop_readflag


class ListBulkRecorder:
    """The recorder of the bulk pass of the body of a LIST record.

    Stored in the copy of the vardict with which the body is generated for
    the bulk form (see :meth:`ListBulkForm.generate`); found with
    :func:`~endf_parserpy.compiler.mode_management.get_list_bulk_recorder`.
    The field getter and the reading of a line of the parsing mode emit
    the code reading the decoded body (:meth:`field`, :meth:`next_line`),
    the code of the body reports its elements (:meth:`start_element`,
    :meth:`finish_element`), and the assignment code the stores of the
    values (:meth:`record_store`) and the code of the type of the variable
    (:meth:`record_type_code`).
    """

    def __init__(self):
        self.elements = {}
        self.loops = {}
        self.fields = 0
        self.line_args = None
        self.body_code = None
        self.first_line = None
        self._current = None

    def field(self, fieldpos, parse_opts):
        self.fields += 1
        return list_body_field(float, fieldpos, parse_opts)

    def next_line(self, linevar, mat, mf, mt, parse_opts):
        self.line_args = (linevar, mat, mf, mt, parse_opts)
        return list_body_next_line(linevar, mat, mf, mt, parse_opts)

    def start_element(self, node, classification):
        self._current = _ListElement(classification)
        self.elements[id(node)] = self._current

    def finish_element(self, node, code):
        element = self.elements[id(node)]
        element.code = code
        self._current = None

    def record_store(
        self,
        node,
        vartok,
        kind,
        container,
        indices,
        index_exprs,
        preceded,
        preparations=None,
    ):
        if self._current is not None:
            self._current.stores.append(
                _ListStore(
                    vartok,
                    kind,
                    container,
                    indices,
                    index_exprs,
                    preceded,
                    preparations,
                )
            )

    def record_type_code(self, node, vartok, code):
        if self._current is not None:
            self._current.type_codes.append((vartok, code))


def _parse_nodes(node):
    # the nodes of a tree to which code can be attached (ParseNode)
    if not isinstance(node, Tree):
        return
    if hasattr(node, "precode"):
        yield node
    for child in node.children:
        yield from _parse_nodes(child)


def _sandbox_vardict(vardict):
    # A copy of a scope for a second generation of a part of it: the
    # containers of the scope are copied (the types of its variables, the
    # loop variables, the abbreviations), so that the generation changes
    # nothing of the scope; the enclosing scopes are not changed by the
    # generation of the code of a scope, and the basic operations are
    # shared (their registries record the same for both generations).
    copy = {}
    for key, value in vardict.items():
        if key in ("__up", "__basic_ops"):
            copy[key] = value
        elif isinstance(value, dict):
            copy[key] = dict(value)
        elif isinstance(value, set):
            copy[key] = set(value)
        else:
            copy[key] = value
    return copy


class _BulkSite:
    # an element of the body of a LIST record, in the loops `loops` (from
    # the outermost one) of the body; of these, the row loops (`rloops`)
    # and the copy loops (`cloops`), see ListBulkForm._strided_plan
    def __init__(self, node, element, loops):
        self.node = node
        self.element = element
        self.kind = element.kind
        self.vartok = element.vartok
        self.code = element.code
        self.loops = loops
        self.rloops = []
        self.cloops = list(loops)


class _BulkLoop:
    # a loop of the body of a LIST record, in the loops `ancestors` (from
    # the outermost one) of the body; `row`: whether it is a row loop
    def __init__(self, node, depth, info, ancestors):
        self.node = node
        self.depth = depth
        self.variable = info.variable
        self.bounds = info.bounds
        self.setup = info.setup
        self.readflag = info.readflag
        self.ancestors = list(ancestors)
        self.row = False
        self.items = []


class ListBulkForm:
    """The bulk form of the reading of the body of a LIST record.

    The body is read in today's per-field form (each float value with
    ``cpp_read_field`` while the lines are read one after the other) and,
    in a second copy, in the bulk form: all lines of the body are read and
    their fields converted into a buffer first (``CppListBody`` in
    ``module_header_reading.hpp``), and the values are then delivered
    from the buffer. The form is chosen once per record: the bulk form if
    a row kernel is selected (``cpp_float_row_kernel``), the input is held
    in memory and the original strings of the values are not kept, and,
    for a body without a regular layout, if all bodies are read in the
    bulk form, i.e. with a vector tier or a tier forced by the environment
    variable (``cpp_list_bulk``): with the scalar row kernel, the delivery
    by the code of the per-field form is not faster than the per-field
    form itself.

    The values are delivered by the code of the per-field form generated
    a second time (:meth:`generate`), in which each reading of a field
    takes the value from the buffer (as long as the conversion of the
    buffer has not stopped before it) and the reading of a line is
    ``CppListBody::next_line``, so that the checks and errors are those of
    the per-field form in the same order. If the layout of the body is
    regular (:meth:`_strided_plan`), the values are delivered by strided
    copies instead, provided that the whole body is converted, that the
    number of values given by the layout is NPL and that the checks of
    the values pass; otherwise, and if a copy cannot be done, the values
    are delivered by the code of the per-field form, which repeats the
    operations done before (all of which can be repeated without changing
    their result).
    """

    @staticmethod
    def condition(strided):
        # the per-field form is chosen at runtime by this condition
        flag = "true" if strided else "false"
        return f"! cpp_list_bulk(cont, parse_opts, {flag})"

    @staticmethod
    def generate(body_node, vardict, generate_body):
        """Generate the code of the body of a LIST record for the bulk form
        (the bulk pass) and return its recorder (:class:`ListBulkRecorder`).

        The body is generated by ``generate_body(body_node, vardict)`` with
        a copy of the scope that holds the recorder, as the body of an
        if-statement with lookahead is generated with a copy. The pass
        leaves no trace: the code placed on the nodes of the tree (see
        ``ParseNode``) and the bounds and variables of the loops are
        restored afterwards, so that the per-field form, generated after
        it, is the code generated without the bulk form; the code placed
        on the loops of the body in this pass is kept by the recorder.
        """
        root = body_node
        while getattr(root, "parent", None) is not None:
            root = root.parent
        saved = [
            (
                n,
                n.precode,
                n.loop_setup,
                n.loop_bounds,
                n.loop_variable,
                n.loop_readflag,
            )
            for n in _parse_nodes(root)
        ]
        recorder = ListBulkRecorder()
        sandbox = _sandbox_vardict(vardict)
        sandbox["__list_bulk_body"] = recorder
        try:
            recorder.body_code = generate_body(body_node, sandbox)
            recorder.first_line = get_prepare_line_func(sandbox)(sandbox)
            for node in _parse_nodes(body_node):
                if get_name(node) == "list_loop":
                    recorder.loops[id(node)] = _ListLoop(node)
        finally:
            for node, precode, setup, bounds, variable, readflag in saved:
                node.precode = precode
                node.loop_setup = setup
                node.loop_bounds = bounds
                node.loop_variable = variable
                node.loop_readflag = readflag
        return recorder

    # --- the regular layout -----------------------------------------

    @classmethod
    def _tree(cls, body_node, bulk, loops, depth, items, sites, all_loops):
        for child in body_node.children:
            name = get_name(child)
            if name == "expr":
                element = bulk.elements.get(id(child))
                if element is None:
                    return "element not recorded"
                site = _BulkSite(child, element, list(loops))
                items.append(site)
                sites.append(site)
            elif name == "list_loop":
                info = bulk.loops.get(id(child))
                if info is None or info.variable is None or info.bounds is None:
                    return "loop not recorded"
                loop = _BulkLoop(child, depth, info, loops)
                items.append(loop)
                all_loops.append(loop)
                reason = cls._tree(
                    get_child(child, "list_body"),
                    bulk,
                    loops + [loop],
                    depth + 1,
                    loop.items,
                    sites,
                    all_loops,
                )
                if reason is not None:
                    return reason
            elif name == "LINEPADDING":
                return "line padding"
        return None

    @staticmethod
    def _bound_keys(loop, vardict):
        head = get_child(loop.node, "list_for_head")
        keys = set()
        for part in ("for_start", "for_stop"):
            expr = get_child(get_child(head, part), "expr")
            expr = transform_nodes(expr, expand_abbreviation, vardict)
            keys.update(_all_variable_keys(expr))
        return keys

    @staticmethod
    def _loop_key(loop):
        # the name of the variable of a loop, as a key of _all_variable_keys
        head = get_child(loop.node, "list_for_head")
        return (str(get_child(head, "VARNAME")), 0)

    @staticmethod
    def _depends(expr, keys, vardict):
        # whether an expression (abbreviations expanded, indices included)
        # contains one of the variables `keys`
        expr = transform_nodes(expr, expand_abbreviation, vardict)
        return len(_all_variable_keys(expr) & keys) > 0

    @staticmethod
    def _list_store(element):
        # the only store of an element into a list, without code before it
        # in the code of the assignment other than preparations of
        # elements; None otherwise
        if len(element.stores) != 1:
            return None
        store = element.stores[0]
        if store.kind != "list" or not _same_variable(store.vartok, element.vartok):
            return None
        if store.preceded and store.preparations is None:
            return None
        return store

    @classmethod
    def _store(cls, element, forbidden, vardict):
        # The store of the value of an element in a loop into an array, as
        # reported by the assignment code: the only store of the element,
        # into a list (set) or a block (operator()), with no other code
        # before it in the code of the assignment than preparations of
        # elements (a pointer assigned, e.g. to the row of a list of
        # lists) whose indices do not depend on the variables `forbidden`
        # (those of the copy loops), so that the code of the assignment is
        # these preparations, the store and the code of the type of the
        # variable (see assign_exprstr_to_var in cpp_varops_assign.py).
        # Returns the store, the code of the type and the code of the
        # preparations, or None.
        if len(element.stores) != 1:
            return None
        store = element.stores[0]
        if store.kind not in ("list", "block"):
            return None
        if not _same_variable(store.vartok, element.vartok):
            return None
        prepare_code = ""
        if store.preceded:
            if not store.preparations:
                return None
            for code, expr in store.preparations:
                if cls._depends(expr, forbidden, vardict):
                    return None
                prepare_code += code
        type_code = "".join(
            code for v, code in element.type_codes if _same_variable(v, element.vartok)
        )
        return store, type_code, prepare_code

    @classmethod
    def _strided_plan(cls, body_node, bulk, vardict):
        """The plan of the strided delivery of the values of the body, or
        the reason why there is none, as ``(plan, reason)``.

        The rule (general, from the recipe and the decisions of the code
        generator): every element of the body is a literal, whose value is
        checked (with ``cpp_validate_field``, as the per-field form does),
        or a variable assigned for the first time; the bounds of the loops
        of the body do not depend on variables assigned in the body, and
        depend on variables of loops of the body only if these loops
        enclose them.

        A loop of the body is a row loop if the bounds of a loop inside it
        depend on its variable, if it encloses the loop of a list filled
        in the innermost of several loops (a list per iteration of the
        outer loops), or if it encloses a row loop; the other loops are
        copy loops. Every iteration of a copy loop has the same number of
        values, given the iteration of the enclosing row loops, and the
        row loops are the outermost loops around every element. All
        bounds and numbers of values can then be evaluated before the
        values are delivered: those of the copy loops once per iteration
        of the enclosing row loops, the number of values of a row loop by
        summing over its iterations. A copy loop inside a copy loop has no
        setup code (preparation of elements, blocks, reservations); the
        setup code of the other loops is executed as in the per-field
        form, i.e. once per iteration of the enclosing row loops.

        A variable outside of the copy loops (S1, outside of all loops,
        or a value per iteration of the row loops) is assigned by the code
        of the per-field form from the value at its position. A variable in
        copy loops (S) is an array whose indices are the variables of
        these loops (each in one index) and indices that do not depend on
        them (but may depend on the variables of the row loops), stored as
        reported by the assignment code (:meth:`_store`): either a list
        (the value set with ``set``) in one copy loop, whose values are
        appended by one strided copy (``set_strided``), per iteration of
        the row loops if there are any (R), or a block (the value assigned
        with ``operator()``), whose values are copied with the strides of
        the block. The preparations of elements in the code of the
        assignment (e.g. of the row of a list of lists) are done before
        the copy.
        """
        items, sites, loops = [], [], []
        reason = cls._tree(body_node, bulk, [], 0, items, sites, loops)
        if reason is not None:
            return None, reason
        if len(loops) == 0:
            return None, "no loop"
        loopvar_keys = {cls._loop_key(loop) for loop in loops}
        assigned = set()
        for site in sites:
            if site.kind == "other":
                return None, site.element.reason
            if site.kind == "assign":
                assigned.add((str(site.vartok), len(site.vartok.indices)))
        # the row loops: those whose variables the bounds of the loops
        # inside them depend on ...
        rows = set()
        for loop in loops:
            keys = cls._bound_keys(loop, vardict)
            outer = {cls._loop_key(a): a for a in loop.ancestors}
            dependencies = keys & loopvar_keys
            if any(key not in outer for key in dependencies):
                return None, "loop bounds depend on a loop of the body"
            if keys & assigned:
                return None, "loop bounds depend on a value of the body"
            rows.update(id(outer[key]) for key in dependencies)
        # ... those around a list filled in the innermost of several loops
        # (a list per iteration of the outer loops) ...
        for site in sites:
            if site.kind != "assign" or len(site.loops) < 2:
                continue
            store = cls._list_store(site.element)
            if store is not None and store.indices[0] == site.loops[-1].variable:
                rows.update(id(lp) for lp in site.loops[:-1])
        # ... and those around a row loop
        for loop in loops:
            if id(loop) in rows:
                rows.update(id(a) for a in loop.ancestors)
        for loop in loops:
            loop.row = id(loop) in rows
        for site in sites:
            site.rloops = [lp for lp in site.loops if lp.row]
            site.cloops = [lp for lp in site.loops if not lp.row]
        for site in sites:
            if site.kind == "literal" or len(site.cloops) == 0:
                continue
            # the variables of the loops of the body other than the row
            # loops around the site
            forbidden = loopvar_keys - {cls._loop_key(lp) for lp in site.rloops}
            found = cls._store(site.element, forbidden, vardict)
            if found is None:
                return None, "assignment code"
            store, type_code, prepare_code = found
            mapping = []
            for idx, expr in zip(store.indices, store.index_exprs):
                loop = next((lp for lp in site.cloops if lp.variable == idx), None)
                if loop is None and cls._depends(expr, forbidden, vardict):
                    return None, "index expression"
                mapping.append(loop)
            if (
                store.kind == "list"
                and len(site.cloops) > 1
                and mapping[0] is site.cloops[-1]
            ):
                # a list in the innermost of several copy loops (not
                # reached: the outer loops are row loops)
                return None, "rows"
            mapped = [lp for lp in mapping if lp is not None]
            if len(set(map(id, mapped))) != len(mapped) or len(mapped) != len(
                site.cloops
            ):
                return None, "indices"
            site.copy = (
                store.kind,
                store.container,
                store.indices,
                mapping,
                type_code,
                prepare_code,
            )
        for loop in loops:
            if any(not a.row for a in loop.ancestors) and loop.setup != "":
                return None, "setup code of an inner loop"
        return items, None

    # --- the code -----------------------------------------------------

    @staticmethod
    def _at(site, pos):
        # the code of the element with the value at the position pos of
        # the buffer (the value cpp_i of the decoded body)
        code = cpp.statement(f"const int cpp_i = static_cast<int>({pos})")
        return cpp.block(code + site.code)

    @staticmethod
    def _offset(const, terms):
        parts = [str(const)] if const != 0 or len(terms) == 0 else []
        return " + ".join(parts + terms)

    @staticmethod
    def _row_header(loop, q):
        # the variable of a row loop under its name in the per-field form,
        # and its read flag, for the iteration cpp_r{q}
        code = cpp.statement(
            f"int {loop.variable} = cpp_la{q} + static_cast<int>(cpp_r{q})"
        )
        return code + loop.readflag

    @staticmethod
    def _row_for(q, body):
        return cpp.forloop(
            f"long long cpp_r{q} = 0", f"cpp_r{q} < cpp_ln{q}", f"cpp_r{q}++", body
        )

    @classmethod
    def _sizes_code(cls, items, names):
        # the code computing the start, count, size of an iteration and
        # offset (in its container) of each loop; the offset of each site
        # in its container; returns the code and the size of the container.
        # For a row loop: its start, count, number of values (cpp_lt, the
        # sum over its iterations, which are bounded by NPL) and offset;
        # the code and the size of an iteration are kept for the delivery
        code = ""
        const, terms = 0, []
        for item in items:
            if isinstance(item, _BulkSite):
                item.offset = cls._offset(const, terms)
                const += 1
                continue
            q = names[id(item)]
            start, stop = item.bounds
            code += cpp.statement(f"cpp_la{q} = {start}")
            code += cpp.statement(f"cpp_ln{q} = cpp_list_loop_count(cpp_la{q}, {stop})")
            inner_code, inner_size = cls._sizes_code(item.items, names)
            if item.row:
                fallback = cpp.statement("throw cpp_list_bulk_fallback()")
                code += cpp.pureif(f"cpp_ln{q} > cpp_npl", fallback)
                code += cpp.statement(f"cpp_lt{q} = 0")
                body = cls._row_header(item, q) + inner_code
                body += cpp.statement(f"cpp_lt{q} += {inner_size}")
                body += cpp.pureif(f"cpp_lt{q} > cpp_npl", fallback)
                code += cls._row_for(q, body)
                code += cpp.statement(f"cpp_lo{q} = {cls._offset(const, terms)}")
                terms.append(f"cpp_lt{q}")
                item.inner_code, item.inner_size = inner_code, inner_size
                continue
            code += inner_code
            code += cpp.statement(f"cpp_lz{q} = {inner_size}")
            code += cpp.statement(f"cpp_lo{q} = {cls._offset(const, terms)}")
            terms.append(f"cpp_list_size(cpp_ln{q}, cpp_lz{q})")
        return code, cls._offset(const, terms)

    @staticmethod
    def _base(site, names, base=None):
        # the position of the first value of a site in the buffer (base:
        # the start of the iteration of the innermost row loop around it)
        parts = [] if base is None else [base]
        return " + ".join(
            parts
            + [f"cpp_lo{names[id(lp)]}" for lp in site.cloops]
            + [f"({site.offset})"]
        )

    @classmethod
    def _check_code(cls, site, names, base=None):
        # the check of the values of a literal in copy loops, as by the
        # per-field form, for all its positions
        pos = cls._base(site, names, base)
        for k, loop in enumerate(site.cloops):
            pos += f" + cpp_k{k} * cpp_lz{names[id(loop)]}"
        code = cls._at(site, pos)
        for k in reversed(range(len(site.cloops))):
            q = names[id(site.cloops[k])]
            code = cpp.forloop(
                f"long long cpp_k{k} = 0", f"cpp_k{k} < cpp_ln{q}", f"cpp_k{k}++", code
            )
        return code

    @classmethod
    def _copy_code(cls, site, names, base=None):
        kind, obj, indices, mapping, type_code, prepare_code = site.copy
        pos = cls._base(site, names, base)
        code = prepare_code
        if kind == "list":
            q = names[id(mapping[0])]
            copy = (
                f"{obj}set_strided(cpp_la{q}, cpp_body.values() + {pos}, "
                f"cpp_lz{q}, cpp_ln{q})"
            )
            code += cpp.pureif(
                f"! {copy}", cpp.statement("throw cpp_list_bulk_fallback()")
            )
        else:
            first = [
                idx if lp is None else f"cpp_la{names[id(lp)]}"
                for idx, lp in zip(indices, mapping)
            ]
            position = {id(lp): d for d, lp in enumerate(mapping) if lp is not None}
            counts = [f"cpp_ln{names[id(lp)]}" for lp in site.cloops]
            dst = [f"{obj}.block_stride({position[id(lp)]})" for lp in site.cloops]
            src = [f"cpp_lz{names[id(lp)]}" for lp in site.cloops]
            n = len(site.cloops)
            inner = cpp.statement(
                f"const long long cpp_count[{n}] = {{{', '.join(counts)}}}"
            )
            inner += cpp.statement(
                f"const long long cpp_dst_step[{n}] = {{{', '.join(dst)}}}"
            )
            inner += cpp.statement(
                f"const long long cpp_src_step[{n}] = {{{', '.join(src)}}}"
            )
            inner += cpp.statement(
                f"cpp_copy_strided(&{obj}({', '.join(first)}), "
                f"cpp_body.values() + {pos}, {n}, cpp_count, cpp_dst_step, "
                "cpp_src_step)"
            )
            code += cpp.block(inner)
        code += type_code
        if len(site.cloops) == 0:
            return code
        guard = cpp.logical_and([f"cpp_ln{names[id(lp)]} > 0" for lp in site.cloops])
        return cpp.pureif(guard, code)

    @classmethod
    def _delivery_code(cls, items, names, base=None):
        # the delivery in the order of the body: the sites outside of copy
        # loops by the code of the per-field form, then for each loop its
        # setup code, as in the per-field form, and the copies of its
        # sites; a row loop is iterated (see _row_code)
        code = ""
        for item in items:
            if isinstance(item, _BulkSite):
                pos = item.offset if base is None else f"{base} + ({item.offset})"
                code += cls._at(item, pos)
                continue
            code += item.setup
            if item.row:
                code += cls._row_code(item, names, base, deliver=True)
            else:
                code += cls._loop_copies(item, names, base)
        return code

    @classmethod
    def _row_code(cls, loop, names, base, deliver):
        # the iterations of a row loop, each with the variable of the loop
        # and the numbers of values of its loops computed again (as in the
        # pre-pass), then the delivery (or the checks of the literals) of
        # its items from the start of the iteration (cpp_rb)
        q = names[id(loop)]
        start = f"cpp_lo{q}" if base is None else f"{base} + cpp_lo{q}"
        code = cpp.statement(f"cpp_rb{q} = {start}")
        body = cls._row_header(loop, q) + loop.inner_code
        if deliver:
            body += cls._delivery_code(loop.items, names, f"cpp_rb{q}")
        else:
            body += cls._check_walk(loop.items, names, f"cpp_rb{q}")
        body += cpp.statement(f"cpp_rb{q} += {loop.inner_size}")
        code += cls._row_for(q, body)
        if deliver:
            code += cpp.statement(f"cpp_rows += cpp_ln{q}")
        return code

    @classmethod
    def _loop_copies(cls, loop, names, base=None):
        code = ""
        for item in loop.items:
            if isinstance(item, _BulkLoop):
                code += cls._loop_copies(item, names, base)
            elif item.kind == "assign":
                code += cls._copy_code(item, names, base)
        return code

    @classmethod
    def _check_walk(cls, items, names, base=None):
        # the checks of the literals in loops, before the delivery: in copy
        # loops for all positions, in row loops per iteration
        code = ""
        for item in items:
            if isinstance(item, _BulkSite):
                if base is not None and item.kind == "literal":
                    code += cls._at(item, f"{base} + ({item.offset})")
                continue
            if item.row:
                if any(site.kind == "literal" for site in cls._sites(item.items)):
                    code += cls._row_code(item, names, base, deliver=False)
                continue
            for site in cls._sites(item.items):
                if site.kind == "literal":
                    code += cls._check_code(site, names, base)
        return code

    @classmethod
    def _strided_code(cls, items):
        loops = []

        def collect(its):
            for it in its:
                if isinstance(it, _BulkLoop):
                    loops.append(it)
                    collect(it.items)

        collect(items)
        names = {id(lp): q for q, lp in enumerate(loops)}
        rows = [lp for lp in loops if lp.row]
        if len(rows) == 0:
            code = cpp.comment("LIST body: strided copies from the buffer")
        else:
            code = cpp.comment("LIST body: strided copies from the buffer, per row")
        decls = []
        for q in range(len(loops)):
            decls += [f"cpp_ln{q} = 0", f"cpp_lz{q} = 0", f"cpp_lo{q} = 0"]
        for lp in rows:
            q = names[id(lp)]
            decls += [f"cpp_lt{q} = 0", f"cpp_rb{q} = 0"]
        if len(rows) > 0:
            decls.append("cpp_rows = 0")
        code += cpp.statement(
            "int " + ", ".join(f"cpp_la{q} = 0" for q in names.values())
        )
        code += cpp.statement("long long " + ", ".join(decls))
        code += cpp.statement("bool cpp_strided = cpp_body.complete()")
        sizes_code, total = cls._sizes_code(items, names)
        checks = cls._check_walk(items, names)
        prepass = sizes_code
        prepass += cpp.pureif(
            f"cpp_npl != {total}", cpp.statement("throw cpp_list_bulk_fallback()")
        )
        prepass += checks
        catch = cpp.statement("cpp_strided = false")
        # the bounds, the number of values and the checks first, then the
        # delivery, which only changes the variables
        code += cpp.pureif("cpp_strided", cpp.trycatch(prepass, "...", catch))
        delivery = cls._delivery_code(items, names)
        delivery += cpp.statement("cpp_list_bulk_counter().strided++")
        if len(rows) > 0:
            delivery += cpp.statement("cpp_list_bulk_counter().row_bodies++")
            delivery += cpp.statement("cpp_list_bulk_counter().row_values += cpp_npl")
            delivery += cpp.statement("cpp_list_bulk_counter().row_rows += cpp_rows")
        code += cpp.pureif("cpp_strided", cpp.trycatch(delivery, "...", catch))
        return code

    @staticmethod
    def _sites(items):
        for it in items:
            if isinstance(it, _BulkSite):
                yield it
            else:
                yield from ListBulkForm._sites(it.items)

    @classmethod
    def plan(cls, bulk, body_node, vardict):
        """The plan of the strided delivery (see :meth:`_strided_plan`) of
        the body generated in the bulk pass ``bulk``, as ``(plan,
        reason)``."""
        return cls._strided_plan(body_node, bulk, vardict)

    @classmethod
    def select_form(cls, code, npl_val, bulk, body_node, vardict):
        """Return the code that reads the body of a LIST record in the form
        chosen at runtime, from the code ``code`` of the per-field form,
        the bulk pass ``bulk`` (see :meth:`generate`) and the value
        ``npl_val`` of NPL. Only the per-field form is returned if the body
        reads no float value."""
        if bulk.fields == 0 or bulk.line_args is None:
            return code
        linevar, mat, mf, mt, parse_opts = bulk.line_args
        args = f"{linevar}, cont, cpp_npl, {mat}, {mf}, {mt}, {parse_opts}"
        bulk_code = cpp.statement(f"int cpp_npl = {npl_val}")
        bulk_code += cpp.statement("int cpp_i = 0")
        bulk_code += cpp.statement("int cpp_j = 0")
        bulk_code += cpp.statement(f"CppListBody cpp_body({args})")
        plan, reason = cls.plan(bulk, body_node, vardict)
        looped = cpp.statement("cpp_list_bulk_counter().looped++")
        looped += cpp.pureif("cpp_npl > 0", bulk.first_line)
        looped += bulk.body_code
        looped += cpp.pureif(
            "cpp_i != cpp_npl",
            cpp.statement(
                'throw std::runtime_error("not exactly NPL elements consumed")'
            ),
        )
        reposition = cpp.statement(
            f"cpp_body.reposition(cpp_i, {linevar}, cont, {mat}, {mf}, {mt}, "
            + f"{parse_opts})"
        )
        reposition += cpp.statement("throw")
        looped = cpp.trycatch(looped, "...", reposition)
        if plan is not None:
            bulk_code += cls._strided_code(plan)
            bulk_code += cpp.pureif("! cpp_strided", looped)
        else:
            bulk_code += cpp.comment(
                f"LIST body: code of the per-field form ({reason})"
            )
            bulk_code += looped
        return cpp.ifelse(cls.condition(plan is not None), code, cpp.block(bulk_code))


class ListBodyRecorder:

    @staticmethod
    def _bulk_form(vardict):
        # the bulk form, if registered for the mode, except in a lookahead
        if in_lookahead(vardict):
            return None
        return get_list_bulk_form(vardict)

    @staticmethod
    def recorder(vardict):
        """The recorder of the bulk pass (see :class:`ListBulkRecorder`),
        to which the elements of the body are reported, or None outside of
        the bulk pass."""
        return get_list_bulk_recorder(vardict)

    @staticmethod
    def generate_bulk_form(list_body_node, vardict, generate_body):
        # the bulk pass of the body (see ListBulkForm.generate), if the mode
        # has a bulk form, only for a body with a loop (otherwise it reads
        # a fixed number of values, usually only a few); None otherwise
        bulk_form = ListBodyRecorder._bulk_form(vardict)
        if bulk_form is None:
            return None
        if not any(get_name(c) == "list_loop" for c in list_body_node.children):
            return None
        return bulk_form.generate(list_body_node, vardict, generate_body)

    @staticmethod
    def start_list_body_loop(npl_val, vardict):
        code = cpp.open_block()
        code += cpp.statement(f"int cpp_npl = {npl_val}", cpp.INDENT)
        code += cpp.statement("int cpp_i = 0", cpp.INDENT)
        code += cpp.statement("int cpp_j = 0", cpp.INDENT)
        # only read the first body line if the LIST is non-empty; an
        # NPL=0 LIST occupies its header line only, and an unconditional
        # read would consume the following record (e.g. the SEND)
        code += cpp.indent_code(
            cpp.pureif("cpp_npl > 0", get_prepare_line_func(vardict)(vardict)),
            cpp.INDENT,
        )
        return code

    @staticmethod
    def finish_list_body_loop(vardict):
        code = cpp.indent_code(
            cpp.pureif(
                "cpp_i != cpp_npl",
                cpp.statement(
                    'throw std::runtime_error("not exactly NPL elements consumed")'
                ),
            ),
            cpp.INDENT,
        )
        # as the first body line, the last one only exists if the LIST is
        # non-empty; finalizing it unconditionally would write the header
        # line of an NPL=0 LIST a second time
        finalize_code = get_finalize_line_func(vardict)(vardict)
        if finalize_code:
            code += cpp.indent_code(
                cpp.pureif("cpp_npl > 0", finalize_code), cpp.INDENT
            )
        code += cpp.close_block()
        return code

    @staticmethod
    def select_form(code, bulk, list_body_node, vardict, npl_val):
        # the code of the loop reading the body, from start_list_body_loop
        # to finish_list_body_loop, in the forms of the mode (bulk: the
        # bulk pass, see generate_bulk_form)
        if bulk is None:
            return code
        bulk_form = ListBodyRecorder._bulk_form(vardict)
        return bulk_form.select_form(code, npl_val, bulk, list_body_node, vardict)

    @staticmethod
    def get_element(node, vardict):
        # an element after the NPL elements of the body is an error, raised
        # before the field is accessed: the line of the NPL-th element is
        # the last line of the body and the field may lie beyond the six
        # fields of the line (cpp_j > 5), i.e. beyond the line
        code = cpp.pureif(
            "cpp_i >= cpp_npl", cpp.statement("cpp_throw_list_body_overrun(cpp_npl)")
        )
        valcode, addcode = get_numeric_field_getter(vardict)(
            node, "cpp_j", float, vardict
        )
        return valcode, code + addcode

    @staticmethod
    def update_counters_and_line(vardict):
        code = cpp.statement("cpp_i++")
        code += cpp.statement("cpp_j++")
        code += cpp.pureif(
            cpp.logical_and(["cpp_j > 5", "cpp_i < cpp_npl"]),
            cpp.concat(
                [
                    get_finalize_line_func(vardict)(vardict),
                    get_prepare_line_func(vardict)(vardict),
                    cpp.statement("cpp_j = 0"),
                ]
            ),
        )
        return code

    @staticmethod
    def indent(code):
        return cpp.indent_code(code, cpp.INDENT)
