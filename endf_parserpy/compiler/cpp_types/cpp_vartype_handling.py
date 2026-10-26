############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/06
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from bisect import bisect_right
from endf_parserpy.compiler import cpp_primitives as cpp
from endf_parserpy.compiler.variable_management import get_var_types
from .cpp_dtype_aux import get_dtype_str, get_dtype_idx, get_available_dtypes
from .cpp_type_information import get_vartype_idx, get_vartype_names


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
    code = cpp.line("inline std::string vartype2str(vartype vt) {")
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
    inline void validate_vartype_consistency(std::string varname, vartype current_type, vartype expected_type) {
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
    code = cpp.statement(
        f'validate_vartype_consistency("{vartok}", {vartype}, {last_type_varname})'
    )
    return code


_TYPE_VARNAME_RE = re.compile(r"\baux_last_type_read_for_(\w+)\b")
_TYPE_DECL_RE = re.compile(
    r"^[ \t]*vartype aux_last_type_read_for_(\w+) = UNKNOWN;$", re.M
)
_TYPE_UPDATE_RE = re.compile(r"^[ \t]*aux_last_type_read_for_(\w+) = (\w+);$", re.M)
_TYPE_CHECK_RE = re.compile(
    r'^[ \t]*validate_vartype_consistency\("(\w+)", (\w+), '
    r"aux_last_type_read_for_(\w+)\);\n",
    re.M,
)
_TYPE_COMPARISON_RE = re.compile(r"\baux_last_type_read_for_\w+ == \w+\)")


def _code_braces(code):
    # the positions and kinds of the braces of the code that delimit
    # blocks, i.e. outside of string and character literals and comments,
    # and the ranges of the literals and comments
    braces = []
    skipped = []
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c and code[j] != "\n":
                j += 2 if code[j] == "\\" else 1
            skipped.append((i, j + 1))
            i = j + 1
        elif code.startswith("//", i):
            j = code.find("\n", i)
            j = n if j == -1 else j
            skipped.append((i, j))
            i = j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            j = n if j == -1 else j + 2
            skipped.append((i, j))
            i = j
        else:
            if c in "{}":
                braces.append((i, c))
            i += 1
    return braces, skipped


def remove_redundant_type_checks(code):
    """Remove the type checks of a function that cannot fail.

    The variable ``aux_last_type_read_for_X`` holding the type of the last
    value assigned to the variable X is declared with the value
    ``UNKNOWN`` in the block of the scope of X (the function, a section
    or a named TAB1, TAB2 or LIST record, which have their own variables)
    and changes only in the statements generated by
    :func:`update_last_type_var`. Each of these statements and each check
    generated by :func:`type_change_check` refers to the declaration of
    the innermost enclosing block that declares the variable, as in C++.
    If all the statements referring to a declaration assign the same
    type, the variable holds either ``UNKNOWN`` or this type, so that the
    checks of this type referring to the declaration cannot fail and are
    removed. The checks of a variable assigned values of different types
    in one scope (e.g. integer and float, or a scalar and an array) are
    kept, and so are all checks of a variable that occurs in any other
    statement.
    """
    braces, skipped = _code_braces(code)
    skipped_starts = [s for s, _ in skipped]

    def in_skipped(pos):
        k = bisect_right(skipped_starts, pos) - 1
        return k >= 0 and pos < skipped[k][1]

    # the events in the order of the code: braces, declarations, type
    # updates and checks (each at the position of its variable name)
    events = [(pos, kind, None) for pos, kind in braces]
    recognized = set()
    for kind, regex in (
        ("decl", _TYPE_DECL_RE),
        ("update", _TYPE_UPDATE_RE),
        ("check", _TYPE_CHECK_RE),
    ):
        for m in regex.finditer(code):
            if in_skipped(m.start()):
                continue
            group = 3 if kind == "check" else 1
            recognized.add(m.start(group) - len("aux_last_type_read_for_"))
            events.append((m.start(), kind, m))
    # a variable in another statement (other than the comparisons of the
    # stores) keeps all its checks
    unsafe = set()
    for m in _TYPE_VARNAME_RE.finditer(code):
        if m.start() in recognized or in_skipped(m.start()):
            continue
        if _TYPE_COMPARISON_RE.match(code, m.start()):
            continue
        unsafe.add(m.group(1))
    events.sort(key=lambda e: e[0])

    # each declaration is identified by a number; the declarations of
    # the variables used without a declaration of the code by their name
    scopes = [{}]
    assigned_types = {}
    checks = []
    num_decls = 0
    for pos, kind, m in events:
        if kind == "{":
            scopes.append({})
        elif kind == "}":
            if len(scopes) > 1:
                scopes.pop()
        elif kind == "decl":
            scopes[-1][m.group(1)] = num_decls
            num_decls += 1
        else:
            varname = m.group(1) if kind == "update" else m.group(3)
            decl = next(
                (sc[varname] for sc in reversed(scopes) if varname in sc), varname
            )
            if kind == "update":
                assigned_types.setdefault(decl, set()).add(m.group(2))
            else:
                checks.append((m, decl))

    removed = []
    for m, decl in checks:
        vartok, vartype, varname = m.groups()
        if (
            vartok == varname
            and varname not in unsafe
            and assigned_types.get(decl) == {vartype}
        ):
            removed.append((m.start(), m.end()))
    if not removed:
        return code
    parts = []
    last = 0
    for start, end in removed:
        parts.append(code[last:start])
        last = end
    parts.append(code[last:])
    return "".join(parts)


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
