############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/23
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from .variable_management import find_parent_dict


def init_lookahead_counter(steps, vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    if pardic is not None:
        TypeError("already in lookahead")
    vardict["__lookahead"] = steps


def remove_lookahead_counter(vardict):
    if "__lookahead" not in vardict:
        raise TypeError("call at end of lookahead")
    if vardict["__lookahead"] != 0:
        raise IndexError("implementation error of lookahead")
    del vardict["__lookahead"]


def decrease_lookahead_counter(vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    if pardic is not None:
        pardic["__lookahead"] -= 1


def in_lookahead(vardict):
    return find_parent_dict("__lookahead", vardict) is not None


def should_proceed(vardict):
    pardic = find_parent_dict("__lookahead", vardict)
    return pardic is None or pardic["__lookahead"] > 0
