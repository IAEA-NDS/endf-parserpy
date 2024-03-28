############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/03/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .expr_utils.conversion import VariableToken


def align_code(code, indent):
    missing_newline = "\n" if code.endswith("\n") else ""
    code_lines = code.splitlines()
    if indent < 0:
        i = -indent
        code_lines = [line[i:] for line in code_lines]
    else:
        i = indent
        code_lines = [" " * i + line for line in code_lines]

    code = "\n".join(code_lines) + missing_newline
    return code


def module_header():
    code = r"""
    #include <pybind11/pybind11.h>
    #include <pybind11/stl.h> // Necessary for STL containers like std::map

    #include <stdexcept>
    #include <iostream>
    #include <vector>
    #include <string>

    namespace py = pybind11;


    double endfstr2float(const std::string& str) {
        char tbuf[str.size()+1];
        int j = 0;
        bool in_number = false;
        bool in_exponent = false;
        for (int i=0; i < (int)str.size(); i++) {
            char c = str[i];
            if (c == ' ') continue;
            if (in_number) {
                if (!in_exponent) {
                    if (c=='+' || c=='-') {
                        tbuf[j++] = 'e';
                        in_exponent = true;
                    }
                } else if (c=='e' || c=='E') {
                    in_exponent = true;
                }
            } else {
                if (c == '.' || (c >= '0' && c <= '9')) {
                    in_number = true;
                }
            }
            tbuf[j++] = c;
        }
        if (j==0) tbuf[j++] = '0';
        tbuf[j++] = '\0';
        return std::stod(tbuf);
    }


    int endfstr2int(const std::string& str) {
        if (str.find_first_not_of(' ') == std::string::npos) {
            return 0;
        }
        return std::stoi(str);
    }


    double cpp_read_float_field(const std::string& str, const char fieldnum) {
        return endfstr2float(str.substr(fieldnum*11, 11));
    }


    double cpp_read_int_field(const std::string& str, const char fieldnum) {
        return endfstr2int(str.substr(fieldnum*11, 11));
    }


    std::string* cpp_read_line(std::vector<std::string>& lines, int& linenum) {
        if (lines.size() <= linenum) {
            throw std::runtime_error("expected more lines");
        }
        return &lines[linenum++];
    }


    void cpp_read_send(std::vector<std::string>& lines, int& linenum) {
        std::string* lineptr = cpp_read_line(lines, linenum);
        int mtnum = std::stoi(lineptr->substr(72, 3));
        if (cpp_read_float_field(*lineptr, 0) != 0.0 ||
            cpp_read_float_field(*lineptr, 1) != 0.0 ||
            cpp_read_int_field(*lineptr, 2) != 0 ||
            cpp_read_int_field(*lineptr, 3) != 0 ||
            cpp_read_int_field(*lineptr, 4) != 0 ||
            cpp_read_int_field(*lineptr, 5) != 0 ||
            mtnum != 0) {

            std::cout << linenum << std::endl;
            std::cout << *lineptr << std::endl;
            throw std::runtime_error("expected SEND record");
        }
    }


    std::vector<int> cpp_read_int_vec(std::vector<std::string>& lines, const int numel, int& linenum) {
        int j = 0;
        std::vector<int> res;
        std::string* lineptr = &lines[linenum];
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_int_field(*lineptr, j++));
            if (j > 5) {
                lineptr = &lines[++linenum];
                j = 0;
            }
        }
        if (j != 0) linenum++;
        return res;
    }


    std::vector<double> cpp_read_float_vec(std::vector<std::string>& lines, const int numel, int& linenum) {
        int j = 0;
        std::vector<double> res;
        std:: string* lineptr = &lines[linenum];
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_float_field(*lineptr, j++));
            if (j > 5) {
                lineptr = &lines[++linenum];
                j = 0;
            }
        }
        if (j != 0) linenum++;
        return res;
    }

    """
    return align_code(code, -4)


def register_cpp_parsefuns(parsefuns):
    code = "\n\nPYBIND11_MODULE(cpp_parsefuns, m) {\n"
    for parsefun in parsefuns:
        curcode = f"""m.def("{parsefun}", &{parsefun}, "parsing function");\n"""
        code += align_code(curcode, 4)
    code += "\n}"
    return code


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


