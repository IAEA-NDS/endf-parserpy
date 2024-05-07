############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/25
# Last modified:   2024/05/07
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.compiler.expr_utils.custom_nodes import VariableToken
from endf_parserpy.compiler.expr_utils.equation_utils import (
    get_variables_in_expr,
    contains_variable,
)
from endf_parserpy.compiler.node_checks import is_loop
from endf_parserpy.compiler.node_aux import get_loopvar


def can_moveup_ptrassign(vartok, idxexpr, orig_node, dest_node):
    if dest_node is None:
        return False
    if contains_variable(dest_node, vartok, skip_nodes=[orig_node]):
        return False
    variables = get_variables_in_expr(idxexpr)
    for v in variables:
        if contains_variable(dest_node, v, skip_nodes=[orig_node]):
            return False

    if is_loop(dest_node):
        loopvar = get_loopvar(dest_node)
        if contains_variable(idxexpr, loopvar):
            return False
    return True


def moveup_ptrassign(vartok, idx, node, limit_node=None, only_checkpoints=True):
    idxexpr = vartok.indices[idx]
    checkpoint = node
    curnode = node
    parent_node = curnode.parent
    while curnode.parent is not None and curnode is not limit_node:
        if not can_moveup_ptrassign(vartok, idxexpr, curnode, curnode.parent):
            break
        curnode = curnode.parent
        if is_loop(curnode):
            checkpoint = curnode
    if only_checkpoints:
        return checkpoint
    else:
        return curnode


def get_ptr_varname(vartok, i):
    if not isinstance(vartok, VariableToken):
        raise TypeError("expect vartok of type VariableToken")
    if i < 0 or i + 1 >= len(vartok.indices):
        raise IndexError(f"index i={i} out of range")
    varname = f"ptr_{vartok}_{len(vartok.indices)}d_idx{i}"
    return varname
