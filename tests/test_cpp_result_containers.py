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

"""Python containers of the arrays returned by EndfParserCpp.

The lists and dictionaries holding the arrays of a parse result are
created with their final size and filled element by element, and floats
without original string are created directly. The result must have the
same structure in all array types: a list of array_type="list" is a
dictionary with consecutive ascending integer keys (starting at the first
index of the array) for array_type="dict" (except for the columns of
TAB1/TAB2 tables, which are lists in both), the keys of the other
dictionaries are in the same order, empty arrays are empty containers,
the floats are of type float, or EndfFloat with the original string of
the field with preserve_value_strings=True, and the results are the
same as those of EndfParserPy.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfFloat


TESTDATA = Path(__file__).parent / "testdata"
FILES = ["n_2925_29-Cu-63.endf", "dec-094_Pu_244.endf", "tsl_Al.endf"]


def _parse(fname, atype, preserve=False):
    parser = EndfParserCpp(array_type=atype, preserve_value_strings=preserve)
    return parser.parsefile(str(TESTDATA / fname))


def _is_array_dict(obj):
    return (
        isinstance(obj, dict)
        and len(obj) > 0
        and all(type(k) is int for k in obj)
        and list(obj) == list(range(min(obj), min(obj) + len(obj)))
    )


def _compare(lst, dct, path, preserve):
    # lst: element of the result with array_type="list", dct: the same
    # element with array_type="dict"
    if type(lst) is list:
        if len(lst) == 0:
            # an empty array
            assert dct == {} or dct == [], path
            return
        if type(dct) is list:
            # the columns of TAB1/TAB2 tables are lists in all modes
            assert len(lst) == len(dct), path
            for i, (v, w) in enumerate(zip(lst, dct)):
                _compare(v, w, path + (i,), preserve)
            return
        assert _is_array_dict(dct), path
        for v, (k, w) in zip(lst, dct.items()):
            _compare(v, w, path + (k,), preserve)
        return
    if type(lst) is dict:
        assert type(dct) is dict, path
        assert list(lst) == list(dct), path
        for k in lst:
            _compare(lst[k], dct[k], path + (k,), preserve)
        return
    assert type(lst) is type(dct), path
    if type(lst) is EndfFloat:
        assert preserve, path
        assert lst.get_original_string() == dct.get_original_string(), path
        assert float(lst) == float(dct), path
    elif type(lst) is float:
        assert lst == dct or (lst != lst and dct != dct), path
    else:
        assert lst == dct, path


def _check_floats(obj, preserve, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_floats(v, preserve, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_floats(v, preserve, path + (i,))
    elif isinstance(obj, EndfFloat):
        assert preserve, path
        assert obj.get_original_string() != "", path
    elif isinstance(obj, float):
        assert type(obj) is float, path
    elif isinstance(obj, int) and not isinstance(obj, bool):
        assert type(obj) is int, path


@pytest.mark.parametrize("preserve", [False, True])
@pytest.mark.parametrize("fname", FILES)
def test_list_and_dict_results_agree(fname, preserve):
    lst = _parse(fname, "list", preserve)
    dct = _parse(fname, "dict", preserve)
    _check_floats(lst, preserve)
    _check_floats(dct, preserve)
    _compare(lst, dct, (), preserve)


@pytest.mark.parametrize("fname", FILES)
def test_numpy_results_agree_with_lists(fname):
    np = pytest.importorskip("numpy")
    lst = _parse(fname, "list")
    arr = _parse(fname, "numpy")

    def cmp(a, b, path):
        if isinstance(b, np.ndarray):
            assert np.array(a, dtype=b.dtype).shape == b.shape, path
            assert np.array_equal(np.array(a, dtype=b.dtype), b, equal_nan=True), path
        elif isinstance(b, dict):
            assert list(a) == list(b), path
            for k in a:
                cmp(a[k], b[k], path + (k,))
        elif isinstance(b, list):
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)):
                cmp(x, y, path + (i,))
        else:
            assert type(a) is type(b) and (a == b or a != a), path

    cmp(lst, arr, ())


@pytest.mark.parametrize("atype", ["list", "dict"])
@pytest.mark.parametrize("fname", ["n_2925_29-Cu-63.endf", "dec-094_Pu_244.endf"])
def test_same_results_as_python_parser(fname, atype):
    cpp = _parse(fname, atype)
    py = EndfParserPy(array_type=atype, print_cache_info=False).parsefile(
        str(TESTDATA / fname)
    )

    def exact(obj):
        if isinstance(obj, EndfFloat):
            return ("EndfFloat", float(obj).hex(), obj.get_original_string())
        if isinstance(obj, float):
            return ("float", obj.hex())
        if isinstance(obj, dict):
            return ("dict", sorted((repr(k), exact(v)) for k, v in obj.items()))
        if isinstance(obj, list):
            return ("list", [exact(v) for v in obj])
        return (type(obj).__name__, obj)

    assert exact(cpp) == exact(py)
