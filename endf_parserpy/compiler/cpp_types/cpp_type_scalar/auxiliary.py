from ..cpp_varaux import (
    init_local_var_from_global_var,
)
import endf_parserpy.compiler.cpp_primitives as cpp


def readflag_varname(vartok):
    varname = str(vartok)
    return f"aux_{varname}_read"


def init_readflag(vartok, glob=True, val=False):
    v = readflag_varname(vartok)
    valstr = "true" if val else "false"
    if glob:
        return cpp.statement(f"bool {v} = {valstr}")
    return init_local_var_from_global_var(v, "bool")


def initialize_aux_read_vars(vartok, save_state=False):
    glob = not save_state
    code = init_readflag(vartok, glob=glob)
    return code


def mark_var_as_read(vartok):
    varname = str(vartok)
    code = cpp.statement(f"aux_{varname}_read = true")
    return code
