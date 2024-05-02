############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/05/02
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.compiler.variable_management import find_parent_dict
import endf_parserpy.compiler.cpp_primitives as cpp
from ..cpp_varaux import get_cpp_varname


class Query:

    @staticmethod
    def get_specialtype_name():
        return "NestedVector"

    @classmethod
    def get_cpp_varname(cls, vartok, vardict):
        specialtype = cls.get_specialtype_name()
        return get_cpp_varname(vartok, vardict, specialtype=specialtype)

    @classmethod
    def is_responsible(cls, vartok, vardict):
        pardict = find_parent_dict(vartok, vardict)
        return pardict[vartok][1] == "NestedVector" if pardict is not None else False

    @classmethod
    def assemble_extvarname(cls, varname, idxstrs):
        return varname + "".join(f"[{s}]" for s in idxstrs)

    @classmethod
    def did_read_var(cls, vartok, vardict, indices=None):
        assert cls.is_responsible(vartok, vardict)
        varname = get_cpp_varname(vartok, vardict)
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
