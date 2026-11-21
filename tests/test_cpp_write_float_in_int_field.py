"""EndfParserCpp writing a float (or another object) into an integer field.

As EndfParserPy (without strict_datatypes, an option EndfParserCpp does
not have), a float with an integral value is written as that integer; a
float with another value raises a ValueError and an object that is not a
number a TypeError, naming the variable, instead of "Unable to cast
Python instance of type <class 'float'> to C++ type '?'".
"""

import copy
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy

TESTDATA = Path(__file__).resolve().parent / "testdata"
PU244 = TESTDATA / "dec-094_Pu_244.endf"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"


@pytest.fixture(scope="module")
def pu244():
    return EndfParserPy().parsefile(PU244)


@pytest.fixture(scope="module")
def cu63_mf3():
    return {
        atype: EndfParserCpp(array_type=atype).parsefile(CU63, include=[(3, 1)])
        for atype in ("dict", "list", "numpy")
    }


def _set(mat, path, value):
    obj = mat
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def _float_types():
    types = [float]
    try:
        import numpy as np
    except ImportError:
        return types
    return types + [np.float64, np.float32]


# a scalar of a HEAD record, an element of an array in a loop (the
# directory) and the element of a list of integers of a TAB1 table (NBT)
SCALAR = (1, 451, "LRP")
ARRAY_ELEMENT = (1, 451, "NCx", 2)


@pytest.mark.parametrize("ftype", _float_types())
@pytest.mark.parametrize("path", [SCALAR, ARRAY_ELEMENT], ids=["scalar", "array"])
def test_integral_float_written_as_integer(pu244, path, ftype):
    mat = copy.deepcopy(pu244)
    expected = EndfParserCpp().write(mat)
    current = mat
    for key in path[:-1]:
        current = current[key]
    _set(mat, path, ftype(current[path[-1]]))
    assert EndfParserCpp().write(mat) == expected
    if path == SCALAR:
        # the same as EndfParserPy
        assert EndfParserPy().write(mat) == expected


@pytest.mark.parametrize("path", [SCALAR, ARRAY_ELEMENT], ids=["scalar", "array"])
def test_non_integral_float_raises(pu244, path):
    mat = copy.deepcopy(pu244)
    _set(mat, path, 5.5)
    varname = path[2]
    with pytest.raises(ValueError, match=f"the variable `{varname}` .* is 5.5"):
        EndfParserCpp().write(mat)
    if path == SCALAR:
        with pytest.raises(Exception, match="not of type integer"):
            EndfParserPy().write(mat)


def test_strict_python_parser_rejects_integral_float(pu244):
    mat = copy.deepcopy(pu244)
    _set(mat, SCALAR, 5.0)
    with pytest.raises(Exception, match="not of type integer"):
        EndfParserPy(strict_datatypes=True).write(mat)


@pytest.mark.parametrize("value", ["5", None, [5]], ids=["str", "None", "list"])
@pytest.mark.parametrize("path", [SCALAR, ARRAY_ELEMENT], ids=["scalar", "array"])
def test_other_objects_raise_type_error(pu244, path, value):
    mat = copy.deepcopy(pu244)
    _set(mat, path, value)
    varname = path[2]
    with pytest.raises(TypeError, match=f"the variable `{varname}` .* of type"):
        EndfParserCpp().write(mat)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1e20])
def test_floats_out_of_range_raise(pu244, value):
    mat = copy.deepcopy(pu244)
    _set(mat, SCALAR, value)
    with pytest.raises(ValueError, match="the variable `LRP`"):
        EndfParserCpp().write(mat)


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
def test_table_integers(cu63_mf3, atype):
    mat = copy.deepcopy(cu63_mf3[atype])
    parser = EndfParserCpp(array_type=atype)
    expected = parser.write(mat)
    tbl = mat[3][1]["xstable"]
    nbt = [float(v) for v in tbl["NBT"]]
    tbl["NBT"] = nbt if atype != "numpy" else __import__("numpy").array(nbt)
    assert parser.write(mat) == expected
    tbl["NBT"] = [v + 0.5 for v in nbt]
    with pytest.raises(ValueError, match="the variable `NBT`"):
        parser.write(mat)
    tbl["NBT"] = "abc"
    with pytest.raises(TypeError, match="the variable `NBT`"):
        parser.write(mat)


@pytest.mark.parametrize("atype", ["list", "numpy"])
def test_float_array_for_integer_array(pu244, atype):
    np = pytest.importorskip("numpy")
    parser = EndfParserCpp(array_type=atype)
    mat = parser.parsefile(PU244)
    expected = parser.write(mat)
    mt451 = mat[1][451]
    mt451["NCx"] = np.asarray(mt451["NCx"], dtype=float)
    if atype == "list":
        mt451["NCx"] = mt451["NCx"].tolist()
    assert parser.write(mat) == expected
    mt451["NCx"][0] = 2.5
    with pytest.raises(ValueError, match="the variable `NCx`"):
        parser.write(mat)
