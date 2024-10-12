############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/12
# Last modified:   2024/10/13
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import MutableMapping


def list_set(lst, idx, value):
    length = len(lst)
    if idx < 0 or idx > length:
        raise IndexError("Index out of range")
    if idx == length:
        lst.append(value)
    else:
        lst[idx] = value


def list_setdefault(lst, idx, value):
    length = len(lst)
    if idx < 0 or idx > length:
        raise IndexError("Index out of range")
    if idx == length:
        lst.append(value)
    return lst[idx]


def array_dict_to_list(dic):
    """Convert all dict to list inplace."""
    for key, obj in tuple(dic.items()):
        if not isinstance(obj, MutableMapping):
            continue
        array_dict_to_list(obj)
        if not all(isinstance(k, int) for k in obj):
            continue
        min_idx = min(k for k in obj)
        max_idx = max(k for k in obj)
        new_obj = [obj.get(k, None) for k in range(min_idx, max_idx + 1)]
        dic[key] = new_obj


def shift_indices(varname, idcs, datadic):
    startidcs = datadic.setdefault("__startidcs", dict())
    info = startidcs.setdefault(varname, dict())
    shifted_idcs = []
    for idx in idcs:
        shift = info.setdefault("start_index", idx)
        info = info.setdefault(idx, dict())
        shifted_idx = idx - shift
        shifted_idcs.append(shifted_idx)
    return shifted_idcs
