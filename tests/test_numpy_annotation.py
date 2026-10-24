############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/24
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
    blocks = {
        (node_path(walker, loop), node_path(walker, expr), var.name, num_leading)
        for var, num_leading, loop, expr in walker.blocks
    }
    assert assignments == expected_assignments
    assert preparations == set(layout["preparations"])
    assert blocks == set(layout["blocks"])


# Regular blocks in custom recipes: the rank of the block of each
# assignment of M (0: no block), determined in the same way by the code
# generator and the annotation
BLOCK_RECIPES = {
    "rectangular": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        SEND
        """,
        {2},
    ),
    "transposed": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for j=1 to 3:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NW, 0/ {M[i,j]}{i=1 to N} ]LIST
        endfor
        SEND
        """,
        {2},
    ),
    "outer limit with array": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, 2, 0/ NA[1], NA[2] ]LIST
        for i=1 to NA[1]:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        SEND
        """,
        {2},
    ),
    "block of the trailing two of three indices": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, K[i], L[i], 0, 0]CONT
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NW, 0/
                {{M[i,j,k]}{k=1 to L[i]}}{j=1 to K[i]} ]LIST
        endfor
        SEND
        """,
        {2},
    ),
    "inner limit with outer variable": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, i, 0/ {M[i,j]}{j=1 to i} ]LIST
        endfor
        SEND
        """,
        {0},
    ),
    "limit read in outer loop": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NC[i], 0/ {M[i,j]}{j=1 to NC[i]} ]LIST
        endfor
        SEND
        """,
        {0},
    ),
    "later write": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[N+1,j]}{j=1 to 3} ]LIST
        SEND
        """,
        {0},
    ),
    "later read": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
        endfor
        [MAT, 1, MT/ M[1,1], 0.0, 0, 0, 0, 0]CONT
        SEND
        """,
        {0},
    ),
    "enclosing loop without leading index": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for q=1 to 2:
            for i=1 to q:
                [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
            endfor
        endfor
        SEND
        """,
        {0},
    ),
    "limit read before and checked in the loop": (
        """
        [MAT, 1, MT/ 0.0, 0.0, N, NP, 0, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NP, 0/ {M[q,i]}{q=1 to NP} ]LIST
        endfor
        SEND
        """,
        {2},
    ),
    "limit first read in the loop": (
        """
        [MAT, 1, MT/ 0.0, 0.0, N, 0, 0, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NP, 0/ {M[q,i]}{q=1 to NP} ]LIST
        endfor
        SEND
        """,
        {0},
    ),
    "limit only the size of a table before": (
        # the fields NR and NP of a TAB1 record are the sizes of its tables,
        # so NP is first read in the loop (as in MF7/MT2)
        """
        [MAT, 1, MT/ 0.0, 0.0, N, 0, NR, NP/ E / Y ]TAB1
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NP, 0/ {M[q,i]}{q=1 to NP} ]LIST
        endfor
        SEND
        """,
        {0},
    ),
    "limit possibly read before": (
        # NP is only read if L == 1; otherwise the first LIST record
        # assigns it
        """
        [MAT, 1, MT/ 0.0, 0.0, N, L, 0, 0]HEAD
        if L == 1:
            [MAT, 1, MT/ 0.0, 0.0, NP, 0, 0, 0]CONT
        endif
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NP, 0/ {M[q,i]}{q=1 to NP} ]LIST
        endfor
        SEND
        """,
        {0},
    ),
    "limit read before and redefined as abbreviation": (
        """
        [MAT, 1, MT/ 0.0, 0.0, N, NP, 0, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, NP, 0/ {M[q,i]}{q=1 to NP} ]LIST
            NP := 3
        endfor
        SEND
        """,
        {0},
    ),
    "block does not span the scope of a named LIST record": (
        """
        [MAT, 1, MT/ 0.0, 0.0, 0, 0, N, 0]HEAD
        for i=1 to N:
            [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST (sub[i])
        endfor
        SEND
        """,
        {0},
    ),
    "mutually exclusive branches": (
        """
        [MAT, 1, MT/ 0.0, 0.0, LB, 0, N, 0]HEAD
        if LB == 1:
            for i=1 to N:
                [MAT, 1, MT/ 0.0, 0.0, 0, 0, 3, 0/ {M[i,j]}{j=1 to 3} ]LIST
            endfor
        else:
            for i=1 to N:
                [MAT, 1, MT/ 0.0, 0.0, 0, 0, 2, 0/ {M[i,j]}{j=1 to 2} ]LIST
            endfor
        endif
        SEND
        """,
        {2},
    ),
}


@pytest.mark.parametrize("case", list(BLOCK_RECIPES))
def test_blocks_of_custom_recipes(case, recipe_parser):
    recipe, ranks = BLOCK_RECIPES[case]
    layout = get_recipe_layout(recipe)
    assert {a[3][3] for a in layout["assignments"] if a[2] == "M"} == ranks
    walker = annotate_recipe_tree(recipe_parser.parse(recipe))
    assert {
        kind[3] for var, _, kind, _, _ in walker.assignments if var.name == "M"
    } == ranks
