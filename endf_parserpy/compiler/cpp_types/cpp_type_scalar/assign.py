############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/22
# Last modified:   2024/05/06
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import endf_parserpy.compiler.cpp_primitives as cpp
from endf_parserpy.compiler.variable_management import (
    register_var,
    get_var_types,
)
from ..cpp_vartype_handling import (
    has_loopvartype,
    has_vartype,
)
from ..cpp_varaux import (
    check_variable,
    init_local_var_from_global_var,
)
from ..cpp_dtype_aux import map_dtype
from .query import Query
from .auxiliary import (
    initialize_aux_read_vars,
    mark_var_as_read,
)
from .query import Query


class Assign:

    @classmethod
    def define_var(cls, vartok, vardict, save_state=False):
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtypes = tuple(v[0] for v in vartypes if v[1] == specialtype)
        varnames = tuple(
            Query.get_cpp_varname(vartok, vardict, dtype=dt) for dt in dtypes
        )
        dtypes = tuple(map_dtype(dt) for dt in dtypes)
        code = ""
        for v, dt in zip(varnames, dtypes):
            if save_state:
                code += init_local_var_from_global_var(v, dt)
            else:
                code += cpp.statement(f"{dt} {v}")
        code += initialize_aux_read_vars(vartok, save_state)
        return code

    @classmethod
    def assign_exprstr_to_var(cls, vartok, indices, exprstr, dtype, vardict, node):
        if has_loopvartype(vartok, vardict):
            return ""

        if len(indices) != 0:
            return False

        check_variable(vartok, vardict)
        register_var(vartok, dtype, "Scalar", vardict)
        code = ""
        cpp_varname = Query.get_cpp_varname(vartok, vardict, dtype=dtype)
        code += cpp.statement(f"{cpp_varname} = {exprstr}")
        code += mark_var_as_read(vartok)
        return code

    @classmethod
    def store_var_in_endf_dict2(cls, vartok, vardict):
        # counter variables are not stored in the endf dictionary
        if has_loopvartype(vartok, vardict):
            return ""
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtypes = tuple(v[0] for v in vartypes if v[1] == specialtype)
        code = ""
        for dtype in dtypes:
            src_varname = Query.get_cpp_varname(vartok, vardict, dtype=dtype)
            assigncode = cpp.statement(f'cpp_current_dict["{vartok}"] = {src_varname}')
            cond = cpp.logical_and(
                [
                    has_vartype(vartok, dtype, specialtype),
                    Query.did_read_var(vartok, vardict),
                ]
            )
            code += cpp.pureif(cond, assigncode)
        return code
