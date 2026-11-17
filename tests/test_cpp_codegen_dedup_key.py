############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests of the deduplication of the generated C++ parse and write
functions.

The C++ code generator emits the parse and write function of each recipe
once into the shared translation units, also across flavors. It
specializes each function for the MF number, and for the MT number if
one is given, of the section it is registered for: the numbers are put
into the body as constants. The functions were deduplicated by the
recipe text alone, so a recipe text registered under several MF numbers,
or several explicit MT numbers, got the function of the first
registration for all of them: EndfParserCpp put the wrong MF (or MT)
into the dictionary and wrote the records of the section with it.

The dedup key now includes the MF number and the MT number. These tests
check the generated code, so they do not need a compiled module.
"""

import re

from endf_parserpy.compiler.code_generator_parsing import (
    generate_all_cpp_parsefuns_code,
)
from endf_parserpy.compiler.code_generator_writing import (
    generate_all_cpp_writefuns_code,
)


# a recipe with MF and MT as variables
RECIPE = """
[MAT, MF, MT/ ZA, AWR, 0, 0, N, 0] HEAD
SEND
"""

# a recipe with a literal MF and MT only in the record header
RECIPE_LITERAL_MF = """
[MAT, 3, MT/ ZA, AWR, 0, 0, N, 0] HEAD
SEND
"""


def _generate(recipes, registry, name="x"):
    generate_all_cpp_parsefuns_code(recipes, name, shared_registry=registry)
    generate_all_cpp_writefuns_code(recipes, name, shared_registry=registry)
    return registry


def _constants(code):
    mf = re.findall(r"int mf = (\d+);", code)
    mt = re.findall(r"int mt = (\d+);", code)
    return (mf[0] if mf else None, mt[0] if mt else None)


def _specializations(registry, side):
    return sorted(_constants(code) for _, code in registry[side].values())


def _names(registry, side):
    return sorted(name for name, _ in registry[side].values())


def test_one_text_under_two_mf_numbers():
    reg = _generate({3: RECIPE, 6: RECIPE}, {})
    for side in ("parse", "write"):
        assert len(reg[side]) == 2
        assert [mf for mf, _ in _specializations(reg, side)] == ["3", "6"]
        assert len(set(_names(reg, side))) == 2


def test_one_text_under_two_explicit_mt_numbers():
    # MT is specialized whether or not the recipe uses it as a variable
    for recipe in (RECIPE, RECIPE_LITERAL_MF):
        reg = _generate({3: {1: recipe, 2: recipe}}, {})
        for side in ("parse", "write"):
            assert _specializations(reg, side) == [("3", "1"), ("3", "2")]
            assert len(set(_names(reg, side))) == 2


def test_recipe_for_all_mts_of_an_mf_stays_one_function():
    # mt=-1 serves every MT of the MF; it is not specialized for an MT
    reg = _generate({3: {-1: RECIPE}, 6: {-1: RECIPE}}, {})
    for side in ("parse", "write"):
        assert len(reg[side]) == 2
        assert [mt for _, mt in _specializations(reg, side)] == [None, None]
    reg_str = _generate({3: RECIPE}, {})
    reg_all = _generate({3: {-1: RECIPE}}, {})
    for side in ("parse", "write"):
        assert _names(reg_str, side) == _names(reg_all, side)


def test_same_text_and_specialization_shared_across_flavors():
    reg = {}
    _generate({3: {1: RECIPE}, 6: RECIPE}, reg, name="flavor_a")
    names = {side: _names(reg, side) for side in ("parse", "write")}
    _generate({3: {1: RECIPE}, 6: RECIPE}, reg, name="flavor_b")
    for side in ("parse", "write"):
        assert _names(reg, side) == names[side]
    _generate({4: RECIPE}, reg, name="flavor_c")
    for side in ("parse", "write"):
        assert len(reg[side]) == 3


def test_flavor_code_calls_the_function_of_its_mf():
    reg = {}
    parts = generate_all_cpp_parsefuns_code({3: RECIPE, 6: RECIPE}, "x", reg)
    code = "\n".join(p for p in parts if isinstance(p, str))
    by_mf = {_constants(c)[0]: name for name, c in reg["parse"].values()}
    assert by_mf["3"] != by_mf["6"]
    for name in by_mf.values():
        assert name + "_istream" in code
