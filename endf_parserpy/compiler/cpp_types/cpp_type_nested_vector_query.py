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
from .. import cpp_primitives as cpp


def is_responsible(vartok, vardict):
    pardict = find_parent_dict(vartok, vardict)
    return pardict[vartok][1] == "NestedVector" if pardict is not None else False


def get_cpp_varname(vartok):
    return f"var_{vartok}_{len(vartok.indices)}d"


def assemble_extvarname(varname, idxstrs):
    return varname + "".join(f"[{s}]" for s in idxstrs)


def did_read_var(vartok, vardict, indices=None):
    assert is_responsible(vartok, vardict)
    varname = get_cpp_varname(vartok)
    if indices is None:
        return f"({varname}.get_last_index() != -1)"
    idxstr = indices[0]
    code = f"{varname}.contains({idxstr})"
    lastidxstr = idxstr
    for idxstr in indices[1:]:
        varname += f"[{lastidxstr}]"
        code = cpp.logical_and([code, f"{varname}.contains({idxstr})"])
        lastidxstr = idxstr
    return code
