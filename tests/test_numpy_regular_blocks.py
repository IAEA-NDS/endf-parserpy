############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regular blocks of trailing indices with array_type="numpy".

If the code generator can prove that the trailing indices of a variable
form a rectangular array for each value of the leading indices, this
block is a single numpy array, e.g. b[j] of MF6 LAW=1, an array of shape
(NEP[j], NA[j]+1) for each incident energy j, or a covariance matrix of
MF33 with LB=5/LS=0. A block whose loops have no iterations is an empty
array of the shape given by the loop limits, e.g. (0, NA[j]+1) for
NEP[j]=0 and (NEP[j], 0) for NA[j]=-1; with array_type="list" and
"dict", the result is the same as before (empty lists or dictionaries).
Both parsers return the same result (with array_type="list" and
"numpy") and write it back unchanged.
"""

import copy
from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfFloat

np = pytest.importorskip("numpy")


TESTDATA = Path(__file__).parent / "testdata"
MODES = ("dict", "list", "numpy")
# with array_type="dict", EndfParserCpp keeps the empty elements of nested
# arrays created before the loops, EndfParserPy omits them (as before)
SAME_RESULT_MODES = ("list", "numpy")
PARSERS = ("cpp", "python")


def _parser(name, mode):
    if name == "python":
        return EndfParserPy(
            array_type=mode, print_cache_info=False, ignore_missing_tpid=True
        )
    return EndfParserCpp(array_type=mode, ignore_missing_tpid=True)


def _text(endf_dict):
    writer = EndfParserPy(array_type="dict", print_cache_info=False, check_arrays=False)
    return "\n".join(writer.write(endf_dict))


def _exact(obj):
    if isinstance(obj, np.ndarray):
        return ("ndarray", str(obj.dtype), obj.shape, _exact(obj.tolist()))
    if isinstance(obj, EndfFloat):
        return ("EndfFloat", float(obj).hex(), obj.get_original_string())
    if isinstance(obj, float):
        return ("float", obj.hex())
    if isinstance(obj, dict):
        return ("dict", {k: _exact(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ("list", [_exact(v) for v in obj])
    return (type(obj).__name__, obj)


_RESULTS = {}


def _parse(text, name, mode):
    key = (text, name, mode)
    if key not in _RESULTS:
        _RESULTS[key] = _parser(name, mode).parse(text)
    return copy.deepcopy(_RESULTS[key])


# ---------------------------------------------------------------------
# MF6 LAW=1: b[j] of each incident energy j
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def mf6_section():
    # MF6/MT16 of Cu-63: three subsections with LAW=1
    parser = EndfParserCpp(array_type="dict")
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    return parser.parsefile(path, include=[(6, 16)])[6][16]


MF6_CASES = [
    (what, where)
    for what in ("NEP=0", "NA=-1")
    for where in ("first", "middle", "last")
]


def _mf6_text(section, what, where):
    section = copy.deepcopy(section)
    sub = section["subsection"][1]
    assert sub["LAW"] == 1
    j = {"first": 1, "middle": sub["NE"] // 2, "last": sub["NE"]}[where]
    if what == "NEP=0":
        sub["NEP"][j] = 0
        del sub["Ep"][j]
    else:
        sub["NA"][j] = -1
    del sub["b"][j]
    return _text({6: {16: section}}), j


def _mf6_b(result):
    return result[6][16]["subsection"][0]["b"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("case", MF6_CASES, ids=str)
def test_mf6_roundtrip(mf6_section, case, name, mode):
    text, _ = _mf6_text(mf6_section, *case)
    result = _parse(text, name, mode)
    written = _parser(name, mode).write(result)
    assert "\n".join(written) == text


@pytest.mark.parametrize("mode", SAME_RESULT_MODES)
@pytest.mark.parametrize("case", MF6_CASES, ids=str)
def test_mf6_same_result_both_parsers(mf6_section, case, mode):
    text, _ = _mf6_text(mf6_section, *case)
    assert _exact(_parse(text, "python", mode)) == _exact(_parse(text, "cpp", mode))


@pytest.mark.parametrize("case", MF6_CASES, ids=str)
def test_mf6_list_slow_as_list(mf6_section, case):
    # EndfParserPy with the internal representation of arrays as lists
    text, _ = _mf6_text(mf6_section, *case)
    assert _exact(_parse(text, "python", "list_slow")) == _exact(
        _parse(text, "python", "list")
    )


@pytest.mark.parametrize("case", MF6_CASES, ids=str)
def test_mf6_block_shapes(mf6_section, case):
    text, j = _mf6_text(mf6_section, *case)
    sub = _parse(text, "cpp", "list")[6][16]["subsection"][0]
    b_numpy = _mf6_b(_parse(text, "cpp", "numpy"))
    b_list = _mf6_b(_parse(text, "cpp", "list"))
    for i, (blk, lst) in enumerate(zip(b_numpy, b_list)):
        shape = (sub["NEP"][i], sub["NA"][i] + 1)
        assert isinstance(blk, np.ndarray) and blk.dtype == np.float64
        assert blk.shape == shape
        assert blk.tolist() == lst
    if case[0] == "NEP=0":
        assert b_numpy[j - 1].shape == (0, sub["NA"][j - 1] + 1)
        assert b_list[j - 1] == []
    else:
        nep = sub["NEP"][j - 1]
        assert b_numpy[j - 1].shape == (nep, 0)
        assert b_list[j - 1] == [[] for _ in range(nep)]


# ---------------------------------------------------------------------
# MF33: matrices of LB=5 (LS=0 and LS=1) and LB=6
# ---------------------------------------------------------------------


def _mf33_section():
    ni = {
        # asymmetric matrix: one 2x2 block
        1: {"LS": 0, "LB": 5, "NE": 3, "E": {1: 1.0, 2: 2.0, 3: 3.0}},
        # upper triangle: rows of 3, 2 and 1 elements
        2: {"LS": 1, "LB": 5, "NE": 4, "E": {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}},
        # rectangular matrix of 2x1 elements
        3: {"LB": 6, "NER": 3, "NEC": 2, "ER": {1: 1.0, 2: 2.0, 3: 3.0}},
    }
    ni[3]["EC"] = {1: 1.5, 2: 2.5}
    ni[1]["F"] = {k: {kp: 0.1 * k + 0.01 * kp for kp in (1, 2)} for k in (1, 2)}
    ni[2]["F"] = {k: {kp: 0.1 * k + 0.01 * kp for kp in range(k, 4)} for k in (1, 2, 3)}
    ni[3]["F"] = {k: {1: 0.5 * k} for k in (1, 2)}
    sub = {"XMF1": 0.0, "XLFS1": 0.0, "MAT1": 0, "MT1": 1, "NC": 0, "NI": 3}
    sub["ni_subsection"] = ni
    section = {"MAT": 2925, "MF": 33, "MT": 1, "ZA": 29063.0, "AWR": 62.389}
    section.update({"MTL": 0, "NL": 1, "subsection": {1: sub}})
    return {33: {1: section}}


@pytest.fixture(scope="module")
def mf33_text():
    return _text(_mf33_section())


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", PARSERS)
def test_mf33_roundtrip(mf33_text, name, mode):
    result = _parse(mf33_text, name, mode)
    assert "\n".join(_parser(name, mode).write(result)) == mf33_text


@pytest.mark.parametrize("mode", MODES)
def test_mf33_same_result_both_parsers(mf33_text, mode):
    py_result = _parse(mf33_text, "python", mode)
    assert _exact(py_result) == _exact(_parse(mf33_text, "cpp", mode))


def test_mf33_matrix_forms(mf33_text):
    ni = _parse(mf33_text, "cpp", "numpy")[33][1]["subsection"][0]["ni_subsection"]
    ni_list = _parse(mf33_text, "cpp", "list")[33][1]["subsection"][0]
    ni_list = ni_list["ni_subsection"]
    assert isinstance(ni[0]["F"], np.ndarray) and ni[0]["F"].shape == (2, 2)
    assert isinstance(ni[1]["F"], list)
    assert [row.shape for row in ni[1]["F"]] == [(3,), (2,), (1,)]
    assert isinstance(ni[2]["F"], np.ndarray) and ni[2]["F"].shape == (2, 1)
    for numpy_sub, list_sub in zip(ni, ni_list):
        f = numpy_sub["F"]
        f = f.tolist() if isinstance(f, np.ndarray) else [r.tolist() for r in f]
        assert f == list_sub["F"]


# ---------------------------------------------------------------------
# MF7/MT2: S[q,i] is not a block: its limit NP is the size of the table
# of the TAB1 record before the loop over i, which is not an assignment
# of NP, and NP is first read in the LIST record in the loop
# ---------------------------------------------------------------------


def _mf7_section(lthr):
    # coherent elastic scattering at T0 and LT=2 further temperatures
    np_, lt = 3, 2
    section = {"MAT": 1325, "MF": 7, "MT": 2, "ZA": 13027.0, "AWR": 26.75}
    section.update({"LTHR": lthr, "T0": 20.0, "LT": lt, "NP": np_, "LI": 2})
    section["S_T0_table"] = {
        "Eint": [0.0037, 0.0050, 0.0100],
        "S": [0.0053, 0.0088, 0.0135],
        "INT": [1],
        "NBT": [np_],
    }
    section["T"] = {1: 80.0, 2: 293.6}
    section["S"] = {q: {i: 0.001 * q + 0.0001 * i for i in (1, 2)} for q in (1, 2, 3)}
    if lthr == 3:
        section.update({"SB": 0.0082, "Tint": [20.0, 400.0, 800.0]})
        section.update({"Wp": [0.1, 0.2, 0.3], "INT": [2], "NBT": [np_]})
    return {7: {2: section}}


@pytest.fixture(scope="module", params=[1, 3], ids=["LTHR=1", "LTHR=3"])
def mf7_text(request):
    return _text(_mf7_section(request.param))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", PARSERS)
def test_mf7_roundtrip(mf7_text, name, mode):
    result = _parse(mf7_text, name, mode)
    assert "\n".join(_parser(name, mode).write(result)) == mf7_text


@pytest.mark.parametrize("mode", SAME_RESULT_MODES)
def test_mf7_same_result_both_parsers(mf7_text, mode):
    py_result = _parse(mf7_text, "python", mode)
    assert _exact(py_result) == _exact(_parse(mf7_text, "cpp", mode))


@pytest.mark.parametrize("name", PARSERS)
def test_mf7_layout(mf7_text, name):
    s_numpy = _parse(mf7_text, name, "numpy")[7][2]["S"]
    s_list = _parse(mf7_text, name, "list")[7][2]["S"]
    assert isinstance(s_numpy, list) and len(s_numpy) == 3
    assert all(isinstance(row, np.ndarray) and row.shape == (2,) for row in s_numpy)
    assert [row.tolist() for row in s_numpy] == s_list
