############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/15
# Last modified:   2024/05/24
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .expr_utils.equation_utils import get_variables_in_expr
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.tree_walkers import transform_nodes
from .expr_utils.node_trafos import node2str
from .expr_utils.conversion import convert_to_exprtree
from .node_checks import is_extvar
from . import endf2cpp_aux as aux
from .cpp_types import cpp_varaux
from .cpp_types.cpp_varops_query import get_idxstr
from .cpp_types.cpp_dtype_aux import map_dtype
from . import cpp_primitives as cpp
from .variable_management import expand_abbreviation


def get_node_value_using_endf_dict(node, dictvar, dtype, vardict, defaults=None):
    defaults = {} if defaults is None else defaults
    if not isinstance(node, VariableToken):
        return node2str(node)
    if dtype not in defaults:
        varname = f'{dictvar}["{node}"]'
    else:
        defval = defaults[dtype]
        varname = f'{dictvar}.attr("get")("{node}", {defval})'
    idxstrs = []
    for i, idxtok in enumerate(node.indices):
        # we retrieve the index values from the
        # variables in the cpp code and not the dictionary
        # as they have already been read before
        curidxstr = get_idxstr(node, i, vardict)
        idxstrs.append(curidxstr)
    idxstrs = [f"[py::cast({idxstr})]" for idxstr in idxstrs]
    extvarname = varname + "".join(idxstrs)
    if dtype is None:
        return extvarname
    else:
        dtypestr = map_dtype(dtype)
        return f"py::cast<{dtypestr}>({extvarname})"


def get_expr_value_using_endf_dict(node, dictvar, dtype, vardict, defaults=None):
    node = convert_to_exprtree(node)
    node = transform_nodes(node, expand_abbreviation, vardict)
    valcode = transform_nodes(
        node, get_node_value_using_endf_dict, dictvar, dtype, vardict, defaults
    )
    return valcode


def generate_parse_or_read_verbatim(funname, parse_opts):  # debug
    code = cpp.ifelse(
        aux.should_parse_section("mf", "mt", "exclude", "include"),
        cpp_varaux.dict_assign(
            "mfmt_dict",
            ["mf", "mt"],
            f"{funname}_istream(cont, endf_dict[py::cast(mf)][py::cast(mt)], {parse_opts})",
        ),
        cpp.concat(
            [
                cpp.line("")
                # aux.read_section_verbatim(
                #     "verbatim_section",
                #     "mat",
                #     "mf",
                #     "mt",
                #     "cont",
                #     "is_firstline",
                #     parse_opts,
                # ),
                # cpp_varaux.dict_assign("mfmt_dict", ["mf", "mt"], "verbatim_section"),
            ]
        ),
    )
    return code
