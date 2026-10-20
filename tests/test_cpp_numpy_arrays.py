############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests for the option `array_type="numpy"` of EndfParserCpp.

With this option, arrays of numbers are returned as numpy arrays and
all other arrays as lists. Apart from the types of the containers, the
result is the same as with `array_type="list"`, and data parsed with
either option are written in the same way.
"""

import sys
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")

from endf_parserpy import (
    EndfParserCpp,
    EndfParserPy,
    EndfParserFactory,
    EndfFloat,
)


TESTDATA = Path(__file__).parent / "testdata"
FILES = ["n_2925_29-Cu-63.endf", "tsl_Al.endf"]


def _to_lists(obj):
    """Map numpy arrays recursively to (nested) lists of Python numbers."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_lists(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_lists(v) for v in obj]
    return obj


def _exact(obj):
    """Representation for comparing floats exactly, incl. -0.0 and NaN."""
    if isinstance(obj, float):
        return ("float", obj.hex())
    if isinstance(obj, EndfFloat):
        return ("EndfFloat", float(obj).hex(), obj.get_original_string())
    if isinstance(obj, dict):
        return {k: _exact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_exact(v) for v in obj]
    return (type(obj).__name__, obj)


def _assert_same(numpy_dict, list_dict):
    assert _exact(_to_lists(numpy_dict)) == _exact(list_dict)


def _iter_values(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_values(v)
    elif isinstance(obj, list):
        yield obj
        for v in obj:
            yield from _iter_values(v)
    else:
        yield obj


# MF33 section with the three matrix layouts of NI-type subsections:
# LB=5/LS=0 (rectangular NE-1 x NE-1), LB=5/LS=1 (upper triangle) and
# LB=6 (rectangular NER-1 x NEC-1)
def _mf33_section():
    ni_rect = {
        "LS": 0,
        "LB": 5,
        "NE": 4,
        "E": [1e-5, 1.0, 1e3, 2e7],
        "F": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, -0.9]],
    }
    ni_tri = {
        "LS": 1,
        "LB": 5,
        "NE": 4,
        "E": [1e-5, 1.0, 1e3, 2e7],
        "F": [[0.1, 0.2, 0.3], [0.5, 0.6], [0.9]],
    }
    ni_lb6 = {
        "LB": 6,
        "NER": 3,
        "NEC": 4,
        "ER": [1e-5, 1.0, 2e7],
        "EC": [1e-5, 1.0, 1e3, 2e7],
        "F": [[0.01, 0.02, 0.03], [0.04, 0.05, 0.06]],
    }
    subsection = {
        "XMF1": 0.0,
        "XLFS1": 0.0,
        "MAT1": 0,
        "MT1": 102,
        "NC": 0,
        "NI": 3,
        "ni_subsection": [ni_rect, ni_tri, ni_lb6],
    }
    return {
        "MAT": 2925,
        "MF": 33,
        "MT": 102,
        "ZA": 29063.0,
        "AWR": 62.389,
        "MTL": 0,
        "NL": 1,
        "subsection": [subsection],
    }


@pytest.fixture(scope="module")
def mf33_text():
    parser = EndfParserCpp(array_type="list")
    return "\n".join(parser.write({33: {102: _mf33_section()}}))


def _parse_opts(**kwargs):
    return dict(ignore_missing_tpid=True, **kwargs)


@pytest.mark.parametrize("filename", FILES)
def test_parse_results_equal_list_mode(filename):
    path = str(TESTDATA / filename)
    list_dict = EndfParserCpp(array_type="list").parsefile(path)
    numpy_parser = EndfParserCpp(array_type="numpy")
    numpy_dict = numpy_parser.parsefile(path)
    _assert_same(numpy_dict, list_dict)
    from_string = numpy_parser.parse(Path(path).read_text())
    _assert_same(from_string, list_dict)


@pytest.mark.parametrize("filename", FILES)
def test_all_arrays_of_numbers_are_numpy_arrays(filename):
    path = str(TESTDATA / filename)
    numpy_dict = EndfParserCpp(array_type="numpy").parsefile(path)
    for value in _iter_values(numpy_dict):
        if isinstance(value, list):
            # lists contain no numbers, only sections, arrays or strings
            assert not any(isinstance(v, (int, float)) for v in value)
        elif isinstance(value, np.ndarray):
            assert value.dtype in (np.float64, np.int64)


def test_dtypes_of_known_arrays():
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    endf_dict = EndfParserCpp(array_type="numpy").parsefile(path)
    xstable = endf_dict[3][1]["xstable"]
    for name, dtype in (("E", np.float64), ("xs", np.float64)):
        assert isinstance(xstable[name], np.ndarray)
        assert xstable[name].dtype == dtype
        assert xstable[name].ndim == 1
    for name in ("NBT", "INT"):
        assert isinstance(xstable[name], np.ndarray)
        assert xstable[name].dtype == np.int64
    # MF4 Legendre coefficients: one array per incident energy
    al = endf_dict[4][2]["al"]
    assert isinstance(al, list)
    assert all(isinstance(row, np.ndarray) for row in al)
    assert all(row.dtype == np.float64 for row in al)
    assert len(set(len(row) for row in al)) > 1


