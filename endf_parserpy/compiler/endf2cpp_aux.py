############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/04/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .expr_utils.conversion import VariableToken
from . import cpp_primitives as cpp


def _initialize_aux_read_vars(vartok, save_state=False):
    varname = get_cpp_varname(vartok)
    num_dims = len(vartok.indices)
    code = ""
    if num_dims == 0:
        v = f"{varname}_read"
        if save_state:
            code += f"bool& glob_{v} = {v};\n"
            code += f"bool {v} = glob_{v};\n"
        else:
            code += f"bool {varname}_read = false;\n"
    else:
        for i in range(num_dims):
            v = f"{varname}_lastidx{i}_read"
            if save_state:
                code += f"int& glob_{v} = {v};\n"
                code += f"int {v} = glob_{v};\n"
            else:
                code += f"int {v} = -1;\n"
    return code


def define_var(vartok, dtype, save_state=False):
    if dtype == float:
        dtype = "double"
    elif dtype == int:
        dtype = "int"
    elif dtype == str:
        dtype = "std::string"
    else:
        raise TypeError(f"unknown dtype {dtype}")
    num_indices = len(vartok.indices)
    if num_indices > 0:
        for i in range(num_indices):
            dtype = "std::vector<" + dtype
        for i in range(num_indices):
            dtype += ">"
    varname = get_cpp_varname(vartok)
    code = ""
    if save_state:
        code += f"{dtype}& glob_{varname} = {varname};\n"
        code += f"{dtype} {varname} = glob_{varname};\n"
    else:
        code += f"{dtype} {varname};\n"
    code += _initialize_aux_read_vars(vartok, save_state)
    return code


def _did_read_var(vartok):
    varname = get_cpp_varname(vartok)
    indices = vartok.indices
    num_dims = len(indices)
    if num_dims == 0:
        return f"({varname}_read == true)"
    return cpp.logical_and(
        f"({varname}_lastidx{i}_read == {get_cpp_varname(idx)})"
        for i, idx in enumerate(indices)
    )


def mark_var_as_read(vartok, prefix=""):
    varname = get_cpp_varname(vartok)
    indices = vartok.indices
    num_dims = len(indices)
    if num_dims == 0:
        return f"{prefix}{varname}_read = true;\n"
    return (
        "\n".join(
            f"{prefix}{varname}_lastidx{i}_read = {get_cpp_varname(idx)};"
            for i, idx in enumerate(indices)
        )
        + "\n"
    )


def mark_var_as_unread(vartok, prefix=""):
    varname = get_cpp_varname(vartok)
    indices = vartok.indices
    num_dims = len(indices)
    if num_dims == 0:
        return f"{prefix}{varname}_read = false;\n"
    return (
        "\n".join(
            f"{prefix}{varname}_lastidx{i}_read = -1;" for i, idx in enumerate(indices)
        )
        + "\n"
    )


def _check_variable(vartok, vardict):
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
        if not type(d[idxvar]) == tuple:
            raise TypeError(f"variable {idxvar} used as index not a loop variable")


def get_cpp_varname(vartok, quote=False):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    if quote:
        varname = '"' + varname + '"'
    return varname


def did_read_var(vartok):
    return _did_read_var(vartok)


def did_not_read_var(vartok):
    return "(! " + _did_read_var(vartok) + ")"


def any_unread_vars(vartoks):
    return cpp.logical_or(did_not_read_var(v) for v in vartoks)


def all_vars_read(vartoks):
    return cpp.logical_and(did_read_var(v) for v in vartoks)


def get_cpp_extvarname(vartok, vardict):
    varname = get_cpp_varname(vartok)
    for idxtok in vartok.indices:
        shifted_idxstr = get_shifted_idxstr(idxtok, vardict)
        varname += f"[{shifted_idxstr}]"
    return varname


def get_shifted_idxstr(idxtok, vardict):
    cpp_idxstr = get_cpp_extvarname(idxtok, vardict)
    if not isinstance(idxtok, VariableToken):
        idxstr = f"{cpp_idxstr}"
    else:
        shift_exprstr = vardict[idxtok][0]
        idxstr = f"({cpp_idxstr}-({shift_exprstr}))"
    return idxstr


def assign_exprstr_to_var(
    vartok, exprstr, vardict, use_cpp_name=True, mark_as_read=True
):
    _check_variable(vartok, vardict)
    if use_cpp_name:
        cpp_varname = get_cpp_varname(vartok)
    else:
        cpp_varname = str(vartok)
    code = cpp.comment(f"assign expression to variable {vartok}")
    if mark_as_read:
        code += mark_var_as_read(vartok)
    if len(vartok.indices) == 0:
        code += cpp.statement(f"{cpp_varname} = {exprstr}")
    else:
        indices = vartok.indices
        most_outer_code = cpp.statement(f"auto& cpp_curvar = {cpp_varname}")
        outer_code = cpp.concat(
            [
                cpp.pureif(
                    condition="cpp_curvar.size() <= ({idxstr})",
                    code=cpp.concat(
                        [
                            cpp.statement(
                                "using cpp_cureltype = "
                                + "std::remove_reference<decltype(cpp_curvar)>"
                                + "::type::value_type"
                            ),
                            cpp.statement("cpp_cureltype cpp_curel"),
                            cpp.statement("cpp_curvar.push_back(cpp_curel)"),
                        ]
                    ),
                    escape=True,
                ),
                cpp.statement("auto& cpp_lastcurvar = cpp_curvar"),
                cpp.statement("auto& cpp_curvar = cpp_lastcurvar[{idxstr}]"),
            ]
        )
        inner_code = cpp.statement("cpp_curvar = {exprstr}")
        nested_codes = [most_outer_code] + [outer_code] * len(indices) + [inner_code]
        extra_params = {
            **{"exprstr": {len(indices) + 1: exprstr}},
            **{
                "idxstr": {
                    i: get_shifted_idxstr(idx, vardict)
                    for i, idx in enumerate(indices, start=1)
                }
            },
        }
        code += cpp.nested_block_repeat(nested_codes, len(indices) + 2, extra_params)
    return code


