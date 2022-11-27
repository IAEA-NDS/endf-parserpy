############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/09
# Last modified:   2022/09/09
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

from .math_utils import math_allclose


def smart_is_equal(x, y, atol=1e-8, rtol=1e-6):
    if type(x) != type(y):
        return False
    elif isinstance(x, float):
        return math_allclose(x, y, atol=atol, rtol=rtol)
    elif isinstance(x, int):
        return x == y
    else:
        return x == y


def compare_objects(obj1, obj2, curpath='', atol=1e-8, rtol=1e-6,
        strlen_only=False, do_rstrip=False, rstrcut=None):

    if type(obj1) != type(obj2):
        raise TypeError(f'type mismatch found, obj1: {obj1}, obj2: {obj2}')

    if isinstance(obj1, dict):
        only_in_obj1 = set(obj1).difference(obj2)
        if len(only_in_obj1) > 0:
            raise IndexError(f'at path {curpath}: only obj1 contains {only_in_obj1}')
        only_in_obj2 = set(obj2).difference(obj1)
        if len(only_in_obj2) > 0:
            raise IndexError(f'at path {curpath}: only obj2 contains {only_in_obj2}')

        for key in obj1:
            compare_objects(obj1[key], obj2[key], '.'.join((curpath, str(key))),
                    atol=atol, rtol=rtol, strlen_only=strlen_only,
                    do_rstrip=do_rstrip, rstrcut=rstrcut)

    else:
        if isinstance(obj1, str):
            if do_rstrip:
                obj1 = obj1.rstrip()
                obj2 = obj2.rstrip()
            if rstrcut is not None:
                obj1 = obj1[:rstrcut]
                obj2 = obj2[:rstrcut]
            if strlen_only:
                if len(obj1) != len(obj2):
                    raise ValueError(f'at path {curpath}: string lengths differ ({obj1} != {obj2})')
            elif obj1 != obj2:
                raise ValueError(f'at path {curpath}: strings differ ({obj1} != {obj2})')

        elif hasattr(obj1, '__iter__'):
            len_obj1 = len(tuple(obj1))
            len_obj2 = len(tuple(obj2))
            if len_obj1 != len_obj2:
                raise ValueError(f'Length mismatch at {curpath} ({len_obj1} vs {len_obj2})')

            for i, (subel1, subel2) in enumerate(zip(obj1, obj2)):
                compare_objects(subel1, subel2, f'{curpath}[{str(i)}]',
                        atol=atol, rtol=rtol, strlen_only=strlen_only,
                        do_rstrip=do_rstrip, rstrcut=rstrcut)
        else:
            if not smart_is_equal(obj1, obj2, atol=atol, rtol=rtol):
                raise ValueError(f'Value mismatch at {curpath} ({obj1} vs {obj2})')
