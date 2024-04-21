############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/22
# Last modified:   2024/04/23
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .. import cpp_primitives as cpp
from ..expr_utils.conversion import VariableToken
from ..expr_utils.equation_utils import (
    contains_variable,
    get_variables_in_expr,
)
from ..variable_management import (
    register_var,
    find_parent_dict,
)
from .cpp_varaux import (
    get_cpp_varname,
    map_dtype,
    init_local_var_from_global_var,
)
from .cpp_type_nested_vector_query import did_read_var
from .cpp_varaux import (
    is_loop,
    get_loopvar,
)


def can_moveup_ptrassign(vartok, idxexpr, orig_node, dest_node):
    if dest_node is None:
        return False
    if contains_variable(dest_node, vartok, skip_nodes=[orig_node]):
        return False
    variables = get_variables_in_expr(idxexpr)
    for v in variables:
        if contains_variable(dest_node, v, skip_nodes=[orig_node]):
            return False

    if is_loop(dest_node):
        loopvar = get_loopvar(dest_node)
        if contains_variable(idxexpr, loopvar):
            return False
    return True


def moveup_ptrassign(vartok, idx, node, limit_node=None, only_checkpoints=True):
    idxexpr = vartok.indices[idx]
    checkpoint = node
    curnode = node
    parent_node = curnode.parent
    while curnode.parent is not None and curnode is not limit_node:
        if not can_moveup_ptrassign(vartok, idxexpr, curnode, curnode.parent):
            break
        curnode = curnode.parent
        if is_loop(curnode):
            checkpoint = curnode
    if only_checkpoints:
        return checkpoint
    else:
        return curnode


def get_ptr_varname(vartok, i):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if i < 0 or i + 1 >= len(vartok.indices):
        raise IndexError(f"index i={i} out of range")
    varname = f"ptr_{vartok}_{len(vartok.indices)}d_idx{i}"
    return varname


def define_var(vartok, vardict, save_state=False):
    pardict = find_parent_dict(vartok, vardict, fail=True)
    dtype = map_dtype(pardict[vartok][0])
    varname = get_cpp_varname(vartok)
    num_indices = len(vartok.indices)
    ptr_vardefs = ""
    for i in range(num_indices):
        dtype = "CustomVector<" + dtype + ">"
        if i + 1 < num_indices:
            cur_ptr_var = get_ptr_varname(vartok, num_indices - i - 2)
            ptr_vardefs += cpp.statement(f"{dtype}* {cur_ptr_var}")
    code = ""
    if save_state:
        code += init_local_var_from_global_var(varname, dtype)
    else:
        code += cpp.statement(f"{dtype} {varname}")
    code += ptr_vardefs
    return code


def assign_exprstr_to_var(vartok, indices, exprstr, dtype, vardict, node):
    if len(indices) == 0:
        return False

    code = ""
    cpp_varname = get_cpp_varname(vartok)
    ptrvar_old = cpp_varname
    limit_node = None
    for i in range(0, len(indices) - 1):
        idxstr = indices[i]
        ptrvar_new = get_ptr_varname(vartok, i)
        dot = "." if i == 0 else "->"
        new_code = cpp.statement(f"{ptrvar_new} = {ptrvar_old}{dot}prepare({idxstr})")
        if node is not None:
            destnode = moveup_ptrassign(vartok, i, node, limit_node)
            if destnode is not node:
                destnode.check_my_identity()
                destnode.append_precode(new_code)
                limit_node = destnode
            else:
                code += new_code
        ptrvar_old = ptrvar_new
    idxstr = indices[-1]
    dot = "." if len(indices) == 1 else "->"
    code += cpp.statement(f"{ptrvar_old}{dot}set({idxstr}, {exprstr})")
    register_var(vartok, dtype, "NestedVector", vardict)
    return code


def store_var_in_endf_dict2(vartok, vardict):
    src_varname = get_cpp_varname(vartok)
    code = ""
    for curlev in range(len(vartok.indices), 0, -1):
        newcode = ""
        if curlev < len(vartok.indices):
            newcode += cpp.statement(
                f"auto& cpp_curvar{curlev} = cpp_curvar{curlev-1}[cpp_i{curlev}]"
            )
            newcode += cpp.statement(
                f"cpp_curdict{curlev-1}[py::cast(cpp_i{curlev})] = py::dict()"
            )
            newcode += cpp.statement(
                f"py::dict cpp_curdict{curlev} = cpp_curdict{curlev-1}[py::cast(cpp_i{curlev})]"
            )
        else:
            newcode = cpp.statement(
                f"cpp_curdict{curlev-1}[py::cast(cpp_i{curlev})] = cpp_curvar{curlev-1}[cpp_i{curlev}]"
            )
        newcode = newcode + code
        newcode = cpp.forloop(
            f"int cpp_i{curlev} = cpp_curvar{curlev-1}.get_start_index()",
            f"cpp_i{curlev} <= cpp_curvar{curlev-1}.get_last_index()",
            f"cpp_i{curlev}++",
            newcode,
        )
        code = newcode

    assigncode = cpp.statement(f"auto& cpp_curvar0 = {src_varname}", 4)
    assigncode += cpp.statement(f'cpp_current_dict["{vartok}"] = py::dict()', 4)
    assigncode += cpp.statement(
        f'py::dict cpp_curdict0 = cpp_current_dict["{vartok}"]', 4
    )
    assigncode += cpp.indent_code(newcode, 4)
    code = cpp.pureif(did_read_var(vartok, vardict), assigncode)
    return code
