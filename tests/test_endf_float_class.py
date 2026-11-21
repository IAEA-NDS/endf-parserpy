import pytest
from endf_parserpy.utils.math_utils import (
    EndfFloat,
    math_isclose,
)


@pytest.mark.parametrize(
    "obj1, obj2, relation, expval",
    [
        # for equality testing
        (EndfFloat(7, "7"), 7, lambda x, y: x == y, True),
        (7, EndfFloat(7, "7"), lambda x, y: x == y, True),
        (8, EndfFloat(7, "8"), lambda x, y: x == y, False),
        (EndfFloat(8, "8"), 7, lambda x, y: x == y, False),
        # for inequality testing
        (EndfFloat(3, "3"), 9, lambda x, y: x != y, True),
        (9, EndfFloat(3, "3"), lambda x, y: x != y, True),
        (3, EndfFloat(3, "3"), lambda x, y: x != y, False),
        # for smaller-than testing
        (EndfFloat(3, "3"), 9, lambda x, y: x < y, True),
        (9, EndfFloat(3, "3"), lambda x, y: x < y, False),
        # for larger-than testing
        (EndfFloat(3, "3"), 9, lambda x, y: x > y, False),
        (9, EndfFloat(3, "3"), lambda x, y: x > y, True),
        # for smaller-equal testing
        (EndfFloat(3, "3"), 9, lambda x, y: x <= y, True),
        (9, EndfFloat(3, "3"), lambda x, y: x <= y, False),
        (EndfFloat(3, "3"), 3, lambda x, y: x <= y, True),
        (3, EndfFloat(3, "3"), lambda x, y: x <= y, True),
        # for larger-equal testing
        (EndfFloat(3, "3"), 9, lambda x, y: x >= y, False),
        (9, EndfFloat(3, "3"), lambda x, y: x >= y, True),
        (EndfFloat(3, "3"), 3, lambda x, y: x >= y, True),
        (3, EndfFloat(3, "3"), lambda x, y: x >= y, True),
    ],
)
def test_relations(obj1, obj2, relation, expval):
    assert relation(obj1, obj2) == expval


@pytest.mark.parametrize(
    "obj1, obj2, expval",
    [
        (EndfFloat(7, "7"), 7 + 1e-12, True),
        (7 + 1e-12, EndfFloat(7, "7"), True),
        (EndfFloat(7, "7"), 7 + 1e-1, False),
        (7 + 1e-1, EndfFloat(7, "7"), False),
    ],
)
def test_math_isclose(obj1, obj2, expval):
    assert math_isclose(obj1, obj2) == expval


@pytest.mark.parametrize("left", [2.5, 3.0, 3.5, 3])
def test_reflected_relations_with_float_on_the_left(left):
    # Python calls the swapped comparison of EndfFloat (e.g. __gt__ for
    # left < x); there are no __rlt__ etc. in the comparison protocol
    x = EndfFloat(3.0, "3.0")
    assert (left < x) == (left < 3.0)
    assert (left <= x) == (left <= 3.0)
    assert (left > x) == (left > 3.0)
    assert (left >= x) == (left >= 3.0)
    assert (left == x) == (left == 3.0)
    assert (left != x) == (left != 3.0)


def test_relations_of_two_endf_floats():
    a, b = EndfFloat(1.0, "1.0"), EndfFloat(2.0, "2.0")
    assert a < b and a <= b and b > a and b >= a and a != b
    assert not a > b and not a == b


def test_no_reflected_relation_methods():
    for name in ("__rlt__", "__rle__", "__rgt__", "__rge__"):
        assert not hasattr(EndfFloat, name)