def test_matrices(mf33_text):
    list_dict = EndfParserCpp(**_parse_opts(array_type="list")).parse(mf33_text)
    numpy_dict = EndfParserCpp(**_parse_opts(array_type="numpy")).parse(mf33_text)
    _assert_same(numpy_dict, list_dict)
    ni_list = list_dict[33][102]["subsection"][0]["ni_subsection"]
    ni_numpy = numpy_dict[33][102]["subsection"][0]["ni_subsection"]
    # rectangular matrices (LB=5/LS=0, LB=6) are two-dimensional arrays
    for k, shape in ((0, (3, 3)), (2, (2, 3))):
        F = ni_numpy[k]["F"]
        assert isinstance(F, np.ndarray)
        assert F.dtype == np.float64
        assert F.shape == shape
        assert [row.tolist() for row in F] == ni_list[k]["F"]
    # triangular matrix (LB=5/LS=1): list of rows of decreasing length
    F = ni_numpy[1]["F"]
    assert isinstance(F, list)
    assert all(isinstance(row, np.ndarray) for row in F)
    assert [len(row) for row in F] == [3, 2, 1]
    assert [row.tolist() for row in F] == ni_list[1]["F"]


@pytest.mark.parametrize("keep_e_opt", [False, True])
@pytest.mark.parametrize("filename", FILES)
def test_roundtrip_same_output_as_list_mode(filename, keep_e_opt, tmp_path):
    path = str(TESTDATA / filename)
    list_parser = EndfParserCpp(array_type="list", keep_E=keep_e_opt)
    numpy_parser = EndfParserCpp(array_type="numpy", keep_E=keep_e_opt)
    list_dict = list_parser.parsefile(path)
    numpy_dict = numpy_parser.parsefile(path)
    expected = list_parser.write(list_dict)
    assert numpy_parser.write(numpy_dict) == expected
    # a parser in list mode writes numpy arrays in the same way
    assert list_parser.write(numpy_dict) == expected
    list_parser.writefile(tmp_path / "list.endf", list_dict)
    numpy_parser.writefile(tmp_path / "numpy.endf", numpy_dict)
    assert (tmp_path / "numpy.endf").read_bytes() == (
        tmp_path / "list.endf"
    ).read_bytes()


def test_roundtrip_matrices(mf33_text):
    numpy_parser = EndfParserCpp(**_parse_opts(array_type="numpy"))
    list_parser = EndfParserCpp(**_parse_opts(array_type="list"))
    expected = list_parser.write(list_parser.parse(mf33_text))
    assert numpy_parser.write(numpy_parser.parse(mf33_text)) == expected


INT_DTYPES = ["int8", "int16", "int32", "uint8", "uint16", "uint32", "int64", "uint64"]


@pytest.mark.parametrize("dtype", INT_DTYPES)
def test_writing_integer_arrays_of_other_dtypes(dtype):
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    parser = EndfParserCpp(array_type="numpy")
    endf_dict = parser.parsefile(path, include=(3, 4))
    expected = parser.write(endf_dict)
    # integer arrays in integer fields: TAB1 interpolation tables
    # (written as a whole) and the array NL (element by element)
    for mt in sorted(endf_dict[3]):
        xstable = endf_dict[3][mt]["xstable"]
        if xstable["NBT"].max() <= np.iinfo(dtype).max:
            xstable["NBT"] = xstable["NBT"].astype(dtype)
        xstable["INT"] = xstable["INT"].astype(dtype)
    assert any(endf_dict[3][mt]["xstable"]["NBT"].dtype == dtype for mt in endf_dict[3])
    mf4 = endf_dict[4][2]
    mf4["NL"] = mf4["NL"].astype(dtype)
    # integer arrays in float fields: a TAB1 column and Legendre coefficients
    mf3 = endf_dict[3][2]["xstable"]
    mf3["xs"] = np.zeros(len(mf3["xs"]), dtype=dtype)
    mf4["al"][0] = np.zeros(len(mf4["al"][0]), dtype=dtype)
    ref_dict = parser.parsefile(path, include=(3, 4))
    ref_dict[3][2]["xstable"]["xs"] = [0.0] * len(mf3["xs"])
    ref_dict[4][2]["al"][0] = [0.0] * len(mf4["al"][0])
    assert parser.write(endf_dict) == parser.write(ref_dict)
    assert parser.write(endf_dict) != expected


