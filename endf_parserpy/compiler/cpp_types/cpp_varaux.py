############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/05/07
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import (
    get_name,
    get_child,
)
from endf_parserpy.compiler import cpp_primitives as cpp
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.variable_management import get_var_types
from .cpp_dtype_aux import get_dtype_str


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
