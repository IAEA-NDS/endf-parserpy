############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# These recipes assign values of different types to the same variable,
# which the parsers check when the variable is assigned. With S=1 and
# N>=1, the variable X is a scalar and an array, in this order in MT1 and
# in the reverse order in MT2, so that the second assignment fails. The
# variable Z of MT3 is an integer or a float, depending on S. In MT4, X
# is a scalar and an array in the section part, as in MT1, and a scalar
# outside of it: the section has its own variables, so that only the
# assignments in the section are checked.


ENDF_RECIPE_MF8_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, S, N, 0, 0] HEAD
if S == 1:
    [MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT
endif
for i=1 to N:
    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT
endfor
SEND
"""


ENDF_RECIPE_MF8_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, S, N, 0, 0] HEAD
for i=1 to N:
    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT
endfor
if S == 1:
    [MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT
endif
SEND
"""


ENDF_RECIPE_MF8_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, S, 0, 0, 0] HEAD
if S == 1:
    [MAT,MF,MT/ 0.0, 0.0, Z, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ Z, 0.0, 0, 0, 0, 0] CONT
endif
SEND
"""


ENDF_RECIPE_MF8_MT4 = """
[MAT,MF,MT/ 0.0, 0.0, S, N, 0, 0] HEAD
[MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT
(part)
[MAT,MF,MT/ 0.0, 0.0, S, N, 0, 0] CONT
if S == 1:
    [MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT
endif
for i=1 to N:
    [MAT,MF,MT/ X[i], 0.0, 0, 0, 0, 0] CONT
endfor
(/part)
SEND
"""
