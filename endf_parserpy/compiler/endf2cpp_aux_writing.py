############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/19
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from . import cpp_primitives as cpp


def prepare_line(linevar, mat, mf, mt):
    code = cpp.statement(f"{linevar} = cpp_prepare_line({mat}, {mf}, {mt})")
    return code


def prepare_line_la(linevar, mat, mf, mt, lookahead):
    if lookahead:
        return ""
    return prepare_line(linevar, mat, mf, mt)
