"""EndfPath equality and hashing: equal exactly when the elements are."""

import pytest

from endf_parserpy import EndfPath


@pytest.mark.parametrize(
    "short, long",
    [
        ("a", "a/b"),
        ("a/1", "a/1/b"),
        ("3/102", "3/102/IZAM"),
        ("3/102#1", "3/102#1/IZAM"),
        ("#2", "#2/AWR"),
        ("", "a"),
    ],
)
def test_a_prefix_is_not_equal_to_the_longer_path(short, long):
    assert EndfPath(short) != EndfPath(long)
    assert EndfPath(long) != EndfPath(short)
    assert not EndfPath(short) == EndfPath(long)
    assert not EndfPath(long) == EndfPath(short)


@pytest.mark.parametrize(
    "spec1, spec2",
    [
        ("a/1/b", "a[1]/b"),
        ("a/1/b", ("a", 1, "b")),
        ("a/1/b", ("a", "1", "b")),
        ("a[1,2]/c", "a/1/2/c"),
        (" a / 01 /b ", "a/1/b"),
        ("3/102#1/IZAM", ("3", "102#1", "IZAM")),
        ("#01/xs/E[3]", "#1/xs/E/3"),
        ("", ()),
    ],
)
def test_equal_paths_built_differently(spec1, spec2):
    p1, p2 = EndfPath(spec1), EndfPath(spec2)
    assert p1 == p2
    assert not p1 != p2
    assert hash(p1) == hash(p2)


def test_equal_paths_from_path_algebra():
    path = EndfPath("3/102#1/IZAM")
    assert EndfPath("3") + "102#1" + "IZAM" == path
    assert path[:2] == EndfPath("3/102#1")
    assert path[2] == EndfPath("IZAM")
    assert EndfPath(path) == path
    assert hash(path[:2]) == hash(EndfPath("3/102#1"))
    assert hash("a" + EndfPath("1/b")) == hash(EndfPath("a/1/b"))


@pytest.mark.parametrize(
    "spec1, spec2",
    [
        ("a/b", "a/c"),
        ("a/b", "b/a"),
        ("a/1", "a/2"),
        ("a/b", "a/b/c/d"),
        # the selector tokens differ from plain elements and from each other
        ("3/102#1", "3/102"),
        ("3/102#1", "3/102#2"),
        ("3/102#1", "3/103#1"),
        ("3/102#1", "4/102#1"),
        ("3/102#1", "3/102/1"),
        ("#1", "#2"),
        ("#1", "1"),
        ("#1/IZAM", "3/102#1/IZAM"),
    ],
)
def test_different_paths_are_not_equal(spec1, spec2):
    assert EndfPath(spec1) != EndfPath(spec2)
    assert EndfPath(spec2) != EndfPath(spec1)


def test_array_type_and_leading_do_not_take_part():
    plain = EndfPath("a/1/b")
    as_list = EndfPath("a/1/b", array_type="list", leading="list")
    assert plain == as_list
    assert hash(plain) == hash(as_list)


def test_comparison_with_other_types_is_false():
    path = EndfPath("a/1/b")
    for other in ("a/1/b", ("a", 1, "b"), ["a", 1, "b"], None, 1):
        assert path != other
        assert not path == other
    assert EndfPath("1") != 1


def test_paths_in_a_set_and_as_dict_keys():
    paths = {
        EndfPath("a/1/b"),
        EndfPath("a[1]/b"),
        EndfPath(("a", 1, "b")),
        EndfPath("a"),
        EndfPath("a/1"),
        EndfPath("3/102#1"),
        EndfPath(("3", "102#1")),
        EndfPath("3/102"),
        EndfPath("#0"),
        EndfPath(" #00 "),
    }
    assert len(paths) == 6
    assert EndfPath("a/1/b") in paths
    assert EndfPath("3/102#1") in paths
    assert EndfPath("3/102#2") not in paths
    assert EndfPath("a/1/b/c") not in paths

    values = {EndfPath("a/1/b"): 1, EndfPath("3/102#1"): 2, EndfPath("#0"): 3}
    assert values[EndfPath("a[1]/b")] == 1
    assert values[EndfPath("3") + "102#1"] == 2
    assert values[EndfPath("#0/IZAM")[:1]] == 3
    assert EndfPath("a") not in values
    assert EndfPath("3/102") not in values


def test_membership_in_a_list_of_paths():
    paths = [EndfPath("a/b"), EndfPath("3/102#1/IZAM")]
    assert EndfPath("a/b") in paths
    assert EndfPath("a") not in paths
    assert EndfPath("3/102#1") not in paths
    assert EndfPath("a/b/c") not in paths


def test_index_of_an_element():
    # as used to find the first wildcard of a path
    path = EndfPath("a/b/*/c/*")
    assert path.index(EndfPath("*")) == 2
    assert path.count(EndfPath("*")) == 2
    assert EndfPath("b") in path
    assert EndfPath("a/b") not in path
