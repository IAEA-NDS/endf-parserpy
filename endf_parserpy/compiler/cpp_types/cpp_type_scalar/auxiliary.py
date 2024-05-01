from ..cpp_varaux import (
    init_local_var_from_global_var,
    get_cpp_varname,
)
import endf_parserpy.compiler.cpp_primitives as cpp


def readflag_varname(vartok, vardict):
    varname = get_cpp_varname(vartok, vardict)
    return f"aux_{varname}_read"


def init_readflag(vartok, vardict, glob=True, val=False):
    v = readflag_varname(vartok, vardict)
    valstr = "true" if val else "false"
    if glob:
        return cpp.statement(f"bool {v} = {valstr}")
    return init_local_var_from_global_var(v, "bool")


def initialize_aux_read_vars(vartok, vardict, save_state=False):
    varname = get_cpp_varname(vartok, vardict)
    glob = not save_state
    code = init_readflag(vartok, vardict, glob)
    return code


def mark_var_as_read(vartok, vardict):
    varname = get_cpp_varname(vartok, vardict)
    code = cpp.statement(f"aux_{varname}_read = true")
    return code
