############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.recipe_parser.tree import Tree
from endf_parserpy.utils.tree_utils import get_child
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.node_checks import is_variable


def register_var(vartok, dtype, special_type, vardict, track_read=True):
    reg_vartypes = vardict.setdefault(vartok, dict())
    vartype = (dtype, special_type)
    reg_vartypes[vartype] = True
    track_dict = vardict.setdefault("__no_read_tracking", set())
    if not track_read:
        track_dict.add(vartok)


def unregister_var(vartok, vardict):
    if vartok.startswith("__"):
        raise TypeError("not a valid variable")
    del vardict[vartok]
    track_dict = vardict.get("__no_read_tracking", set())
    if vartok in track_dict:
        track_dict.remove(vartok)


def should_track_read(vartok, vardict):
    track_dict = vardict.get("__no_read_tracking", set())
    return vartok not in track_dict


def get_var_types(vartok, vardict):
    pardict = find_parent_dict(vartok, vardict)
    if pardict is None:
        return None
    return tuple(pardict[vartok])


def update_vardict(vardict, add_vardict):
    for v in tuple(vardict) + tuple(add_vardict):
        if v.startswith("__"):
            continue
        vartypes = vardict.setdefault(v, dict())
        vartypes.update(add_vardict.get(v, {}))


def find_parent_dict(vartok, vardict, fail=False):
    d = vardict
    while vartok not in d and "__up" in d:
        d = d["__up"]
    if vartok in d:
        return d
    if fail:
        raise IndexError(f"{vartok} not found in vardict and parents")
    return None


def register_abbreviation(node, vardict):
    vartok = VariableToken(get_child(node, "VARNAME"))
    expr = get_child(node, "expr")
    abbrevs = vardict.setdefault("__abbrevs", {})
    abbrevs[vartok] = expr


def unregister_abbreviations(vardict):
    if "__abbrevs" in vardict:
        del vardict["__abbrevs"]


def _mark_all_vars_inconsistent(node):
    if isinstance(node, VariableToken):
        if node.inconsistent:
            return node
        new_var = VariableToken(
            node, cpp_namespace=node.cpp_namespace, inconsistent=True
        )
        new_var.indices = node.indices
        return new_var
    if isinstance(node, Tree):
        new_node = node.copy()
        new_node.children = [_mark_all_vars_inconsistent(c) for c in node.children]
        return new_node
    return node


def expand_abbreviation(node, vardict):
    if not is_variable(node):
        return node
    if "__abbrevs" not in vardict:
        return node
    abbrevs = vardict["__abbrevs"]
    if node not in abbrevs:
        return node
    expanded = abbrevs[node].children[0]
    # Propagate the `?` (inconsistent) marker through the placeholder so the
    # downstream `contains_potentially_inconsistent_variable` check still sees
    # it after expansion. Without this, `NX := ...` followed by `NX?` loses
    # the marker because the substituted expression contains only the inner
    # variables, none of which carry `inconsistent=True`. (Issue #55)
    if node.inconsistent:
        expanded = _mark_all_vars_inconsistent(expanded)
    return expanded
