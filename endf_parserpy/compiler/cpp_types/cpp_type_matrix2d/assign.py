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

from lark.lexer import Token
from endf_parserpy.compiler.expr_utils.tree_walkers import transform_nodes
from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.node_trafos import replace_node
from endf_parserpy.compiler.expr_utils.node_checks import is_variable, is_number
from endf_parserpy.compiler.expr_utils.equation_utils import (
    get_variables_in_expr,
    contains_variable,
)
from endf_parserpy.compiler import cpp_primitives as cpp
from endf_parserpy.compiler.variable_management import (
    register_var,
    get_var_types,
)
from endf_parserpy.compiler.node_checks import is_loop, is_loop_head
from endf_parserpy.compiler.node_aux import (
    get_loopvar,
    get_loop_body,
    get_loop_start,
    get_loop_stop,
)
from ..cpp_vartype_handling import has_loopvartype
from ..cpp_varaux import (
    check_variable,
    init_local_var_from_global_var,
)
from ..cpp_dtype_aux import map_dtype
from .query import Query


class Assign:

    @classmethod
    def define_var(cls, vartok, vardict, save_state=False):
        specialtype = Query.get_specialtype_name()
        vartypes = get_var_types(vartok, vardict)
        dtype = next(v[0] for v in vartypes if v[1] == specialtype)
        dtype = map_dtype(dtype)
        dtype = f"Matrix2d<{dtype}>"
        varname = Query.get_cpp_varname(vartok, vardict)
        code = ""
        if save_state:
            code += init_local_var_from_global_var(varname, dtype)
        else:
            code += cpp.statement(f"{dtype} {varname}")
        return code

    @classmethod
    def assign_exprstr_to_var(cls, vartok, indices, exprstr, dtype, vardict, node):

        def return_fail():
            if vardict.get(vartok, None) == "matrix2d":
                raise TypeError(
                    "recipe contains contradicting definitions of "
                    + f"{vartok}, one where it can be interpreted "
                    + "as a matrix and another one where it cannot"
                )
            return False

        if len(vartok.indices) != 2 or node is None:
            return return_fail()
        check_variable(vartok, vardict)

        # ensure that indices contain only
        # a single number or a single (non-array) variable
        if not all(is_variable(v) or is_number(v) for v in vartok.indices):
            return return_fail()

        # sometimes things are defined piece-wise
        # using several consecutive loops.
        # In this case we give up on an array definition here.
        vartypes = get_var_types(vartok, vardict)
        if vartypes is not None:
            return return_fail()

        curnode = node.parent
        inner_loop = None
        outer_loop = None
        while curnode is not None:
            if is_loop(curnode):
                curloopvar = get_loopvar(curnode)
                if any(contains_variable(idx, curloopvar) for idx in vartok.indices):
                    if inner_loop is None:
                        inner_loop = curnode
                    elif outer_loop is None:
                        outer_loop = curnode
                        break
            curnode = curnode.parent

        if curnode is None:
            # can happen if one index contains a number
            # or a loop is missing in the recipe
            return return_fail()

        # ensure that vartok does not appear anywhere
        # else in the nested loop
        outer_body = get_loop_body(outer_loop)
        if contains_variable(outer_body, vartok, skip_nodes=[node]):
            return return_fail()

        # ensure that indices of vartok do not appear
        # in variable assignments in the loop body
        inner_body = get_loop_body(inner_loop)
        for idx in vartok.indices:
            vs = get_variables_in_expr(idx)
            for v in vs:
                # indices are not allowed to contain arrays
                # (ragged arrays are not supported)
                if len(v.indices) > 0:
                    return return_fail()
                if contains_variable(outer_body, v, skip_nodes=[inner_loop]):
                    return return_fail()
                if contains_variable(inner_body, v, skip_nodes=[node]):
                    return return_fail()

        # now let the magic start
        inner_loopvar = get_loopvar(inner_loop)
        outer_loopvar = get_loopvar(outer_loop)
        inner_start = get_loop_start(inner_loop)
        inner_stop = get_loop_stop(inner_loop)
        outer_start = get_loop_start(outer_loop)
        outer_stop = get_loop_stop(outer_loop)

        # ensure that loop boundaries do not appear
        # as variables inside the loops
        limit_vars = set()
        limit_vars.update(get_variables_in_expr(outer_start))
        limit_vars.update(get_variables_in_expr(outer_stop))
        limit_vars.update(get_variables_in_expr(inner_start))
        limit_vars.update(get_variables_in_expr(inner_stop))
        if any(
            contains_variable(outer_loop, v, filters=[is_loop_head]) for v in limit_vars
        ):
            return return_fail()

        outer_lims = (outer_start, outer_stop)
        inner_lims = (inner_start, inner_stop)

        is_triagonal = False
        is_lower = False
        lims = (outer_lims, inner_lims)
        lvars = (inner_loopvar, outer_loopvar)
        depends = [False] * 2
        for i in range(2):
            curlims = lims[i]
            depends[i] = False
        for j, lim in enumerate(curlims):
            vs = get_variables_in_expr(lim)
            # ensure that no arrays are in the
            # limits of the loop variable
            if any(len(w.indices) > 0 for w in vs):
                return return_fail()
            if lvars[i] in vs:
                depends[i] = True
                is_triagonal = True
                if i == 0:
                    is_lower = j == 0
                else:
                    is_lower = j != 0

        # we only allow full and triagonal matrices
        num_depends = sum(depends)
        if num_depends > 1:
            return return_fail()

        real_outer_start = transform_nodes(
            outer_start, replace_node, inner_loopvar, inner_start
        )
        real_outer_stop = transform_nodes(
            outer_stop, replace_node, inner_loopvar, inner_stop
        )
        real_inner_start = transform_nodes(
            inner_start, replace_node, outer_loopvar, outer_start
        )
        real_inner_stop = transform_nodes(
            inner_stop, replace_node, outer_loopvar, outer_stop
        )

        # it may be that the outer loop variable appears as second
        # index and in that case we need to switch variables
        if vartok.indices[0] == outer_loopvar and vartok.indices[1] == inner_loopvar:
            first_idx_range = (real_outer_start, real_outer_stop)
            second_idx_range = (real_inner_start, real_inner_stop)
        if vartok.indices[0] == inner_loopvar and vartok.indices[1] == outer_loopvar:
            first_idx_range = (real_inner_start, real_inner_stop)
            second_idx_range = (real_outer_start, real_outer_stop)

        register_var(vartok, dtype, "Matrix2d", vardict)
        varname = Query.get_cpp_varname(vartok, vardict, dtype=dtype)
        # must be here to avoid a circular import error
        from ..cpp_varops_query import expr2str_shiftidx

        c = (
            f"{varname}.init("
            + ", ".join(
                [
                    transform_nodes(first_idx_range[0], expr2str_shiftidx, vardict),
                    transform_nodes(first_idx_range[1], expr2str_shiftidx, vardict),
                    transform_nodes(second_idx_range[0], expr2str_shiftidx, vardict),
                    transform_nodes(second_idx_range[1], expr2str_shiftidx, vardict),
                    f"{str(is_triagonal).lower()}",
                    f"{str(is_lower).lower()}",
                ]
            )
            + ")"
        )
        precode = cpp.statement(c)
        outer_loop.append_precode(precode)

        extvarname = Query.assemble_extvarname(varname, indices)
        assigncode = cpp.statement(f"{extvarname} = {exprstr}")
        return assigncode

    @classmethod
    def store_var_in_endf_dict2(cls, vartok, vardict):
        src_varname = Query.get_cpp_varname(vartok, vardict)
        assigncode = cpp.statement(
            f'cpp_current_dict["{vartok}"] = {src_varname}.to_pyobj(list_mode)'
        )
        code = cpp.pureif(Query.did_read_var(vartok, vardict), assigncode)
        return code
