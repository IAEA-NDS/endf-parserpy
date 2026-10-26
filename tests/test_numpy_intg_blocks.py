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

"""The values of INTG records as innermost dimension of a regular block.

With array_type="numpy", a record that yields a vector whose length is
known before the enclosing block and does not change within it adds an
innermost dimension to the block, as a loop over its values would. Of
the record types, only INTG records qualify (the number of values KIJ is
a fixed function of NDIGIT). The correlation values KIJ[k] of the INTG
records of MF32 with LCOMP=2, read in a loop over k = 1..NM after
NDIGIT, are therefore one int64 array of shape (NM, n(NDIGIT)) instead of
a list of NM one-dimensional arrays. If the conditions of a block are not
met (test recipes MF9/MT2 to MT4), KIJ remains a list of one-dimensional
arrays. The results with array_type="list" and "dict" are unchanged.
Both parsers give the same result, and the arrays as well as lists of
rows are written in the same way.
"""

import copy
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy

np = pytest.importorskip("numpy")


NUM_VALUES = {2: 18, 3: 13, 4: 11, 5: 9, 6: 8}
PARSERS = ("cpp", "python")

# R-Matrix Limited compact covariance (LCOMP=2) with INTG records, as in
# test_cpp_intg_reading.py; the CONT record with NDIGIT, NNN and NM and
# the INTG records follow
MF32_HEADER = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151\n"
    " 0.000000+0 0.000000+0          0          2          1          1263132151\n"
    " 0.000000+0 0.000000+0          0          0          2          1263132151\n"
    " 1.000000-2 2.000000-2                                            263132151\n"
    " 0.000000+0 0.000000+0          2          1         24          4263132151\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+0263132151\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+0263132151\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+0263132151\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+0263132151\n"
    " 5.000000-1 1.000000+0          0          0         12          2263132151\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0263132151\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-1263132151\n"
    " 0.000000+0 0.000000+0          0          1         12          1263132151\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151\n"
    " 1.000000+1 1.000000-2 5.000000-3 0.000000+0 0.000000+0 0.000000+0263132151\n"
)
MF32_TRAILER = (
    " 0.000000+0 0.000000+0          0          0          0          0263132  0\n"
)


def _parser(name, mode, endf_format="endf6"):
    kwargs = dict(
        endf_format=endf_format,
        array_type=mode,
        ignore_missing_tpid=True,
        ignore_send_records=True,
    )
    if name == "python":
        return EndfParserPy(print_cache_info=False, **kwargs)
    return EndfParserCpp(**kwargs)


def _kij_rows(ndigit, nm):
    n = NUM_VALUES[ndigit]
    top = 10**ndigit - 1
    return [
        [(31 * k + 17 * m) % (2 * top + 1) - top for m in range(n)] for k in range(nm)
    ]


def _mf32_text(ndigit, nm):
    lines = MF32_HEADER
    lines += " 0.000000+0 0.000000+0{:>11}{:>11}{:>11}{:>11}263132151\n".format(
        ndigit, 12, nm, 0
    )
    width = ndigit + 1
    start = 11 if ndigit <= 5 else 10
    for k, kij in enumerate(_kij_rows(ndigit, nm)):
        line = "{:>5}{:>5}".format(k + 2, 1).ljust(start)
        line += "".join(str(v).rjust(width) for v in kij)
        lines += line.ljust(66) + "263132151\n"
    return (lines + MF32_TRAILER).rstrip("\n")


def _range(endf_dict):
    sec = endf_dict[32][151]
    isotope = sec["isotope"]
    rng = (isotope[1] if isinstance(isotope, dict) else isotope[0])["range"]
    return rng[1] if isinstance(rng, dict) else rng[0]


