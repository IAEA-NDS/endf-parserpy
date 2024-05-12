############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import itertools
from lark.lexer import Token
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.equation_utils import (
    get_variables_in_expr,
    get_varassign_from_expr,
)
from .expr_utils.tree_walkers import (
    transform_nodes,
    transform_nodes_inplace,
)
from .expr_utils.node_trafos import (
    node2str,
    replace_node,
)
from .expr_utils.tree_trafos import (
    contains_variables,
    contains_desired_number,
    contains_potentially_inconsistent_variable,
)
from . import cpp_primitives as cpp
from .cpp_types import cpp_varops_query
from .cpp_types import cpp_varops_assign
from .cpp_types import cpp_varaux
from .cpp_types.cpp_vartype_handling import has_vartype
from .lookahead_management import in_lookahead
from .variable_management import (
    expand_abbreviation,
    register_var,
    get_var_types,
    find_parent_dict,
)
from . import endf2cpp_aux as aux
from .cpp_types.cpp_varops_query import expr2str_shiftidx
from .expr_utils.exceptions import (
    ModuloEquationError,
    MultipleVariableOccurrenceError,
    SeveralUnknownVariablesError,
)


def generate_endf_dict_assignments(vardict):
    code = cpp.comment("store data in Python dictionary")
    for vartok in vardict:
        if vartok.startswith("__"):
            continue
        if not vartok.cpp_namespace:
            code += cpp_varops_assign.store_var_in_endf_dict2(vartok, vardict)
    return code


def generate_expr_validation(actual_value, node, vardict):
    # no validation in lookahead
    if in_lookahead(vardict):
        return ""

    node = transform_nodes(node, expand_abbreviation, vardict)
    cont_vars = contains_variables(node)
    cont_des_num = contains_desired_number(node)
    cont_incons_var = contains_potentially_inconsistent_variable(node)
    current_template = aux.get_current_template()

    # using sorted to have a stable ordering across distinct program runs
    variables = sorted(get_variables_in_expr(node))
    vartypes_dict = {v: get_var_types(v, vardict) for v in variables}
    vartype_assignments = [
        {k: v for k, v in zip(vartypes_dict.keys(), combination)}
        for combination in itertools.product(*vartypes_dict.values())
    ]
    conditions = []
    validation_codes = []
    for vta in vartype_assignments:
        vartype_checks = (
            has_vartype(vartok, vta[vartok][0], vta[vartok][1]) for vartok in variables
        )
        conditions.append(cpp.logical_and(vartype_checks))
        expected_value = transform_nodes(node, expr2str_shiftidx, vardict, vartypes=vta)
        exprstr = transform_nodes(node, node2str)
        quoted_exprstr = f'"{exprstr}"'
        validation_code = aux.validate_field(
            expected_value,
            actual_value,
            contains_variable=cont_vars,
            contains_desired_number=cont_des_num,
            contains_inconsistent_varspec=cont_incons_var,
            exprstr=quoted_exprstr,
            line_template=current_template,
            parse_opts="parse_opts",
        )
        validation_codes.append(validation_code)

    code = ""
    if len(validation_codes) > 1:
        code += cpp.conditional_branches(conditions, validation_codes)
    elif len(validation_codes) == 1:
        code += validation_codes[0]
    else:
        NotImplementedError("should not happen")
    return code


