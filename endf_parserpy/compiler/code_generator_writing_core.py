############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/15
# Last modified:   2025/06/04
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
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
from .cpp_types.cpp_varaux import get_cpp_varname
from . import cpp_primitives as cpp
from .variable_management import (
    expand_abbreviation,
    get_var_types,
)


def get_node_value_using_endf_dict(
    node, index_shifter_store, dtype, vardict, defaults=None, idx=None
):
    defaults = {} if defaults is None else defaults
    if not isinstance(node, VariableToken):
        return node2str(node)

    # if variable is of loopvartype, we do not read it
    # from the Python dictionary but directly from the cpp variable
    vartypes = get_var_types(node, vardict)
    if vartypes is not None and any(v[0] == "loopvartype" for v in vartypes):
        assert len(vartypes) == 1
        return get_cpp_varname(node, vardict, dtype=vartypes[0][0])

    varname = str(node)
    idxstrs = []
    for i, idxtok in enumerate(node.indices):
        curidxstr = get_idxstr(node, i, vardict)
        idxstrs.append(curidxstr)

    idcsarg = "std::vector<int>({" + ", ".join(idxstrs) + "})"
    defval = "py::none()" if dtype not in defaults else f"py::cast({defaults[dtype]})"
    retobj = f'{index_shifter_store}.get_value("{varname}", {idcsarg}, {defval})'

    # if the accessed object is a container
    # the idx specification allows to get a specific
    # element of this container rather than the entire container.
    if idx is not None:
        retobj += f"[py::cast({idx})]"
    if dtype is None:
        return retobj
    else:
        dtypestr = map_dtype(dtype)
        return f"py::cast<{dtypestr}>({retobj})"


def get_expr_value_using_endf_dict(
    node, index_shifter_store, dtype, vardict, defaults=None, idx=None
):
    node = convert_to_exprtree(node)
    node = transform_nodes(node, expand_abbreviation, vardict)
    valcode = transform_nodes(
        node,
        get_node_value_using_endf_dict,
        index_shifter_store,
        dtype,
        vardict,
        defaults,
        idx=idx,
    )
    return valcode


def get_mat_from_mfmt_section(mfmt_dict):
    code = f"get_mat_from_mfmt_section({mfmt_dict})"
    return code


def generate_section_writing_code(funname, write_opts):
    code = cpp.ifelse(
        f"py::isinstance<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)])",
        cpp.concat(
            [
                # inject MF and MT number into Pyton dictionary if missing
                cpp.pureif(
                    cpp.logical_not('mt_dict.contains("MF")'),
                    cpp.statement('mt_dict["MF"] = mf'),
                ),
                cpp.pureif(
                    cpp.logical_not('mt_dict.contains("MT")'),
                    cpp.statement('mt_dict["MT"] = mt'),
                ),
                # call the mf/mt section specific write function
                cpp.statement(
                    f"{funname}_ostream(cont, py::cast<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)]), {write_opts})"
                ),
            ]
        ),
        write_section_verbatim(
            "cont",
            "py::cast<py::list>(endf_dict[py::cast(mf)][py::cast(mt)])",
            "write_opts",
        ),
    )
    return code