def _exact(obj):
    if isinstance(obj, np.ndarray):
        return ("ndarray", str(obj.dtype), obj.shape, obj.tolist())
    if isinstance(obj, dict):
        return ("dict", {k: _exact(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ("list", [_exact(v) for v in obj])
    if isinstance(obj, float):
        return ("float", obj.hex())
    return (type(obj).__name__, obj)


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _canonical(text, endf_format="endf6"):
    # the text as written from the dict-mode result of the Python parser
    parser = _parser("python", "dict", endf_format)
    return _lines(parser.write(parser.parse(text)))


# ---------------------------------------------------------------------
# MF32 LCOMP=2: KIJ of the package recipes
# ---------------------------------------------------------------------


@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
@pytest.mark.parametrize("name", PARSERS)
def test_mf32_kij_is_two_dimensional(name, ndigit):
    nm = 5
    rng = _range(_parser(name, "numpy").parse(_mf32_text(ndigit, nm)))
    kij = rng["KIJ"]
    assert isinstance(kij, np.ndarray)
    assert kij.dtype == np.int64
    assert kij.shape == (nm, NUM_VALUES[ndigit])
    assert kij.tolist() == _kij_rows(ndigit, nm)
    # II and JJ are unchanged
    for key, values in (("II", list(range(2, nm + 2))), ("JJ", [1] * nm)):
        assert isinstance(rng[key], np.ndarray) and rng[key].dtype == np.int64
        assert rng[key].tolist() == values


@pytest.mark.parametrize("name", PARSERS)
def test_mf32_list_and_dict_unchanged(name):
    text = _mf32_text(3, 4)
    rows = _kij_rows(3, 4)
    kij = _range(_parser(name, "list").parse(text))["KIJ"]
    assert _exact(kij) == _exact(rows)
    kij = _range(_parser(name, "dict").parse(text))["KIJ"]
    assert _exact(kij) == _exact({k + 1: row for k, row in enumerate(rows)})


@pytest.mark.parametrize("ndigit", (2, 6))
def test_mf32_parsers_agree(ndigit):
    text = _mf32_text(ndigit, 7)
    results = [_parser(name, "numpy").parse(text) for name in PARSERS]
    assert _exact(results[0]) == _exact(results[1])


@pytest.mark.parametrize("name", PARSERS)
def test_mf32_without_intg_records(name):
    rng = _range(_parser(name, "numpy").parse(_mf32_text(2, 0)))
    assert "KIJ" not in rng


def _kij_forms(kij):
    # the 2-D array, a list of rows (lists and 1-D arrays) and other dtypes
    return {
        "2d": kij,
        "2d int32": kij.astype(np.int32),
        "2d transposed copy": np.asfortranarray(kij),
        "list of lists": kij.tolist(),
        "list of arrays": [row for row in kij],
    }


@pytest.mark.parametrize("writer_mode", ("numpy", "list"))
@pytest.mark.parametrize("writer", PARSERS)
@pytest.mark.parametrize("ndigit", (2, 4, 6))
def test_mf32_write_arrays_and_rows(ndigit, writer, writer_mode):
    text = _mf32_text(ndigit, 6)
    expected = _canonical(text)
    parsed = _parser("cpp", "numpy").parse(text)
    for form, kij in _kij_forms(_range(parsed)["KIJ"]).items():
        data = copy.deepcopy(parsed)
        _range(data)["KIJ"] = kij
        written = _lines(_parser(writer, writer_mode).write(data))
        assert written == expected, form


@pytest.mark.parametrize("name", PARSERS)
def test_mf32_round_trip(name):
    text = _mf32_text(5, 9)
    parser = _parser(name, "numpy")
    first = parser.parse(text)
    second = parser.parse("\n".join(_lines(parser.write(first))))
    assert _exact(first) == _exact(second)


# ---------------------------------------------------------------------
# test recipes MF9 (endf_recipes/test/endf_recipe_mf9.py)
# ---------------------------------------------------------------------


def _rows(ndigits, offset):
    rows = []
    for k, ndigit in enumerate(ndigits):
        top = 10**ndigit - 1
        n = NUM_VALUES[ndigit]
        rows.append([(offset + 13 * k + 7 * m) % top for m in range(n)])
    return rows


def _mf9_section(mt, **kw):
    d = {"MAT": 1, "MF": 9, "MT": mt}
    if mt == 1:
        nms, ndigit = kw["nms"], kw["ndigit"]
        d.update({"NDIGIT": ndigit, "N": len(nms), "NM": {}})
        d.update({"II": {}, "JJ": {}, "KIJ": {}})
        for i, nm in enumerate(nms, start=1):
            d["NM"][i] = nm
            for k, row in enumerate(_rows([ndigit] * nm, i), start=1):
                d["II"].setdefault(i, {})[k] = k
                d["JJ"].setdefault(i, {})[k] = i
                d["KIJ"].setdefault(i, {})[k] = row
        return d
    ndigits = kw["ndigits"]
    d["NM"] = len(ndigits)
    d["NDIGIT"] = ndigits[0]
    if mt == 4:
        d["L"] = kw["L"]
    rows = _rows(ndigits, 1)
    d["II"] = {k: k for k in range(1, len(rows) + 1)}
    d["JJ"] = {k: 1 for k in range(1, len(rows) + 1)}
    d["KIJ"] = {k: row for k, row in enumerate(rows, start=1)}
    return d


MF9_CASES = {
    "MT1": (1, dict(nms=[2, 0, 3], ndigit=3)),
    "MT1 all empty": (1, dict(nms=[0, 0], ndigit=2)),
    "MT2": (2, dict(ndigits=[3, 3, 3])),
    "MT3": (3, dict(ndigits=[4, 4])),
    "MT4 L=1": (4, dict(ndigits=[5, 5, 5], L=1)),
    "MT4 L=2": (4, dict(ndigits=[5, 5, 5], L=2)),
}


def _mf9_text(case):
    mt, kw = MF9_CASES[case]
    writer = _parser("python", "dict", "test")
    return "\n".join(_lines(writer.write({9: {mt: _mf9_section(mt, **kw)}})))


def _expected_kij(case):
    mt, kw = MF9_CASES[case]
    if mt == 1:
        n = NUM_VALUES[kw["ndigit"]]
        return [
            ("ndarray", "int64", (nm, n), _rows([kw["ndigit"]] * nm, i))
            for i, nm in enumerate(kw["nms"], start=1)
        ]
    rows = _rows(kw["ndigits"], 1)
    if mt == 4 and kw["L"] == 1:
        return ("ndarray", "int64", (len(rows), len(rows[0])), rows)
    return [("ndarray", "int64", (len(row),), row) for row in rows]


def _plain_kij(kij):
    if isinstance(kij, list):
        return [_plain_kij(v) for v in kij]
    return ("ndarray", str(kij.dtype), kij.shape, kij.tolist())


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("case", sorted(MF9_CASES))
def test_mf9_kij_layout(case, name):
    mt = MF9_CASES[case][0]
    sec = _parser(name, "numpy", "test").parse(_mf9_text(case))[9][mt]
    assert _plain_kij(sec["KIJ"]) == _expected_kij(case)


@pytest.mark.parametrize("mode", ("numpy", "list", "dict"))
@pytest.mark.parametrize("case", sorted(MF9_CASES))
def test_mf9_parsers_agree_and_round_trip(case, mode):
    text = _mf9_text(case)
    results = [_parser(name, mode, "test").parse(text) for name in PARSERS]
    assert _exact(results[0]) == _exact(results[1])
    expected = _canonical(text, "test")
    for name in PARSERS:
        written = _lines(_parser(name, mode, "test").write(results[0]))
        assert written == expected, name


def test_mf9_kij_read_twice():
    # MT5: KIJ occurs twice, so it is no block. The second loop checks the
    # values read by the first one, which EndfParserPy does; EndfParserCpp
    # does not implement the check of vectors and raises an error, as for
    # the former container of KIJ (the generated code uses the rows of the
    # array of rows by their indices, see NestedArray::contains)
    d = _mf9_section(3, ndigits=[2, 2])
    d["MT"] = 5
    text = "\n".join(_lines(_parser("python", "dict", "test").write({9: {5: d}})))
    sec = _parser("python", "numpy", "test").parse(text)[9][5]
    expected = [("ndarray", "int64", (18,), row) for row in _rows([2, 2], 1)]
    assert _plain_kij(sec["KIJ"]) == expected
    with pytest.raises(RuntimeError):
        _parser("cpp", "numpy", "test").parse(text)
