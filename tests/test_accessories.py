import pytest
from copy import deepcopy
from endf_parserpy.utils.accessories import (
    EndfPath,
    EndfVariable,
    EndfDict,
    EndfList,
)


@pytest.fixture(scope="function")
def testdict():
    return {"a": {"b": 10, "c": {"d": 5}}, 3: {"x": "abc"}}


@pytest.fixture(scope="function")
def testdict2(testdict):
    return EndfDict(testdict)


@pytest.fixture(scope="function")
def testpath(testdict):
    return EndfPath("a/c/d")


def test_dict_endfdict_association(testdict, testdict2):
    assert id(testdict) == id(testdict2.unwrap())


def test_endfdict_path_split(testdict2):
    d1 = testdict2["a/c"]
    d2 = testdict2["a"]["c"]
    assert id(d1.unwrap()) == id(d2.unwrap())


def test_endfdict_wrap_and_unwrap(testdict, testdict2):
    testdict2["u"] = {"x": 7}
    testdict["v"] = {"y": 9}
    testdict2["w"] = EndfDict({"z": 10})
    assert type(testdict2["u"]) == EndfDict
    assert type(testdict2["v"]) == EndfDict
    assert type(testdict2["w"]) == EndfDict
    assert type(testdict["u"]) == dict
    assert type(testdict["v"]) == dict
    assert type(testdict["w"]) == dict


def test_dict_endfdict_update(testdict, testdict2):
    testdict2 = EndfDict(testdict)
    testdict2["u/3"] = 25
    testdict.setdefault("v", {}).setdefault(5, 7)
    assert testdict["u"][3] == testdict2["u/3"]
    assert testdict["v"][5] == testdict2["v/5"]


def test_endfdict_equal(testdict, testdict2):
    assert testdict == testdict2
    testdict3 = deepcopy(testdict2)
    assert testdict2 == testdict3
    testdict3["x/y"] = 13.0
    assert testdict2 != testdict3
    testdict3 = deepcopy(testdict2)
    testdict2["x/a"] = "abc"
    testdict3["x/a"] = "abd"
    assert testdict2 != testdict3
    testdict3 = deepcopy(testdict2)
    testdict2["x"] = (1, 2, 3)
    testdict3["x"] = (1, 2, 3)
    assert testdict2 == testdict3
    testdict3["x"] = (1, 3, 3)
    assert testdict2 != testdict3


def test_endfdict_list_mode():
    p = EndfPath("3/151/a/0")
    testdict = EndfDict(array_type="list")
    testdict[p] = 5
    assert type(testdict[3]) == EndfDict
    assert type(testdict["3/151"]) == EndfDict
    assert type(testdict["3/151/a"]) == EndfList
    assert testdict["3/151/a/0"] == 5


def test_endfdict_dict_mode():
    p = EndfPath("3/151/a/0")
    testdict = EndfDict(array_type="dict")
    testdict[p] = 5
    assert type(testdict[3]) == EndfDict
    assert type(testdict["3/151"]) == EndfDict
    assert type(testdict["3/151/a"]) == EndfDict
    assert testdict["3/151/a/0"] == 5


def test_endfdict_list_mode_split():
    p = EndfPath("3/151/a/0/0/b/0")
    testdict = EndfDict(array_type="list")
    testdict[p] = 8
    testobj1 = testdict["3/151"]
    assert type(testobj1) == EndfDict
    testobj2 = testobj1["a"]
    assert type(testobj2) == EndfList
    testobj3 = testobj2["0"]
    assert type(testobj3) == EndfList
    testobj4 = testobj3["0"]
    assert type(testobj4) == EndfDict
    testobj5 = testobj4["b"]
    assert type(testobj5) == EndfList


def test_endfpath_get_and_set(testdict, testdict2, testpath):
    testpath.set(testdict, 13)
    assert testpath.get(testdict) == 13
    assert testdict2[str(testpath)] == 13


def test_endfpath_get_and_set_with_lists():
    testpath = EndfPath("a/1/b", array_type="list")
    testdict = {"a": [0, {"b": 5}, 0]}
    assert testpath.get(testdict) == 5
    testpath.set(testdict, 15)
    assert testdict["a"][1]["b"] == 15
    assert testpath.get(testdict) == 15


def test_endfpath_remove_with_lists():
    testpath = EndfPath("a/1/b", array_type="list")
    testdict = {"a": [0, {"b": 5}, 2]}
    assert testpath.exists(testdict)
    testpath.remove(testdict)
    assert "b" not in testdict["a"][1]
    assert not testpath.exists(testdict)
    testpath[:-1].remove(testdict)
    assert testdict["a"][1] == 2


def test_endfpath_get_type(testdict, testdict2, testpath):
    assert type(testpath[:-1].get(testdict)) == dict
    assert type(testpath[:-1].get(testdict2)) == EndfDict


def test_endfpath_with_list_mode_and_leading_dict():
    testpath1 = EndfPath("0/0/a/0/b", array_type="list", leading="dict")
    testpath2 = EndfPath("0/0/a/1/b", array_type="list", leading="dict")
    testpath3 = EndfPath("0/1/a/0/b", array_type="list", leading="dict")
    testdict = {}
    testpath1.set(testdict, 5)
    testpath2.set(testdict, 6)
    testpath3.set(testdict, 7)
    assert type(testdict[0]) == dict
    assert type(testdict[0][0]) == dict
    assert type(testdict[0][1]) == dict
    assert type(testdict[0][1]["a"]) == list
    assert type(testdict[0][0]["a"][1]) == dict
    assert testdict[0][0]["a"][0]["b"] == 5
    assert testdict[0][0]["a"][1]["b"] == 6
    assert testdict[0][1]["a"][0]["b"] == 7


def test_endfpath_set_type(testdict, testdict2, testpath):
    d1 = testpath[:-1].get(testdict)
    d2 = testpath[:-1].get(testdict2)
    for d, t in zip((d1, d2), (testdict, testdict2)):
        testpath[:-1].set(t, d)
        assert type(testpath[:-1].get(testdict)) == dict
        assert type(testpath[:-1].get(testdict2)) == EndfDict
        assert id(testpath[:-1].get(testdict)) == id(
            testpath[:-1].get(testdict2).unwrap()
        )
        v = d
        if isinstance(v, EndfDict):
            v = v.unwrap()
        assert id(testpath[:-1].get(testdict)) == id(v)


def test_endfpath_alternative_representations():
    p1 = EndfPath("a/b[1,2]/3")
    p2 = EndfPath("a/b/1/2/3")
    p3 = EndfPath("a /  b[ 1] / 2/3")
    p4 = EndfPath("a/b") + EndfPath("1/2/3")
    p5 = EndfPath("a/  ///b[1,2,3]")
    assert p1 == p2
    assert p2 == p3
    assert p3 == p4
    assert p4 == p5


def test_endfpath_addition():
    p1 = "1/2/3" + EndfPath("4/5/6")
    p2 = EndfPath("1/2/3") + "4/5/6"
    p3 = (1, 2, "3") + EndfPath("4/5/6")
    p4 = EndfPath("1/2/3/4/5/6")
    assert p1 == p2
    assert p2 == p3
    assert p3 == p4


def test_endfvariable_endfdict_assocation(testpath, testdict2):
    myvar = EndfVariable(testpath, testdict2)
    assert myvar.value == testdict2[testpath]
    myvar.value = 93
    assert myvar.value == testdict2[testpath]
    testdict2[testpath] = 98
    assert myvar.value == testdict2[testpath]
