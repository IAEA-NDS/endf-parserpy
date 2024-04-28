############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/22
# Last modified:   2024/04/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import endf_parserpy.compiler.cpp_primitives as cpp
from endf_parserpy.compiler.variable_management import (
    register_var,
    get_var_type,
    find_parent_dict,
)
from ..cpp_varaux import (
    get_cpp_varname,
    check_variable,
    map_dtype,
    init_local_var_from_global_var,
)
from .query import Query
from .auxiliary import (
    initialize_aux_read_vars,
    mark_var_as_read,
)


class Assign:

    @staticmethod
    def define_var(vartok, vardict, save_state=False):
        pardict = find_parent_dict(vartok, vardict, fail=True)
        dtype = map_dtype(pardict[vartok][0])
        varname = get_cpp_varname(vartok)
        code = ""
        if save_state:
            code += init_local_var_from_global_var(varname, dtype)
        else:
            code += cpp.statement(f"{dtype} {varname}")
        code += initialize_aux_read_vars(vartok, save_state)
        return code

    @staticmethod
    def assign_exprstr_to_var(vartok, indices, exprstr, dtype, vardict, node):
        vartype = get_var_type(vartok, vardict)
        if vartype is not None and vartype[0] == "loopvartype":
            return ""

        if len(indices) != 0:
            return False

        check_variable(vartok, vardict)
        code = ""
        cpp_varname = get_cpp_varname(vartok)
        code += cpp.statement(f"{cpp_varname} = {exprstr}")
        code += mark_var_as_read(vartok)
        register_var(vartok, dtype, "Scalar", vardict)
        return code

    @staticmethod
    def store_var_in_endf_dict2(vartok, vardict):
        # counter variables are not stored in the endf dictionary
        if vardict[vartok] == "loopvartype":
            return ""
        src_varname = get_cpp_varname(vartok)
        assigncode = cpp.statement(f'cpp_current_dict["{vartok}"] = {src_varname}')
        code = cpp.pureif(Query.did_read_var(vartok, vardict), assigncode)
        return code
