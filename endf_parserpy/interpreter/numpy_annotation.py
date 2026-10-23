############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Container kinds of the variables of a recipe for ``array_type="numpy"``.

With ``array_type="numpy"``, the form of an array returned by
:class:`~endf_parserpy.EndfParserCpp` is determined by the C++ container
that the code generator chooses for the variable at the place in the
recipe where it is assigned. :func:`annotate_recipe_tree` determines the
same decisions by a walk over the parse tree of a recipe, without the
code generator, and annotates the nodes that the interpreter executes:

``_np_marks`` (record nodes, ``table_name`` and ``list_name`` nodes of
named TAB1, TAB2 and LIST records, ``list_loop`` nodes)
    A tuple of ``(varname, kind)`` pairs: the variables assigned by the
    record (outside named sections), in the body of the named record
    (outside LIST loops) and in the body of the LIST loop (outside inner
    LIST loops), respectively. The C++ code assigns these variables when
    the record is read, the named section is opened, and the loop body
    is executed at least once, respectively.
``_np_prepare`` (loop nodes)
    A tuple of ``(varname, indexspecs, kind)`` triples: the C++ code
    creates the (possibly empty) element of the nested array ``varname``
    given by the indices ``indexspecs`` each time it reaches the loop,
    also if the loop body is never executed (see ``moveup_ptrassign`` in
    the code generator). An index is given by the name of a loop
    variable or by its ``indexquant`` node.

A kind is a tuple ``(container, dtype, num_indices, is_triagonal,
is_lower)`` with ``container`` one of ``"Scalar"``, ``"NestedVector"`` and
``"Matrix2d"`` and ``dtype`` one of ``"float"``, ``"int"``, ``"str"``,
``"floatvec"`` (TAB1 columns) and ``"intvec"`` (TAB1/TAB2 interpolation
tables, integers of INTG records); the last two items are only
meaningful for ``"Matrix2d"``.

