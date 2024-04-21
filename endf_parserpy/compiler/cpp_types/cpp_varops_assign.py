############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/22
# Last modified:   2024/04/23
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .. import cpp_primitives as cpp
from . import cpp_type_matrix2d_query as matrix2d_type_query
from . import cpp_type_matrix2d_assign as matrix2d_type_assign
from . import cpp_type_scalar_query as scalar_type_query
from . import cpp_type_scalar_assign as scalar_type_assign
from . import cpp_type_nested_vector_query as nested_vector_type_query
from . import cpp_type_nested_vector_assign as nested_vector_type_assign
from .cpp_varaux import (
    check_variable,
    dict_assign,
)
from .cpp_varops_query import (
    get_idxstr,
    did_read_var,
    get_cpp_varname,
    get_cpp_extvarname,
)


VARTYPES = {
    "Matrix2d": (matrix2d_type_query, matrix2d_type_assign),
    "NestedVector": (nested_vector_type_query, nested_vector_type_assign),
    "Scalar": (scalar_type_query, scalar_type_assign),
}


def define_var(vartok, vardict, save_state=False):
    for query, assign in VARTYPES.values():
        if query.is_responsible(vartok, vardict):
            return assign.define_var(vartok, vardict, save_state)
    raise TypeError(f"{vartok} is of unknown type")


def assign_exprstr_to_var(vartok, exprstr, dtype, vardict, node=None):
    indices = [get_idxstr(vartok, i, vardict) for i in range(len(vartok.indices))]
    code = cpp.comment(f"assign expression to variable {vartok}")
    for cpp_type, (query, assign) in VARTYPES.items():
        new_code = assign.assign_exprstr_to_var(
            vartok, indices, exprstr, dtype, vardict, node
        )
        if new_code is not False:
            code += new_code
            return code
    raise TypeError(f"{vartok} has unknown type")


def store_var_in_endf_dict(vartok, vardict):
    if vartok.cpp_namespace:
        raise NotImplementedError(
            f"{vartok} in cpp_namespace, cannot be stored in endf dict"
        )
    check_variable(vartok, vardict)
    src_varname = get_cpp_extvarname(vartok, vardict)
    indices_str = [f'"{vartok}"'] + [get_cpp_objstr(v, vardict) for v in vartok.indices]
    code = cpp.comment(f"store variable {vartok} in endf dictionary")
    code += dict_assign("cpp_current_dict", indices_str, src_varname)
    return code


def store_var_in_endf_dict2(vartok, vardict):
    if vartok.cpp_namespace:
        raise NotImplementedError(
            f"{vartok} in cpp_namespace cannot be stored in endf dict"
        )

    # counter variables are not stored in the endf dictionary
    if vardict[vartok] == "loopvartype":
        return ""

    for query, assign in VARTYPES.values():
        if query.is_responsible(vartok, vardict):
            return assign.store_var_in_endf_dict2(vartok, vardict)
    raise TypeError(f"{vartok} has unknown type")