def store_var_in_endf_dict(vartok, vardict):
    _check_variable(vartok, vardict)
    code = cpp.comment(f"store variable {vartok} in endf dictionary")
    src_varname = get_cpp_extvarname(vartok, vardict)
    indices = vartok.indices
    if len(indices) == 0:
        code += cpp.statement(f"""cpp_current_dict["{vartok}"] = {src_varname}""")
        return code

    code += cpp.statement("cpp_workdict = cpp_current_dict")
    change_dict_code = cpp.concat(
        [
            cpp.pureif(
                condition="! cpp_workdict.contains(py::cast({idxstr}))",
                code=cpp.statement("cpp_workdict[py::cast({idxstr})] = py::dict()"),
                escape=True,
            ),
            cpp.statement("cpp_workdict = cpp_workdict[py::cast({idxstr})]"),
        ]
    )
    cpp_idxstrs = [f'"{vartok}"']
    cpp_idxstrs += [
        str(idx) if not isinstance(idx, VariableToken) else get_cpp_varname(idx)
        for idx in indices
    ]
    extra_params = {"idxstr": {i: v for i, v in enumerate(cpp_idxstrs[:-1])}}
    code += cpp.block_repeat(change_dict_code, len(indices), extra_params=extra_params)
    src_varname = get_cpp_extvarname(vartok, vardict)
    code += cpp.statement(f"cpp_workdict[py::cast({cpp_idxstrs[-1]})] = {src_varname}")
    return code


def read_line():
    code = "cpp_lineptr = cpp_read_line(cpp_lines, cpp_linenum);\n"
    return code


def get_numeric_field(fieldpos, dtype):
    if dtype == float:
        readfun = "cpp_read_float_field"
    elif dtype == int:
        readfun = "cpp_read_int_field"
    code = f"{readfun}(*cpp_lineptr, {fieldpos})"
    return code


def get_text_field(vartok, start, length, vardict):
    code = f"(*cpp_lineptr).substr({start}, {length})"
    return code


def open_section(vartok, vardict):
    _check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices
    code = cpp.indent_code(
        f"""
    {{
        py::dict cpp_parent_dict = cpp_current_dict;
        if (! cpp_parent_dict.contains("{secname}")) {{
            cpp_parent_dict["{secname}"] = py::dict();
        }}
        py::dict cpp_current_dict = cpp_parent_dict["{secname}"];
    """,
        -4,
    )
    for idx in indices:
        cpp_idxstr = get_cpp_varname(idx)
        idxstr = f"py::cast({cpp_idxstr})"
        code += cpp.indent_code(
            f"""
        if (! cpp_current_dict.contains({idxstr})) {{
            cpp_current_dict[{idxstr}] = py::dict();
        }}
        cpp_current_dict = cpp_current_dict[{idxstr}];
        """,
            -4,
        )
    return code


def close_section():
    code = cpp.indent_code(
        """
        cpp_current_dict = cpp_parent_dict;
    }
    """,
        -4,
    )
    return code


def read_tab_body(xvar, yvar):
    code = cpp.indent_code(
        """
    {
        int cpp_j;
        int cpp_nr = cpp_read_int_field(*cpp_lineptr, 4);
        int cpp_np = cpp_read_int_field(*cpp_lineptr, 5);

        std::vector<int> NBT;
        std::vector<int> INT;
        cpp_intvec = cpp_read_int_vec(cpp_lines, 2*cpp_nr, cpp_linenum);
        cpp_j = 0;
        for (int cpp_i=0; cpp_i < cpp_nr; cpp_i++) {
            NBT.push_back(cpp_intvec[cpp_j++]);
            INT.push_back(cpp_intvec[cpp_j++]);
        }

        cpp_current_dict["NBT"] = NBT;
        cpp_current_dict["INT"] = INT;
    """,
        -4,
    )

    if xvar is not None or yvar is not None:
        if xvar is None or yvar is None:
            raise ValueError("provide both xyvar with xvar")
        code += cpp.indent_code(
            f"""
        std::vector<double> {xvar};
        std::vector<double> {yvar};
        cpp_floatvec = cpp_read_float_vec(cpp_lines, 2*cpp_np, cpp_linenum);
        cpp_j = 0;
        for (int cpp_i=0; cpp_i < cpp_np; cpp_i++) {{
            {xvar}.push_back(cpp_floatvec[cpp_j++]);
            {yvar}.push_back(cpp_floatvec[cpp_j++]);
        }}

        cpp_current_dict["{xvar}"] = {xvar};
        cpp_current_dict["{yvar}"] = {yvar};
        """,
            -8,
        )
    code += cpp.indent_code(
        """
    }
    """,
        -4,
    )
    return code
