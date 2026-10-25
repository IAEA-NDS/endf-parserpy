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

"""Elements of array variables in loops written by EndfParserCpp.

If an indexed variable occurs only once in a loop, the C++ writer
retrieves its elements with an accessor declared before the loop
(CppArrayAccessor in compiler/cpp_templates/index_shifter.hpp), which
reads exact dicts, exact lists and numpy arrays directly and uses the
generic access in all other cases. The recipes MF7/MT1 and MF7/MT3 of the
test flavor (endf_recipes/test/endf_recipe_mf7.py) are written with
accessors, the recipes MF7/MT2 and MF7/MT4 with the same records without
them. For each array type and many valid and invalid variants of the
data, the output, or the type and message of the exception, must be the
same for both.
"""

import copy
import re
import pytest
from endf_parserpy import EndfParserCpp, EndfFloat
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes.test import endf_recipe_mf7 as mf7

np = pytest.importorskip("numpy")

MODES = ("dict", "list", "numpy")


def _parser(mode, preserve=False):
    return EndfParserCpp(
        endf_format="test",
        array_type=mode,
        ignore_missing_tpid=True,
        preserve_value_strings=preserve,
    )


def _mt1_dict(i0=3, j0=5, ni=3, nj=2):
    sec = {"MAT": 1, "MF": 7, "MT": 1, "NI": ni, "NJ": nj, "I0": i0, "J0": j0}
    sec["A"] = {i: 1.5 + i for i in range(i0, i0 + ni)}
    sec["K"] = {i: 10 + i for i in range(i0, i0 + ni)}
    sec["T"] = {
        i: {j: i + j / 100 for j in range(j0, j0 + nj)} for i in range(i0, i0 + ni)
    }
    return sec


# NJ[i] and NW[i,j] of MF7/MT3, including empty loops
MT3_SHAPE = {1: [2, 0], 2: [1, 3, 2], 3: []}


def _mt3_dict():
    sec = {"MAT": 1, "MF": 7, "MT": 3, "NI": len(MT3_SHAPE)}
    sec.update({"NJ": {}, "NW": {}, "C": {}, "L": {}, "B": {}})
    for i, nws in MT3_SHAPE.items():
        sec["NJ"][i] = len(nws)
        if not nws:
            continue
        sec["NW"][i] = {j: nw for j, nw in enumerate(nws, start=1)}
        sec["C"][i] = {j: 0.25 * i + j for j in range(1, len(nws) + 1)}
        sec["L"][i] = {j: 100 * i + j for j in range(1, len(nws) + 1)}
        sec["B"][i] = {
            j: {k: i + j / 10 + k / 100 for k in range(1, nw + 1)}
            for j, nw in enumerate(nws, start=1)
        }
    return sec


def _section(mt, mode, preserve=False):
    # the section as obtained by parsing with the given array type
    sec = _mt1_dict() if mt == 1 else _mt3_dict()
    text = _parser("dict").write({7: {mt: sec}})
    return _parser(mode, preserve).parse(text)[7][mt]


def _outcome(parser, sec, mt):
    sec = dict(sec)
    sec["MT"] = mt
    try:
        lines = parser.write({7: {mt: sec}})
    except Exception as exc:
        return ("error", type(exc), str(exc))
    # without the MT number
    return ("ok", [line[:72] + line[75:] for line in lines])


def _check(mode, sec, mt_with, preserve=False):
    parser = _parser(mode, preserve)
    res = _outcome(parser, sec, mt_with)
    assert res == _outcome(parser, sec, mt_with + 1)
    return res


def _first(arr):
    # key or index of the first element
    return min(arr) if isinstance(arr, dict) else 0


def _last(arr):
    return max(arr) if isinstance(arr, dict) else len(arr) - 1


def _drop_last(arr):
    if isinstance(arr, dict):
        arr = dict(arr)
        del arr[max(arr)]
        return arr
    return arr[:-1]


