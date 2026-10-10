from ..cpp_varaux import (
    init_local_var_from_global_var,
)
import endf_parserpy.compiler.cpp_primitives as cpp
from endf_parserpy.compiler.lookahead_management import in_lookahead
from endf_parserpy.compiler.mode_management import get_lookahead_presence_check


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


def mark_var_as_read(vartok, vardict=None):
    varname = str(vartok)
    readflag = "true"
    # Within a lookahead, a mode may decide whether the variable
    # is actually available. For writing, a variable absent from
    # the dictionary must not count as read, so that comparisons
    # involving it in the if-condition evaluate to false, as in
    # EndfParserPy.
    if vardict is not None and in_lookahead(vardict):
        presence_check = get_lookahead_presence_check(vardict)
        if presence_check is not None:
            readflag = presence_check(vartok)
    code = cpp.statement(f"aux_{varname}_read = {readflag}")
    return code
