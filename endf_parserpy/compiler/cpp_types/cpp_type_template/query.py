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

from endf_parserpy.compiler.variable_management import get_var_types
from ..cpp_varaux import get_cpp_varname


class Query:

    @staticmethod
    def get_specialtype_name():
        raise NotImplementedError("`get_specialtype_name` method must be implemented")

    @classmethod
    def did_read_var(cls, vartok, vardict, indices=None):
        raise NotImplementedError("`did_read_var` method must be implemented")

    @classmethod
    def assemble_extvarname(cls, varname, idxstrs):
        raise NotImplementedError("`assemble_extvarname` must be implemented")

    @classmethod
    def is_responsible(cls, vartok, vardict):
        specialtype = cls.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        if vartypes is None:
            return False
        return any(v[1] == specialtype for v in vartypes)

    @classmethod
    def get_cpp_varname(cls, vartok, vardict, dtype=None):
        specialtype = cls.get_specialtype_name()
        return get_cpp_varname(vartok, vardict, specialtype=specialtype, dtype=dtype)
