############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/15
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import is_token, get_name, search_name, get_value
from endf_parserpy.utils.math_utils import math_allclose
from .logging_utils import logging, abbreviate_valstr, should_skip_logging_info
from .custom_exceptions import (
    NumberMismatchError,
    InvalidIntegerError,
    SeveralUnboundVariablesError,
    SizeMismatchError,
)
from .endf_mapping_utils import (
    get_varname,
    get_child,
    get_indexquants,
    eval_expr,
    eval_expr_without_unknown_var,
    varvalue_expr_conversion,
    set_array_value,
    set_varval,
    get_varval,
    generate_varname_str,
)


# TODO: Need to refactor the error message stuff
def create_variable_exists_error_msg(varname, prev_val, cur_val):
    return (
        "If the same variable appears in several record specifications "
        + "in the ENDF recipe, the corresponding values "
        + "in the ENDF file must be so that the variable evaluates to the "
        + f"same value. This is not the case for {varname} which previously "
        + f"was determined to be {prev_val} but in the present "
        + f"record would be determined to be {cur_val}. Either the ENDF recipe "
        + "is wrong or the ENDF file contains inconsistent data. Note that "
        + f"{varname} may be an array, in which case this statement would "
        + "apply to one of the variables in that array"
    )


def create_variable_wrong_value_error_msg(realval, expval, sourcekey):
    return (
        f"Expected {expval} in the ENDF file but got {realval}. "
        f"The value was encountered in a source field named {sourcekey}"
    )


def create_size_mismatch_error_msg(realval, expval, sourcekey):
    msgpart1 = "Attempted to associate "
    if hasattr(realval, "__len__"):
        msgpart2 = f"an array ({sourcekey}) of length {len(realval)} "
    else:
        msgpart2 = f"a single value ({sourcekey}) "
    msgpart3 = "in an ENDF record with a variable " + "that is already associated with "
    if hasattr(expval, "__len__"):
        msgpart4 = f"an array of different length {len(expval)}."
    else:
        msgpart4 = f"with a scalar value ({expval})"
    return msgpart1 + msgpart2 + msgpart3 + msgpart4


def log_offending_line(record_dic, logging_method, logger=None):
    logfun = getattr(logger, logging_method)
    if "__record_spec" in record_dic:
        record_spec = record_dic["__record_spec"]
        logfun("Record specification: " + record_spec)
    if "__line" in record_dic:
        line = record_dic["__line"]
        logfun("Offending line: " + line)


def map_recorddic_to_datadic(
    basekeys, record_dic, expr_list, datadic, loop_vars, parse_opts, logger=None
):
    parse_opts = parse_opts if parse_opts is not None else {}
    fuzzy_matching = parse_opts.get("fuzzy_matching", False)
    ignore_zero_mismatch = parse_opts.get("ignore_zero_mismatch", True)
    ignore_number_mismatch = parse_opts.get("ignore_number_mismatch", True)
    ignore_varspec_mismatch = parse_opts.get("ignore_varspec_mismatch", True)
    ignore_all_mismatches = parse_opts.get("ignore_all_mismatches", False)
    cast_int = not ignore_all_mismatches
    zipit = zip(basekeys, expr_list)
    found_unbound = False
    varnames = []
    for sourcekey, curexpr in zipit:
        try:
            expr_vv = eval_expr(
                curexpr,
                datadic,
                loop_vars,
                parse_opts,
                look_up=False,
                cast_int=cast_int,
            )
        except SeveralUnboundVariablesError:
            found_unbound = True
            continue

        targetkey = get_varname(expr_vv[2])
        varnames.append(targetkey)
        # If the record specification in the ENDF recipe
        # specification contains a value, hence targetkey is None,
        # we check if the value in the ENDF file is equal to this
        # value and raise an exception otherwise. Apart from this,
        # we don't do anything else, as the value in the record
        # specification can be employed while translating informatoin
        # in the datadic back to an an ENDF-6 file.
        # NOTE: This branch is also entered if all variables
        # appearing in an expression have already been read in
        # before.
        if targetkey is None:
            assert expr_vv[1] == 0
            # If we have a DESIRED_NUMBER in the expression,
            # we expect a specific number but do not require it.
            # If, on the other hand, there are only NUMBERs in the
            # expression, any inconsistency between these numbers
            # and the number in the ENDF file will yield an error.
            contains_desired_number = search_name(curexpr, "DESIRED_NUMBER")
            contains_inconsistent_varspec = search_name(curexpr, "inconsistent_varspec")

            srcval = record_dic[sourcekey]
            expval = expr_vv[0]
            srcval_has_len = hasattr(srcval, "__len__")
            expval_has_len = hasattr(expval, "__len__")
            if (
                (srcval_has_len and not expval_has_len)
                or (expval_has_len and not srcval_has_len)
                or (srcval_has_len and expval_has_len and len(srcval) != len(expval))
            ):
                errmsg = create_size_mismatch_error_msg(srcval, expval, sourcekey)
                raise SizeMismatchError(errmsg)

            if not fuzzy_matching:
                value_mismatch_occurred = record_dic[sourcekey] != expr_vv[0]
            else:
                value_mismatch_occurred = not math_allclose(
                    record_dic[sourcekey], expr_vv[0], atol=1e-7, rtol=1e-5
                )
            msg = create_variable_wrong_value_error_msg(
                record_dic[sourcekey], expr_vv[0], sourcekey
            )
            if value_mismatch_occurred and not ignore_all_mismatches:
                # `ignore_all_mismatches` active means we are in lookahead
                # and number mismatches are expected to occur.
                if ignore_zero_mismatch and expr_vv[0] == 0:
                    logger.warning(msg)
                    log_offending_line(record_dic, "warning", logger)
                elif ignore_number_mismatch and contains_desired_number:
                    logger.warning(msg)
                    log_offending_line(record_dic, "warning", logger)
                elif ignore_varspec_mismatch and contains_inconsistent_varspec:
                    logger.warning(msg)
                    log_offending_line(record_dic, "warning", logger)
                else:
                    log_offending_line(record_dic, "error", logger)
                    raise NumberMismatchError(msg)
        # The else branch covers the case when there is still a dangling variable
        # but the linear equation given in the slot can be solved to obtain its value.
        else:
            try:
                val = varvalue_expr_conversion(
                    expr_vv, record_dic[sourcekey], rwmode="read", cast_int=cast_int
                )
            except InvalidIntegerError as pexc:
                raise InvalidIntegerError(str(pexc) + f" (variable {targetkey})")

            idxquants = get_indexquants(expr_vv[2])
            if idxquants is None:
                datadic[targetkey] = val
            else:
                set_array_value(
                    targetkey, idxquants, val, datadic, loop_vars, parse_opts
                )

    # Logging info is only produced the first time we encounter a variable
    tmp = tuple(v for v in varnames if v is not None)
    if not should_skip_logging_info(tmp, datadic):
        varvals = tuple(abbreviate_valstr(datadic[v]) for v in tmp)
        logger.info(
            "Variable names in this record: "
            + ", ".join([f"{v}: {vv}" for v, vv in zip(tmp, varvals)])
        )

    if found_unbound:
        raise SeveralUnboundVariablesError(
            "Found several unbound variables in this line"
        )
    else:
        return datadic