def test_writing_numpy_scalars():
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    parser = EndfParserCpp(array_type="numpy")
    endf_dict = parser.parsefile(path, include=(3,))
    sec = endf_dict[3][1]
    sec["AWR"] = 62.5
    expected = parser.write(endf_dict)
    sec["LR"] = np.int8(sec["LR"])  # integer field
    sec["AWR"] = np.float32(62.5)  # float fields
    sec["ZA"] = np.int32(sec["ZA"])
    sec["QM"] = np.uint16(sec["QM"])
    assert parser.write(endf_dict) == expected


def test_writing_float32_arrays():
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    parser = EndfParserCpp(array_type="numpy")
    endf_dict = parser.parsefile(path, include=(3, 4))
    # values exactly representable as float32
    values = np.arange(len(endf_dict[3][1]["xstable"]["xs"])) * 0.125
    endf_dict[3][1]["xstable"]["xs"] = values
    endf_dict[4][2]["al"][0] = values[: len(endf_dict[4][2]["al"][0])]
    expected = parser.write(endf_dict)
    endf_dict[3][1]["xstable"]["xs"] = values.astype(np.float32)
    endf_dict[4][2]["al"][0] = endf_dict[4][2]["al"][0].astype(np.float32)
    assert parser.write(endf_dict) == expected


@pytest.mark.parametrize("dtype", ["int64", "uint64", "uint32"])
def test_writing_out_of_range_integers_raises(dtype):
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    parser = EndfParserCpp(array_type="numpy")
    big = np.iinfo(dtype).max
    endf_dict = parser.parsefile(path, include=(3, 4))
    xstable = endf_dict[3][1]["xstable"]
    xstable["NBT"] = xstable["NBT"].astype(dtype)
    xstable["NBT"][-1] = big
    with pytest.raises(Exception):
        parser.write(endf_dict)
    endf_dict = parser.parsefile(path, include=(3, 4))
    mf4 = endf_dict[4][2]
    mf4["NL"] = mf4["NL"].astype(dtype)
    mf4["NL"][0] = big
    with pytest.raises(Exception):
        parser.write(endf_dict)


def test_preserve_value_strings():
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    opts = dict(preserve_value_strings=True)
    list_parser = EndfParserCpp(array_type="list", **opts)
    numpy_parser = EndfParserCpp(array_type="numpy", **opts)
    list_dict = list_parser.parsefile(path)
    numpy_dict = numpy_parser.parsefile(path)
    _assert_same(numpy_dict, list_dict)
    xstable = numpy_dict[3][1]["xstable"]
    # float arrays remain lists of EndfFloat objects
    assert isinstance(xstable["xs"], list)
    assert all(isinstance(v, EndfFloat) for v in xstable["xs"])
    assert isinstance(numpy_dict[4][2]["al"][0], list)
    # integer arrays are numpy arrays
    assert isinstance(xstable["NBT"], np.ndarray)
    assert xstable["NBT"].dtype == np.int64
    assert isinstance(numpy_dict[4][2]["NL"], np.ndarray)
    # verbatim round trip
    assert numpy_parser.write(numpy_dict) == list_parser.write(list_dict)
    lines = Path(path).read_text().splitlines()
    assert numpy_parser.write(numpy_dict) == lines


def test_factory_selects_cpp_parser():
    for select in ("cpp", "fastest"):
        parser = EndfParserFactory.create(select=select, array_type="numpy")
        assert isinstance(parser, EndfParserCpp)
        assert parser.read_opts["array_type"] == "numpy"


def test_factory_python_parser_raises():
    with pytest.raises(ValueError, match="array_type"):
        EndfParserFactory.create(select="python", array_type="numpy")
    with pytest.raises(ValueError, match="compat"):
        EndfParserFactory.create(
            select="fastest", require_compat=True, array_type="numpy"
        )


def test_python_parser_raises():
    with pytest.raises(ValueError, match="numpy"):
        EndfParserPy(array_type="numpy", print_cache_info=False)


def test_factory_fastest_does_not_fall_back(monkeypatch):
    def unavailable(parser_args):
        raise ImportError("C++ module not available")

    monkeypatch.setattr(EndfParserFactory, "get_cpp_parser", staticmethod(unavailable))
    with pytest.raises(ImportError, match="numpy"):
        EndfParserFactory.create(select="fastest", array_type="numpy")
    # without numpy arrays, the Python parser is still used as fallback
    parser = EndfParserFactory.create(
        select="fastest", array_type="list", warn_slow=False, print_cache_info=False
    )
    assert isinstance(parser, EndfParserPy)


def test_missing_numpy_raises(monkeypatch):
    monkeypatch.setitem(sys.modules, "numpy", None)
    with pytest.raises(ImportError, match="numpy"):
        EndfParserCpp(array_type="numpy")
    # the other modes do not need numpy
    EndfParserCpp(array_type="list")
