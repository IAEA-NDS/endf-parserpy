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

from .logging_utils import logging, abbreviate_valstr, should_skip_logging_info
from .custom_exceptions import (
        NumberMismatchError,
        InconsistentVariableAssignmentError,
        InvalidIntegerError,
    )
from .endf_mapping_utils import (
        get_varname, get_indexquants, eval_expr,
        varvalue_expr_conversion, get_indexvalue
    )
from .tree_utils import (is_token, is_tree, get_name, search_name)
import numpy as np


# these internal functions are hacks to allow for default names for some fields:
# some fields in the ENDF language specification are optional and then no
# Tree/Token is created for them but we still need to use their default names
# in the mapping. For instance, the specification (xstable) after
# [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable) is optional


def get_varname_tmp(expr):
    # the "not is_token(expr)" part is a hack because a Token seems to be regarded
    # as type "str" because isinstance(expr, str) evaluates to true for a Token
    return expr if isinstance(expr, str) and not is_token(expr)  else get_varname(expr)


def get_indexquants_tmp(expr):
    return None if isinstance(expr, str) else get_indexquants(expr)


def eval_expr_tmp(expr, datadic=None, loop_vars=None):
    # this is the same result as returned by eval_expr on an expr with just the variable name
    if not isinstance(expr, str):
        return eval_expr(expr, datadic, loop_vars)
    else:
        return (0, 1, expr)


def varvalue_expr_conversion_tmp(vv, val, inverse):
    # in the case of a tab1, the value of the variable (val) will be a list
    if isinstance(val, list):
        return [varvalue_expr_conversion(vv, x, inverse) for x in val]
    # in the case of a text record, it will be a string, which we return unaltered
    elif isinstance(val, str):
        return val
    # also if it is a dictionary, we return it unaltered
    elif isinstance(val, dict):
        return val
    # otherwise it is a number and we can convert back and forth (e.g., if N/6 in a record specification)
    else:
        return varvalue_expr_conversion(vv, val, inverse)


# TODO: Need to refactor the error message stuff
def create_variable_exists_error_msg(varname, prev_val, cur_val):
    return ('If the same variable appears in several record specifications ' +
            'in the ENDF recipe, the corresponding values ' +
            'in the ENDF file must be so that the variable evaluates to the ' +
           f'same value. This is not the case for {varname} which previously ' +
           f'was determined to be {prev_val} but in the present ' +
           f'record would be determined to be {cur_val}. Either the ENDF recipe ' +
            'is wrong or the ENDF file contains inconsistent data. Note that ' +
           f'{varname} may be an array, in which case this statement would ' +
            'apply to one of the variables in that array')


def create_variable_wrong_value_error_msg(realval, expval, sourcekey):
    return (f'Expected {expval} in the ENDF file but got {realval}. '
            f'The value was encountered in a source field named {sourcekey}')


