############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/05/04
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import (
    get_name,
    get_child,
)
from endf_parserpy.compiler import cpp_primitives as cpp
from endf_parserpy.compiler.expr_utils.conversion import VariableToken
from endf_parserpy.compiler.expr_utils.node_trafos import node2str
from endf_parserpy.compiler.expr_utils.equation_utils import contains_variable
from endf_parserpy.compiler.variable_management import get_var_types
from .cpp_dtype_aux import get_dtype_str, get_dtype_idx
from .cpp_type_information import get_vartype_idx


def get_cpp_varname(vartok, vardict, specialtype=None, dtype=None):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if vartok.cpp_namespace:
        return str(vartok)

    vartypes = get_var_types(vartok, vardict)
    # select the appropriate variable type
    if specialtype is not None:
        vartypes = tuple(v for v in vartypes if v[1] == specialtype)
    if dtype is not None:
        vartypes = tuple(v for v in vartypes if v[0] == dtype)
    if len(vartypes) == 0:
        raise IndexError(f"no appropriate vartype for variable {vartok} registered")
    if len(vartypes) > 1:
        raise IndexError(f"could not resolve vartype for variable {vartok}")

    vartype = vartypes[0]
    specialtype = vartype[1] if specialtype is None else specialtype
    dtype = vartype[0] if dtype is None else dtype
    dtypestr = get_dtype_str(vartype[0])
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    varname += f"_{dtypestr}_{specialtype}"
    return varname


def get_dtype_vartype_idx(vartok, vardict):
    vartype = get_var_types(vartok, vardict)
    # as an intermediate step we still expect just a single vartype
    assert len(vartype) == 1
    vartype = vartype[0]
    vartype_idx = get_vartype_idx(vartype[1])
    dtype_idx = get_dtype_idx(vartype[0])
    combined_idx = vartype_idx * 100 + dtype_idx
    return combined_idx


def get_last_type_varname(vartok, vardict):
    varname = "aux_last_type_read_for_"
    varname += str(vartok)
    return varname


def initialize_last_type_var(vartok, vardict):
    varname = get_last_type_varname(vartok, vardict)
    code = cpp.statement(f"int {varname} = -1")
    return code


def update_last_type_var(vartok, vardict):
    idx = get_dtype_vartype_idx(vartok, vardict)
    varname = get_last_type_varname(vartok, vardict)
    code = cpp.statement(f"{varname} = {idx}")
    return code


def type_change_check(vartok, vardict):
    last_type_varname = get_last_type_varname(vartok, vardict)
    typeidx = get_dtype_vartype_idx(vartok, vardict)
    logical_expr = f"{last_type_varname} != {typeidx}"
    icode = cpp.line("std::string errmsg = ")
    iicode = cpp.line(f'std::string("variable {vartok} now with different type ")')
    iicode += cpp.line('+ "which must not happen. Either ENDF recipe wrong "')
    iicode += cpp.line('+ "or the ENDF file has some forbidden flag values "')
    iicode += cpp.line(
        f'+ std::to_string({last_type_varname}) + " vs " + std::to_string({typeidx});'
    )
    icode += cpp.indent_code(iicode)
    code = cpp.pureif(logical_expr, icode)
    return code


def has_loopvartype(vartok, vardict):
    vartypes = get_var_types(vartok, vardict)
    if vartypes is None:
        return False
    for vartype in vartypes:
        if vartype[0] == "loopvartype":
            if len(vartypes) != 1:
                raise IndexError(
                    f"variable `{vartok}` of loopvartype cannot be associated with other types"
                )
            return True
    return False


def is_loop(node):
    if node is None:
        return False
    node_name = get_name(node)
    return node_name in ("for_loop", "list_loop")


def get_loop_head(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_head")
    elif node_name == "list_loop":
        return get_child(node, "list_for_head")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_body")
    elif node_name == "list_loop":
        return get_child(node, "list_body")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loopvar(node):
    node = get_loop_head(node)
    return VariableToken(get_child(node, "VARNAME"))


def get_loop_start(node):
    node = get_loop_head(node)
    return get_child(get_child(node, "for_start"), "expr")


def get_loop_stop(node):
    node = get_loop_head(node)
    return get_child(get_child(node, "for_stop"), "expr")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "list_loop":
        return get_child(node, "list_body")
    elif node_name == "for_loop":
        return get_child(node, "for_body")
    else:
        raise TypeError("not a loop node")


def init_local_var_from_global_var(v, ctyp):
    return cpp.concat(
        [
            cpp.statement(f"{ctyp}& glob_{v} = {v}"),
            cpp.statement(f"{ctyp} {v} = glob_{v}"),
        ]
    )


def check_variable(vartok, vardict):
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
    code = cpp.open_block() + cpp.indent_code(code, cpp.INDENT) + cpp.close_block()
    return code
