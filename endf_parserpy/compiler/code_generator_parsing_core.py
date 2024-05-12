############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/12
# Last modified:   2024/05/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from . import cpp_primitives as cpp
from .cpp_types import cpp_varops_assign
from .cpp_types import cpp_varaux
from . import endf2cpp_aux as aux


def generate_endf_dict_assignments(vardict):
    code = cpp.comment("store data in Python dictionary")
    for vartok in vardict:
        if vartok.startswith("__"):
            continue
        if not vartok.cpp_namespace:
            code += cpp_varops_assign.store_var_in_endf_dict2(vartok, vardict)
    return code


def generate_parse_or_read_verbatim(funname, parse_opts):
    code = cpp.ifelse(
        aux.should_parse_section("mf", "mt", "exclude", "include"),
        cpp_varaux.dict_assign(
            "mfmt_dict", ["mf", "mt"], f"{funname}_istream(cont, {parse_opts})"
        ),
        cpp.concat(
            [
                aux.read_section_verbatim(
                    "verbatim_section",
                    "mat",
                    "mf",
                    "mt",
                    "cont",
                    "is_firstline",
                    parse_opts,
                ),
                cpp_varaux.dict_assign("mfmt_dict", ["mf", "mt"], "verbatim_section"),
            ]
        ),
    )
    return code
