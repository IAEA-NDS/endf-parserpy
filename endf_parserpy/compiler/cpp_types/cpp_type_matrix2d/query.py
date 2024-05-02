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

from endf_parserpy.compiler.variable_management import get_var_types
from ..cpp_type_template.query import Query as BaseQuery


class Query(BaseQuery):

    @staticmethod
    def get_specialtype_name():
        return "Matrix2d"

    @classmethod
    def assemble_extvarname(cls, varname, idxstrs):
        return varname + "(" + ", ".join(idxstrs) + ")"

    @classmethod
    def did_read_var(cls, vartok, vardict, indices=None):
        varname = cls.get_cpp_varname(vartok, vardict)
        return f"{varname}.did_read()"
