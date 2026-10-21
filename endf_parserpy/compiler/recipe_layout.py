############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Result layout of the C++ parse functions of ENDF recipes.

The code generator decides for each assignment of a variable which C++
container stores the variable (``Scalar``, ``NestedVector`` or
``Matrix2d``) and with which element type, and where the elements of
nested arrays are created. These decisions determine the form of the
arrays that :class:`~endf_parserpy.EndfParserCpp` returns with
``array_type="numpy"``. :func:`get_recipe_layout` runs the code
generator for parsing on a recipe and returns these decisions as plain
Python data, e.g. to check that another parser reproduces them.

Nodes of the parse tree are identified by their *path*, the tuple of
child indices leading from the root of the tree to the node, which is
the same in the tree of the code generator and in the tree obtained by
parsing the same recipe text. The *scope path* of a section is a tuple
of ``(section_name, number_of_indices)`` pairs, starting at the
outermost section (named TAB1, TAB2 and LIST records are sections, too).

The layout is a dictionary with the following items:

``"sections"``
    A dictionary that maps the scope path of each section scope to a
    dictionary that maps the names of the variables stored in the result
    dictionary of that section to a tuple of the container kinds stored
    (one per scope with this path), see
    :func:`~endf_parserpy.compiler.cpp_types.cpp_varops_assign.get_var_layout`.
``"assignments"``
    A tuple with one tuple ``(scope_path, site, varname, kind)`` for
    each place where the generated code assigns a variable and updates
    its type information. ``site`` is the path of the expression node of
    the assignment, or ``None`` if the assignment has no such node
    (columns of TAB1 and TAB2 records, TEXT fields). ``kind`` is a tuple
    ``(container, dtype, num_indices, is_triagonal, is_lower)``; the
    last two items are those of the initialization of a ``Matrix2d``
    variable and ``False`` for other containers. The data types are
    ``"float"``, ``"int"``, ``"str"``, ``"floatvec"`` and ``"intvec"``
    (the latter two for the columns of TAB1/TAB2 records and the
    integers of INTG records).
``"preparations"``
    A tuple with one tuple ``(loop, site, varname, level)`` for each
    element of a nested array (``NestedVector``) that the generated code
    creates before the loop with path ``loop`` (each time it reaches the
    loop); ``site`` is the path of the assignment and ``level`` the
    number of indices of the element minus one.
"""

from .code_generator_core import get_section_path
from .cpp_types.cpp_varops_assign import get_var_layout


_DTYPE_NAMES = {
    float: "float",
    int: "int",
    str: "str",
    "intvec": "intvec",
    "floatvec": "floatvec",
}


def _scope_path(vardict):
    return tuple((str(t), len(t.indices)) for t in get_section_path(vardict))


def _node_path(node):
    # child indices from the root; None for nodes not in the tree
    if not hasattr(node, "parent"):
        return None
    path = []
    while node.parent is not None:
        parent = node.parent
        path.append(next(i for i, c in enumerate(parent.children) if c is node))
        node = parent
    return tuple(reversed(path))


def _canonical_store(layout):
    specialtype = layout[0]
    if specialtype == "Scalar":
        return (specialtype, tuple(sorted(_DTYPE_NAMES[dt] for dt in layout[1])))
    if specialtype == "NestedVector":
        return (specialtype, _DTYPE_NAMES[layout[1]], layout[2])
    return (specialtype, _DTYPE_NAMES[layout[1]])


class LayoutRecorder:
    """Collects the layout reported by the code generator for parsing.

    An instance is passed as ``layout_recorder`` argument to
    :func:`~endf_parserpy.compiler.code_generator_parsing.generate_cpp_parsefun`.
    The code generator may visit a part of the recipe more than once
    (e.g. the body of an if-statement with lookahead), so the same
    information may be reported repeatedly.
    """

    def __init__(self):
        self._sections = {}
        self._assignments = set()
        self._preparations = set()
        self._matrices = {}

    def record_section_scope(self, vardict):
        scope = self._sections.setdefault(_scope_path(vardict), {})
        for vartok in vardict:
            if vartok.startswith("__"):
                continue
            layout = get_var_layout(vartok, vardict)
            if layout is not None:
                scope.setdefault(str(vartok), set()).add(_canonical_store(layout))

    def record_matrix2d_definition(self, vartok, node, is_triagonal, is_lower):
        # reported before the assignment of the same variable and node
        self._matrices[(id(node), str(vartok))] = (bool(is_triagonal), bool(is_lower))

    def record_assignment(self, vartok, dtype, specialtype, node, vardict):
        if vartok.cpp_namespace:
            return
        tri, lower = False, False
        if specialtype == "Matrix2d":
            tri, lower = self._matrices[(id(node), str(vartok))]
        kind = (specialtype, _DTYPE_NAMES[dtype], len(vartok.indices), tri, lower)
        site = _node_path(node)
        self._assignments.add((_scope_path(vardict), site, str(vartok), kind))

    def record_pointer_preparation(self, vartok, level, loop_node, node):
        entry = (_node_path(loop_node), _node_path(node), str(vartok), level)
        self._preparations.add(entry)

    def get_layout(self):
        sections = {
            path: {k: tuple(sorted(v)) for k, v in sorted(scope.items())}
            for path, scope in sorted(self._sections.items())
        }
        return {
            "sections": sections,
            "assignments": tuple(sorted(self._assignments, key=repr)),
            "preparations": tuple(sorted(self._preparations, key=repr)),
        }


_RECIPE_PARSER = None


def _get_recipe_parser():
    global _RECIPE_PARSER
    if _RECIPE_PARSER is None:
        from lark import Lark
        from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar

        _RECIPE_PARSER = Lark(
            endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True
        )
    return _RECIPE_PARSER


def get_recipe_layout(recipe, parser=None):
    """Return the result layout of the C++ parse function of a recipe.

    Parameters
    ----------
    recipe : str
        The ENDF recipe.
    parser : lark.Lark
        Parser for the recipe language; if ``None``, one is created
        (and reused in subsequent calls).

    Returns
    -------
    dict
        The layout described in the documentation of this module.
    """
    from .code_generator_parsing import generate_cpp_parsefun

    if parser is None:
        parser = _get_recipe_parser()
    recorder = LayoutRecorder()
    generate_cpp_parsefun(
        "layout_probe", recipe, parser=parser, layout_recorder=recorder
    )
    return recorder.get_layout()