def map_recorddic_datadic(basekeys, record_dic, expr_list,
                          inverse, datadic, loop_vars, parse_opts):

    parse_opts = parse_opts if parse_opts is not None else {}
    fuzzy_matching = parse_opts.get('fuzzy_matching', False)
    ignore_zero_mismatch = parse_opts.get('ignore_zero_mismatch', True)
    zipit = zip(basekeys, expr_list)
    if not inverse:
        varnames = []
        for sourcekey, curexpr in zipit:

            expr_vv = eval_expr_tmp(curexpr, datadic, loop_vars)
            targetkey = get_varname_tmp(expr_vv[2])
            varnames.append(targetkey)
            # if the record specification contains a value,
            # hence targetkey is None, we check if the value
            # in the ENDF file is equal to that value and
            # bomb out if not. Except that, we don't do anything else,
            # as the fixed value can be written back during
            # the inverse transform from the record specification
            # in the ENDF recipe.
            if targetkey is None:
                assert expr_vv[1] == 0

                if not ignore_zero_mismatch:
                    # if we have a DESIRED_NUMBER in the expression,
                    # we expect a certain number but we do not require it.
                    # with only NUMBER in the expression, any mismatch between
                    # our expectation and the number in the ENDF file will yield
                    # an error.
                    contains_desired_number = search_name(curexpr, 'DESIRED_NUMBER')
                    value_mismatch_occurred = record_dic[sourcekey] != expr_vv[0]
                    #msg = f'Expected {expr_vv[0]} in the ENDF file but got {record_dic[sourcekey]}'
                    msg = create_variable_wrong_value_error_msg(record_dic[sourcekey],
                                                                expr_vv[0], sourcekey)
                    if value_mismatch_occurred:
                        if contains_desired_number:
                            logging.warning(msg)
                        else:
                            raise NumberMismatchError(msg)
            # all variables in the current slot of the record
            # were already assigned so we just check for consistency
            elif expr_vv[1] == 0:
                inconsistency_allowed = is_tree(curexpr) and search_name(curexpr, 'inconsistent_varspec')
                if expr_vv[1] == 0:
                    if record_dic[sourcekey] != expr_vv[0]:
                        if not inconsistency_allowed:
                            if not fuzzy_matching:
                                mismatch_occurred = True
                            else:
                                mismatch_occurred = \
                                    not np.isclose(record_dic[sourcekey], expr_vv[0],
                                                   atol=1e-7, rtol=1e-5)
                            if mismatch_occurred:
                                raise InconsistentVariableAssignmentError(
                                         'The term with the values of the existing variables ' +
                                         f'evaluates to a value {expr_vv[0]} that is inconsistent ' +
                                         f'with the value {record_dic[sourcekey]} in the file ' +
                                         f'for slot {sourcekey}')
            # there is still a dangling variable but we can
            # solve the linear equation given in the slot to obtain its value
            else:
                inconsistency_allowed = is_tree(curexpr) and search_name(curexpr, 'inconsistent_varspec')
                try:
                    val = varvalue_expr_conversion_tmp(expr_vv, record_dic[sourcekey], inverse)
                except InvalidIntegerError as pexc:
                    raise InvalidIntegerError(str(pexc) + f' (variable {targetkey})')

                idxquants = get_indexquants_tmp(expr_vv[2])
                if idxquants is None:
                    if targetkey in datadic:
                        prev_val = datadic[targetkey]
                        if not inconsistency_allowed:
                            if not fuzzy_matching:
                                mismatch_occurred = prev_val != val
                            else:
                                # NOTE: some files may contain small inconsistencies
                                # which do not matter for all practical purposes, e.g., O-18 in FENDL 3.2.
                                # we tolerate such small inconsistencies.
                                mismatch_occurred = not np.isclose(prev_val, val, atol=1e-7, rtol=1e-5)
                            if mismatch_occurred:
                                raise InconsistentVariableAssignmentError(
                                        create_variable_exists_error_msg(targetkey, prev_val, val))
                    else:
                        datadic[targetkey] = val
                else:
                    # loop through indexvars, and initialize
                    # nested dictionaries with the indicies as keys
                    datadic.setdefault(targetkey, {})
                    curdic = datadic[targetkey]
                    for i, idxquant in enumerate(idxquants):
                        idx = get_indexvalue(idxquant, loop_vars)
                        if i < len(idxquants)-1:
                            curdic.setdefault(idx, {})
                            curdic = curdic[idx]
                    idx = get_indexvalue(idxquants[-1], loop_vars)
                    if idx in curdic:
                        prev_val = curdic[idx]
                        # NOTE: some files may contain small inconsistencies
                        # which do not matter for all practical purposes, e.g., O-18 in FENDL 3.2.
                        # we tolerate such small inconsistencies.
                        if not inconsistency_allowed:
                            if not fuzzy_matching:
                                mismatch_occurred = prev_val != val
                            else:
                                mismatch_occurred = not np.isclose(prev_val, val, atol=1e-7, rtol=1e-5)
                            if mismatch_occurred:
                                raise InconsistentVariableAssignmentError(
                                        create_variable_exists_error_msg(targetkey, prev_val, val))
                    else:
                        curdic[idx] = val

        # we write out logging info the first time we encounter a variable
        tmp = tuple(v for v in varnames if v is not None)
        if not should_skip_logging_info(tmp, datadic):
            varvals = tuple(abbreviate_valstr(datadic[v]) for v in tmp)
            logging.info('Variable names in this record: ' + ', '.join([f'{v}: {vv}' for v, vv in zip(tmp, varvals)]))

        return datadic
    # inverse transform
    else:
        for sourcekey, curexpr in zipit:
            expr_vv = eval_expr_tmp(curexpr, datadic, loop_vars)
            if expr_vv[1] != 0:
                # TODO: More informative error what variable is missing
                IndexError('some variable missing in dictionary')
            record_dic[sourcekey] = expr_vv[0]
        return record_dic


def map_record_helper(expr_list, basekeys, record_dic, datadic, loop_vars,
                      inverse, parse_opts=None):
    # remove COMMA token because it is not relevant
    expr_list = [expr for expr in expr_list
                 if not is_token(expr) or get_name(expr) != 'COMMA']

    return map_recorddic_datadic(basekeys, record_dic, expr_list, inverse,
                                 datadic, loop_vars, parse_opts)
