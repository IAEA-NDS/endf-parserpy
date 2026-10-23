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

"""The annotation of recipes for array_type="numpy" follows the code generator.

EndfParserPy annotates the recipe parse trees with the container kinds of
the variables by a walk over the tree that replicates the decisions of
the C++ code generator (endf_parserpy.interpreter.numpy_annotation),
without using the code generator. This test compares the result with the
decisions reported by the code generator (endf_parserpy.compiler
.recipe_layout) for all recipes of all ENDF flavors: every assignment
with its container kind (including the shape of matrices) and every
creation of an element of a nested array before a loop.
"""

from hashlib import md5
import pytest
from endf_parserpy.endf_recipes import get_recipe_dict, list_endf_flavors
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.interpreter.endf_recipe_utils import get_recipe_parser
from endf_parserpy.interpreter.numpy_annotation import annotate_recipe_tree
from endf_parserpy.compiler.recipe_layout import get_recipe_layout


def node_path(walker, node):
    """Child indices leading from the root of the tree to ``node``."""
    path = []
    cur = node
    par = walker.parent(cur)
    while par is not None:
        path.append(next(i for i, c in enumerate(par.children) if c is cur))
        cur = par
        par = walker.parent(cur)
    return tuple(reversed(path))


def _all_recipes():
    recipes = {}
    for flavor in list_endf_flavors():
        for mf, mfdic in get_recipe_dict(flavor).items():
            items = [(None, mfdic)] if isinstance(mfdic, str) else mfdic.items()
            for mt, recipe in items:
                key = md5(recipe.encode()).hexdigest()
                recipes.setdefault(key, (f"{flavor}-MF{mf}-MT{mt}", recipe))
    return sorted(recipes.values())


RECIPES = _all_recipes()


@pytest.fixture(scope="module")
def recipe_parser():
    return get_recipe_parser(endf_recipe_grammar)


@pytest.mark.parametrize("recipe", [r for _, r in RECIPES], ids=[n for n, _ in RECIPES])
def test_annotation_follows_code_generator(recipe, recipe_parser):
    layout = get_recipe_layout(recipe)
    # MAT, MF and MT are assigned before the recipe is processed
    expected_assignments = {
        a
        for a in layout["assignments"]
        if not (a[0] == () and a[1] is None and a[2] in ("MAT", "MF", "MT"))
    }
    walker = annotate_recipe_tree(recipe_parser.parse(recipe))
    assignments = {
        (scope, None if expr is None else node_path(walker, expr), var.name, kind)
        for var, expr, kind, anchor, scope in walker.assignments
    }
    preparations = {
        (node_path(walker, loop), node_path(walker, expr), var.name, level)
        for var, level, loop, expr in walker.preparations
    }
    assert assignments == expected_assignments
    assert preparations == set(layout["preparations"])


# Matrices of custom recipes: the proof of the code generator that a
# variable with two indices can be stored as a matrix checks the limits of
# both loops (before, only those of the inner loop were checked)
MATRIX_RECIPES = {
    "rectangular": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        SEND
        """,
        "Matrix2d",
    ),
    "outer limit with array": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, 2, 0/ NA[1], NA[2] ]LIST
        for i=1 to NA[1]:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        SEND
        """,
        "NestedVector",
    ),
}


@pytest.mark.parametrize("case", list(MATRIX_RECIPES))
def test_matrix_proof_checks_both_loops(case, recipe_parser):
    recipe, container = MATRIX_RECIPES[case]
    layout = get_recipe_layout(recipe)
    kinds = {a[3][0] for a in layout["assignments"] if a[2] == "M"}
    assert kinds == {container}
    walker = annotate_recipe_tree(recipe_parser.parse(recipe))
    assert {
        kind[0] for var, _, kind, _, _ in walker.assignments if var.name == "M"
    } == {container}