def _replace(arr, pos, value):
    if isinstance(arr, np.ndarray):
        arr = arr.astype(object) if not isinstance(value, (int, float)) else arr.copy()
        arr[pos] = value
        return arr
    arr = copy.copy(arr)
    arr[pos] = value
    return arr


class _List(list):
    # a list subclass whose elements are retrieved by __getitem__
    def __getitem__(self, i):
        val = super().__getitem__(i)
        return val * 2 if isinstance(val, float) else val


class _Dict(dict):
    def __missing__(self, key):
        return 7.0


def _subclass(arr):
    if isinstance(arr, dict):
        return _Dict(arr)
    return _List(arr.tolist() if isinstance(arr, np.ndarray) else arr)


def _row(arr, i):
    # the inner array of the element i (first) of a nested array
    if isinstance(arr, np.ndarray) and arr.ndim > 1:
        return arr[i]
    return arr[i]


# variants of the data of MF7/MT1: a function changing the section
MT1_VARIANTS = {
    "unchanged": lambda s: None,
    "missing_A": lambda s: s.pop("A"),
    "missing_T": lambda s: s.pop("T"),
    "short_A": lambda s: s.update(A=_drop_last(s["A"])),
    "short_K": lambda s: s.update(K=_drop_last(s["K"])),
    "short_T": lambda s: s.update(T=_drop_last(s["T"])),
    "str_A": lambda s: s.update(A=_replace(s["A"], _first(s["A"]), "x")),
    "int_A": lambda s: s.update(A=_replace(s["A"], _last(s["A"]), 7)),
    "bool_A": lambda s: s.update(A=_replace(s["A"], _last(s["A"]), True)),
    "float_K": lambda s: s.update(K=_replace(s["K"], _first(s["K"]), 1.5)),
    "bool_K": lambda s: s.update(K=_replace(s["K"], _last(s["K"]), True)),
    "large_K": lambda s: s.update(K=_replace(s["K"], _last(s["K"]), 2**40)),
    "none_K": lambda s: s.update(K=_replace(s["K"], _last(s["K"]), None)),
    "endffloat_A": lambda s: s.update(
        A=_replace(s["A"], _first(s["A"]), EndfFloat(2.5, " 2.50000000"))
    ),
    "subclass_A": lambda s: s.update(A=_subclass(s["A"])),
    "subclass_K": lambda s: s.update(K=_subclass(s["K"])),
    "tuple_A": lambda s: s.update(
        A=tuple(s["A"].values()) if isinstance(s["A"], dict) else tuple(s["A"])
    ),
    "dict_A": lambda s: s.update(
        A=dict(enumerate(s["A"])) if not isinstance(s["A"], dict) else s["A"]
    ),
    "list_A": lambda s: s.update(
        A=list(s["A"].values()) if isinstance(s["A"], dict) else list(s["A"])
    ),
    "numpy_A": lambda s: s.update(A=np.array(list(_values(s["A"])))),
    "float32_A": lambda s: s.update(A=np.array(list(_values(s["A"])), np.float32)),
    "int64_A": lambda s: s.update(A=np.array([4, 5, 6], np.int64)),
    "uint8_A": lambda s: s.update(A=np.array([4, 5, 6], np.uint8)),
    "float64_K": lambda s: s.update(K=np.array([13.0, 14.0, 15.0])),
    "int32_K": lambda s: s.update(K=np.array([13, 14, 15], np.int32)),
    "uint64_K": lambda s: s.update(K=np.array([13, 14, 2**40], np.uint64)),
    "int64_large_K": lambda s: s.update(K=np.array([13, -(2**40), 15], np.int64)),
    "bool_array_K": lambda s: s.update(K=np.array([True, False, True])),
    "short_array_A": lambda s: s.update(A=np.array([4.5, 5.5])),
    "array2d_A": lambda s: s.update(A=np.ones((3, 1))),
    "row_short_T": lambda s: s.update(T=_short_row(s["T"])),
    "row_tuple_T": lambda s: s.update(T=_map_rows(s["T"], tuple)),
    "row_subclass_T": lambda s: s.update(T=_map_rows(s["T"], _subclass)),
    "row_numpy_T": lambda s: s.update(T=_map_rows(s["T"], _np_row)),
    "row_float32_T": lambda s: s.update(
        T=_map_rows(s["T"], lambda r: _np_row(r).astype(np.float32))
    ),
    "block_T": lambda s: s.update(
        T=np.array([[3.05, 3.06], [4.05, 4.06], [5.05, 5.06]])
    ),
    "block_fortran_T": lambda s: s.update(
        T=np.asfortranarray(np.array([[3.05, 3.06], [4.05, 4.06], [5.05, 5.06]]))
    ),
    "block_transposed_T": lambda s: s.update(
        T=np.array([[3.05, 4.05, 5.05], [3.06, 4.06, 5.06]]).T
    ),
    "block_int_T": lambda s: s.update(T=np.arange(6, dtype=np.int16).reshape(3, 2)),
    "block_short_T": lambda s: s.update(T=np.ones((3, 1))),
    "block_3d_T": lambda s: s.update(T=np.ones((3, 2, 1))),
    "block_strided_T": lambda s: s.update(T=np.arange(24.0).reshape(6, 4)[::2, 1::2]),
    "empty_loops_missing_arrays": lambda s: [
        s.update(NI=0, NJ=0),
        s.pop("A"),
        s.pop("K"),
        s.pop("T"),
    ],
    "empty_inner_loop": lambda s: [s.update(NI=0), s.pop("A"), s.pop("K")],
}


