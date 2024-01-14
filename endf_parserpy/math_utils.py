############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/15
# Last modified:   2022/11/15
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################
from .custom_exceptions import InvalidIntegerError


def math_isclose(x, y, rtol=1e-5, atol=1e-8):
    return abs(x-y) <= (atol + rtol*abs(y))


def math_op(x, y, op, **kwargs):
    if hasattr(x, '__iter__') and hasattr(y, '__iter__'):
        if len(x) != len(y):
            raise ValueError('x and y must be of same length ' +
                             f'(len(x)={len(x)} vs len(y)={len(y)})')
        return type(x)(op(z1, z2, **kwargs) for z1, z2 in zip(x, y))
    elif hasattr(x, '__iter__'):
        return type(x)(op(z, y, **kwargs) for z in x)
    elif hasattr(y, '__iter__'):
        return type(y)(op(x, z, **kwargs) for z in y)
    else:
        return op(x, y, **kwargs)


def math_neg(x):
    if hasattr(x, '__iter__'):
        return type(x)(-z for z in x)
    else:
        return -x


def math_mul(x, y):
    return math_op(x, y, lambda a, b: a*b)


def math_div(x, y, cast_int=False):
    res = math_op(x, y, lambda a, b: a/b)
    if isinstance(x, int) and isinstance(y, int):
        if int(res) != res:
            if cast_int:
                raise InvalidIntegerError(
                        f'both x and y are int so {x}/{y} must ' +
                        f'evaluate to integer (got {x/y})')
            return res
        return int(res)
    return res


def math_mod(x, y, cast_int=False):
    res = math_op(x, y, lambda a, b: a % b)
    if isinstance(x, int) and isinstance(y, int) and cast_int:
        if int(res) != res:
            raise InvalidIntegerError(
                    f'both x and y are int so {x}%{y} must ' +
                    f'evaluate to integer (got {x%y})')
        return int(res)
    else:
        return res


def math_add(x, y):
    return math_op(x, y, lambda a, b: a+b)


def math_sub(x, y):
    return math_op(x, y, lambda a, b: a-b)


def math_allclose(x, y, rtol=1e-5, atol=1e-8):
    return math_op(x, y, math_isclose, rtol=rtol, atol=atol)
