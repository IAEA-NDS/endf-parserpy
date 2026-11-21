"""math_mul, math_div, math_add and math_sub: numbers, lists and tuples
(numpy arrays are not supported, as documented)."""

import pytest

from endf_parserpy.utils.math_utils import math_add, math_div, math_mul, math_sub


@pytest.mark.parametrize(
    "func, x, y, expected",
    [
        (math_mul, [1, 2], 3, [3, 6]),
        (math_mul, (1, 2), (3, 4), (3, 8)),
        (math_div, [2.0, 4.0], 2.0, [1.0, 2.0]),
        (math_div, 6, 3, 2),
        (math_add, 1, (1, 2), (2, 3)),
        (math_sub, [3, 4], [1, 1], [2, 3]),
    ],
)
def test_lists_and_tuples(func, x, y, expected):
    res = func(x, y)
    assert res == expected
    assert type(res) is type(expected)


@pytest.mark.parametrize("func", [math_mul, math_div, math_add, math_sub])
def test_numpy_arrays_raise(func):
    np = pytest.importorskip("numpy")
    with pytest.raises(TypeError):
        func(np.array([1.0, 2.0]), 2.0)