The rules replicate those of the code generator for parsing
(``endf_parserpy.compiler``): which variables of a field are assigned
(``generate_code_for_varassign``, ``generate_code_from_record_fields``),
the data type of each field, the proof that a variable with two indices
can be stored as matrix (``cpp_type_matrix2d/assign.py``) and the
placement of the preparation of nested arrays (``moveup_ptrassign`` in
``cpp_type_nested_vector``). The test ``tests/test_numpy_annotation.py``
compares the result with the decisions reported by the code generator
for all recipes of the package.
"""

from lark.tree import Tree
from lark.lexer import Token
from ..utils.tree_utils import get_child
from .custom_exceptions import RecipeAnnotationError


RECORD_NODES = (
    "head_or_cont_line",
    "text_line",
    "dir_line",
    "intg_line",
    "tab1_line",
    "tab2_line",
    "list_line",
)
LOOP_NODES = ("for_loop", "list_loop", "repeat_loop")
_LOOP_HEADS = {
    "for_loop": "for_head",
    "list_loop": "list_for_head",
    "repeat_loop": "repeat_head",
}
_LOOP_BODIES = {
    "for_loop": "for_body",
    "list_loop": "list_body",
    "repeat_loop": "repeat_body",
}
# nodes that are removed by the simplification of expressions in the code
# generator if they have a single child
_COLLAPSED_NODES = ("expr", "addpart", "mulpart", "bracketexpr")
_KEPT_TOKENS = ("VARNAME", "NUMBER", "DESIRED_NUMBER")


def _child(node, name, nofail=False):
    child = get_child(node, name, nofail=True)
    if child is None and not nofail:
        raise RecipeAnnotationError(f"no child {name} in {node.data}")
    return child


def _children(node, name):
    return [c for c in node.children if isinstance(c, Tree) and c.data == name]


# ---------------------------------------------------------------------
# variables in expressions
#
# The code generator converts every `expr` subtree into an expression
# tree in which each `extvarname` node is a single token (its index
# specifications are attributes, not children). Variables are therefore
# only visible inside `expr` subtrees, and the variables in the index
# specifications of a visible variable are not visible.
# ---------------------------------------------------------------------


class Var:
    """A variable occurrence: name, number of indices and its node."""

    __slots__ = ("name", "nidx", "node")

    def __init__(self, node):
        self.node = node
        name = None
        nidx = 0
        for c in node.children:
            if isinstance(c, Token) and c.type == "VARNAME":
                name = str(c)
            elif isinstance(c, Tree) and c.data == "indexquant":
                nidx += 1
        self.name = name
        self.nidx = nidx

    @property
    def key(self):
        return (self.name, self.nidx)

    def indexquants(self):
        return _children(self.node, "indexquant")


def visible_vars(node, in_expr=False):
    """Variables (extvarname nodes) visible in the converted tree."""
    if isinstance(node, Token):
        return
    if node.data == "extvarname" and in_expr:
        yield node
        return
    if node.data == "expr":
        in_expr = True
    for c in node.children:
        yield from visible_vars(c, in_expr)


def contains_var(node, name, skip_nodes=(), skip_loop_heads=False, in_expr=False):
    """Replicates contains_variable of the code generator."""
    if any(node is s for s in skip_nodes):
        return False
    if isinstance(node, Token):
        return False
    if skip_loop_heads and node.data in ("for_head", "list_for_head"):
        return False
    if node.data == "extvarname" and in_expr:
        return Var(node).name == name
    if node.data == "expr":
        in_expr = True
    return any(
        contains_var(c, name, skip_nodes, skip_loop_heads, in_expr)
        for c in node.children
    )


def _var_set(node):
    # set semantics of VariableToken: one entry per (name, nidx)
    ret = {}
    for n in visible_vars(node):
        v = Var(n)
        ret.setdefault(v.key, v)
    return ret


def _simplified(node):
    # the node remaining of an expression after the simplification
    while isinstance(node, Tree) and node.data in _COLLAPSED_NODES:
        kids = [
            c for c in node.children if isinstance(c, Tree) or c.type in _KEPT_TOKENS
        ]
        if len(kids) != 1:
            return node
        node = kids[0]
    return node


def _simple_index(indexquant):
    # a single variable without indices or a number
    node = _simplified(indexquant.children[0])
    if isinstance(node, Token):
        return node.type == "NUMBER"
    if node.data == "inconsistent_varspec":
        node = _child(node, "extvarname")
    return node.data == "extvarname" and Var(node).nidx == 0


def _loopvar(loop):
    head = _child(loop, _LOOP_HEADS[loop.data])
    if loop.data == "repeat_loop":
        head = _child(head, "repeat_varassign")
    return str(_child(head, "VARNAME"))


def _loop_body(loop):
    return _child(loop, _LOOP_BODIES[loop.data])


def _loop_limits(loop):
    head = _child(loop, _LOOP_HEADS[loop.data])
    if loop.data == "repeat_loop":
        return (_child(_child(head, "repeat_varassign"), "expr"), None)
    return (
        _child(_child(head, "for_start"), "expr"),
        _child(_child(head, "for_stop"), "expr"),
    )


def _vars_of(node):
    return {} if node is None else _var_set(node)


# ---------------------------------------------------------------------
# scopes of variables (vardict of the code generator)
# ---------------------------------------------------------------------


class _Scope:

    def __init__(self, parent=None, name=None):
        self.parent = parent
        # (section name, number of indices) of a section scope
        self.name = name
        # (name, nidx) -> True for loop variables
        self.vars = {}
        self.abbrevs = None

    def copy(self):
        s = _Scope(self.parent, self.name)
        s.vars = dict(self.vars)
        s.abbrevs = self.abbrevs
        return s

    def find(self, key):
        s = self
        while s is not None:
            if key in s.vars:
                return s
            s = s.parent
        return None

    def path(self):
        ret = []
        s = self
        while s is not None:
            if s.name is not None:
                ret.append(s.name)
            s = s.parent
        return tuple(reversed(ret))

    def is_loopvar(self, key):
        s = self.find(key)
        return s is not None and s.vars[key]


# ---------------------------------------------------------------------
# the walk over the recipe
# ---------------------------------------------------------------------


class _Walker:

    def __init__(self, root):
        self.parents = {id(root): None}
        self.assignments = []
        self.preparations = []

    def parent(self, node):
        return self.parents[id(node)]

    def register_parents(self, node):
        if isinstance(node, Tree):
            for c in node.children:
                self.parents[id(c)] = node
                self.register_parents(c)

    # --- annotation --------------------------------------------------

    def mark(self, anchor, varname, kind):
        marks = getattr(anchor, "_np_marks", ())
        entry = (varname, kind)
        if entry not in marks:
            anchor._np_marks = marks + (entry,)

    def prepare(self, loop, varname, indexquants, kind, scope):
        # an index given by a loop variable is represented by its name,
        # other indices by their indexquant node
        specs = []
        for q in indexquants:
            node = _simplified(q.children[0])
            if isinstance(node, Tree) and node.data == "extvarname":
                v = Var(node)
                if v.nidx == 0 and scope.is_loopvar(v.key):
                    specs.append(v.name)
                    continue
            specs.append(q)
        entry = (varname, tuple(specs), kind)
        preps = getattr(loop, "_np_prepare", ())
        if not any(
            p[0] == varname
            and len(p[1]) == len(entry[1])
            and all(a is b or a == b for a, b in zip(p[1], entry[1]))
            for p in preps
        ):
            loop._np_prepare = preps + (entry,)

    # --- program flow ------------------------------------------------

    def walk(self, node, scope, anchor=None):
        if isinstance(node, Token):
            return
        d = node.data
        if d in RECORD_NODES:
            self.record(node, scope)
        elif d == "section":
            head = _child(_child(node, "section_head"), "extvarname")
            sub = _Scope(scope, Var(head).key)
            self.walk_children(_child(node, "section_body"), sub)
        elif d in ("for_loop", "repeat_loop"):
            self.loop(node, scope, self.walk_children, anchor)
        elif d == "if_clause":
            self.if_clause(node, scope)
        elif d == "abbreviation":
            if scope.abbrevs is None:
                scope.abbrevs = {}
            scope.abbrevs[str(_child(node, "VARNAME"))] = _child(node, "expr")
        else:
            self.walk_children(node, scope, anchor)

    def walk_children(self, node, scope, anchor=None):
        for c in node.children:
            self.walk(c, scope, anchor)

    def loop(self, node, scope, body_fun, anchor):
        key = (_loopvar(node), 0)
        scope.vars[key] = True
        body_fun(_loop_body(node), scope, anchor)
        del scope.vars[key]

    def if_clause(self, node, scope):
        branches = []
        for c in node.children:
            if isinstance(c, Tree) and c.data in (
                "if_statement",
                "elif_statement",
                "else_statement",
            ):
                branch = scope.copy()
                self.walk_children(_child(c, "if_body"), branch)
                branches.append(branch)
        for branch in branches:
            for key, is_loopvar in branch.vars.items():
                scope.vars.setdefault(key, is_loopvar)

    # --- records -----------------------------------------------------

    def record(self, node, scope):
        d = node.data
        if d == "head_or_cont_line":
            self.record_fields(node, _child(node, "record_fields"), (), 0, scope)
        elif d == "dir_line":
            self.record_fields(node, _child(node, "dir_fields"), (0, 1), 2, scope)
        elif d == "text_line":
            for tph in _children(_child(node, "text_fields"), "textplaceholder"):
                ext = _child(tph, "extvarname", nofail=True)
                if ext is not None:
                    self.varassign(Var(ext), None, "str", scope, node)
        elif d == "intg_line":
            fields = _children(_child(node, "intg_fields"), "expr")
            self.varassign_expr(fields[0], "int", scope, node)
            self.varassign_expr(fields[1], "int", scope, node)
            self.varassign_expr(fields[2], "intvec", scope, node)
        elif d == "tab1_line":
            tab1_fields = _child(node, "tab1_fields")
            self.record_fields(
                node, _child(tab1_fields, "record_fields"), (4, 5), 0, scope
            )
            body_scope, anchor = self.named_scope(node, "table_name", scope)
            cols = _children(_child(tab1_fields, "tab1_def"), "extvarname")
            self.varassign(Var(cols[0]), None, "floatvec", body_scope, anchor)
            self.varassign(Var(cols[1]), None, "floatvec", body_scope, anchor)
            self.table_body(body_scope, anchor)
        elif d == "tab2_line":
            tab2_fields = _child(node, "tab2_fields")
            self.record_fields(
                node, _child(tab2_fields, "record_fields"), (4,), 0, scope
            )
            body_scope, anchor = self.named_scope(node, "table_name", scope)
            self.table_body(body_scope, anchor)
        elif d == "list_line":
            self.record_fields(node, _child(node, "record_fields"), (), 0, scope)
            body_scope, anchor = self.named_scope(node, "list_name", scope)
            self.list_body(_child(node, "list_body"), body_scope, anchor)

    def named_scope(self, node, name_node, scope):
        name = _child(node, name_node, nofail=True)
        if name is None:
            return scope, node
        return _Scope(scope, Var(_child(name, "extvarname")).key), name

    def table_body(self, scope, anchor):
        # INT and NBT are implicit variables of TAB1/TAB2 records
        for name in ("INT", "NBT"):
            v = Var(Tree("extvarname", [Token("VARNAME", name)]))
            self.varassign(v, None, "intvec", scope, anchor)

    def list_body(self, node, scope, anchor):
        for c in node.children:
            if isinstance(c, Token):
                continue
            if c.data == "expr":
                self.varassign_expr(c, "float", scope, anchor)
            elif c.data == "list_loop":
                self.loop(c, scope, self.list_body, c)

    def record_fields(self, record, fields_node, skip, ofs, scope):
        exprs = _children(fields_node, "expr")
        pending = list(enumerate(exprs))
        failures = 0
        while pending:
            idx, expr = pending.pop(0)
            idx += ofs
            if idx in skip:
                continue
            dtype = "float" if idx < 2 else "int"
            if not self.varassign_expr(expr, dtype, scope, record):
                # more than one unknown variable: try again later
                pending.append((idx - ofs, expr))
                failures += 1
                if failures > 10:
                    raise RecipeAnnotationError("several unknown variables")

    # --- assignments -------------------------------------------------

    def expand_abbreviations(self, scope, node):
        # variable occurrences of a field after the expansion of
        # abbreviations, which are only those of the current scope,
        # and whether the expression contains a modulo operation
        occurrences = []
        has_modulo = any(t.data == "modulo" for t in node.iter_subtrees())
        for n in visible_vars(node):
            v = Var(n)
            if v.nidx == 0 and scope.abbrevs and v.name in scope.abbrevs:
                occ, mod = self.expand_abbreviations(scope, scope.abbrevs[v.name])
                occurrences.extend(occ)
                has_modulo = has_modulo or mod
            else:
                occurrences.append(v)
        return occurrences, has_modulo

    def varassign_expr(self, expr, dtype, scope, anchor):
        occurrences, has_modulo = self.expand_abbreviations(scope, expr)
        variables = {}
        for v in occurrences:
            variables.setdefault(v.key, v)
        unknown = [k for k in variables if scope.find(k) is None]
        if len(unknown) > 1:
            return False
        # the code generator assigns each variable whose fellow variables
        # in the field are all known, in alphabetical order
        for key in sorted(variables, key=lambda k: k[0]):
            others = [k for k in variables if k != key]
            if any(scope.find(k) is None for k in others):
                continue
            num_occurrences = sum(v.name == key[0] for v in occurrences)
            if has_modulo or num_occurrences > 1:
                # the equation cannot be solved for the variable, the
                # generated code only checks the value (or fails)
                if not scope.is_loopvar(key):
                    scope.vars.setdefault(key, False)
                continue
            self.varassign(variables[key], expr, dtype, scope, anchor)
        return True

    def varassign(self, var, expr, dtype, scope, anchor):
        key = var.key
        if scope.is_loopvar(key):
            # loop variables are not assigned
            return
        kind = None
        if var.nidx == 2 and expr is not None:
            kind = self.matrix2d_kind(var, expr, dtype, scope)
        if kind is None:
            container = "Scalar" if var.nidx == 0 else "NestedVector"
            kind = (container, dtype, var.nidx, False, False)
        scope.vars.setdefault(key, False)
        self.mark(anchor, var.name, kind)
        self.assignments.append((var, expr, kind, anchor, scope.path()))
        if kind[0] == "NestedVector" and expr is not None:
            self.prepare_nested(var, expr, kind, scope)

    def prepare_nested(self, var, expr, kind, scope):
        # see moveup_ptrassign in cpp_type_nested_vector/auxiliary.py
        limit = None
        indexquants = var.indexquants()
        for i in range(var.nidx - 1):
            idxexpr = indexquants[i].children[0]
            dest = self.moveup(var, idxexpr, expr, limit)
            limit = dest
            if dest is not expr:
                self.prepare(dest, var.name, indexquants[: i + 1], kind, scope)
                self.preparations.append((var, i, dest, expr))

    def moveup(self, var, idxexpr, node, limit):
        checkpoint = node
        cur = node
        idxvars = _var_set(idxexpr)
        while self.parent(cur) is not None and cur is not limit:
            dest = self.parent(cur)
            if contains_var(dest, var.name, skip_nodes=(cur,)):
                break
            if any(
                contains_var(dest, v.name, skip_nodes=(cur,)) for v in idxvars.values()
            ):
                break
            if isinstance(dest, Tree) and dest.data in LOOP_NODES:
                if contains_var(idxexpr, _loopvar(dest)):
                    break
            cur = dest
            if cur.data in LOOP_NODES:
                checkpoint = cur
        return checkpoint

    def matrix2d_kind(self, var, expr, dtype, scope):
        # see Assign.assign_exprstr_to_var in cpp_type_matrix2d/assign.py
        indexquants = var.indexquants()
        if not all(_simple_index(q) for q in indexquants):
            return None
        # matrices are only defined by a single assignment
        if scope.find(var.key) is not None:
            return None
        idxexprs = [q.children[0] for q in indexquants]
        inner = outer = None
        cur = self.parent(expr)
        while cur is not None:
            if cur.data in LOOP_NODES:
                lv = _loopvar(cur)
                if any(contains_var(e, lv) for e in idxexprs):
                    if inner is None:
                        inner = cur
                    elif outer is None:
                        outer = cur
                        break
            cur = self.parent(cur)
        if cur is None:
            return None
        outer_body = _loop_body(outer)
        if contains_var(outer_body, var.name, skip_nodes=(expr,)):
            return None
        inner_body = _loop_body(inner)
        for e in idxexprs:
            for v in _var_set(e).values():
                if v.nidx > 0:
                    return None
                if contains_var(outer_body, v.name, skip_nodes=(inner,)):
                    return None
                if contains_var(inner_body, v.name, skip_nodes=(expr,)):
                    return None
        inner_lims = _loop_limits(inner)
        limit_vars = {}
        for lim in _loop_limits(outer) + inner_lims:
            limit_vars.update(_vars_of(lim))
        if any(
            contains_var(outer, v.name, skip_loop_heads=True)
            for v in limit_vars.values()
        ):
            return None
        # the limits of both loops must not contain arrays, and only one
        # loop may depend on the variable of the other (triangular matrix)
        is_triagonal = False
        is_lower = False
        num_depends = 0
        lims_and_keys = (
            (_loop_limits(outer), (_loopvar(inner), 0), True),
            (inner_lims, (_loopvar(outer), 0), False),
        )
        for lims, key, is_outer in lims_and_keys:
            depends = False
            for j, lim in enumerate(lims):
                vs = _vars_of(lim)
                if any(v.nidx > 0 for v in vs.values()):
                    return None
                if key in vs:
                    depends = True
                    is_triagonal = True
                    is_lower = (j == 0) if is_outer else (j != 0)
            num_depends += depends
        if num_depends > 1:
            return None
        return ("Matrix2d", dtype, 2, is_triagonal, is_lower)


def annotate_recipe_tree(tree):
    """Annotate the parse tree of a recipe for ``array_type="numpy"``.

    Returns the walker, whose attributes ``assignments`` and
    ``preparations`` list the assignments and the preparations of nested
    arrays found (used by the tests).
    """
    walker = _Walker(tree)
    walker.register_parents(tree)
    root_scope = _Scope()
    for name in ("MAT", "MF", "MT"):
        root_scope.vars[(name, 0)] = False
    walker.walk(tree, root_scope)
    return walker
