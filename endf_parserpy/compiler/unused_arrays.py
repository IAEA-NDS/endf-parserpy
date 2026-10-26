############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Array variables whose values the writing code does not need to store.

When writing, the value of each field is retrieved from the dictionary and
assigned to the C++ variables in the field. For a variable with indices,
the assignment stores the value in a NestedArray, with the bookkeeping of
the type of the variable (``validate_vartype_consistency``). These stores
are only needed if the value is used later: in an expression of another
field, an if-condition, a loop bound, an index or a counter. The function
:func:`find_unused_arrays` determines the variables of a recipe for which
omitting the stores provably changes neither the output nor the errors:

- every occurrence of the name in the recipe (with any number of indices,
  anywhere, also in abbreviations and indices) is the whole expression of
  a field of a HEAD, CONT, LIST, TAB1 or TAB2 record (except the sizes NR
  and NP of the tables) or an element of a LIST record, so that the
  stored value is never read;
- the indices of each occurrence are the variables of the enclosing loops
  in the same order (the last index that of the innermost loop), with no
  if-clause between these loops nor between the innermost loop and the
  field, and no further loop around them up to the section (or the named
  LIST record) of the variable, so that each element is stored at most
  once and in the order of the elements, which is the condition under
  which a store into a NestedArray (and the preparation of its elements
  and blocks) cannot fail;
- with several occurrences, they are in the same section, of the same
  type (float or integer field) and with the same number of indices, and
  in different branches of if-clauses, so that at most one of them is
  executed and the type check cannot fail either;
- the name is not MAT, MF or MT, which the writing code assigns apart
  from the recipe.

In addition, the code generator omits the stores of an occurrence only
if the elements of the leading indices are prepared once in each
iteration of the loop of the index (see ``_prepared_per_iteration`` in
``cpp_types/cpp_type_nested_array/assign.py``). The registration of the
elements with the index bookkeeping of the writer (``register_element``),
which determines the positions of the elements in lists, is not affected.
"""

from endf_parserpy.recipe_parser.tree import Token
from endf_parserpy.utils.tree_utils import get_child
from .expr_utils.custom_nodes import VariableToken
from .node_checks import is_loop, is_if_clause, is_section, is_list
from .node_aux import get_loopvar


# fields of the tables of TAB1 and TAB2 records that are their sizes
_TABLE_SIZE_FIELDS = {"tab1_fields": (4, 5), "tab2_fields": (4,)}


def _field_dtype(expr_node):
    # float or int for a field (or LIST element) whose value is assigned
    # to the variables in it, None for any other expression
    parent = expr_node.parent
    if parent is None:
        return None
    if parent.data == "list_body":
        return float
    if parent.data != "record_fields":
        return None
    exprs = [c for c in parent.children if not isinstance(c, Token)]
    pos = next(i for i, c in enumerate(exprs) if c is expr_node)
    record = parent.parent
    if record.data in _TABLE_SIZE_FIELDS:
        if pos in _TABLE_SIZE_FIELDS[record.data]:
            return None
    elif record.data not in ("head_or_cont_line", "list_line"):
        return None
    return float if pos < 2 else int


def _add_tokens(node, occurrences):
    # occurrences of variable names in node that are not whole fields
    if isinstance(node, VariableToken):
        occurrences.setdefault(str(node), []).append(None)
        for idx in node.indices:
            _add_tokens(idx, occurrences)
    elif isinstance(node, Token):
        if node.type in ("VARNAME", "VARIABLE"):
            occurrences.setdefault(str(node), []).append(None)
    else:
        for child in node.children:
            _add_tokens(child, occurrences)


def _collect(node, occurrences):
    if isinstance(node, Token):
        _add_tokens(node, occurrences)
        return
    if node.data == "expr":
        child = node.children[0] if len(node.children) == 1 else None
        if (
            isinstance(child, VariableToken)
            and len(child.indices) > 0
            and not child.inconsistent
            and _field_dtype(node) is not None
        ):
            occurrences.setdefault(str(child), []).append((child, node))
            for idx in child.indices:
                _add_tokens(idx, occurrences)
            return
        _add_tokens(node, occurrences)
        return
    for child in node.children:
        _collect(child, occurrences)


def _site_info(vartok, expr_node):
    # the root node of the scope of the field and the outermost loop of
    # its indices (or the field), or None if not as required
    names = []
    for idx in vartok.indices:
        if not isinstance(idx, VariableToken) or len(idx.indices) > 0:
            return None
        names.append(str(idx))
    loops = []
    after_if = False
    node = expr_node
    while True:
        parent = node.parent
        if parent is None or is_section(parent):
            scope = parent if parent is not None else node
            break
        if is_list(parent) and node.data == "list_body":
            if get_child(parent, "list_name", nofail=True) is not None:
                scope = parent
                break
        if is_loop(parent):
            if after_if or len(loops) == len(names):
                return None
            loops.append(parent)
        elif is_if_clause(parent):
            if len(loops) < len(names):
                return None
            after_if = True
        node = parent
    if len(loops) != len(names):
        return None
    for loop, name in zip(loops, reversed(names)):
        if loop.data == "repeat_loop":
            if get_child(loop.children[0], "repeat_varassign", nofail=True) is None:
                return None
        if str(get_loopvar(loop)) != name:
            return None
    return scope, loops[-1]


def _ancestors(node):
    ret = []
    while node is not None:
        ret.append(node)
        node = node.parent
    return ret


def _exclusive(node1, node2):
    # whether the nodes are in different branches of an if-clause
    anc1 = _ancestors(node1)
    anc2 = _ancestors(node2)
    ids2 = {id(n): i for i, n in enumerate(anc2)}
    for i, n in enumerate(anc1):
        if id(n) in ids2:
            j = ids2[id(n)]
            return (
                is_if_clause(n) and i > 0 and j > 0 and anc1[i - 1] is not anc2[j - 1]
            )
    return False


def find_unused_arrays(tree):
    """Names of the variables whose stores can be omitted when writing.

    ``tree`` is the parse tree of a recipe as used by the code generator
    (with ``ParseNode`` nodes and simplified expressions).
    """
    occurrences = {}
    _collect(tree, occurrences)
    ret = set()
    for name, occs in occurrences.items():
        if name in ("MAT", "MF", "MT") or any(occ is None for occ in occs):
            continue
        sites = []
        for vartok, expr_node in occs:
            info = _site_info(vartok, expr_node)
            if info is None:
                break
            sites.append((len(vartok.indices), _field_dtype(expr_node)) + info)
        else:
            if len({(s[0], s[1], id(s[2])) for s in sites}) != 1:
                continue
            if all(
                _exclusive(s[3], t[3]) for k, s in enumerate(sites) for t in sites[:k]
            ):
                ret.add(name)
    return ret


class UnstoredAssignment(str):
    """Code of an assignment to an unused array without the store (see
    ``assign_exprstr_to_var`` of the NestedArray type), which needs no
    bookkeeping of the type of the variable either."""
