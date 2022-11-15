from .custom_exceptions import InvalidIntegerError


def math_op(x, y, op):
    if hasattr(x, '__iter__') and hasattr(y, '__iter__'):
        if len(x) != len(y):
            raise ValueError('x and y must be of same length ' +
                             f'(len(x)={len(x)} vs len(y)={len(y)})')
        return type(x)(op(z1, z2) for z1, z2 in zip(x, y))
    elif hasattr(x, '__iter__'):
        return type(x)(op(z, y) for z in x)
    elif hasattr(y, '__iter__'):
        return type(y)(op(x, z) for z in y)
    else:
        return op(x, y)


def math_neg(x):
    if hasattr(x, '__iter__'):
        return type(x)(-z for z in x)
    else:
        return -x


def math_mul(x, y):
    return math_op(x, y, lambda a, b: a*b)


def math_div(x, y, cast_int=False):
    res = math_op(x, y, lambda a, b: a/b)
    if isinstance(x, int) and isinstance(y, int) and cast_int:
        if int(res) != res:
            raise InvalidIntegerError(
                    f'both x and y are int so {x}/{y} must ' +
                    f'evaluate to integer (got {x/y})')
        return int(res)
    else:
        return res


def math_add(x, y):
    return math_op(x, y, lambda a, b: a+b)


def math_sub(x, y):
    return math_op(x, y, lambda a, b: a-b)
