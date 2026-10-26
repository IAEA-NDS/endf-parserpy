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

A list of a nested array (NestedArray in
compiler/cpp_types/cpp_type_nested_array/definition.py), i.e. the
variable or an element of a level L, whose elements (index L+1) are set
by a loop over this index gets its capacity reserved for the iterations
of the loop (``reserve``), so that the elements are not moved and the
list is not reallocated while it grows: before the loop if the list is
known there, otherwise when the element is created in the loop (see
``_reservation_loop`` in assign.py). The reservation is limited, so that the
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
                ("var_Y_2d_double_NestedArray", "var_N_0d_int_Scalar"),
            ],
        ),
        # the list is created before the loop (triangular matrix)
        (
            _HEAD
            + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, (N*(N+1))/2, 0/ {{F[k,kp]}{kp=k to N}}{k=1 to N} ] LIST\n",
            [
                ("var_F_2d_double_NestedArray", "var_N_0d_int_Scalar"),
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
    # MF7/MT5: Ep[j,k] and the list of the elements of Ep and of b over j
    # (b[j,k,m] is a regular block of the indices k and m)
    assert _reserved(_parsefun(mf7.ENDF_RECIPE_MF7_MT5)) == [
        ("ptr_Ep_2d_idx0", "var_NEP_1d_int_NestedArray(var_j_0d_int_Scalar)"),
        ("var_E_1d_double_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_Ep_2d_double_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_NA_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_NEP_1d_int_NestedArray", "var_NE_0d_int_Scalar"),
        ("var_b_3d_double_NestedArray", "var_NE_0d_int_Scalar"),
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


# Reservations of the lists of the elements of nested arrays at all
# levels: the list of the elements of a variable or of an element is
# reserved for the loop of the next index, before the loop if the list
# is known there, otherwise when the element is created in the loop.

_RESERVATION_RE = re.compile(
    r"^\s*(?:if \((\S+)->empty\(\)\) \{\n\s*)?int cpp_first = (.*);\n"
    r"\s*(\S+?)(?:\.|->)reserve\(cpp_first, (.*)\);$",
    re.M,
)


def _reservations(code):
    # (list, upper bound, reserved when the element is created) of each
    # reservation
    return sorted(
        {
            (arr, stop, created != "")
            for created, _, arr, stop in _RESERVATION_RE.findall(code)
        }
    )


def _created(code):
    return [r for r in _reservations(code) if r[2]]


def _renamed(reservations, names):
    def rename(text):
        return re.sub(
            r"(?<=var_|ptr_)([A-Za-z0-9]+)(?=_)",
            lambda m: names.get(m.group(1), m.group(1)),
            text,
        )

    return sorted((rename(a), rename(s), c) for a, s, c in reservations)


def test_reservations_of_mf7_mt4_table():
    # S[q,i,j]: the elements S[q] and S[q,i] are created in the loop over
    # q and filled by the loops over i and j around it
    from endf_parserpy.endf_recipes.endf6.endf_recipe_mf7 import ENDF_RECIPE_MF7_MT4

    code = _parsefun(ENDF_RECIPE_MF7_MT4)
    assert _created(code) == [
        ("ptr_S_3d_idx0", "var_NB_0d_int_Scalar", True),
        ("ptr_S_3d_idx1", "var_LT_1d_int_NestedArray(var_i_0d_int_Scalar)", True),
    ]
    assert ("var_S_3d_double_NestedArray", "var_NP_0d_int_Scalar", False) in (
        _reservations(code)
    )
    # the reservation follows the creation of the element
    pos_prepare = code.index(
        "ptr_S_3d_idx1 = ptr_S_3d_idx0->prepare(var_i_0d_int_Scalar);"
    )
    pos_reserve = code.index("if (ptr_S_3d_idx1->empty()) {")
    pos_set = code.index("ptr_S_3d_idx1->set(var_j_0d_int_Scalar,")
    assert pos_prepare < pos_reserve < pos_set


def test_reservations_independent_of_names():
    # MF7/MT6 of the test flavor has the structure of MF7/MT4 of ENDF-6
    # with other names and gets the same reservations
    from endf_parserpy.endf_recipes.endf6.endf_recipe_mf7 import ENDF_RECIPE_MF7_MT4

    names = {
        "S": "V",
        "NB": "NG",
        "LT": "NC",
        "NP": "NK",
        "q": "r",
        "i": "g",
        "j": "c",
        "beta": "Y",
        "T": "Z",
        "LI": "M",
    }
    mt4 = [
        r
        for r in _reservations(_parsefun(ENDF_RECIPE_MF7_MT4))
        if not r[0].startswith("var_B_")
    ]
    mt6 = _reservations(_parsefun(mf7.ENDF_RECIPE_MF7_MT6))
    assert _renamed(mt4, names) == mt6
    assert len(_created(_parsefun(mf7.ENDF_RECIPE_MF7_MT6))) == 2


_MT4_LIKE = (
    _HEAD
    + "for i=1 to N:\n"
    + "    [MAT,MF,MT/ 0.0, 0.0, LT[i], 0, 0, 0] CONT\n"
    + "    for j=1 to LT[i]:\n"
    + "{body}"
    + "    endfor\n"
    + "endfor\n"
)
_LIST = "[MAT,MF,MT/ 0.0, 0.0, 0, 0, M, 0/ {S[q,i,j]}{q=1 to M} ] LIST\n"


@pytest.mark.parametrize(
    "recipe, expected",
    [
        # the elements S[q] and S[q,i] are created in the loop over q
        (
            _MT4_LIKE.format(body="        " + _LIST),
            [
                ("ptr_S_3d_idx0", "var_N_0d_int_Scalar", True),
                (
                    "ptr_S_3d_idx1",
                    "var_LT_1d_int_NestedArray(var_i_0d_int_Scalar)",
                    True,
                ),
            ],
        ),
        # an if-clause between the loop over j and the assignment: no
        # reservation for the loops over i and j
        (
            _MT4_LIKE.format(
                body="        if M > 0:\n            " + _LIST + "        endif\n"
            ),
            [],
        ),
        # the bound of the loop over j occurs in a record of the loop, so
        # that it may change in the loop: no reservation for S[q,i]
        (
            _MT4_LIKE.format(
                body="        [MAT,MF,MT/ 0.0, 0.0, LT[i], 0, 0, 0] CONT\n"
                + "        "
                + _LIST
            ),
            [("ptr_S_3d_idx0", "var_N_0d_int_Scalar", True)],
        ),
        # two assignments of S[q,i,j]: no reservation when the elements are
        # created
        (
            _MT4_LIKE.format(body="        " + _LIST + "        " + _LIST),
            [],
        ),
        # the loop over j is executed more than once for an element (in
        # each iteration of the loop over k), so that its bounds when the
        # element is created do not hold for all its elements
        (
            _HEAD
            + "for k=1 to 2:\n"
            + "    for j=1 to N:\n"
            + "        [MAT,MF,MT/ 0.0, 0.0, 0, 0, M, 0/ {S[q,j]}{q=1 to M} ] LIST\n"
            + "    endfor\n"
            + "endfor\n",
            [],
        ),
        # the leading index of the element changes in the loop over j
        # otherwise than with a loop inside it
        (
            _HEAD
            + "for j=1 to N:\n"
            + "    [MAT,MF,MT/ 0.0, 0.0, K, 0, 0, 0] CONT\n"
            + "    for q=1 to M:\n"
            + "        [MAT,MF,MT/ S[K,j], 0.0, 0, 0, 0, 0] CONT\n"
            + "    endfor\n"
            + "endfor\n",
            [],
        ),
    ],
    ids=[
        "created_in_inner_loop",
        "if_clause",
        "bound_in_loop",
        "two_assignments",
        "loop_executed_again",
        "leading_index_changes",
    ],
)
def test_reservations_when_created(recipe, expected):
    assert _created(_parsefun(recipe)) == expected


def test_outer_lists_reserved_before_loop():
    # the list of the elements of a variable with several indices is
    # reserved before the loop of its first index, as that of a variable
    # with one index
    recipe = (
        _HEAD
        + "for j=1 to N:\n"
        + "    [MAT,MF,MT/ 0.0, 0.0, NK[j], 0, NK[j], 0/ {Y[j,k]}{k=1 to NK[j]} ] LIST\n"
        + "endfor\n"
    )
    assert ("var_Y_2d_double_NestedArray", "var_N_0d_int_Scalar", False) in (
        _reservations(_parsefun(recipe))
    )


def _mt6_section(ng, nc, nk):
    # MF7/MT6 of the test flavor with NG groups of NC records of NK values
    sec = {"MAT": 1, "MF": 7, "MT": 6, "NG": ng, "NK": nk, "W0": 0.5}
    sec.update({"Y": {}, "NC": {}, "Z": {}, "M": {}, "V": {}, "V_table": {}})
    for g in range(1, ng + 1):
        sec["Y"][g] = 0.25 * g
        sec["NC"][g] = nc
        sec["V_table"][g] = {
            "NR": 1,
            "NP": 2,
            "NBT": [2],
            "INT": [2],
            "X": [1.0, 2.0],
            "V": [3.0 * g, 4.0 * g],
        }
        for c in range(1, nc + 1):
            sec["Z"][c] = 10.0 * c
            sec["M"][c] = c
            for r in range(1, nk + 1):
                sec["V"].setdefault(r, {}).setdefault(g, {})[c] = float(
                    100 * r + 10 * g + c
                )
    return sec


def _plain(obj):
    # numpy arrays as (dtype, list) for comparisons
    if hasattr(obj, "dtype") and hasattr(obj, "tolist"):
        return (str(obj.dtype), obj.tolist())
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
@pytest.mark.parametrize("ng, nc, nk", [(3, 4, 5), (1, 1, 1), (2, 0, 3), (2, 3, 0)])
def test_mt6_results(atype, ng, nc, nk):
    # the values of the elements created with reserved capacity, compared
    # with EndfParserPy, and writing them back
    kwargs = dict(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )
    text = EndfParserPy(**kwargs).write({7: {6: _mt6_section(ng, nc, nk)}})
    kwargs["array_type"] = atype
    pyparser = EndfParserPy(**kwargs)
    lines = text.splitlines() if isinstance(text, str) else list(text)
    cppparser = EndfParserCpp(**kwargs)
    res_cpp = cppparser.parse(lines)
    res_py = pyparser.parse(lines)
    assert _plain(res_cpp) == _plain(res_py)
    written = cppparser.write(res_cpp)
    written = written.splitlines() if isinstance(written, str) else list(written)
    assert written == lines