def map_datadic_to_recorddic(
    basekeys, record_dic, expr_list, datadic, loop_vars, parse_opts, logger=None
):
    zipit = zip(basekeys, expr_list)
    for sourcekey, curexpr in zipit:
        val = eval_expr_without_unknown_var(
            curexpr, datadic, loop_vars, parse_opts, look_up=False, cast_int=False
        )
        record_dic[sourcekey] = val
    return record_dic


def map_record_helper(
    expr_list,
    basekeys,
    record_dic,
    datadic,
    loop_vars,
    rwmode,
    parse_opts=None,
    logger=None,
):
    # remove COMMA tokens as they are not needed
    expr_list = [
        expr for expr in expr_list if not is_token(expr) or get_name(expr) != "COMMA"
    ]

    if rwmode == "read":
        parse_tries = 3
        while parse_tries > 0:
            try:
                return map_recorddic_to_datadic(
                    basekeys,
                    record_dic,
                    expr_list,
                    datadic,
                    loop_vars,
                    parse_opts,
                    logger=logger,
                )
            except SeveralUnboundVariablesError:
                parse_tries -= 1

        raise SeveralUnboundVariablesError("Found several unbound variables")
    else:
        return map_datadic_to_recorddic(
            basekeys,
            record_dic,
            expr_list,
            datadic,
            loop_vars,
            parse_opts,
            logger=logger,
        )


def map_text_record_helper(
    expr_list, basekeys, record_dic, datadic, loop_vars, rwmode, parse_opts=None
):
    assert len(basekeys) == 1 and basekeys[0] == "HL"
    if rwmode == "read":
        charcount = 0
        fullstring = record_dic[basekeys[0]]
        for expr in expr_list:
            extvarname_node = get_child(expr, "extvarname", nofail=True)
            textlength_node = get_child(expr, "TEXTLENGTH", nofail=True)
            if textlength_node is None:
                upper_index = len(fullstring)
            else:
                textlength = int(get_value(textlength_node))
                upper_index = charcount + textlength
            if charcount >= upper_index:
                raise SizeMismatchError(
                    "Variables span more character slots than "
                    + "provided in the file. Either the ENDF-6 recipe "
                    + "is wrong or the `width` argument was smaller "
                    + "than 11 in the EndfParser constructor call."
                )
            curstr = fullstring[charcount:upper_index]
            if extvarname_node is not None:
                set_varval(extvarname_node, datadic, loop_vars, curstr, parse_opts)
            charcount = upper_index
        return datadic
    else:
        fullstring = ""
        for expr in expr_list:
            extvarname_node = get_child(expr, "extvarname", nofail=True)
            textlength_node = get_child(expr, "TEXTLENGTH", nofail=True)
            textlength = None
            if textlength_node is not None:
                textlength = int(get_value(textlength_node))
            if extvarname_node is not None:
                curstr = get_varval(
                    extvarname_node,
                    datadic,
                    loop_vars,
                    parse_opts,
                    raise_if_missing=True,
                )
                if textlength is not None and len(curstr) != textlength:
                    varnamestr = generate_varname_str(
                        extvarname_node, datadic, loop_vars, parse_opts, True
                    )
                    raise SizeMismatchError(
                        f"String in variable {varnamestr} is of "
                        + f"length {len(curstr)} but expected to be of "
                        + f"length {textlength}"
                    )
            else:
                if textlength is None:
                    raise IndexError("Programming error: should never happen")
                curstr = " " * textlength
            fullstring += curstr
        record_dic[basekeys[0]] = fullstring
        return record_dic
