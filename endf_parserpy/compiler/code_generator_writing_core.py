############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/15
# Last modified:   2024/05/22
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .expr_utils.equation_utils import get_variables_in_expr
from .expr_utils.tree_walkers import transform_nodes
from .cpp_types.cpp_varops_query import expr2str_shiftidx
from . import endf2cpp_aux as aux
from .cpp_types import cpp_varaux
from . import cpp_primitives as cpp


def get_expr_value_using_endf_dict(node):
    variables = get_variables_in_expr(node)
    valcode = transform_nodes(node, expr2str_shiftidx, dictvars=variables)
    return valcode


def generate_parse_or_read_verbatim(funname, parse_opts):  # debug
    code = cpp.ifelse(
        aux.should_parse_section("mf", "mt", "exclude", "include"),
        cpp_varaux.dict_assign(
            "mfmt_dict",
            ["mf", "mt"],
            f"{funname}_istream(cont, endf_dict, {parse_opts})",
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
