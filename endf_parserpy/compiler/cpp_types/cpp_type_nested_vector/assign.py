############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/22
# Last modified:   2024/10/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import endf_parserpy.compiler.cpp_primitives as cpp
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.equation_utils import (
    contains_variable,
    get_variables_in_expr,
)
from endf_parserpy.compiler.variable_management import (
    register_var,
    get_var_types,
)
from endf_parserpy.compiler.node_checks import is_loop
from endf_parserpy.compiler.node_aux import (
    get_loopvar,
)
from ..cpp_varaux import (
    init_local_var_from_global_var,
)
from ..cpp_dtype_aux import map_dtype
from .query import Query
from .auxiliary import (
    get_ptr_varname,
    moveup_ptrassign,
)


class Assign:

    def define_var(vartok, vardict, save_state=False):
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtype = next(v[0] for v in vartypes if v[1] == specialtype)
        dtype = map_dtype(dtype)
        varname = Query.get_cpp_varname(vartok, vardict)
        num_indices = len(vartok.indices)
        ptr_vardefs = ""
        for i in range(num_indices):
            dtype = "NestedVector<" + dtype + ">"
            if i + 1 < num_indices:
                cur_ptr_var = get_ptr_varname(vartok, num_indices - i - 2)
                ptr_vardefs += cpp.statement(f"{dtype}* {cur_ptr_var}")
        code = ""
        if save_state:
            code += init_local_var_from_global_var(varname, dtype)
        else:
            code += cpp.statement(f"{dtype} {varname}")
        code += ptr_vardefs
        return code

    def assign_exprstr_to_var(vartok, indices, exprstr, dtype, vardict, node):
        if len(indices) == 0:
            return False

        register_var(vartok, dtype, "NestedVector", vardict)
        code = ""
        cpp_varname = Query.get_cpp_varname(vartok, vardict, dtype=dtype)
        ptrvar_old = cpp_varname
        limit_node = None
        for i in range(0, len(indices) - 1):
            idxstr = indices[i]
            ptrvar_new = get_ptr_varname(vartok, i)
            dot = "." if i == 0 else "->"
            new_code = cpp.statement(
                f"{ptrvar_new} = {ptrvar_old}{dot}prepare({idxstr})"
            )
            if node is not None:
                destnode = moveup_ptrassign(vartok, i, node, limit_node)
                limit_node = destnode
                if destnode is not node:
                    destnode.check_my_identity()
                    destnode.append_precode(new_code)
                else:
                    code += new_code
            ptrvar_old = ptrvar_new
        idxstr = indices[-1]
        dot = "." if len(indices) == 1 else "->"
        code += cpp.statement(f"{ptrvar_old}{dot}set({idxstr}, {exprstr})")
        return code

    def store_var_in_endf_dict2(vartok, vardict):
        src_varname = Query.get_cpp_varname(vartok, vardict)
        assigncode = cpp.statement(
            f'cpp_current_dict["{vartok}"] = {src_varname}.to_pyobj(list_mode)'
        )
        code = cpp.pureif(Query.did_read_var(vartok, vardict), assigncode)
        return code
