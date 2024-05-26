############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/26
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
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["text_field_getter"] = func


def get_text_field_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["text_field_getter"]


def register_custom_int_field_getter(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must be a callable with parameters `node`, `start`, `length`, `lookahead`"
        )
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["custom_int_field_getter"] = func


def get_custom_int_field_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["custom_int_field_getter"]


def register_counter_field_getter(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must be a callable with parameters `node`, `idx`, `lookahead`"
        )
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["counter_field_getter"] = func


def get_counter_field_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["counter_field_getter"]


def register_tab1_body_getter(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must be a callable with parameters `xvar`, `xvar`, `nr`, `np`,  `lookahead`"
        )
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["tab1_body_getter"] = func


def get_tab1_body_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["tab1_body_getter"]


def register_tab2_body_getter(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable with parameters `nr`, `lookahead`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["tab2_body_getter"] = func


def get_tab2_body_getter(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["tab2_body_getter"]


def register_prepare_line_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable with parameters `lookahead`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["prepare_line_func"] = func


def get_prepare_line_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["prepare_line_func"]


def register_send_line_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable with parameters `lookahead`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["send_func"] = func


def get_send_line_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["send_func"]


def register_finalize_line_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable with parameters `lookahead`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["finalize_line_func"] = func


def get_finalize_line_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["finalize_line_func"]


def register_prepare_line_tape_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["prepare_line_tape"] = func


def get_prepare_line_tape_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["prepare_line_tape"]


def register_finalize_line_tape_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["finalize_line_tape"] = func


def get_finalize_line_tape_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["finalize_line_tape"]


def register_prepare_section_func(func, vardict):
    if not callable(func):
        raise TypeError("func must be a callable with parameters `vartok`, `vardict`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["prepare_section_func"] = func


def get_prepare_section_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["prepare_section_func"]


def register_finalize_section_func(func, vardict):
    if not callable(func):
        raise TypeError("func must gbe a callable with parameters `vartok`, `vardict`")
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["finalize_section_func"] = func


def get_finalize_section_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["finalize_section_func"]


def register_lookahead_tellg_statement(statement, vardict):
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["lookahead_tellg_statement"] = statement


def get_lookahead_tellg_statement(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["lookahead_tellg_statement"]


def register_lookahead_seekg_statement(statement, vardict):
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["lookahead_seekg_statement"] = statement


def get_lookahead_seekg_statement(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["lookahead_seekg_statement"]


def register_generate_expr_validation_func(func, vardict):
    if not callable(func):
        raise TypeError(
            "func must gbe a callable with parameters `actual_value`, `node`, `vardict`"
        )
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops["generate_expr_validation_func"] = func


def get_generate_expr_validation_func(vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops["generate_expr_validation_func"]
