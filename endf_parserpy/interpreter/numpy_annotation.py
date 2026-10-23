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
``_np_blocks`` (loop nodes)
    A tuple of ``(varname, indexspecs, loops, kind)``: the C++ code
    creates the regular block of the trailing indices of ``varname``
    with the leading indices ``indexspecs`` each time it reaches the
    loop, the outermost loop of the block; ``loops`` are the loops of
    the indices of the block, whose limits give its shape (see
    :meth:`_Walker.find_block`).

A kind is a tuple ``(container, dtype, num_indices, block_rank)`` with
``container`` one of ``"Scalar"`` and ``"NestedArray"``, ``dtype`` one
of ``"float"``, ``"int"``, ``"str"``, ``"floatvec"`` (TAB1 columns) and
``"intvec"`` (TAB1/TAB2 interpolation tables, integers of INTG
records), and ``block_rank`` the number of trailing indices that form a
regular block, i.e. a numpy array with as many dimensions, or 0.

The rules replicate those of the code generator for parsing
(``endf_parserpy.compiler``): which variables of a field are assigned
(``generate_code_for_varassign``, ``generate_code_from_record_fields``),
the data type of each field, the rule for regular blocks of trailing
indices (``find_block`` in ``cpp_type_nested_array/assign.py``) and the
placement of the preparation of nested arrays (``moveup_ptrassign`` in
``cpp_type_nested_array``). The test ``tests/test_numpy_annotation.py``
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
        self.blocks = []

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

    def index_specs(self, indexquants, scope):
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
        return tuple(specs)

    def prepare(self, loop, varname, indexquants, kind, scope):
        specs = self.index_specs(indexquants, scope)
        entry = (varname, specs, kind)
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
        if var.nidx == 0:
            kind = ("Scalar", dtype, 0, 0)
            block = None
        else:
            block = None if expr is None else self.find_block(var, expr, scope)
            rank = 0 if block is None else len(block[0])
            kind = ("NestedArray", dtype, var.nidx, rank)
        scope.vars.setdefault(key, False)
        self.mark(anchor, var.name, kind)
        self.assignments.append((var, expr, kind, anchor, scope.path()))
        if expr is None:
            return
        num_leading = var.nidx - kind[3] if block else var.nidx - 1
        dests = self.prepare_dests(var, expr, num_leading)
        indexquants = var.indexquants()
        for i, dest in enumerate(dests):
            if dest is not expr:
                self.prepare(dest, var.name, indexquants[: i + 1], kind, scope)
                self.preparations.append((var, i, dest, expr))
        if block:
            self.add_block(var, expr, kind, block, scope)

    def prepare_dests(self, var, expr, num_levels):
        # where the elements of the first num_levels levels of a nested
        # array are created, see moveup_ptrassign in the code generator
        dests = []
        limit = None
        indexquants = var.indexquants()
        for i in range(num_levels):
            limit = self.moveup(var, indexquants[i].children[0], expr, limit)
            dests.append(limit)
        return dests

    def add_block(self, var, expr, kind, block, scope):
        # the regular block of the trailing indices is created before
        # its outermost loop, see the regularity rule in find_block
        block, outer = block
        num_leading = var.nidx - len(block)
        specs = self.index_specs(var.indexquants()[:num_leading], scope)
        entry = (var.name, specs, block, kind)
        blocks = getattr(outer, "_np_blocks", ())
        if not any(b[0] == var.name for b in blocks):
            outer._np_blocks = blocks + (entry,)
        self.blocks.append((var, num_leading, outer, expr))

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

    def find_block(self, var, expr, scope):
        """Loops of the largest regular block of trailing indices.

        Returns the loops of the trailing indices ``i_{k+1}, ..., i_n``
        of ``var`` (in the order of the indices) that form a regular
        block, i.e. a rectangular array whose shape is known before its
        outermost loop starts, together with the outermost loop, or
        ``None`` if there is no such block with at least two indices.
        The block has the largest number of indices for which:

        1. the variable is assigned here for the first time, and the
           trailing indices are the bare loop variables of the innermost
           enclosing ``for`` or LIST loops, one index per loop in any
           order, without an if-statement or a section in between;
        2. the leading indices do not depend on the loop variables of
           the block;
        3. the variable does not occur elsewhere in its scope (the
           enclosing section or named LIST record, or the recipe),
           except in branches of if-statements that exclude the branch
           of the assignment, so that no other code writes to the block;
        4. each loop enclosing the outermost loop of the block (in the
           scope of the variable) has a leading index that is its bare
           loop variable, so that each block is created only once;
        5. the limits of the loops of the block do not depend on the
           loop variables of the block, and the other variables in them
           are loop variables of enclosing loops, do not occur in the
           outermost loop of the block (except in loop heads), or are
           scalars read from a field of a record each time before the
           outermost loop that occur in it only in expressions (their
           fields in the loop are then only checked);
        6. with leading indices, the element of the last leading index
           is created before the outermost loop of the block (by the
           rule for the creation of elements of nested arrays).
        """
        if var.nidx < 2 or scope.find(var.key) is not None:
            return None
        idxexprs = [q.children[0] for q in var.indexquants()]
        names = [_bare_varname(e) for e in idxexprs]
        loops = []
        cur = self.parent(expr)
        while cur is not None and len(loops) < var.nidx:
            if cur.data in ("if_clause", "section", "repeat_loop"):
                break
            if cur.data in ("for_loop", "list_loop"):
                loops.append(cur)
            cur = self.parent(cur)
        for rank in range(len(loops), 1, -1):
            # the loops of the trailing indices, in the order of the indices
            byvar = {_loopvar(loop): loop for loop in loops[:rank]}
            trailing = names[-rank:]
            if None in trailing or set(trailing) != set(byvar):
                continue
            block = tuple(byvar[name] for name in trailing)
            if self.is_block(var, expr, idxexprs, block, loops[rank - 1], scope):
                return block, loops[rank - 1]
        return None

    def occurs_elsewhere(self, key, expr):
        # see condition 3 of find_block
        branches = {}
        scope = expr
        while self.parent(scope) is not None and not _is_scope_node(scope):
            parent = self.parent(scope)
            if parent.data == "if_clause":
                branches[id(parent)] = id(scope)
            scope = parent
        return _occurs_in(scope, key, expr, branches)

    def is_read_before(self, name, loop):
        # whether a field with the variable is read each time before the
        # loop (see condition 5 of find_block)
        cur = loop
        while self.parent(cur) is not None:
            parent = self.parent(cur)
            if parent.data in _SEQUENCE_NODES:
                for child in parent.children:
                    if child is cur:
                        break
                    if _in_field(child, name):
                        return True
            cur = parent
        return False

    def is_checked_only(self, key, loop):
        # a scalar variable read from a field each time before the loop and
        # occurring in the loop only in expressions is only checked there
        return (
            key[1] == 0
            and self.is_read_before(key[0], loop)
            and _only_in_expressions(loop, key[0])
        )

    def is_block(self, var, expr, idxexprs, block, outer, scope):
        num_leading = var.nidx - len(block)
        loopvars = {(_loopvar(loop), 0) for loop in block}
        if any(_all_vars(e) & loopvars for e in idxexprs[:num_leading]):
            return False
        if self.occurs_elsewhere(var.key, expr):
            return False
        leading = {_bare_varname(e) for e in idxexprs[:num_leading]}
        cur = self.parent(outer)
        while cur is not None and not _is_scope_node(cur):
            if cur.data in LOOP_NODES and _loopvar(cur) not in leading:
                return False
            cur = self.parent(cur)
        for loop in block:
            for lim in _loop_limits(loop):
                for key in _all_vars(lim):
                    if key in loopvars:
                        return False
                    if key[1] == 0 and scope.abbrevs and key[0] in scope.abbrevs:
                        return False
                    if scope.is_loopvar(key):
                        continue
                    if not contains_var(outer, key[0], skip_loop_heads=True):
                        continue
                    if not self.is_checked_only(key, outer):
                        return False
        if num_leading > 0:
            dests = self.prepare_dests(var, expr, num_leading)
            if dests[-1] is not outer:
                return False
        return True


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


