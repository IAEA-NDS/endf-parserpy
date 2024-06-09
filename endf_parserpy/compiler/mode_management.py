############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/06/09
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


def _find_parent_dict(varname, vardict):
    curdict = vardict
    while varname not in curdict and "__up" in curdict:
        curdict = curdict["__up"]
    if varname not in curdict:
        raise TypeError(f"{varname} not found in dictionary hierarchy")
    return curdict


def _register_getter(name, vardict, funcname, params):
    if params is not None and not callable(name):
        raise TypeError("func must be a callable with parameters " + ", ".join(params))
    basic_ops = vardict.setdefault("__basic_ops", {})
    basic_ops[funcname] = name


def _get_getter(name, vardict):
    pardict = _find_parent_dict("__basic_ops", vardict)
    basic_ops = pardict["__basic_ops"]
    return basic_ops[name]


def register_numeric_field_getter(func, vardict):
    _register_getter(
        func, vardict, "numeric_field_getter", ("node", "idx", "dtype", "lookahead")
    )


def get_numeric_field_getter(vardict):
    return _get_getter("numeric_field_getter", vardict)


def register_text_field_getter(func, vardict):
    _register_getter(
        func, vardict, "text_field_getter", ("node", "start", "length", "lookahead")
    )


def get_text_field_getter(vardict):
    return _get_getter("text_field_getter", vardict)


def register_custom_int_field_getter(func, vardict):
    _register_getter(
        func,
        vardict,
        "custom_int_field_getter",
        ("node", "start", "length", "lookahead"),
    )


def get_custom_int_field_getter(vardict):
    return _get_getter("custom_int_field_getter", vardict)


def register_counter_field_getter(func, vardict):
    _register_getter(
        func, vardict, "counter_field_getter", ("node", "idx", "lookahead")
    )


def get_counter_field_getter(vardict):
    return _get_getter("counter_field_getter", vardict)


def register_tab1_body_getter(func, vardict):
    _register_getter(
        func, vardict, "tab1_body_getter", ("xvar", "yvar", "nr", "np", "lookahead")
    )


def get_tab1_body_getter(vardict):
    return _get_getter("tab1_body_getter", vardict)


def register_tab2_body_getter(func, vardict):
    _register_getter(func, vardict, "tab2_body_getter", ("nr", "lookahead"))


def get_tab2_body_getter(vardict):
    return _get_getter("tab2_body_getter", vardict)


def register_prepare_line_func(func, vardict):
    _register_getter(func, vardict, "prepare_line_func", ("lookahead",))


def get_prepare_line_func(vardict):
    return _get_getter("prepare_line_func", vardict)


def register_send_line_func(func, vardict):
    _register_getter(func, vardict, "send_func", ("lookahead",))


def get_send_line_func(vardict):
    return _get_getter("send_func", vardict)


def register_finalize_line_func(func, vardict):
    _register_getter(func, vardict, "finalize_line_func", ("lookahead",))


def get_finalize_line_func(vardict):
    return _get_getter("finalize_line_func", vardict)


def register_prepare_line_tape_func(func, vardict):
    _register_getter(func, vardict, "prepare_line_tape", tuple())


def get_prepare_line_tape_func(vardict):
    return _get_getter("prepare_line_tape", vardict)


def register_finalize_line_tape_func(func, vardict):
    _register_getter(func, vardict, "finalize_line_tape", tuple())


def get_finalize_line_tape_func(vardict):
    return _get_getter("finalize_line_tape", vardict)


def register_prepare_section_func(func, vardict):
    _register_getter(func, vardict, "prepare_section_func", ("vartok", "vardict"))


def get_prepare_section_func(vardict):
    return _get_getter("prepare_section_func", vardict)


def register_finalize_section_func(func, vardict):
    _register_getter(func, vardict, "finalize_section_func", ("vartok", "vardict"))


def get_finalize_section_func(vardict):
    return _get_getter("finalize_section_func", vardict)


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
    _register_getter(
        func,
        vardict,
        "generate_expr_validation_func",
        ("actual_value", "node", "vardict"),
    )


def get_generate_expr_validation_func(vardict):
    return _get_getter("generate_expr_validation_func", vardict)
