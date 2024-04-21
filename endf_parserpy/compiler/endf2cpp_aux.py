############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/04/21
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from ..tree_utils import get_name, get_child
from .expr_utils.conversion import VariableToken
from .expr_utils.node_checks import is_number
from . import cpp_primitives as cpp
from .expr_utils.equation_utils import contains_variable
from .node_aux import get_variables_in_expr
from .variable_management import get_special_type


def _check_variable(vartok, vardict):
    if not isinstance(vartok, VariableToken):
        raise TypeError(f"vartok {vartok} must be of type Variabletoken")
    if vartok.indices == 0:
        return
    for idxvar in vartok.indices:
        if not isinstance(idxvar, VariableToken):
            return
        d = vardict
        while "__up" in d and idxvar not in d:
            d = d["__up"]
        if idxvar not in d:
            raise IndexError(f"variable {idxvar} does not exist")


def read_send():
    code = cpp.statement("cpp_read_send(cont)")
    return code


def read_line():
    code = cpp.statement("cpp_line = cpp_read_line(cont)")
    return code


def get_int_field(idx):
    code = f"cpp_read_int_field(cpp_line, {idx})"
    return code


def get_custom_int_field(start_pos, length):
    code = f"cpp_read_custom_int_field(cpp_line, {start_pos}, {length})"
    return code


def get_float_vec(numel):
    code = cpp.statement(f"cpp_read_float_vec(cont, {numel})")
    return code


def get_numeric_field(fieldpos, dtype):
    if dtype == float:
        readfun = "cpp_read_float_field"
        code = f"{readfun}(cpp_line.c_str(), {fieldpos})"
    elif dtype == int:
        readfun = "cpp_read_int_field"
        code = f"{readfun}(cpp_line, {fieldpos})"
    return code


def get_text_field(vartok, start, length, vardict):
    code = f"cpp_line.substr({start}, {length})"
    return code


def read_tab_body(xvar, yvar):
    code = cpp.open_block()
    code += cpp.indent_code(
        """
        int cpp_j;
        int cpp_nr = cpp_read_int_field(cpp_line, 4);
        int cpp_np = cpp_read_int_field(cpp_line, 5);

        std::vector<int> NBT;
        std::vector<int> INT;
        cpp_intvec = cpp_read_int_vec(cont, 2*cpp_nr);
        cpp_j = 0;
        for (int cpp_i=0; cpp_i < cpp_nr; cpp_i++) {
            NBT.push_back(cpp_intvec[cpp_j++]);
            INT.push_back(cpp_intvec[cpp_j++]);
        }

        cpp_current_dict["NBT"] = NBT;
        cpp_current_dict["INT"] = INT;
        """,
        -4,
    )

    if xvar is not None or yvar is not None:
        if xvar is None or yvar is None:
            raise ValueError("provide both xyvar with xvar")
        code += cpp.indent_code(
            f"""
        std::vector<double> {xvar};
        std::vector<double> {yvar};
        cpp_floatvec = cpp_read_float_vec(cont, 2*cpp_np);
        cpp_j = 0;
        for (int cpp_i=0; cpp_i < cpp_np; cpp_i++) {{
            {xvar}.push_back(cpp_floatvec[cpp_j++]);
            {yvar}.push_back(cpp_floatvec[cpp_j++]);
        }}

        cpp_current_dict["{xvar}"] = {xvar};
        cpp_current_dict["{yvar}"] = {yvar};
        """,
            -8,
        )
    code += cpp.close_block()
    return code


