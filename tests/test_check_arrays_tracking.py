"""check_arrays=True of EndfParserPy: surplus array elements are reported
in all three array types, also in nested arrays, and TrackingList and
TrackingDict support their mutators."""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserPy
from endf_parserpy.utils.debugging_utils import TrackingDict, TrackingList

np = pytest.importorskip("numpy")

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"
ARRAY_TYPES = ("dict", "list", "numpy")


@pytest.fixture(scope="module")
def parsed():
    # one parse per array type, the sections of the tests parsed
    res = {}
    for atype in ARRAY_TYPES:
        parser = EndfParserPy(array_type=atype)
        res[atype] = parser.parsefile(CU63, include=[(3, 1), (4, 2)])
    return res


def _copy(obj):
    # a deep copy of dicts, lists and numpy arrays
    if isinstance(obj, dict):
        return {k: _copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_copy(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.copy()
    return obj


def _material(parsed, atype):
    return _copy(parsed[atype])


def _append(arr, value):
    # a further element at the end of an array of the given array type
    if isinstance(arr, dict):
        arr[max(arr) + 1] = value
        return arr
    if isinstance(arr, np.ndarray):
        return np.append(arr, value)
    arr.append(value)
    return arr


def _first(arr):
    return arr[min(arr)] if isinstance(arr, dict) else arr[0]


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_complete_arrays_pass(parsed, atype):
    mat = _material(parsed, atype)
    lines = EndfParserPy(array_type=atype).write(mat)
    unchecked = EndfParserPy(array_type=atype, check_arrays=False).write(mat)
    assert lines == unchecked


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_surplus_element_of_top_level_array(parsed, atype):
    mat = _material(parsed, atype)
    sec = mat[4][2]
    sec["E"] = _append(sec["E"], 1e9)
    with pytest.raises(IndexError, match="/E/.* was not accessed"):
        EndfParserPy(array_type=atype).write(mat)


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_surplus_element_of_nested_array(parsed, atype):
    # al[i] of MF4/MT2 (LTT=3) with one Legendre coefficient more than NL[i]
    mat = _material(parsed, atype)
    al = mat[4][2]["al"]
    if isinstance(al, dict):
        first = min(al)
        al[first] = _append(al[first], 0.5)
    else:
        al[0] = _append(al[0], 0.5)
    with pytest.raises(IndexError, match="/al/.* was not accessed"):
        EndfParserPy(array_type=atype).write(mat)


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_surplus_elements_ignored_without_check(parsed, atype):
    # check_arrays=False: the surplus elements are not written
    mat = _material(parsed, atype)
    expected = EndfParserPy(array_type=atype).write(mat)
    al = mat[4][2]["al"]
    if isinstance(al, dict):
        al[min(al)] = _append(al[min(al)], 0.5)
    else:
        al[0] = _append(al[0], 0.5)
    sec = mat[4][2]
    sec["E"] = _append(sec["E"], 1e9)
    parser = EndfParserPy(array_type=atype, check_arrays=False)
    assert parser.write(mat) == expected


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_tab1_table_is_written_as_a_whole(parsed, atype):
    # the columns of a TAB1 table have no counter variable (NP is the
    # length of the columns): a further point in both columns is written,
    # alike in all array types; a single longer column is an error
    mat = _material(parsed, atype)
    tbl = mat[3][1]["xstable"]
    np_orig = len(tbl["E"])
    tbl["E"] = _append(tbl["E"], 3e7)
    tbl["xs"] = _append(tbl["xs"], 1.0)
    lines = EndfParserPy(array_type=atype).write(mat)
    mf3 = [line for line in lines if line[66:75] == "2925 3  1"]
    assert int(mf3[1][55:66]) == np_orig + 1
    mat = _material(parsed, atype)
    tbl = mat[3][1]["xstable"]
    tbl["E"] = _append(tbl["E"], 3e7)
    with pytest.raises(Exception):
        EndfParserPy(array_type=atype).write(mat)


def test_tab1_table_same_in_all_array_types(parsed):
    results = []
    for atype in ARRAY_TYPES:
        mat = _material(parsed, atype)
        tbl = mat[3][1]["xstable"]
        tbl["E"] = _append(tbl["E"], 3e7)
        tbl["xs"] = _append(tbl["xs"], 1.0)
        results.append(EndfParserPy(array_type=atype).write(mat))
    assert results[0] == results[1] == results[2]


# TrackingList


def test_tracking_list_nested_unread_element():
    tl = TrackingList([[1, 2], [3, 4]])
    tl[0][0]
    tl[0][1]
    tl[1][0]
    with pytest.raises(IndexError, match="/1/1 was not accessed"):
        tl.verify_complete_retrieval()
    tl[1][1]
    tl.verify_complete_retrieval()


def test_tracking_list_same_wrapper_per_index():
    tl = TrackingList([[1, 2], {1: 5}])
    assert tl[0] is tl[0]
    assert isinstance(tl[0], TrackingList)
    assert isinstance(tl[1], TrackingDict)
    assert tl[-1] is tl[1]


def test_tracking_list_nested_dict():
    tl = TrackingList([{1: 1.0, 2: 2.0}])
    tl[0][1]
    with pytest.raises(IndexError, match="/0/2 was not accessed"):
        tl.verify_complete_retrieval()


def test_tracking_list_untouched_inner_list_is_reported():
    tl = TrackingList([[1, 2], [3, 4]])
    tl[0][0]
    tl[0][1]
    with pytest.raises(IndexError, match="/1 was not accessed"):
        tl.verify_complete_retrieval()


def test_tracking_list_nothing_read_passes():
    TrackingList([[1, 2], [3]]).verify_complete_retrieval()


def test_tracking_list_setitem():
    base = [1, 2, 3]
    tl = TrackingList(base)
    tl[0], tl[1], tl[2]
    tl[0] = 5
    assert base == [5, 2, 3]
    with pytest.raises(IndexError, match="/0 was not accessed"):
        tl.verify_complete_retrieval()
    assert tl[0] == 5
    tl.verify_complete_retrieval()


def test_tracking_list_setitem_replaces_wrapper():
    tl = TrackingList([[1, 2]])
    inner = tl[0]
    tl[0] = [7]
    assert tl[0] is not inner
    assert list(tl[0]) == [7]


def test_tracking_list_delitem():
    base = [1, 2, 3]
    tl = TrackingList(base)
    tl[0], tl[2]
    del tl[1]
    assert base == [1, 3]
    tl.verify_complete_retrieval()
    del tl[0]
    assert base == [3]
    assert len(tl) == 1


def test_tracking_list_insert_append_extend():
    base = [1, 2]
    tl = TrackingList(base)
    tl[0], tl[1]
    tl.insert(0, 9)
    assert base == [9, 1, 2]
    with pytest.raises(IndexError, match="/0 was not accessed"):
        tl.verify_complete_retrieval()
    tl[0]
    tl.verify_complete_retrieval()
    tl.append(4)
    tl.extend([5, 6])
    assert base == [9, 1, 2, 4, 5, 6]
    with pytest.raises(IndexError, match="/3 was not accessed"):
        tl.verify_complete_retrieval()
    tl[3], tl[4], tl[5]
    tl.verify_complete_retrieval()


def test_tracking_list_slices():
    base = [[1], [2], [3], [4]]
    tl = TrackingList(base)
    part = tl[1:3]
    assert isinstance(part, list)
    assert part[0] is tl[1]
    part[0][0], part[1][0]
    with pytest.raises(IndexError, match="/0 was not accessed"):
        tl.verify_complete_retrieval()
    tl[::3]
    tl[0][0]
    tl[3][0]
    tl.verify_complete_retrieval()
    tl[1:3] = [[8], [9], [10]]
    assert base == [[1], [8], [9], [10], [4]]
    with pytest.raises(IndexError, match="/1 was not accessed"):
        tl.verify_complete_retrieval()
    del tl[1:4]
    assert base == [[1], [4]]
    tl.verify_complete_retrieval()


def test_tracking_list_index_errors_leave_records_unchanged():
    tl = TrackingList([1])
    with pytest.raises(IndexError):
        tl[1]
    with pytest.raises(IndexError):
        tl[1] = 0
    with pytest.raises(IndexError):
        del tl[1]
    assert len(tl._accessed) == len(tl._trackingobjs) == 1


# TrackingDict


def test_tracking_dict_delitem_of_accessed_key():
    base = {1: 1.0, 2: 2.0, 3: 3.0}
    td = TrackingDict(base)
    td[1], td[3]
    del td[1]
    assert base == {2: 2.0, 3: 3.0}
    with pytest.raises(IndexError, match="/2 was not accessed"):
        td.verify_complete_retrieval()
    del td[2]
    td.verify_complete_retrieval()


def test_tracking_dict_delitem_of_nested_key():
    base = {"a": {1: 1.0, 2: 2.0}}
    td = TrackingDict(base)
    td["a"][1]
    del td["a"]
    assert base == {}
    td.verify_complete_retrieval()


def test_tracking_dict_setitem():
    base = {1: 1.0, 2: 2.0}
    td = TrackingDict(base)
    td[1], td[2]
    td[2] = 5.0
    with pytest.raises(IndexError, match="/2 was not accessed"):
        td.verify_complete_retrieval()
    assert td[2] == 5.0
    td.verify_complete_retrieval()


def test_tracking_dict_with_nested_lists():
    td = TrackingDict({"x": [[1, 2], [3, 4]]})
    x = td["x"]
    x[0][0], x[0][1], x[1][0]
    with pytest.raises(IndexError, match="/x/1/1 was not accessed"):
        td.verify_complete_retrieval()
