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

"""EndfPath, EndfDict and path wildcards with numpy arrays.

Data parsed with array_type="numpy" is indexed as with array_type="list",
so EndfPath and EndfDict (with array_type="list") give the same access to
it. numpy arrays have a fixed size: appending an element to them or
removing one raises a TypeError.
"""

from pathlib import Path
import pytest

np = pytest.importorskip("numpy")

from endf_parserpy import EndfParserPy
from endf_parserpy.utils.accessories import (
    EndfPath,
    EndfDict,
    EndfVariable,
)
from endf_parserpy.utils.matching import endf_path_generator


TESTFILE = Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf"


def _data(array_type):
    """A dictionary with arrays as in the results of the parsers."""
    if array_type == "numpy":
        b = [np.array([[1.0, 2.0], [3.0, 4.0]]), np.array([[5.0, 6.0, 7.0]])]
        xs = np.array([0.5, 1.5, 2.5])
        nbt = np.array([3], dtype=np.int64)
    else:
        b = [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0, 7.0]]]
        xs = [0.5, 1.5, 2.5]
        nbt = [3]
    return {6: {5: {"b": b, "xs": xs, "NBT": nbt, "LAW": 1}}}


@pytest.mark.parametrize("mode", ["list", "numpy"])
def test_get_and_exists(mode):
    d = EndfDict(_data(mode), array_type="list")
    assert d["6/5/b/0/1/0"] == 3.0
    assert d["6/5/b[0,1,0]"] == 3.0
    assert d["6/5/b/1/0/2"] == 7.0
    assert list(d["6/5/b/0/1"]) == [3.0, 4.0]
    assert d["6/5/NBT/0"] == 3
    assert d.exists("6/5/b/0/1/1")
    assert not d.exists("6/5/b/0/2/0")
    assert not d.exists("6/5/b/0/1/1/0")
    assert EndfPath("6/5/xs/2").get(d.unwrap()) == 2.5


@pytest.mark.parametrize("mode", ["list", "numpy"])
def test_set_existing_elements(mode):
    data = _data(mode)
    d = EndfDict(data, array_type="list")
    d["6/5/b/0/1/0"] = 30.0
    d["6/5/xs/1"] = 15.0
    assert data[6][5]["b"][0][1][0] == 30.0
    assert data[6][5]["xs"][1] == 15.0
    v = EndfVariable("6/5/xs/0", data)
    v.value = 0.25
    assert data[6][5]["xs"][0] == 0.25
    assert v.value == 0.25


def test_set_replaces_numpy_array_in_place():
    data = _data("numpy")
    xs = data[6][5]["xs"]
    EndfDict(data, array_type="list")["6/5/xs/2"] = 25.0
    assert data[6][5]["xs"] is xs
    assert xs[2] == 25.0
    EndfDict(data, array_type="list")["6/5/b/1"] = np.zeros((2, 3))
    assert data[6][5]["b"][1].shape == (2, 3)


def test_append_to_numpy_array_rejected():
    data = _data("numpy")
    d = EndfDict(data, array_type="list")
    with pytest.raises(TypeError, match="numpy array, as its size is fixed"):
        d["6/5/xs/3"] = 3.5
    with pytest.raises(TypeError, match="numpy array, as its size is fixed"):
        d["6/5/b/0/2/0"] = 3.5
    assert len(data[6][5]["xs"]) == 3
    assert data[6][5]["b"][0].shape == (2, 2)


def test_append_to_list_still_possible():
    data = _data("list")
    EndfDict(data, array_type="list")["6/5/xs/3"] = 3.5
    assert data[6][5]["xs"] == [0.5, 1.5, 2.5, 3.5]


def test_remove_from_numpy_array_rejected():
    data = _data("numpy")
    with pytest.raises(TypeError, match="numpy array, as its size is fixed"):
        del EndfDict(data, array_type="list")["6/5/xs/0"]
    assert len(data[6][5]["xs"]) == 3
    # removing the whole array is possible
    del EndfDict(data, array_type="list")["6/5/xs"]
    assert "xs" not in data[6][5]


@pytest.mark.parametrize("left", ["list", "numpy"])
@pytest.mark.parametrize("right", ["list", "numpy"])
def test_equality(left, right):
    assert EndfDict(_data(left)) == _data(right)
    other = _data(right)
    other[6][5]["b"][0][1][1] = -4.0
    assert not EndfDict(_data(left)) == other
    shorter = _data(right)
    shorter[6][5]["xs"] = shorter[6][5]["xs"][:2]
    assert not EndfDict(_data(left)) == shorter


def test_equality_of_numpy_array_with_other_objects():
    data = _data("numpy")
    for other in (2.5, "abc", {0: 0.5, 1: 1.5, 2: 2.5}):
        changed = _data("numpy")
        changed[6][5]["xs"] = other
        assert not EndfDict(data) == changed


@pytest.mark.parametrize("mode", ["list", "numpy"])
def test_wildcard_over_arrays(mode):
    d = _data(mode)
    paths = [str(p) for p in endf_path_generator("6/5/xs/*", d)]
    assert paths == ["6/5/xs/0", "6/5/xs/1", "6/5/xs/2"]
    paths = [str(p) for p in endf_path_generator("6/5/b/*/0/0", d)]
    assert paths == ["6/5/b/0/0/0", "6/5/b/1/0/0"]
    paths = [str(p) for p in endf_path_generator("6/5/b/0/*/1", d)]
    assert paths == ["6/5/b/0/0/1", "6/5/b/0/1/1"]


@pytest.fixture(scope="module")
def parsed():
    res = {}
    for array_type in ("list", "numpy"):
        parser = EndfParserPy(array_type=array_type, print_cache_info=False)
        res[array_type] = parser.parsefile(str(TESTFILE), include=[3, 6])
    return res


def test_parsed_numpy_and_list_results_equal(parsed):
    assert EndfDict(parsed["numpy"]) == parsed["list"]
    assert EndfDict(parsed["list"]) == parsed["numpy"]


def test_parsed_wildcards_agree(parsed):
    for pattern in ("3/1/xstable/xs/*", "6/*/subsection/0/b/*/0/0"):
        paths = {
            array_type: [str(p) for p in endf_path_generator(pattern, d)]
            for array_type, d in parsed.items()
        }
        assert len(paths["list"]) > 0
        assert paths["numpy"] == paths["list"]
        for p in paths["list"]:
            dl = EndfDict(parsed["list"], array_type="list")
            dn = EndfDict(parsed["numpy"], array_type="list")
            assert dn[p] == dl[p]