def dict_assign(dictvar, idcs, val):
    if len(idcs) == 0:
        return TypeError("len(idcs) must be >= 1")
    elif len(idcs) == 1:
        idx = idcs[0]
        idxstr = f"py::cast({idx})"
        code = cpp.statement(f"{dictvar}[{idxstr}] = {val}")
        return code
    code = cpp.statement(f"py::dict curdict = {dictvar}")
    for i, idx in enumerate(idcs[:-1]):
        idxstr = f"py::cast({idx})"
        inner_code = cpp.pureif(
            f"! curdict.contains({idxstr})",
            cpp.statement(f"curdict[{idxstr}] = py::dict()"),
        )
        inner_code += cpp.statement(f"curdict = curdict[{idxstr}]")
        code += inner_code
    idxstr = f"py::cast({idcs[-1]})"
    code += cpp.statement(f"curdict[{idxstr}] = {val}")
    code = cpp.open_block() + cpp.indent_code(code, 4) + cpp.close_block()
    return code


def open_section(vartok, vardict):
    _check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices
    code = cpp.indent_code(
        f"""
    {{
        py::dict cpp_parent_dict = cpp_current_dict;
        if (! cpp_parent_dict.contains("{secname}")) {{
            cpp_parent_dict["{secname}"] = py::dict();
        }}
        py::dict cpp_current_dict = cpp_parent_dict["{secname}"];
        """,
        -4,
    )
    for idx in indices:
        cpp_idxstr = get_cpp_varname(idx)
        idxstr = f"py::cast({cpp_idxstr})"
        code += cpp.indent_code(
            f"""
        if (! cpp_current_dict.contains({idxstr})) {{
            cpp_current_dict[{idxstr}] = py::dict();
        }}
        cpp_current_dict = cpp_current_dict[{idxstr}];
        """,
            -4,
        )
    return code


def close_section():
    code = cpp.statement("cpp_current_dict = cpp_parent_dict", 4)
    code += cpp.close_block()
    return code


def get_cpp_objstr(tok, vardict):
    if isinstance(tok, VariableToken):
        return get_cpp_extvarname(tok, vardict)
    elif is_number(tok):
        varname = str(tok)
        return varname
    raise NotImplementedError("evil programmer, what did you do?")


def get_cpp_varname(vartok):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    return varname


def get_ptr_varname(vartok, i):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if i < 0 or i + 1 >= len(vartok.indices):
        raise IndexError(f"index i={i} out of range")
    varname = f"ptr_{vartok}_{len(vartok.indices)}d_idx{i}"
    return varname


def get_cpp_extvarname(vartok, vardict):
    varname = get_cpp_varname(vartok)
    if len(vartok.indices) == 0:
        return varname
    idxstrs = []
    for i, idxtok in enumerate(vartok.indices):
        idxstrs.append(get_idxstr(vartok, i, vardict))
    special_type = get_special_type(vartok, vardict)
    if special_type == "Matrix2d":
        extvarname = varname + "(" + ",".join(idxstrs) + ")"
    else:
        extvarname = varname + "".join(f"[{s}]" for s in idxstrs)
    return extvarname


def get_idxstr(vartok, i, vardict):
    idxtok = vartok.indices[i]
    cpp_idxstr = get_cpp_objstr(idxtok, vardict)
    return cpp_idxstr


def _init_local_var_from_global_var(v, ctyp):
    return cpp.concat(
        [
            cpp.statement(f"{ctyp}& glob_{v} = {v}"),
            cpp.statement(f"{ctyp} {v} = glob_{v}"),
        ]
    )


def readflag_varname(vartok):
    varname = get_cpp_varname(vartok)
    return f"aux_{varname}_read"


def init_readflag(vartok, glob=True, val=False):
    v = readflag_varname(vartok)
    valstr = "true" if val else "false"
    if glob:
        return cpp.statement(f"bool {v} = {valstr}")
    return _init_local_var_from_global_var(v, "bool")


def _initialize_aux_read_vars(vartok, save_state=False):
    if len(vartok.indices) > 0:
        # CustomVector class manages the read state itself
        return ""
    varname = get_cpp_varname(vartok)
    glob = not save_state
    code = init_readflag(vartok, glob)
    return code


