############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/05/06
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import (
    get_name,
    get_child,
)
from endf_parserpy.compiler import cpp_primitives as cpp
from endf_parserpy.compiler.expr_utils.conversion import VariableToken
from endf_parserpy.compiler.expr_utils.node_trafos import node2str
from endf_parserpy.compiler.expr_utils.equation_utils import contains_variable
from endf_parserpy.compiler.variable_management import get_var_types
from .cpp_dtype_aux import get_dtype_str, get_dtype_idx, get_available_dtypes
from .cpp_type_information import get_vartype_idx, get_vartype_names


def get_cpp_varname(vartok, vardict, specialtype=None, dtype=None):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if vartok.cpp_namespace:
        return str(vartok)

    vartypes = get_var_types(vartok, vardict)
    # select the appropriate variable type
    if specialtype is not None:
        vartypes = tuple(v for v in vartypes if v[1] == specialtype)
    if dtype is not None:
        vartypes = tuple(v for v in vartypes if v[0] == dtype)
    if len(vartypes) == 0:
        raise IndexError(f"no appropriate vartype for variable {vartok} registered")
    if len(vartypes) > 1:
        raise IndexError(f"could not resolve vartype for variable {vartok}")

    vartype = vartypes[0]
    specialtype = vartype[1] if specialtype is None else specialtype
    dtype = vartype[0] if dtype is None else dtype
    dtypestr = get_dtype_str(vartype[0])
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    varname += f"_{dtypestr}_{specialtype}"
    return varname


def get_dtype_vartype_idx(dtype, specialtype):
    vartype_idx = get_vartype_idx(specialtype)
    dtype_idx = get_dtype_idx(dtype)
    combined_idx = vartype_idx * 100 + dtype_idx
    return combined_idx


def get_dtype_vartype_name(dtype, specialtype):
    dtstr = get_dtype_str(dtype)
    typename = f"{specialtype}_{dtstr}".upper()
    return typename


def construct_vartype_dtype_enum():
    dtypes = get_available_dtypes()
    specialtypes = get_vartype_names()
    typenames = set()
    typenames.add("UNKNOWN")
    for st in specialtypes:
        for dt in dtypes:
            t = get_dtype_vartype_name(dt, st)
            typenames.add(t)
    code = cpp.line(f"enum vartype {{")
    icode = ",\n".join(p for p in sorted(typenames))
    code += cpp.indent_code(icode)
    code += cpp.line("")
    code += cpp.statement("}")
    return code


def construct_vartype2str_func():
    code = cpp.line("std::string vartype2str(vartype vt) {")
    dtypes = get_available_dtypes()
    specialtypes = get_vartype_names()
    icode = cpp.line("switch (vt) {")
    iicode = ""
    typenames = set()
    for st in specialtypes:
        for dt in dtypes:
            t = get_dtype_vartype_name(dt, st)
            if t in typenames:
                continue
            iicode += cpp.statement(f'case {t}:  return "{t}"')
            typenames.add(t)
    icode += cpp.indent_code(iicode, 4)
    icode += cpp.close_block()
    code += cpp.indent_code(icode, 4)
    code += cpp.throw_runtime_error("should not arrivere here", 4)
    code += cpp.statement('return "should not arrive here"', 4)
    code += cpp.close_block()
    return code


def construct_vartype_validation_func():
    code = r"""
    void validate_vartype_consistency(std::string varname, vartype current_type, vartype expected_type) {
      if (current_type != expected_type && expected_type != UNKNOWN) {
        std::string current_type_str = vartype2str(current_type);
        std::string expected_type_str = vartype2str(expected_type);
        std::stringstream errmsg;
        errmsg << "variable `" << varname << "` is now encountered "
              << "with type `" << current_type_str << "` but was "
              << "previously encountered with type `" << expected_type_str << ". "
              << "Either the ENDF recipe is wrongly specified or the ENDF file "
              << "contains some forbidden flag values." << std::endl;
        throw std::runtime_error(errmsg.str());
      }
    }
    """
    return cpp.indent_code(code, -4)


def get_last_type_varname(vartok):
    varname = "aux_last_type_read_for_"
    varname += str(vartok)
    return varname


def initialize_last_type_var(vartok):
    varname = get_last_type_varname(vartok)
    code = cpp.statement(f"vartype {varname} = UNKNOWN")
    return code


def update_last_type_var(vartok, dtype, specialtype):
    vartype = get_dtype_vartype_name(dtype, specialtype)
    varname = get_last_type_varname(vartok)
    code = cpp.statement(f"{varname} = {vartype}")
    return code


def has_vartype(vartok, dtype, specialtype):
    vartype = get_dtype_vartype_name(dtype, specialtype)
    v = get_last_type_varname(vartok)
    return f"({v} == {vartype})"


def type_change_check(vartok, dtype, specialtype):
    last_type_varname = get_last_type_varname(vartok)
    vartype = get_dtype_vartype_name(dtype, specialtype)
    logical_expr1 = f"{last_type_varname} != {vartype}"
    logical_expr2 = f"{last_type_varname} != UNKNOWN"
    logical_expr = cpp.logical_and([logical_expr1, logical_expr2])
    statement = cpp.statement("raise_vartype_mismatch()")
    code = cpp.pureif(logical_expr, statement)
    return code


def has_loopvartype(vartok, vardict):
    vartypes = get_var_types(vartok, vardict)
    if vartypes is None:
        return False
    for vartype in vartypes:
        if vartype[0] == "loopvartype":
            if len(vartypes) != 1:
                raise IndexError(
                    f"variable `{vartok}` of loopvartype cannot be associated with other types"
                )
            return True
    return False


def init_local_var_from_global_var(v, ctyp):
    return cpp.concat(
        [
            cpp.statement(f"{ctyp}& glob_{v} = {v}"),
            cpp.statement(f"{ctyp} {v} = glob_{v}"),
        ]
    )


def check_variable(vartok, vardict):
    if not isinstance(vartok, VariableToken):
        raise TypeError(f"vartok {vartok} must be of type Variabletoken")
    if vartok.indices == 0:
        return
    for idxvar in vartok.indices:
        if not isinstance(idxvar, VariableToken):
            return
        d = vardict
        while "__up" in d and idxvar not in d:
            d = d["__up"]
        if idxvar not in d:
            raise IndexError(f"variable {idxvar} does not exist")


def dict_assign(dictvar, idcs, val):
    if len(idcs) == 0:
        return TypeError("len(idcs) must be >= 1")
    elif len(idcs) == 1:
        idx = idcs[0]
        idxstr = f"py::cast({idx})"
        code = cpp.statement(f"{dictvar}[{idxstr}] = {val}")
        return code
    code = cpp.statement(f"py::dict curdict = {dictvar}")
    for i, idx in enumerate(idcs[:-1]):
        idxstr = f"py::cast({idx})"
        inner_code = cpp.pureif(
            f"! curdict.contains({idxstr})",
            cpp.statement(f"curdict[{idxstr}] = py::dict()"),
        )
        inner_code += cpp.statement(f"curdict = curdict[{idxstr}]")
        code += inner_code
    idxstr = f"py::cast({idcs[-1]})"
    code += cpp.statement(f"curdict[{idxstr}] = {val}")
    code = cpp.open_block() + cpp.indent_code(code, cpp.INDENT) + cpp.close_block()
    return code
