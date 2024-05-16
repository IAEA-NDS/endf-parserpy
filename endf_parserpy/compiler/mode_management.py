############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/16
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


def set_mode(mode, vardict):
    if mode not in ("read", "write"):
        raise TypeError("`mode` must be either `read` or `write`")
    vardict["__mode"] = mode


def set_write_mode(vardict):
    set_mode("write", vardict)


def set_read_mode(vardict):
    set_mode("read", vardict)


def get_mode(vardict):
    curdict = vardict
    while "__mode" not in curdict and "__up" in curdict:
        curdict = curdict["__up"]
    if "__mode" not in curdict:
        raise TypeError("parser mode has not been set")
    return curdict["__mode"]


def in_read_mode(vardict):
    mode = get_mode(vardict)
    return mode == "read"


def in_write_mode(vardict):
    mode = get_mode(vardict)
    return mode == "write"


def _find_parent_dict(varname, vardict):
    curdict = vardict
    while varname not in curdict and "__up" in curdict:
        curdict = curdict["__up"]
    if varname not in curdict:
        raise TypeError(f"{varname} not found in dictionary hierarchy")
    return curdict


def register_numeric_field_getter(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must be a callable with parameters `node`, `idx`, `dtype`, `lookahead`"
        )
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["numeric_field_getter"] = func


def get_numeric_field_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["numeric_field_getter"]


def register_text_field_getter(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must be a callable with parameters `node`, `start`, `length`, `lookahead`"
        )
    basic_ops = vardict.setdefault("__basic_ops", vardict)
    basic_ops["text_field_getter"] = func


def get_text_field_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["text_field_getter"]