def define_var(vartok, dtype, vardict, save_state=False):
    if dtype == float:
        dtype = "double"
    elif dtype == int:
        dtype = "int"
    elif dtype == str:
        dtype = "std::string"
    elif dtype == "loopvartype":
        dtype = "int"
    elif dtype == "intvec":
        dtype = "std::vector<int>"
    else:
        raise TypeError(f"unknown dtype {dtype}")
    varname = get_cpp_varname(vartok)
    num_indices = len(vartok.indices)
    ptr_vardefs = ""
    if num_indices > 0:
        for i in range(num_indices):
            dtype = "CustomVector<" + dtype + ">"
            if i + 1 < num_indices:
                cur_ptr_var = get_ptr_varname(vartok, num_indices - i - 2)
                ptr_vardefs += cpp.statement(f"{dtype}* {cur_ptr_var}")
    code = ""
    if save_state:
        code += _init_local_var_from_global_var(varname, dtype)
    else:
        code += cpp.statement(f"{dtype} {varname}")
    code += _initialize_aux_read_vars(vartok, save_state)
    code += ptr_vardefs
    return code


def mark_var_as_read(vartok, prefix=""):
    varname = get_cpp_varname(vartok)
    code = cpp.statement(f"{prefix}aux_{varname}_read = true")
    return code


def _did_read_var(vartok, vardict, indices=None):
    varname = get_cpp_varname(vartok)
    if indices is None or len(vartok.indices) == 0:
        if len(vartok.indices) == 0:
            return f"(aux_{varname}_read == true)"
        else:
            return f"({varname}.get_last_index() != -1)"
    idxstr = get_cpp_objstr(indices[0], vardict)
    code = f"{varname}.contains({idxstr})"
    lastidxstr = idxstr
    for idx in indices[1:]:
        idxstr = get_cpp_objstr(idx, vardict)
        varname += f"[{lastidxstr}]"
        code = cpp.logical_and([code, f"{varname}.contains({idxstr})"])
        lastidxstr = idxstr
    return code


def did_read_var(vartok, vardict, indices=None):
    return _did_read_var(vartok, vardict, indices)


def did_not_read_var(vartok, vardict, indices=None):
    return "(! " + _did_read_var(vartok, vardict, indices) + ")"


def any_unread_vars(vartoks, vardict, glob=False):
    if glob:
        return cpp.logical_or(did_not_read_var(v, vardict) for v in vartoks)
    else:
        return cpp.logical_or(did_not_read_var(v, vardict, v.indices) for v in vartoks)


def _is_loop(node):
    if node is None:
        return False
    node_name = get_name(node)
    return node_name in ("for_loop", "list_loop")


