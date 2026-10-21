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

"""Tests for the export of the result layout by the C++ code generator.

endf_parserpy.compiler.recipe_layout.get_recipe_layout reports the C++
container of every stored variable and the shape of every definition of a
Matrix2d variable, as determined by the code generator for parsing,
without changing the generated code.
"""

import pytest
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.compiler import recipe_layout
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun


def test_layout_of_matrix_definitions():
    layout = recipe_layout.get_recipe_layout(get_recipe_dict("endf6-ext")[33])
    path = (("subsection", 1), ("ni_subsection", 1))
    kinds = {a[3] for a in layout["assignments"] if a[0] == path and a[2] == "F"}
    # LB=5 with LS=0 (rectangular) and LS=1 (upper triangle), LB=6
    # (rectangular) and the arrays F[k] of the other LB values
    assert kinds == {
        ("Matrix2d", "float", 2, False, False),
        ("Matrix2d", "float", 2, True, False),
        ("NestedVector", "float", 1, False, False),
    }
    assert layout["sections"][path]["E"] == (("NestedVector", "float", 1),)


def test_layout_of_nested_arrays():
    # al[i,j] of MF4: the array al[i] is created before the loop over j
    layout = recipe_layout.get_recipe_layout(get_recipe_dict("endf6-ext")[4])
    preps = [p for p in layout["preparations"] if p[2] == "al"]
    assert preps and all(p[3] == 0 for p in preps)


@pytest.mark.parametrize("mf", [3, 4, 33])
def test_layout_recorder_does_not_change_cpp_code(mf):
    recipe = get_recipe_dict("endf6-ext")[mf]
    recorder = recipe_layout.LayoutRecorder()
    with_recorder = generate_cpp_parsefun("fun", recipe, layout_recorder=recorder)
    assert generate_cpp_parsefun("fun", recipe) == with_recorder
    assert recorder.get_layout()["assignments"]