def _in_field(node, name):
    # whether the variable is in a field of a record reached from node
    # without passing a loop, an if-clause or a section, so that the
    # field is read each time node is executed
    if isinstance(node, Token):
        return False
    if node.data == "expr":
        return contains_var(node, name)
    if node.data == "list_line":
        # the fields in the body of a named LIST record are variables of
        # its own scope
        named = _child(node, "list_name", nofail=True) is not None
        return any(
            _in_field(c, name)
            for c in node.children
            if isinstance(c, Tree)
            and (c.data == "record_fields" or (c.data == "list_body" and not named))
        )
    if node.data in _TABLE_FIELDS:
        # the fields NR and NP of a TAB1 record and NR of a TAB2 record
        # are the sizes of its tables, not assignments of variables
        exprs = [
            c
            for c in _child(node, "record_fields").children
            if isinstance(c, Tree) and c.data == "expr"
        ]
        skip = _TABLE_FIELDS[node.data]
        return any(_in_field(e, name) for i, e in enumerate(exprs) if i not in skip)
    if node.data in _RECORD_PATH_NODES or node.data == "list_body":
        return any(_in_field(c, name) for c in node.children)
    return False


def _only_in_expressions(node, name, in_expr=False):
    # whether a token `name` occurs in node only in expressions
    if isinstance(node, Token):
        return in_expr or str(node) != name
    in_expr = in_expr or node.data == "expr"
    return all(_only_in_expressions(c, name, in_expr) for c in node.children)


def _is_scope_node(node):
    # sections and named LIST records have their own variables
    if node.data == "section":
        return True
    return (
        node.data == "list_line" and _child(node, "list_name", nofail=True) is not None
    )


def _occurs_in(node, key, site, branches):
    # whether the variable (name and number of indices) occurs in node
    # apart from the site, also in indices, skipping the branches of
    # if-clauses that exclude the branch of the site
    if node is site or isinstance(node, Token):
        return False
    if node.data == "extvarname" and Var(node).key == key:
        return True
    for child in node.children:
        if node.data == "if_clause" and branches.get(id(node), id(child)) != id(child):
            continue
        if _occurs_in(child, key, site, branches):
            return True
    return False


def _bare_varname(expr):
    # name of a variable without indices that is the whole expression
    node = _simplified(expr)
    if isinstance(node, Tree) and node.data == "extvarname":
        v = Var(node)
        if v.nidx == 0:
            return v.name
    return None


def _all_vars(node):
    # (name, nidx) of all variables in an expression, also in indices
    return {Var(n).key for n in node.iter_subtrees() if n.data == "extvarname"}


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
