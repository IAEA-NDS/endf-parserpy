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

import itertools
from . import cpp_primitives as cpp
from .cpp_types import cpp_varops_assign
from .cpp_types import cpp_varaux
from . import endf2cpp_aux as aux
from .lookahead_management import in_lookahead
from .expr_utils.tree_walkers import transform_nodes
from .variable_management import (
    expand_abbreviation,
    get_var_types,
)
from .expr_utils.tree_trafos import (
    contains_variables,
    contains_desired_number,
    contains_potentially_inconsistent_variable,
)
from .expr_utils.equation_utils import get_variables_in_expr
from .cpp_types.cpp_varops_query import expr2str_shiftidx
from .expr_utils.node_trafos import node2str
from .cpp_types.cpp_vartype_handling import has_vartype


def generate_endf_dict_assignments(vardict):
    code = cpp.comment("store data in Python dictionary")
    for vartok in vardict:
        if vartok.startswith("__"):
            continue
        if not vartok.cpp_namespace:
            code += cpp_varops_assign.store_var_in_endf_dict2(vartok, vardict)
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
