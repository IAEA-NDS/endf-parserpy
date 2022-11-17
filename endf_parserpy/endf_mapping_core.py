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
        SeveralUnboundVariablesError,
    )
from .endf_mapping_utils import (
        get_varname, get_indexquants, eval_expr,
        varvalue_expr_conversion, get_indexvalue
    )
from .tree_utils import (is_token, is_tree, get_name, search_name)
import numpy as np


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
    found_unbound = False
    if not inverse:
        varnames = []
        for sourcekey, curexpr in zipit:
            try:
                expr_vv = eval_expr(curexpr, datadic,
                                    loop_vars, look_up=False)
            except SeveralUnboundVariablesError:
                found_unbound = True
                continue

            targetkey = get_varname(expr_vv[2])
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

                if not ignore_zero_mismatch or expr_vv[0] != 0:
                    # if we have a DESIRED_NUMBER in the expression,
                    # we expect a certain number but we do not require it.
                    # with only NUMBER in the expression, any mismatch between
                    # our expectation and the number in the ENDF file will yield
                    # an error.
                    contains_desired_number = search_name(curexpr, 'DESIRED_NUMBER')
                    contains_inconsistent_varspec = search_name(curexpr, 'inconsistent_varspec')
                    value_mismatch_occurred = record_dic[sourcekey] != expr_vv[0]
                    msg = create_variable_wrong_value_error_msg(record_dic[sourcekey],
                                                                expr_vv[0], sourcekey)
                    if value_mismatch_occurred:
                        if contains_desired_number or contains_inconsistent_varspec:
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
                    val = varvalue_expr_conversion(expr_vv, record_dic[sourcekey], inverse)
                except InvalidIntegerError as pexc:
                    raise InvalidIntegerError(str(pexc) + f' (variable {targetkey})')

                idxquants = get_indexquants(expr_vv[2])
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

        if found_unbound:
            raise SeveralUnboundVariablesError(
                    'Found several unbound variables in this line')
        else:
            return datadic
    # inverse transform
    else:
        for sourcekey, curexpr in zipit:
            expr_vv = eval_expr(curexpr, datadic, loop_vars, look_up=False)
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

    parse_tries = 3
    while parse_tries > 0:
        try:
            return map_recorddic_datadic(
                    basekeys, record_dic, expr_list,
                    inverse, datadic, loop_vars, parse_opts)
        except SeveralUnboundVariablesError:
            parse_tries -= 1

    raise SeveralUnboundVariablesError(
            'Found several unbound variables')