def _values(arr):
    return arr.values() if isinstance(arr, dict) else arr


def _np_row(row):
    return np.array(list(_values(row)), dtype=float)


def _map_rows(arr, func):
    if isinstance(arr, dict):
        return {k: func(v) for k, v in arr.items()}
    return [func(r) for r in arr]


def _short_row(arr):
    if isinstance(arr, dict):
        arr = dict(arr)
        k = _last(arr)
        arr[k] = _drop_last(arr[k])
        return arr
    arr = list(arr)
    arr[-1] = _drop_last(arr[-1])
    return arr


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("variant", sorted(MT1_VARIANTS))
def test_mt1_variants(mode, variant):
    sec = _section(1, mode)
    MT1_VARIANTS[variant](sec)
    res = _check(mode, sec, 1)
    if variant == "unchanged":
        assert res[0] == "ok"
        expected = _parser("dict").write({7: {1: _mt1_dict()}})
        assert res[1] == [line[:72] + line[75:] for line in expected]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("i0, j0", [(1, 1), (0, 0), (3, 5), (-2, 7)])
def test_mt1_start_indices(mode, i0, j0):
    # in list mode, the first index of a loop is position 0 of the list
    sec = _mt1_dict(i0, j0)
    text = _parser("dict").write({7: {1: sec}})
    sec = _parser(mode).parse(text)[7][1]
    assert _check(mode, sec, 1) == ("ok", [line[:72] + line[75:] for line in text])


def test_mt1_dict_keys():
    # dict arrays are indexed by the recipe indices: an element preceding
    # the first index of the loop is not used, a missing one is an error
    sec = _section(1, "dict")
    sec["A"] = dict(sec["A"])
    sec["A"][2] = 99.0
    res = _check("dict", sec, 1)
    assert res[0] == "ok" and "9.900000+1" not in "".join(res[1])
    sec["A"] = {k + 10: v for k, v in sec["A"].items()}
    assert _check("dict", sec, 1)[:2] == ("error", KeyError)


@pytest.mark.parametrize("mode", MODES)
def test_mt1_preserve_value_strings(mode):
    sec = _section(1, mode, preserve=True)
    res = _check(mode, sec, 1, preserve=True)
    assert res[0] == "ok"
    MT1_VARIANTS["endffloat_A"](sec)
    res2 = _check(mode, sec, 1, preserve=True)
    assert res2[0] == "ok" and " 2.50000000" in res2[1][1]


