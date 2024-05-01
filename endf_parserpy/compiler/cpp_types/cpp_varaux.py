############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/21
# Last modified:   2024/05/01
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
from endf_parserpy.compiler.variable_management import get_var_type
from .cpp_type_aux import get_dtype_str


def get_cpp_varname(vartok, vardict):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if vartok.cpp_namespace:
        return str(vartok)

    vartype = get_var_type(vartok, vardict)
    dtypestr = get_dtype_str(vartype[0])
    varname = f"var_{vartok}_{len(vartok.indices)}d"
    varname += f"_{dtypestr}_{vartype[1]}"
    return varname


def is_loop(node):
    if node is None:
        return False
    node_name = get_name(node)
    return node_name in ("for_loop", "list_loop")


def get_loop_head(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_head")
    elif node_name == "list_loop":
        return get_child(node, "list_for_head")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "for_loop":
        return get_child(node, "for_body")
    elif node_name == "list_loop":
        return get_child(node, "list_body")
    else:
        NotImplementedError("node not recognized as loop node")


def get_loopvar(node):
    node = get_loop_head(node)
    return VariableToken(get_child(node, "VARNAME"))


def get_loop_start(node):
    node = get_loop_head(node)
    return get_child(get_child(node, "for_start"), "expr")


def get_loop_stop(node):
    node = get_loop_head(node)
    return get_child(get_child(node, "for_stop"), "expr")


def get_loop_body(node):
    node_name = get_name(node)
    if node_name == "list_loop":
        return get_child(node, "list_body")
    elif node_name == "for_loop":
        return get_child(node, "for_body")
    else:
        raise TypeError("not a loop node")


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
