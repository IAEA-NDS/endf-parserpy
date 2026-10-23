############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from ..cpp_type_template.query import Query as BaseQuery


class Query(BaseQuery):

    @staticmethod
    def get_specialtype_name():
        return "NestedArray"

    @classmethod
    def assemble_extvarname(cls, varname, idxstrs):
        return varname + "(" + ", ".join(idxstrs) + ")"

    @classmethod
    def did_read_var(cls, vartok, vardict, indices=None):
        assert cls.is_responsible(vartok, vardict)
        varname = cls.get_cpp_varname(vartok, vardict)
        if indices is None:
            return f"(! {varname}.empty())"
        return f"{varname}.contains(" + ", ".join(indices) + ")"
