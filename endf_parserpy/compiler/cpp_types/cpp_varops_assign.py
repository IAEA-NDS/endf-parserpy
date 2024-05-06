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

from ..variable_management import should_track_read
from .. import cpp_primitives as cpp
from .cpp_vartype_handling import (
    has_loopvartype,
    initialize_last_type_var,
    update_last_type_var,
    type_change_check,
)
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
from .cpp_type_information import get_vartype_modules, get_assign_modules


def define_var(vartok, vardict, save_state=False):
    for m in get_vartype_modules():
        if m.query.is_responsible(vartok, vardict):
            code = m.assign.define_var(vartok, vardict, save_state)
            track_read = should_track_read(vartok, vardict)
            vars_defined = vardict.setdefault("__defined", {})
            if track_read and str(vartok) not in vars_defined:
                code += initialize_last_type_var(vartok)
                vars_defined[str(vartok)] = True
            return code
    raise TypeError(f"{vartok} is of unknown type")


def assign_exprstr_to_var(vartok, exprstr, dtype, vardict, node=None):
    indices = [get_idxstr(vartok, i, vardict) for i in range(len(vartok.indices))]
    code = cpp.comment(f"assign expression to variable {vartok}")
    for m in get_vartype_modules():
        new_code = m.assign.assign_exprstr_to_var(
            vartok, indices, exprstr, dtype, vardict, node
        )
        if new_code is not False:
            code += new_code
            track_read = should_track_read(vartok, vardict)
            if track_read:
                specialtype = m.query.get_specialtype_name()
                code += type_change_check(vartok, dtype, specialtype)
                code += update_last_type_var(
                    vartok, dtype=dtype, specialtype=specialtype
                )
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
    if has_loopvartype(vartok, vardict):
        return ""

    for m in get_vartype_modules():
        if m.query.is_responsible(vartok, vardict):
            return m.assign.store_var_in_endf_dict2(vartok, vardict)
    raise TypeError(f"{vartok} has unknown type")
