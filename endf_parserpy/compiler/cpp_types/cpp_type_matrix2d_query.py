############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/04/23
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from ..variable_management import find_parent_dict


def is_responsible(vartok, vardict):
    pardict = find_parent_dict(vartok, vardict)
    return pardict[vartok][1] == "Matrix2d" if pardict is not None else False


def get_cpp_varname(vartok):
    return f"var_{vartok}_{len(vartok.indices)}d"


def assemble_extvarname(varname, idxstrs):
    return varname + "(" + ", ".join(idxstrs) + ")"


def did_read_var(vartok, vardict, indices=None):
    varname = get_cpp_varname(vartok)
    return f"{varname}.did_read()"
