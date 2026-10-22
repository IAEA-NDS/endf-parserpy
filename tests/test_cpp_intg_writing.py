############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/22
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Writing INTG records (MF32 LCOMP=2) with EndfParserCpp for all NDIGIT.

The writer retrieves the row of integers KIJ of an INTG record once per
record and reads its elements with fast paths for lists and numpy arrays
of an integer type, and the values II and JJ once per record. The output
must be the same for all representations of the rows (lists, tuples,
numpy arrays of various integer types, rows of a two-dimensional numpy
array) and for all values 2 to 6 of NDIGIT, and data that cannot be
written must still raise an error.
"""

import random
from collections.abc import Sequence
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


# R-Matrix Limited compact covariance (LCOMP=2) without INTG records;
# NDIGIT, NNN, NM and the INTG records are set by the tests
MF32_LCOMP2_RML = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151    3\n"
    " 0.000000+0 0.000000+0          0          2          1          1263132151    4\n"
    " 0.000000+0 0.000000+0          0          0          2          1263132151    5\n"
    " 1.000000-2 2.000000-2                                            263132151    6\n"
    " 0.000000+0 0.000000+0          2          1         24          4263132151    7\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+0263132151    8\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+0263132151    9\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+0263132151   10\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+0263132151   11\n"
    " 5.000000-1 1.000000+0          0          0         12          2263132151   12\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0263132151   13\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-1263132151   14\n"
    " 0.000000+0 0.000000+0          0          1         12          1263132151   15\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151   16\n"
    " 1.000000+1 1.000000-2 5.000000-3 0.000000+0 0.000000+0 0.000000+0263132151   17\n"
    " 0.000000+0 0.000000+0          2          0          0          0263132151   18\n"
    " 0.000000+0 0.000000+0          0          0          0          0263132  099999"
)

NDIGITS = [2, 3, 4, 5, 6]
NUM_LINES = 7


# number of KIJ fields of an INTG record (ENDF-102, Section 0.6.4.9)
NUM_VALUES = {2: 18, 3: 13, 4: 11, 5: 9, 6: 8}


def _num_values(ndigit):
    return NUM_VALUES[ndigit]


def _make_parser(array_type):
    return EndfParserCpp(
        ignore_send_records=True, ignore_missing_tpid=True, array_type=array_type
    )


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _range(endf_dict):
    isotope = endf_dict[32][151]["isotope"]
    rng = (isotope[1] if isinstance(isotope, dict) else isotope[0])["range"]
    return rng[1] if isinstance(rng, dict) else rng[0]


def _intg_data(ndigit, nonnegative=False):
    rnd = random.Random(1000 + ndigit)
    maxval = 10**ndigit - 1
    minval = 0 if nonnegative else -maxval
    n = _num_values(ndigit)
    rows = []
    for k in range(NUM_LINES):
        if k == 0:
            row = [maxval, minval] + [0] * (n - 2)
        else:
            row = [rnd.choice((0, rnd.randint(minval, maxval))) for _ in range(n)]
        rows.append(row)
    ii = [5 + k for k in range(NUM_LINES)]
    jj = [1 + k for k in range(NUM_LINES)]
    return ii, jj, rows


def _set_intg(rng, ndigit, ii, jj, kij, array_type):
    rng["NDIGIT"] = ndigit
    rng["NNN"] = 12
    rng["NM"] = len(kij)
    if array_type == "dict":
        rng["II"] = {k + 1: v for k, v in enumerate(ii)}
        rng["JJ"] = {k + 1: v for k, v in enumerate(jj)}
        rng["KIJ"] = {k + 1: v for k, v in enumerate(kij)}
    else:
        rng["II"] = list(ii)
        rng["JJ"] = list(jj)
        rng["KIJ"] = kij


def _write(ndigit, kij, array_type="list", ii=None, jj=None):
    nii, njj, _ = _intg_data(ndigit)
    ii = nii if ii is None else ii
    jj = njj if jj is None else jj
    parser = _make_parser(array_type)
    endf_dict = parser.parse(MF32_LCOMP2_RML)
    _set_intg(_range(endf_dict), ndigit, ii, jj, kij, array_type)
    return _lines(parser.write(endf_dict))


def _reference_lines(ndigit, nonnegative=False):
    _, _, rows = _intg_data(ndigit, nonnegative)
    return _write(ndigit, [list(r) for r in rows])


@pytest.mark.parametrize("ndigit", NDIGITS)
def test_intg_records_written(ndigit):
    ii, jj, rows = _intg_data(ndigit)
    lines = _reference_lines(ndigit)
    # one INTG record per row, following the CONT record with NDIGIT
    intg_lines = lines[18 : 18 + NUM_LINES]
    assert len(intg_lines) == NUM_LINES
    width = ndigit + 1
    start = 11 if ndigit <= 5 else 10
    for k, line in enumerate(intg_lines):
        assert len(line) == 80
        assert int(line[0:5]) == ii[k]
        assert int(line[5:10]) == jj[k]
        assert line[66:75] == "263132151"
        for m, value in enumerate(rows[k]):
            pos = start + m * width
            assert int(line[pos : pos + width]) == value
        # the columns after the last field are blank
        assert line[start + len(rows[k]) * width : 66].strip() == ""
    # same output as the Python writer
    _, _, rows = _intg_data(ndigit)
    py_parser = EndfParserPy(ignore_send_records=True, ignore_missing_tpid=True)
    endf_dict = py_parser.parse(MF32_LCOMP2_RML)
    _set_intg(_range(endf_dict), ndigit, ii, jj, rows, "dict")
    assert _lines(py_parser.write(endf_dict)) == lines


def _numpy_variants():
    np = pytest.importorskip("numpy")
    return {
        "int64": lambda rows: [np.array(r, dtype=np.int64) for r in rows],
        "int32": lambda rows: [np.array(r, dtype=np.int32) for r in rows],
        "smallest": lambda rows: [
            np.array(r, dtype=np.min_scalar_type(-max(map(abs, r)) - 1)) for r in rows
        ],
        "intc": lambda rows: [np.array(r, dtype=np.intc) for r in rows],
        "2d": lambda rows: np.array(rows, dtype=np.int64),
        "strided": lambda rows: np.array(
            [[v for v in r for _ in range(2)] for r in rows], dtype=np.int64
        )[:, ::2],
        "object": lambda rows: [np.array(r, dtype=object) for r in rows],
    }


class _ReadOnlySequence(Sequence):
    def __init__(self, data):
        self._data = data

    def __getitem__(self, i):
        return self._data[i]

    def __len__(self):
        return len(self._data)


ROW_VARIANTS = {
    "tuple": lambda rows: [tuple(r) for r in rows],
    "sequence": lambda rows: [_ReadOnlySequence(list(r)) for r in rows],
}


@pytest.mark.parametrize("ndigit", NDIGITS)
@pytest.mark.parametrize("variant", list(ROW_VARIANTS) + ["numpy"])
def test_intg_rows_as_other_objects(ndigit, variant):
    expected = _reference_lines(ndigit)
    _, _, rows = _intg_data(ndigit)
    if variant == "numpy":
        for name, conv in _numpy_variants().items():
            assert _write(ndigit, conv(rows)) == expected, name
    else:
        assert _write(ndigit, ROW_VARIANTS[variant](rows)) == expected


@pytest.mark.parametrize("ndigit", NDIGITS)
def test_intg_rows_unsigned_numpy(ndigit):
    np = pytest.importorskip("numpy")
    expected = _reference_lines(ndigit, nonnegative=True)
    _, _, rows = _intg_data(ndigit, nonnegative=True)
    for dtype in (np.uint32, np.uint64) if ndigit > 4 else (np.uint16, np.uint64):
        kij = [np.array(r, dtype=dtype) for r in rows]
        assert _write(ndigit, kij) == expected


@pytest.mark.parametrize("ndigit", NDIGITS)
def test_intg_rows_in_dict_mode(ndigit):
    expected = _reference_lines(ndigit)
    _, _, rows = _intg_data(ndigit)
    assert _write(ndigit, [list(r) for r in rows], array_type="dict") == expected


@pytest.mark.parametrize("ndigit", NDIGITS)
@pytest.mark.parametrize("mode", ["dict", "list", "numpy"])
def test_intg_roundtrip(ndigit, mode):
    if mode == "numpy":
        pytest.importorskip("numpy")
    text = "\n".join(_reference_lines(ndigit))
    parser = _make_parser(mode)
    endf_dict = parser.parse(text)
    assert _range(endf_dict)["NDIGIT"] == ndigit
    kij = _range(endf_dict)["KIJ"]
    first_row = kij[min(kij)] if isinstance(kij, dict) else kij[0]
    assert len(first_row) == NUM_VALUES[ndigit]
    assert _lines(parser.write(endf_dict)) == text.splitlines()


@pytest.mark.parametrize("ndigit", NDIGITS)
def test_intg_row_too_short(ndigit):
    np = pytest.importorskip("numpy")
    _, _, rows = _intg_data(ndigit)
    short = [list(r) for r in rows]
    short[3] = short[3][:-1]
    with pytest.raises(Exception):
        _write(ndigit, short)
    with pytest.raises(Exception):
        _write(ndigit, [np.array(r, dtype=np.int64) for r in short])
    with pytest.raises(Exception):
        _write(ndigit, [tuple(r) for r in short])


def test_intg_invalid_values():
    np = pytest.importorskip("numpy")
    ndigit = 2
    _, _, rows = _intg_data(ndigit)
    # values outside the range of int
    big = [np.array(r, dtype=np.int64) for r in rows]
    big[2][4] = 2**40
    with pytest.raises(Exception):
        _write(ndigit, big)
    bigu = [np.array([abs(v) for v in r], dtype=np.uint64) for r in rows]
    bigu[2][4] = 2**63
    with pytest.raises(Exception):
        _write(ndigit, bigu)
    big_list = [list(r) for r in rows]
    big_list[2][4] = 2**40
    with pytest.raises(Exception):
        _write(ndigit, big_list)
    # floats are not accepted in integer fields
    with pytest.raises(Exception):
        _write(ndigit, [np.array(r, dtype=np.float64) for r in rows])
    float_list = [list(r) for r in rows]
    float_list[1][0] = 1.0
    with pytest.raises(Exception):
        _write(ndigit, float_list)


@pytest.mark.parametrize("ndigit", [1, 7])
def test_intg_invalid_ndigit(ndigit):
    _, _, rows = _intg_data(2)
    with pytest.raises(Exception):
        _write(ndigit, [list(r) for r in rows])


@pytest.mark.parametrize("ndigit", NDIGITS)
@pytest.mark.parametrize("field", ["KIJ", "II"])
@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_intg_value_too_wide(ndigit, field, ParserCls):
    # values that do not fit into their field raise an error instead of
    # shifting the following fields
    ii, jj, rows = _intg_data(ndigit)
    rows = [list(r) for r in rows]
    if field == "KIJ":
        rows[1][2] = 10 ** (ndigit + 1)
    else:
        ii = list(ii)
        ii[1] = 10**5
    if ParserCls is EndfParserPy:
        parser = EndfParserPy(
            ignore_send_records=True, ignore_missing_tpid=True, print_cache_info=False
        )
        array_type = "dict"
    else:
        parser = _make_parser("list")
        array_type = "list"
    endf_dict = parser.parse(MF32_LCOMP2_RML)
    _set_intg(_range(endf_dict), ndigit, ii, jj, rows, array_type)
    with pytest.raises(Exception, match="does not fit"):
        parser.write(endf_dict)
