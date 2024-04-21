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
from ..variable_management import (
    register_var,
    get_var_type,
    find_parent_dict,
)
from .cpp_varaux import (
    get_cpp_varname,
    check_variable,
    map_dtype,
    init_local_var_from_global_var,
)
from .cpp_type_scalar_query import did_read_var


def _readflag_varname(vartok):
    varname = get_cpp_varname(vartok)
    return f"aux_{varname}_read"


def init_readflag(vartok, glob=True, val=False):
    v = _readflag_varname(vartok)
    valstr = "true" if val else "false"
    if glob:
        return cpp.statement(f"bool {v} = {valstr}")
    return init_local_var_from_global_var(v, "bool")


def _initialize_aux_read_vars(vartok, save_state=False):
    varname = get_cpp_varname(vartok)
    glob = not save_state
    code = init_readflag(vartok, glob)
    return code


def mark_var_as_read(vartok):
    varname = get_cpp_varname(vartok)
    code = cpp.statement(f"aux_{varname}_read = true")
    return code


def define_var(vartok, vardict, save_state=False):
    pardict = find_parent_dict(vartok, vardict, fail=True)
    dtype = map_dtype(pardict[vartok][0])
    varname = get_cpp_varname(vartok)
    code = ""
    if save_state:
        code += init_local_var_from_global_var(varname, dtype)
    else:
        code += cpp.statement(f"{dtype} {varname}")
    code += _initialize_aux_read_vars(vartok, save_state)
    return code


def assign_exprstr_to_var(vartok, indices, exprstr, dtype, vardict, node):
    vartype = get_var_type(vartok, vardict)
    if vartype is not None and vartype[0] == "loopvartype":
        return ""

    if len(indices) != 0:
        return False

    check_variable(vartok, vardict)
    code = ""
    cpp_varname = get_cpp_varname(vartok)
    code += cpp.statement(f"{cpp_varname} = {exprstr}")
    code += mark_var_as_read(vartok)
    register_var(vartok, dtype, "Scalar", vardict)
    return code


def store_var_in_endf_dict2(vartok, vardict):
    # counter variables are not stored in the endf dictionary
    if vardict[vartok] == "loopvartype":
        return ""
    src_varname = get_cpp_varname(vartok)
    assigncode = cpp.statement(f'cpp_current_dict["{vartok}"] = {src_varname}')
    code = cpp.pureif(did_read_var(vartok, vardict), assigncode)
    return code
