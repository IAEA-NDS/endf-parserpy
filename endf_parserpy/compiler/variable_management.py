############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/05/01
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.tree_utils import get_child
from .expr_utils.conversion import VariableToken
from .expr_utils.node_checks import is_variable


def register_var(vartok, dtype, special_type, vardict, track_read=True):
    if vartok in vardict:
        if vardict[vartok] != (dtype, special_type):
            previous_dtype = vardict[vartok][0]
            previous_special_type = vardict[vartok][1]
            raise TypeError(
                f"{vartok} was previously associated with "
                + f"datatype ({previous_dtype}, {previous_special_type}) but "
                + f"now should be associated with ({dtype}, {special_type})"
            )
    vardict[vartok] = (dtype, special_type)
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


def get_var_type(vartok, vardict):
    pardict = find_parent_dict(vartok, vardict)
    if pardict is None:
        return None
    return pardict[vartok]


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


def expand_abbreviation(node, vardict):
    if not is_variable(node):
        return node
    if "__abbrevs" not in vardict:
        return node
    abbrevs = vardict["__abbrevs"]
    if node not in abbrevs:
        return node
    return abbrevs[node].children[0]