def adopt_varval(vartok):
    varname = get_cpp_varname(vartok)
    num_dims = len(vartok.indices)
    code = ""
    if num_dims == 0:
        code += f"glob_{varname} = {varname};\n"
        v = f"{varname}_read"
        code += f"glob_{v} = {v};\n"
    else:
        code += f"glob_{varname} = {varname};\n"
        for i in range(num_dims):
            v = f"{varname}_lastidx{i}_read"
            code += f"glob_{v} = {v};\n"
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
    return logical_and(
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


def get_cpp_varname(vartok):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    return varname


def fillout_template(template, params=None, idx=None):
    if params is None:
        return template
    if idx is not None:
        params = {k: v[idx] for k, v in params.items()}
        res = template.format(**params)
    return res


def line(code):
    return code.strip().rstrip("\n") + ";\n"


def comment(text):
    return "// " + text + "\n"


def block(code, only_indent=False):
    code = align_code(code, 4)
    if not only_indent:
        code = "{\n" + code + "}\n"
    return code


def nested_block_repeat(code, num, only_indent=False, extra_params=None):
    if num == 0:
        return ""
    result_code = code
    if extra_params is not None:
        result_code = fillout_template(code, extra_params, idx=0)
    result_code = block(result_code)
    for i in range(1, num):
        result_code = block(
            concat([fillout_template(code, extra_params, idx=i), result_code])
        )
    return result_code


def logical_not(logical_expression):
    if logical_expression.strip("() ") == "true":
        return ""
    return "(! " + logical_expression + ")"


def logical_or(logical_expressions):
    return "(" + " || ".join(logical_expressions) + ")"


def logical_and(logical_expressions):
    return "(" + " && ".join(logical_expressions) + ")"


def did_read_var(vartok):
    return _did_read_var(vartok)


def did_not_read_var(vartok):
    return "(! " + _did_read_var(vartok) + ")"


def any_unread_vars(vartoks):
    return logical_or(did_not_read_var(v) for v in vartoks)


def all_vars_read(vartoks):
    return logical_and(did_read_var(v) for v in vartoks)


def throw_runtime_error(message):
    return f"""throw std::runtime_error("{message}");\n"""


def concat(codes):
    return "\n".join(codes) + "\n"


def conditional_branches(conditions, codes, default=None):
    if_cond = conditions[0]
    code = f"if ({if_cond}) {{\n"
    code += align_code(codes[0], 4)
    for elif_cond, elif_body in zip(conditions[1:], codes[1:]):
        code += f"\n}} else if ({elif_cond}) {{\n"
        code += align_code(elif_body, 4)
    if default is not None:
        code += "\n} else {\n"
        code += align_code(default, 4)
    code += "}\n"
    return code


def ifelse(condition, code, other_code):
    return conditional_branches([condition], [code], default=other_code)


def pureif(condition, code):
    if condition.strip("() ") == "":
        return ""
    return conditional_branches([condition], [code])


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
    code = f"// assign expression to variable {vartok}\n"
    if mark_as_read:
        code += mark_var_as_read(vartok)
    if len(vartok.indices) == 0:
        code += align_code(
            f"""
        {cpp_varname} = {exprstr};
        """,
            -8,
        )
    else:
        indices = vartok.indices
        code += align_code(
            f"""
        {{
            auto& cpp_curvar = {cpp_varname};
        """,
            -8,
        )
        for i, idx in enumerate(indices):
            idxstr = get_shifted_idxstr(idx, vardict)
            code += align_code(
                f"""
            {{
                if (cpp_curvar.size() <= ({idxstr})) {{
                    using cpp_cureltype = std::remove_reference<decltype(cpp_curvar)>::type::value_type;
                    cpp_cureltype cpp_curel;
                    cpp_curvar.push_back(cpp_curel);
                }}
                auto& cpp_lastcurvar = cpp_curvar;
                auto& cpp_curvar = cpp_lastcurvar[{idxstr}];
            """,
                -8 + i * 4,
            )

        code += align_code(
            f"""
                cpp_curvar = {exprstr};
        """,
            -8 + (len(indices) - 1) * 4,
        )

        for i in range(len(indices)):
            code += align_code(
                """
            }
            """,
                -8 + (len(indices) - 1 - i) * 4,
            )

        code += align_code(
            """
        }
        """,
            -8,
        )
    return code


def store_var_in_endf_dict(vartok, vardict):
    _check_variable(vartok, vardict)
    code = f"// store variable {vartok} in endf dictionary"
    src_varname = get_cpp_extvarname(vartok, vardict)
    if len(vartok.indices) == 0:
        code += align_code(
            f"""
        cpp_current_dict["{vartok}"] = {src_varname};
        """,
            -8,
        )
    else:
        dest_varname = vartok
        indices = vartok.indices
        code += align_code(
            f"""
        if (! cpp_current_dict.contains("{dest_varname}")) {{
            cpp_current_dict["{dest_varname}"] = py::dict();
        }}
        cpp_workdict = cpp_current_dict["{dest_varname}"];
        """,
            -8,
        )
        for i, idx in enumerate(indices):
            cpp_idxstr = get_cpp_varname(idx)
            if not isinstance(idx, VariableToken):
                dest_varname += f"[py::cast({cpp_idxstr})]"
            else:
                cpp_idxstr = get_cpp_extvarname(idx, vardict)
                if i + 1 < len(indices):
                    code += align_code(
                        f"""
                    if (! cpp_workdict.contains(py::cast({cpp_idxstr}))) {{
                        cpp_workdict[py::cast({cpp_idxstr})] = py::dict();
                    }}
                    cpp_workdict = cpp_workdict[py::cast({cpp_idxstr})];
                    """,
                        -20,
                    )
                else:
                    code += align_code(
                        f"""
                    cpp_workdict[py::cast({cpp_idxstr})] = {src_varname};
                    """,
                        -20,
                    )
    return code


def read_line():
    code = "cpp_lineptr = cpp_read_line(cpp_lines, cpp_linenum);\n"
    return code


def read_numeric_field(vartok, fieldpos, dtype, vardict):
    if dtype == float:
        readfun = "cpp_read_float_field"
    elif dtype == int:
        readfun = "cpp_read_int_field"
    exprstr = f"{readfun}(*cpp_lineptr, {fieldpos});"
    code = assign_exprstr_to_var(vartok, exprstr, vardict)
    return code


def get_numeric_field(fieldpos, dtype):
    if dtype == float:
        readfun = "cpp_read_float_field"
    elif dtype == int:
        readfun = "cpp_read_int_field"
    code = f"{readfun}(*cpp_lineptr, {fieldpos});"
    return code


def read_text_field(vartok, start, length, vardict):
    exprstr = f"(*cpp_lineptr).substr({start}, {length});"
    code = assign_exprstr_to_var(vartok, exprstr, vardict)
    return code


def open_section(vartok, vardict):
    _check_variable(vartok, vardict)
    secname = vartok
    indices = vartok.indices
    code = align_code(
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
        code += align_code(
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
    code = align_code(
        """
        cpp_current_dict = cpp_parent_dict;
    }
    """,
        -4,
    )
    return code


def read_tab_body(xvar, yvar):
    code = align_code(
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
        code += align_code(
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
    code += align_code(
        """
    }
    """,
        -4,
    )
    return code


def parsefun_header(fun_name):
    code = align_code(
        rf"""
    py::dict {fun_name}(std::vector<std::string> cpp_lines) {{
        std::vector<int> cpp_intvec;
        std::vector<double> cpp_floatvec;
        int cpp_linenum = 0;
        std::string *cpp_lineptr;
        py::dict cpp_parent_dict;
        py::dict cpp_current_dict;
        py::dict cpp_workdict;
        int cpp_idxnum;
        int cpp_int_val;
        double cpp_float_val;

        cpp_current_dict["MAT"] = std::stoi(cpp_lines[0].substr(66, 4));
        cpp_current_dict["MF"] = std::stoi(cpp_lines[0].substr(70, 2));
        cpp_current_dict["MT"] = std::stoi(cpp_lines[0].substr(72, 3));
    """,
        -4,
    )
    return code


def parsefun_footer():
    code = align_code(
        """
        cpp_read_send(cpp_lines, cpp_linenum);
        return cpp_current_dict;
    }
    """,
        -4,
    )
    return code
