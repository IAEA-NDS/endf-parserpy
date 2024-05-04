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


def get_dtype_vartype_idx(dtype, specialtype):
    vartype_idx = get_vartype_idx(specialtype)
    dtype_idx = get_dtype_idx(dtype)
    combined_idx = vartype_idx * 100 + dtype_idx
    return combined_idx


def get_last_type_varname(vartok):
    varname = "aux_last_type_read_for_"
    varname += str(vartok)
    return varname


def initialize_last_type_var(vartok):
    varname = get_last_type_varname(vartok)
    code = cpp.statement(f"int {varname} = -1")
    return code


def update_last_type_var(vartok, dtype, specialtype):
    idx = get_dtype_vartype_idx(dtype, specialtype)
    varname = get_last_type_varname(vartok)
    code = cpp.statement(f"{varname} = {idx}")
    return code


def has_vartype(vartok, dtype, specialtype):
    typeidx = get_dtype_vartype_idx(dtype, specialtype)
    v = get_last_type_varname(vartok)
    return f"({v} == {typeidx})"


def type_change_check(vartok, dtype, specialtype):
    last_type_varname = get_last_type_varname(vartok)
    typeidx = get_dtype_vartype_idx(dtype, specialtype)
    logical_expr1 = f"{last_type_varname} != {typeidx}"
    logical_expr2 = f"{last_type_varname} != -1"
    logical_expr = cpp.logical_and([logical_expr1, logical_expr2])
    statement = cpp.statement("raise_vartype_mismatch()")
    code = cpp.pureif(logical_expr, statement)
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
