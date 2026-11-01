############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/01
# Last modified:   2026/11/01
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The recipe parser keeps no references to the objects of its callers.

The recipe parser backtracks by raising an internal exception. A raised
exception references the frames it passes through, and each frame its
calling frames, so an exception kept beyond the parse would keep the
callers' local variables alive, among them the EndfParserPy instance
whose recipes are parsed during its construction.
"""

import gc
import weakref
import pytest
from endf_parserpy import EndfParserPy
from endf_parserpy.recipe_parser import parse_recipe, RecipeSyntaxError


REC = "[MAT,3,MT/ a, b, c, d, e, f] CONT\n"
# recipes that require backtracking, with and without a syntax error
RECIPES = {
    "valid": "x := (a + b) / c\nif x > 0 and (y < 1 or z == 2):\n"
    + REC
    + "endif\n[MAT,3,MT/ a, b, c, d, e/f, NP/ E / xs] TAB1 (xstable)\n",
    "malformed": "x := (a + b\n",
}


class _Sentinel:
    pass


def _parse_with_local_object(recipe):
    sentinel = _Sentinel()
    try:
        parse_recipe(recipe)
    except RecipeSyntaxError:
        pass
    return weakref.ref(sentinel)


@pytest.mark.parametrize("name", sorted(RECIPES))
def test_parse_recipe_releases_caller_frames(name):
    ref = _parse_with_local_object(RECIPES[name])
    gc.collect()
    assert ref() is None


def test_discarded_parser_instances_are_freed():
    refs = []
    for _ in range(3):
        parser = EndfParserPy()
        refs.append(weakref.ref(parser))
        del parser
        gc.collect()
        assert all(ref() is None for ref in refs)
