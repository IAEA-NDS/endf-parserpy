############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/12
# Last modified:   2026/10/12
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################


# These recipes compare variables in if-conditions, where a variable
# may not have been read when the condition is evaluated. Such a
# comparison is false, whichever side of the relation the variable
# is on. The recipes can be used to check that the Python and the
# C++ parser agree on this.


# B is only read if S==1 and appears on the left of the relation
ENDF_RECIPE_MF3_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, A, S, 0, 0] CONT
if S == 1:
    [MAT,MF,MT/ 0.0, 0.0, B, 0, 0, 0] CONT
endif
if B != A:
    [MAT,MF,MT/ 0.0, 0.0, 1, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, 2, 0, 0, 0] CONT
endif
SEND
"""


# the same with B on the right of the relation
ENDF_RECIPE_MF3_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, A, S, 0, 0] CONT
if S == 1:
    [MAT,MF,MT/ 0.0, 0.0, B, 0, 0, 0] CONT
endif
if A != B:
    [MAT,MF,MT/ 0.0, 0.0, 1, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, 2, 0, 0, 0] CONT
endif
SEND
"""


# a constant on the left and a variable on the right of the relation
# (cf. MF1/MT4 with the variable on the left)
ENDF_RECIPE_MF3_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
if 2 != NX [lookahead=1]:
    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NX, 0/ {X[i]}{i=1 to NX} ] LIST
else:
    [MAT,MF,MT/ 0.0, 0.0, 0, 0, 2, 0/ Y[1], Y[2] ] LIST
endif
SEND
"""
