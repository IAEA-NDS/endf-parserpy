############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/21
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from ..tree_utils import get_child
from .expr_utils.conversion import VariableToken
from .expr_utils.node_checks import is_variable
from .node_aux import get_variables_in_expr


def register_var(vartok, dtype, vardict):
    vardict[vartok] = dtype


def unregister_var(vartok, vardict):
    if vartok.startswith("__"):
        raise TypeError("not a valid variable")
    del vardict[vartok]


def register_special_type(vartok, vardict, special_type):
    special_types = vardict.get("__special_types", {})
    special_types[vartok] = special_type


def did_encounter_var(vartok, vardict):
    while vartok not in vardict and "__up" in vardict:
        vardict = vardict["__up"]
    return vartok in vardict


def count_not_encountered_vars(node, vardict):
    varset = get_variables_in_expr(node)
    return sum(not did_encounter_var(v, vardict) for v in varset)


def register_abbreviation(node, vardict):
    vartok = VariableToken(get_child(node, "VARNAME"))
    expr = get_child(node, "expr")
    abbrevs = vardict.setdefault("__abbrevs", {})
    abbrevs[vartok] = expr


def unregister_abbreviations(vardict):
    if "__abbrevs" in vardict:
        del vardict["__abbrevs"]


def expand_abbreviation(node, vardict):
    if not is_variable(node):
        return node
    if "__abbrevs" not in vardict:
        return node
    abbrevs = vardict["__abbrevs"]
    if node not in abbrevs:
        return node
    return abbrevs[node].children[0]