# variants of the data of MF7/MT3
MT3_VARIANTS = {
    "unchanged": lambda s: None,
    "missing_B": lambda s: s.pop("B"),
    "missing_row_B": lambda s: s.update(B=_drop_last(s["B"])),
    "short_B": lambda s: s.update(B=_short_inner(s["B"])),
    "str_B": lambda s: s.update(B=_set_inner(s["B"], "x")),
    "endffloat_B": lambda s: s.update(
        B=_set_inner(s["B"], EndfFloat(1.0, " 1.00000000"))
    ),
    "int_B": lambda s: s.update(B=_set_inner(s["B"], 3)),
    "float_L": lambda s: s.update(L=_set_level2(s["L"], 2.5)),
    "large_L": lambda s: s.update(L=_set_level2(s["L"], -(2**33))),
    "str_C": lambda s: s.update(C=_set_level2(s["C"], "x")),
    "tuple_rows_B": lambda s: s.update(B=_map_rows(s["B"], tuple)),
    "subclass_B": lambda s: s.update(B=_map_rows(s["B"], _subclass)),
    "numpy_rows_L": lambda s: s.update(
        L=_map_rows(s["L"], lambda r: np.array(list(_values(r)), np.int64))
    ),
    "float_rows_L": lambda s: s.update(
        L=_map_rows(s["L"], lambda r: np.array(list(_values(r)), float))
    ),
}


def _second(arr):
    # key or index of the second element (i=2, the last non-empty row)
    return sorted(arr)[1] if isinstance(arr, dict) else 1


def _set_level2(arr, value):
    # value as the last element of the row i=2
    arr = copy.deepcopy(arr)
    i = _second(arr)
    row = arr[i]
    if isinstance(row, np.ndarray):
        row = row.astype(object)
        row[-1] = value
        arr[i] = row
        return arr
    row[_last(row)] = value
    return arr


def _set_inner(arr, value):
    # value as the last element of the last row of the row i=2
    arr = copy.deepcopy(arr)
    outer = arr[_second(arr)]
    inner = outer[_last(outer)]
    if isinstance(inner, np.ndarray):
        inner = inner.astype(object)
        inner[-1] = value
        outer[_last(outer)] = inner
        return arr
    inner[_last(inner)] = value
    return arr


def _short_inner(arr):
    arr = copy.deepcopy(arr)
    outer = arr[_second(arr)]
    outer[_last(outer)] = _drop_last(outer[_last(outer)])
    return arr


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("variant", sorted(MT3_VARIANTS))
def test_mt3_variants(mode, variant):
    sec = _section(3, mode)
    MT3_VARIANTS[variant](sec)
    res = _check(mode, sec, 3)
    if variant == "unchanged":
        expected = _parser("dict").write({7: {3: _mt3_dict()}})
        assert res == ("ok", [line[:72] + line[75:] for line in expected])


def _accessors(recipe):
    code = generate_cpp_writefun("test_write", recipe)
    return sorted(
        re.findall(
            r'CppArrayAccessor<(\d)> \w+\(cpp_index_shifter_store, "(\w+)"\)', code
        )
    )


def test_accessors_of_test_recipes():
    assert _accessors(mf7.ENDF_RECIPE_MF7_MT1) == [("1", "A"), ("1", "K"), ("2", "T")]
    assert _accessors(mf7.ENDF_RECIPE_MF7_MT2) == []
    assert _accessors(mf7.ENDF_RECIPE_MF7_MT3) == [("2", "C"), ("2", "L"), ("3", "B")]
    assert _accessors(mf7.ENDF_RECIPE_MF7_MT4) == []
    assert _accessors(mf7.ENDF_RECIPE_MF7_MT5) == [
        ("1", "E"),
        ("2", "Ep"),
        ("3", "b"),
    ]


_HEAD = "[MAT,MF,MT/ 0.0, 0.0, N, M, 0, 0] HEAD\n"