def _generate_code_for_varassign(
    vartok, node, vardict, valcode, dtype, throw_cpp=False
):
    try:
        vartok, expr = get_varassign_from_expr(vartok, node, vardict)
    except ModuloEquationError as exc:
        if not throw_cpp:
            raise exc
        exprstr = transform_nodes(node, node2str)
        return cpp.throw_runtime_error(
            f"The equation {exprstr}==value cannot be solved "
            + f"for {vartok} because the modulo operator is not "
            + "supported."
        )
    except MultipleVariableOccurrenceError as exc:
        if not throw_cpp:
            raise exc
        special_type = "Scalar" if len(vartok.indices) == 0 else "NestedVector"
        register_var(vartok, dtype, special_type, vardict)
        exprstr = transform_nodes(node, node2str)
        return cpp.throw_runtime_error(
            f"The equation {exprstr}==value cannot be solved "
            + f"for {vartok} because this variable could not "
            + "be isolated."
        )

    cpp_val_tok = Token("VARIABLE", "cpp_val")
    code = ""
    if expr == cpp_val_tok:
        code += cpp_varops_assign.assign_exprstr_to_var(
            vartok, valcode, dtype, vardict, node=node
        )
    else:
        if dtype == float:
            cpp_newval_tok = Token("VARNAME", "cpp_float_val")
        elif dtype == int:
            cpp_newval_tok = Token("VARNAME", "cpp_int_val")
        elif dtype == "intvec":
            cpp_newval_tok = Token("VARNAME", "cpp_intvec")
        elif dtype == "floatvec":
            cpp_newval_tok = Token("VARNAME", "cpp_floatvec")
        else:
            raise NotImplementedError(f"unknown node type {dtype}")
        cpp_newval_tok = VariableToken(cpp_newval_tok, cpp_namespace=True)
        expr = transform_nodes(expr, replace_node, cpp_val_tok, cpp_newval_tok)
        code += cpp_varops_assign.assign_exprstr_to_var(
            cpp_newval_tok,
            valcode,
            dtype,
            vardict,
            node=node,
        )
        exprstr = transform_nodes(
            expr, expr2str_shiftidx, vardict, rawvars=(cpp_newval_tok,)
        )
        code += cpp_varops_assign.assign_exprstr_to_var(
            vartok, exprstr, dtype, vardict, node=node
        )
    return code


def generate_code_for_varassign(node, vardict, valcode, dtype, throw_cpp=False):
    code = ""
    node = transform_nodes_inplace(node, expand_abbreviation, vardict)
    exprstr = transform_nodes(node, node2str)
    variables = get_variables_in_expr(node)

    if len(variables) == 0:
        code += generate_expr_validation(valcode, node, vardict)
        return code

    if aux.count_not_encountered_vars(node, vardict) > 1:
        raise SeveralUnknownVariablesError(
            f"more than one unencountered variables in {exprstr}"
        )

    # only try to solve for variables for which all remaining variables
    # have appeared before in recipe logic
    # NOTE: sorted() is introduced to make the program output
    #       deterministic/reproducible because iteration over
    #       sets is not stable over program runs.
    for v in sorted(variables):
        other_vars = sorted(variables.difference((v,)))
        some_other_unavail = any(
            find_parent_dict(w, vardict) is None for w in other_vars
        )
        if some_other_unavail:
            continue

        if cpp_varops_query.need_read_check(v, vardict, v.indices):
            # variable may read beore so we need to check
            # that at cpp runtime
            did_not_read_cond = aux.did_not_read_var(v, vardict, v.indices)
            assigncode = _generate_code_for_varassign(
                v, node, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
            validation_code = generate_expr_validation(valcode, node, vardict)
            code += cpp.ifelse(
                condition=did_not_read_cond, code=assigncode, other_code=validation_code
            )
        else:
            # no possibility that variable has been read in beore
            # hence no checks necessary
            code += _generate_code_for_varassign(
                v, node, vardict, valcode, dtype, throw_cpp=throw_cpp
            )
    return code


def generate_parse_or_read_verbatim(funname, parse_opts):
    code = cpp.ifelse(
        aux.should_parse_section("mf", "mt", "exclude", "include"),
        cpp_varaux.dict_assign(
            "mfmt_dict", ["mf", "mt"], f"{funname}_istream(cont, {parse_opts})"
        ),
        cpp.concat(
            [
                aux.read_section_verbatim(
                    "verbatim_section",
                    "mat",
                    "mf",
                    "mt",
                    "cont",
                    "is_firstline",
                    parse_opts,
                ),
                cpp_varaux.dict_assign("mfmt_dict", ["mf", "mt"], "verbatim_section"),
            ]
        ),
    )
    return code
