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
