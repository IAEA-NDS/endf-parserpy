############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Fields of records that yield a vector of a length fixed before the record.

Most fields of an ENDF record hold a single number. A few fields yield a
vector of numbers, e.g. the columns of TAB1 records or the values ``KIJ``
of an INTG record. The length of such a vector is *fixed before the
record* if it is determined by expressions of the recipe that are
evaluated before the record is read, not by the data of the record
itself. This holds for INTG records, whose number of values is a fixed
function of ``NDIGIT``, but not for TAB1 and TAB2 records, whose number
of points ``NP`` is a field of the record.

With ``array_type="numpy"``, a vector field of this kind in the
innermost loop of a regular block of trailing indices adds an innermost
dimension to the block, as a loop over its values would, provided that
the expressions determining the length do not change within the block.
This module defines the property for both parsers: the C++ code
generator (``find_block`` in
``endf_parserpy.compiler.cpp_types.cpp_type_nested_array.assign``) and
the annotation of the recipes for :class:`~endf_parserpy.EndfParserPy`
(``endf_parserpy.interpreter.numpy_annotation``).
"""

from endf_parserpy.recipe_parser.tree import Tree
from .tree_utils import get_child


# number of correlation values KIJ per INTG record for each NDIGIT, from the
# formats 2I5,1X,18I3,1X / 2I5,1X,13I4,3X / 2I5,1X,11I5 / 2I5,1X,9I6,1X /
# 2I5,8I7 of ENDF-102 (Section 0.6.4.9)
INTG_NUM_VALUES = {2: 18, 3: 13, 4: 11, 5: 9, 6: 8}


def _exprs(node):
    return [c for c in node.children if isinstance(c, Tree) and c.data == "expr"]


def fixed_length_vector(record):
    """The vector field of a record whose length is fixed before the record.

    Parameters
    ----------
    record : Tree
        A node of the parse tree of a recipe.

    Returns
    -------
    tuple or None
        ``(field, length_arg)`` if ``record`` is a record with a field
        that yields a vector whose length is fixed before the record is
        read: ``field`` is the ``expr`` node of this field and
        ``length_arg`` the ``expr`` node of the expression that determines
        the length (see :func:`fixed_vector_length`). ``None`` for all
        other nodes, in particular TAB1 and TAB2 records.
    """
    if not isinstance(record, Tree) or record.data != "intg_line":
        return None
    field = _exprs(get_child(record, "intg_fields"))[2]
    length_arg = get_child(get_child(record, "ndigit_expr"), "expr")
    return field, length_arg


def fixed_length_vector_arg(site, parent):
    """The length expression of the vector field ``site``, or ``None``.

    ``site`` is the ``expr`` node of a field and ``parent`` a function
    that returns the parent node of a node (or ``None``). Returns the
    ``length_arg`` of :func:`fixed_length_vector` if ``site`` is the
    vector field of its record, otherwise ``None``.
    """
    if site is None:
        return None
    fields = parent(site)
    record = None if fields is None else parent(fields)
    info = fixed_length_vector(record)
    if info is None or info[0] is not site:
        return None
    return info[1]


def fixed_vector_length(length_arg_value):
    """The length of the vector for the value of the length expression.

    For INTG records, the number of values ``KIJ`` for ``NDIGIT``, or 0
    for an invalid ``NDIGIT`` (which raises an error when a record is
    read).
    """
    try:
        return INTG_NUM_VALUES.get(int(length_arg_value), 0)
    except (TypeError, ValueError):
        return 0