def _get_loop_head(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_head")
    elif node_name == "list_loop":
        return get_child(node, "list_for_head")
    else:
        NotImplementedError("node not recognized as loop node")


def _get_loopvar(node):
    node = _get_loop_head(node)
    return VariableToken(get_child(node, "VARNAME"))


def _get_loop_start(node):
    node = _get_loop_head(node)
    return get_child(node, "for_start")


def _get_loop_stop(node):
    node = _get_loop_head(node)
    return get_child(node, "for_stop")


def _get_loop_body(node):
    node_name = get_name(node)
    if node_name == "list_loop":
        return get_child(node, "list_body")
    elif node_name == "for_loop":
        return get_child(node, "for_body")
    else:
        raise TypeError("not a loop node")


def _can_moveup_ptrassign(vartok, idxexpr, orig_node, dest_node):
    if dest_node is None:
        return False
    if contains_variable(dest_node, vartok, skip_nodes=[orig_node]):
        return False
    variables = get_variables_in_expr(idxexpr)
    for v in variables:
        if contains_variable(dest_node, v, skip_nodes=[orig_node]):
            return False

    if _is_loop(dest_node):
        loopvar = _get_loopvar(dest_node)
        if contains_variable(idxexpr, loopvar):
            return False
    return True


def _moveup_ptrassign(vartok, idx, node, limit_node=None, only_checkpoints=True):
    idxexpr = vartok.indices[idx]
    checkpoint = node
    curnode = node
    parent_node = curnode.parent
    while curnode.parent is not None and curnode is not limit_node:
        if not _can_moveup_ptrassign(vartok, idxexpr, curnode, curnode.parent):
            break
        curnode = curnode.parent
        if _is_loop(curnode):
            checkpoint = curnode
    if only_checkpoints:
        return checkpoint
    else:
        return curnode


def _assign_exprstr_to_nested_vector(vartok, exprstr, vardict, node):
    if len(vartok.indices) == 0:
        return False
    _check_variable(vartok, vardict)
    code = ""
    cpp_varname = get_cpp_varname(vartok)
    indices = vartok.indices
    ptrvar_old = cpp_varname
    limit_node = None
    for i in range(0, len(indices) - 1):
        idxstr = get_idxstr(vartok, i, vardict)
        ptrvar_new = get_ptr_varname(vartok, i)
        dot = "." if i == 0 else "->"
        new_code = cpp.statement(f"{ptrvar_new} = {ptrvar_old}{dot}prepare({idxstr})")
        if node is not None:
            destnode = _moveup_ptrassign(vartok, i, node, limit_node)
            if destnode is not node:
                destnode.check_my_identity()
                destnode.append_precode(new_code)
                limit_node = destnode
            else:
                code += new_code
        ptrvar_old = ptrvar_new
    idxstr = get_idxstr(vartok, len(indices) - 1, vardict)
    dot = "." if len(indices) == 1 else "->"
    code += cpp.statement(f"{ptrvar_old}{dot}set({idxstr}, {exprstr})")
    return code


def _assign_exprstr_to_scalar_var(vartok, exprstr, vardict, use_cpp_name, mark_as_read):
    if len(vartok.indices) > 0:
        return False
    _check_variable(vartok, vardict)
    code = ""
    if use_cpp_name:
        cpp_varname = get_cpp_varname(vartok)
    else:
        cpp_varname = str(vartok)
    if mark_as_read and len(vartok.indices) == 0:
        code += mark_var_as_read(vartok)
    code += cpp.statement(f"{cpp_varname} = {exprstr}")
    return code


def assign_exprstr_to_var(
    vartok, exprstr, vardict, use_cpp_name=True, mark_as_read=True, node=None
):
    if len(vartok.indices) > 0:
        if not use_cpp_name:
            raise NotImplementedError("use_cpp_name=False only available for 1d var")
        if not mark_as_read:
            raise NotImplementedError("mark_as_read=False only available for 1d var")

    code = cpp.comment(f"assign expression to variable {vartok}")
    new_code = False
    if new_code is False:
        new_code = _assign_exprstr_to_scalar_var(
            vartok, exprstr, vardict, use_cpp_name, mark_as_read
        )
    if new_code is False:
        new_code = _assign_exprstr_to_nested_vector(vartok, exprstr, vardict, node)
    if new_code is False:
        raise NotImplementedError("no varassign function matches")
    code += new_code
    return code


def store_var_in_endf_dict(vartok, vardict):
    _check_variable(vartok, vardict)
    src_varname = get_cpp_extvarname(vartok, vardict)
    indices_str = [f'"{vartok}"'] + [get_cpp_objstr(v, vardict) for v in vartok.indices]
    code = cpp.comment(f"store variable {vartok} in endf dictionary")
    code += dict_assign("cpp_current_dict", indices_str, src_varname)
    return code


def store_var_in_endf_dict2(vartok, vardict):
    # counter variables are not stored in the endf dictionary
    if vardict[vartok] == "loopvartype":
        return ""

    src_varname = get_cpp_varname(vartok)
    if len(vartok.indices) == 0:
        assigncode = cpp.statement(f'cpp_current_dict["{vartok}"] = {src_varname}')
        code = cpp.pureif(did_read_var(vartok, vardict), assigncode)
        return code

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
