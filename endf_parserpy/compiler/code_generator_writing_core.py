############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/15
# Last modified:   2024/05/26
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
from .endf2cpp_aux_writing import write_section_verbatim
from .cpp_types import cpp_varaux
from .cpp_types.cpp_varops_query import get_idxstr
from .cpp_types.cpp_dtype_aux import map_dtype
from . import cpp_primitives as cpp
from .variable_management import expand_abbreviation


def get_node_value_using_endf_dict(
    node, dictvar, dtype, vardict, defaults=None, idx=None
):
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
    if idx is not None:
        extvarname += f"[py::cast({idx})]"
    if dtype is None:
        return extvarname
    else:
        dtypestr = map_dtype(dtype)
        return f"py::cast<{dtypestr}>({extvarname})"


def get_expr_value_using_endf_dict(
    node, dictvar, dtype, vardict, defaults=None, idx=None
):
    node = convert_to_exprtree(node)
    node = transform_nodes(node, expand_abbreviation, vardict)
    valcode = transform_nodes(
        node, get_node_value_using_endf_dict, dictvar, dtype, vardict, defaults, idx=idx
    )
    return valcode


def get_mat_from_mfmt_section(mfmt_dict):
    code = f"get_mat_from_mfmt_section({mfmt_dict})"
    return code


def generate_section_writing_code(funname, write_opts):
    code = cpp.ifelse(
        f"py::isinstance<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)])",
        cpp.statement(
            f"{funname}_ostream(cont, py::cast<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)]), {write_opts})"
        ),
        write_section_verbatim(
            "cont",
            "py::cast<py::list>(endf_dict[py::cast(mf)][py::cast(mt)])",
            "write_opts",
        ),
    )
    return code
