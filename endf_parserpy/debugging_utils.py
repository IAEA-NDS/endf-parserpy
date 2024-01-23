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

from collections.abc import MutableMapping
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
                    strlen_only=False, do_rstrip=False, rstrcut=None,
                    fail_on_diff=True, diff_log=None):

    if diff_log is None:
        diff_log = []

    found_diff = False

    def treat_diff(msg, exc):
        nonlocal found_diff
        found_diff = True
        if fail_on_diff:
            raise exc(msg)
        else:
            diff_log.append(msg)
            print(msg)

    if type(obj1) != type(obj2):
        treat_diff(f'at path {curpath}: ' +
                   f'type mismatch found, obj1: {obj1}, obj2: {obj2}',
                   TypeError)

    elif isinstance(obj1, dict):
        only_in_obj1 = set(obj1).difference(obj2)
        if len(only_in_obj1) > 0:
            treat_diff(f'at path {curpath}: only obj1 contains {only_in_obj1}',
                       IndexError)

        only_in_obj2 = set(obj2).difference(obj1)
        if len(only_in_obj2) > 0:
            treat_diff(f'at path {curpath}: only obj2 contains {only_in_obj2}',
                       IndexError)

        common_keys = set(obj1).intersection(set(obj2))
        for key in common_keys:
            ret = compare_objects(obj1[key],
                                  obj2[key], '.'.join((curpath, str(key))),
                                  atol=atol, rtol=rtol,
                                  strlen_only=strlen_only,
                                  do_rstrip=do_rstrip, rstrcut=rstrcut,
                                  fail_on_diff=fail_on_diff, diff_log=diff_log)
            found_diff = found_diff or not ret
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
                    treat_diff(f'at path {curpath}: string lengths differ '
                               f'({obj1} != {obj2})', ValueError)
            elif obj1 != obj2:
                treat_diff(f'at path {curpath}: strings differ '
                           f'({obj1} != {obj2})', ValueError)

        elif hasattr(obj1, '__iter__'):
            len_obj1 = len(tuple(obj1))
            len_obj2 = len(tuple(obj2))
            if len_obj1 != len_obj2:
                treat_diff(f'Length mismatch at {curpath} '
                           f'({len_obj1} vs {len_obj2})', ValueError)

            for i, (subel1, subel2) in enumerate(zip(obj1, obj2)):
                ret = compare_objects(subel1, subel2,
                                      f'{curpath}[{str(i)}]',
                                      atol=atol, rtol=rtol,
                                      strlen_only=strlen_only,
                                      do_rstrip=do_rstrip, rstrcut=rstrcut,
                                      fail_on_diff=fail_on_diff,
                                      diff_log=diff_log)
                found_diff = found_diff or not ret
        else:
            if not smart_is_equal(obj1, obj2, atol=atol, rtol=rtol):
                treat_diff(f'Value mismatch at {curpath} '
                           f'({obj1} vs {obj2})', ValueError)

    # return True if equivalent
    return (not found_diff)


class TrackingDict(MutableMapping):

    def __init__(self, dict_like):
        self._basedict = dict_like
        self._trackingdicts = {}
        self._accessed = set()

    def __getitem__(self, key):
        if isinstance(key, int):
            self._accessed.add(key)
        retval = self._basedict.__getitem__(key)
        if isinstance(retval, MutableMapping) and not str(key).startswith('__'):
            if key not in self._trackingdicts:
                self._trackingdicts[key] = TrackingDict(retval)
            retval = self._trackingdicts[key]
        return retval

    def __setitem__(self, key, value):
        if key in self._accessed:
            self._accessed.remove(key)
        if key in self._trackingdicts:
            self._trackingdicts.__delitem__(key)
        return self._basedict.__setitem__(key, value)

    def __delitem__(self, key):
        if key in self._accessed:
            self._accessed.__delitem__(key)
        if key in self._trackingdicts:
            self._trackingdicts.__delitem__(key)
        return self._basedict.__delitem__(key)

    def __iter__(self):
        return self._basedict.__iter__()

    def __len__(self):
        return self._basedict.__len__()

    def verify_complete_retrieval(self, path=''):
        if len(self._accessed) > 0:
            for k in self._basedict:
                if isinstance(k, int) and k not in self._accessed:
                    indexpath = path + '/' + str(k)
                    raise IndexError(
                        f'The content of {indexpath} was not accessed'
                    )
        for k in self._basedict:
            curval = self.__getitem__(k)
            if isinstance(curval, TrackingDict):
                indexpath = path + '/' + str(k)
                curval.verify_complete_retrieval(indexpath)

    def unwrap(self):
        return self._basedict
