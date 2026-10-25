############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Array variables whose values the C++ writer does not store.

The writing code assigns the value of each field to the C++ variables in
the field. For a variable with indices whose value is never used later,
and whose stores provably cannot fail, the stores are omitted (see
endf_parserpy/compiler/unused_arrays.py). These tests check which
variables are recognized; the identity of the output and of the errors is
checked by writing the recipes of the test flavor MF7 (see
test_cpp_writer_array_accessor.py), whose recipes MT2 and MT4 store all
values, and the recipes of the package.
"""

import re
import pytest
from lark import Lark
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.compiler.expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from endf_parserpy.compiler.node_aux import (
    simplify_expr_node,
    node_and_kids_to_ParseNode,
)
from endf_parserpy.compiler.unused_arrays import find_unused_arrays
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.endf_recipes.test import endf_recipe_mf7 as mf7


_PARSER = Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)
_HEAD = "[MAT,MF,MT/ 0.0, 0.0, N, M, L, 0] HEAD\n"


def _unused(recipe):
    tree = _PARSER.parse(recipe)
    tree = transform_nodes(tree, simplify_expr_node)
    tree = transform_nodes_inplace(tree, node_and_kids_to_ParseNode)
    return find_unused_arrays(tree)


def _loop(body, var="i", stop="N"):
    lines = body.rstrip("\n").split("\n")
    return (
        f"for {var}=1 to {stop}:\n" + "".join(f"    {l}\n" for l in lines) + "endfor\n"
    )


@pytest.mark.parametrize(
    "body, expected",
    [
        # whole fields and LIST elements in the loops of their indices
        (_loop("[MAT,MF,MT/ X[i], 0.0, Y[i], 0, 0, 0] CONT"), {"X", "Y"}),
        (
            _loop(
                "[MAT,MF,MT/ 0.0, 0.0, 0, 0, 2*M, M/ {X[i,j], Y[i,j]}{j=1 to M} ] LIST"
            ),
            {"X", "Y"},
        ),
        (_loop(_loop("[MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT", "j", "M")), {"X"}),
        # a field with arithmetic, a variable in a condition, a loop bound,
        # an index or an abbreviation is used
        (_loop("[MAT,MF,MT/ 2*X[i], 0.0, 0, 0, 0, 0] CONT"), set()),
        (
            _loop(
                "[MAT,MF,MT/ X[i], 0.0, Y[i], 0, 0, 0] CONT\n"
                "if Y[i] > 0:\n"
                "    [MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] CONT\n"
                "endif"
            ),
            {"X"},
        ),
        (
            _loop(
                "[MAT,MF,MT/ 0.0, 0.0, Y[i], 0, 0, 0] CONT\n"
                + _loop("[MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT", "j", "Y[i]")
            ),
            {"X"},
        ),
        (
            _loop(
                "[MAT,MF,MT/ 0.0, 0.0, Y[i], 0, 0, 0] CONT\n"
                "[MAT,MF,MT/ X[Y[i]], 0.0, 0, 0, 0, 0] CONT"
            ),
            set(),
        ),
        (
            "W := X[i]\n"
            + _loop(
                "[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n[MAT,MF,MT/ W, 0.0, 0, 0, 0, 0] CONT"
            ),
            set(),
        ),
        # the sizes of the tables of a TAB1 record are not assignments
        (_loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, Y[i], Z[i]/ E / S] TAB1 (tab[i])"), {"X"}),
        # an element may be skipped or stored twice
        (
            _loop(
                "if L == 1:\n" "    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n" "endif"
            ),
            set(),
        ),
        (_loop(_loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT", "j", "M")), set()),
        (
            _loop(_loop("[MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT", "i", "M"), "j"),
            set(),
        ),
        (_loop("[MAT,MF,MT/ X[i+1], 0.0, 0, 0, 0, 0] CONT"), set()),
        (
            _loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT")
            + _loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT"),
            set(),
        ),
        # occurrences in different branches of an if-clause
        (
            "if L == 1:\n"
            + _loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT")
            + "else:\n"
            + _loop("[MAT,MF,MT/ 0.0, 0.0, 0, 0, 1, 1/ X[i] ] LIST")
            + "endif\n",
            {"X"},
        ),
        (
            "if L == 1:\n"
            + _loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT")
            + "else:\n"
            + _loop("[MAT,MF,MT/ 0.0, 0.0, X[i], 0, 0, 0] CONT")
            + "endif\n",
            set(),
        ),
        # a named LIST record and a section are scopes of their own
        (
            _loop("[MAT,MF,MT/ 0.0, 0.0, 0, 0, M, 0/ {X[j]}{j=1 to M} ] LIST (lst[i])"),
            {"X"},
        ),
        (
            _loop(
                "(sec[i])\n"
                + _loop("[MAT,MF,MT/ X[j], 0.0, 0, 0, 0, 0] CONT", "j", "M")
                + "(/sec[i])"
            ),
            {"X"},
        ),
        (
            _loop(
                "(sec[i])\n"
                + _loop("[MAT,MF,MT/ X[j], 0.0, 0, 0, 0, 0] CONT", "j", "M")
                + "(/sec[i])"
            )
            + _loop("[MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT"),
            set(),
        ),
        # variables without index and MT, which is assigned apart from the recipe
        ("[MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT\n", set()),
        (_loop("[MAT,MF,MT/ MT[i], 0.0, 0, 0, 0, 0] CONT"), set()),
    ],
)
def test_unused_arrays(body, expected):
    assert _unused(_HEAD + body + "SEND\n") == expected


def test_unused_arrays_of_test_recipes():
    assert _unused(mf7.ENDF_RECIPE_MF7_MT1) == {"A", "K"}
    assert _unused(mf7.ENDF_RECIPE_MF7_MT2) == set()
    assert _unused(mf7.ENDF_RECIPE_MF7_MT3) == {"C", "L", "B"}
    assert _unused(mf7.ENDF_RECIPE_MF7_MT4) == set()
    assert _unused(mf7.ENDF_RECIPE_MF7_MT5) == {"E", "Ep", "b"}


def test_no_stores_when_writing():
    write = generate_cpp_writefun("test_write", mf7.ENDF_RECIPE_MF7_MT5)
    parse = generate_cpp_parsefun("test_parse", mf7.ENDF_RECIPE_MF7_MT5)
    for name in ("E", "Ep", "b"):
        # declared, but neither prepared nor assigned
        assert re.findall(rf"var_{name}_\d+d_\w+NestedArray(?:\.|->)\w+\(", write) == []
        assert f'validate_vartype_consistency("{name}"' not in write
        assert f'validate_vartype_consistency("{name}"' in parse
    # the elements are still registered with the index bookkeeping
    assert 'register_element("b", std::vector<int>({var_j_0d_int_Scalar}))' in write
    assert "var_NA_1d_int_NestedArray.set(" in write