@pytest.mark.parametrize(
    "body, expected",
    [
        # variable occurring twice in the loop, in a condition, a loop
        # bound or an abbreviation
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            "    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            "endfor\n",
            [],
        ),
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ 0.0, 0.0, Y[i], 0, 0, 0] CONT\n"
            "    if Y[i] > 0:\n"
            "        [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            "    endif\n"
            "endfor\n",
            [("1", "X")],
        ),
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ X[i], 0.0, Y[i], 0, 0, 0] CONT\n"
            "    for j=1 to Y[i]:\n"
            "        [MAT,MF,MT/ Z[i,j], 0.0, 0, 0, 0, 0] CONT\n"
            "    endfor\n"
            "endfor\n",
            [("1", "X"), ("2", "Z")],
        ),
        (
            "W := X[i]\n"
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT\n"
            "    [MAT,MF,MT/ W, 0.0, 0, 0, 0, 0] CONT\n"
            "endfor\n",
            [],
        ),
        # the outermost loop in which the variable occurs once
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ X[i,1], 0.0, 0, 0, 0, 0] CONT\n"
            "    for j=2 to M:\n"
            "        [MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT\n"
            "    endfor\n"
            "endfor\n",
            [("2", "X")],
        ),
        # a loop containing a lookahead
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ X[i], 0.0, L, 0, 0, 0] CONT\n"
            "    if L == 1 [lookahead=1]:\n"
            "        [MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] CONT\n"
            "    endif\n"
            "endfor\n",
            [],
        ),
        # loops within a section or a named LIST record, not around them
        (
            "for i=1 to N:\n"
            "    (sub[i])\n"
            "    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NX, 0] CONT\n"
            "    for j=1 to NX:\n"
            "        [MAT,MF,MT/ X[j], 0.0, 0, 0, 0, 0] CONT\n"
            "    endfor\n"
            "    (/sub[i])\n"
            "endfor\n",
            [("1", "X")],
        ),
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NX[i], 0/ {X[k]}{k=1 to NX[i]} ] LIST (lst[i])\n"
            "endfor\n",
            [("1", "X")],
        ),
        # no accessor for variables without index or outside of loops
        ("[MAT,MF,MT/ X[1], Y, 0, 0, 0, 0] CONT\n", []),
    ],
)
def test_accessor_placement(body, expected):
    assert _accessors(_HEAD + body + "SEND\n") == expected


def _mt5_dict():
    sec = {"MAT": 1, "MF": 7, "MT": 5, "NE": 3}
    shape = {1: (2, 1), 2: (0, 2), 3: (3, 0)}  # NEP[j], NA[j]
    sec["E"] = {j: 1e6 * j for j in shape}
    sec["NEP"] = {j: nep for j, (nep, na) in shape.items()}
    sec["NA"] = {j: na for j, (nep, na) in shape.items()}
    sec["Ep"] = {
        j: {k: 10.0 * j + k for k in range(1, nep + 1)}
        for j, (nep, na) in shape.items()
    }
    sec["b"] = {
        j: {
            k: {m: j + k / 10 + m / 100 for m in range(na + 1)}
            for k in range(1, nep + 1)
        }
        for j, (nep, na) in shape.items()
    }
    return sec


@pytest.mark.parametrize("mode", MODES)
def test_mt5_list_records(mode):
    from endf_parserpy import EndfParserPy

    pyparser = EndfParserPy(
        endf_format="test",
        array_type="dict",
        print_cache_info=False,
        ignore_missing_tpid=True,
    )
    text = pyparser.write({7: {5: _mt5_dict()}})
    parser = _parser(mode)
    sec = parser.parse(text)[7][5]
    assert parser.write({7: {5: sec}}) == text
    # one row of b[1] fewer
    if isinstance(sec["b"], dict):
        del sec["b"][1][max(sec["b"][1])]
    else:
        sec["b"][0] = sec["b"][0][:-1]
    with pytest.raises((IndexError, KeyError)):
        parser.write({7: {5: sec}})
