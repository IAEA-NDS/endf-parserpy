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

"""Capacity of the lists of values of nested arrays in EndfParserCpp.

A list of values of a nested array (NestedArray<T, 1> in
compiler/cpp_types/cpp_type_nested_array/definition.py) that is filled by
a loop whose variable is the last index gets its capacity reserved before
the loop (``reserve``), so that the values are not moved and the list is
not reallocated while it grows. The reservation is limited, so that the
loop bounds of a damaged file cannot request a huge amount of memory, and
it changes neither the values nor the errors. These tests check where the
code generator reserves the capacity; the identity of the results is
checked by the tests of the recipes of the test flavor MF7 with empty and
non-empty loops (test_cpp_writer_array_accessor.py,
test_empty_inner_loops.py) and by the recipes of the package.
"""

import os
import re
import subprocess
import sys
import json
from pathlib import Path
import pytest
import endf_parserpy
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes.test import endf_recipe_mf7 as mf7
from endf_parserpy.utils.debugging_utils import compare_objects


_RESERVE_RE = re.compile(r"^\s*(\S+?)(?:\.|->)reserve\(cpp_first, (.*)\);$", re.M)


def _reserved(code):
    # the lists whose capacity is reserved and the upper loop bounds
    return sorted(set(_RESERVE_RE.findall(code)))


def _parsefun(recipe):
    return generate_cpp_parsefun("f", recipe)


_HEAD = "[MAT,MF,MT/ 0.0, 0.0, N, M, 0, 0] HEAD\n"


@pytest.mark.parametrize(
    "recipe, expected",
    [
        # a variable with one index in a loop and in a LIST record
        (
            _HEAD
            + "for i=1 to N:\n"
            + "    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            + "endfor\n"
            + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, M, 0/ {Y[k]}{k=1 to M} ] LIST\n",
            [
                ("var_X_1d_double_NestedArray", "var_N_0d_int_Scalar"),
                ("var_Y_1d_double_NestedArray", "var_M_0d_int_Scalar"),
            ],
        ),
        # the pointer to the list is assigned before the loop
        (
            _HEAD
            + "for j=1 to N:\n"
            + "    [MAT,MF,MT/ 0.0, 0.0, NK[j], 0, NK[j], 0/ {Y[j,k]}{k=1 to NK[j]} ] LIST\n"
            + "endfor\n",
            [
                ("ptr_Y_2d_idx0", "var_NK_1d_int_NestedArray(var_j_0d_int_Scalar)"),
                ("var_NK_1d_int_NestedArray", "var_N_0d_int_Scalar"),
            ],
        ),
        # the list is created before the loop (triangular matrix)
        (
            _HEAD
            + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, (N*(N+1))/2, 0/ {{F[k,kp]}{kp=k to N}}{k=1 to N} ] LIST\n",
            [
                (
                    "var_F_2d_double_NestedArray.prepare(var_k_0d_int_Scalar)",
                    "var_N_0d_int_Scalar",
                ),
            ],
        ),
        # the last index is not the variable of the innermost loop
        (
            _HEAD
            + "for j=1 to N:\n"
            + "    for i=1 to M:\n"
            + "        [MAT,MF,MT/ T[i,j], 0.0, 0, 0, 0, 0] CONT\n"
            + "    endfor\n"
            + "endfor\n",
            [],
        ),
        # an expression as last index
        (
            _HEAD
            + "for i=1 to N:\n"
            + "    [MAT,MF,MT/ X[2*i], 0.0, 0, 0, 0, 0] CONT\n"
            + "endfor\n",
            [],
        ),
        # an if-clause between the loop and the assignment
        (
            _HEAD
            + "for i=1 to N:\n"
            + "    if M > 0:\n"
            + "        [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            + "    endif\n"
            + "endfor\n",
            [],
        ),
        # a regular block is created with its final size
        (
            _HEAD
            + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, N*M, 0/ {{B[i,k]}{k=1 to M}}{i=1 to N} ] LIST\n",
            [],
        ),
    ],
    ids=[
        "one_index",
        "pointer_before_loop",
        "created_before_loop",
        "last_index_outer_loop",
        "index_expression",
        "if_clause",
        "regular_block",
    ],
)
def test_reserved_lists(recipe, expected):
    assert _reserved(_parsefun(recipe)) == expected


def test_reserve_before_loop_after_other_code():
    # the reservation is the last code before the loop, right before the
    # loop evaluates its bounds in the same order
    recipe = (
        _HEAD
        + "for j=1 to N:\n"
        + "    [MAT,MF,MT/ 0.0, 0.0, NK[j], 0, NK[j], 0/ {Y[j,k]}{k=1 to NK[j]} ] LIST\n"
        + "endfor\n"
    )
    code = _parsefun(recipe)
    pos_prepare = code.index("ptr_Y_2d_idx0 = var_Y_2d_double_NestedArray.prepare")
    pos_reserve = code.index("ptr_Y_2d_idx0->reserve(cpp_first")
    pos_loop = code.index("for (int var_k_0d_int_Scalar = 1;")
    assert pos_prepare < pos_reserve < pos_loop
    assert "int cpp_first = 1;\n" in code[pos_prepare:pos_reserve]


def test_reserved_lists_of_test_recipes():
    # MF7/MT5: Ep[j,k] (b[j,k,m] is a regular block)
    assert _reserved(_parsefun(mf7.ENDF_RECIPE_MF7_MT5)) == [
        ("ptr_Ep_2d_idx0", "var_NEP_1d_int_NestedArray(var_j_0d_int_Scalar)"),
        ("var_E_1d_double_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_NA_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_NEP_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
    ]


def test_writer_reserves_lists_with_stored_values():
    # the writer stores only the values used later (see unused_arrays.py),
    # here NEP and NA, which are loop bounds
    assert _reserved(generate_cpp_writefun("f", mf7.ENDF_RECIPE_MF7_MT5)) == [
        ("var_NA_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_NEP_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
    ]


def _rec(mt, seq, floats=(0.0, 0.0), ints=(0, 0, 0, 0)):
    fstr = "".join(f"{v:.6e}".replace("e", "")[:11].rjust(11) for v in floats)
    istr = "".join(f"{v:11d}" for v in ints)
    return fstr + istr + f"   1 7{mt:3d}{seq:5d}"


def _mt1_text(ni):
    # MF7/MT1 with NI as given, I0=1, NJ=0, and two CONT records
    lines = [
        _rec(1, 1, ints=(ni, 0, 1, 1)),
        _rec(1, 2, floats=(1.5, 0.0), ints=(3, 0, 0, 0)),
        _rec(1, 3, floats=(2.5, 0.0), ints=(4, 0, 0, 0)),
        _rec(0, 99999),
    ]
    return "\n".join(lines)


# The message is obtained in a separate process: in some builds, a C++
# exception raised by a flavor module other than the first one loaded in
# the process loses its message.
_MESSAGE_SCRIPT = """
import json, sys
from endf_parserpy import EndfParserCpp
parser = EndfParserCpp(
    endf_format="test",
    ignore_send_records=True,
    ignore_missing_tpid=True,
    array_type=sys.argv[1],
)
try:
    parser.parse(sys.stdin.read())
    print(json.dumps(None))
except RuntimeError as exc:
    print(json.dumps(str(exc)))
"""


def _parse_error_message(text, atype):
    # the package imported by the test, also in the separate process
    env = dict(os.environ)
    pkgdir = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (pkgdir, env.get("PYTHONPATH")) if p)
    res = subprocess.run(
        [sys.executable, "-c", _MESSAGE_SCRIPT, atype],
        input=text,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return json.loads(res.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
def test_loop_bounds_of_damaged_file(atype):
    # a huge loop bound reserves a limited capacity and fails when the
    # records are exhausted, as before
    message = _parse_error_message(_mt1_text(999999999), atype)
    assert message is not None
    assert "Blank line detected" in message


@pytest.mark.parametrize("ni", [-3, 0, 2])
def test_loop_lengths(ni):
    # loops without iterations (also with a negative bound) and with
    # iterations; without iterations, the CONT records follow the HEAD
    # record unexpectedly, which both parsers reject
    kwargs = dict(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )
    results = []
    for parser in (EndfParserCpp(**kwargs), EndfParserPy(**kwargs)):
        try:
            results.append(parser.parse(_mt1_text(ni)))
        except Exception:
            results.append(None)
    if ni == 2:
        compare_objects(results[0], results[1])
        assert results[0][7][1]["A"] == {1: 1.5, 2: 2.5}
    else:
        assert results == [None, None]
