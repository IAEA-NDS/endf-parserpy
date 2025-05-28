############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/05/28
# Last modified:   2025/05/28
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
############################################################


# These recipes use expressions with nested arrays as indices.
# The first one employs this functionality directly in record
# fields, whereas the second and third one use it in an if-statement
# and for-loop head, respectively. The recipes can be used
# to check whether extended indexing capabilities work for
# both the Python and the C++ parser.
#
# For example, use the following recipes with these variable assingments:
#   A[1]=9, A[2]=2, B[1]=2, B[2]=4
#   C[1]=5, C[2]=6
#   Then the field linked to B[A[1]-8] should equal B[1]
#   and the field linked to C[B[A[1]-8]] should equal C[2]


ENDF_RECIPE_MF1_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, A[1], A[2], B[1], B[2]] HEAD
[MAT,MF,MT/ 0.0, 0.0, C[1], C[2], 0, 0] CONT
[MAT,MF,MT/ 0.0, 0.0, B[A[1]-8], C[B[A[1]-8]+0], 0, 0] CONT
SEND
"""


ENDF_RECIPE_MF1_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, A[1], A[2], B[1], B[2]] HEAD
[MAT,MF,MT/ 0.0, 0.0, C[1], C[2], 0, 0] CONT
if B[A[1]-8] == B[1]:
    [MAT,MF,MT/ 0.0, 0.0, B[A[1]-8], C[B[A[1]-8]+0], 0, 0] CONT
endif
SEND
"""


ENDF_RECIPE_MF1_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, A[1], A[2], B[1], B[2]] HEAD
[MAT,MF,MT/ 0.0, 0.0, C[1], C[2], 0, 0] CONT
for i=B[A[1]-8] to B[1]:
    [MAT,MF,MT/ 0.0, 0.0, B[A[1]-8], C[B[A[1]-8]+0], 0, 0] CONT
endfor
SEND
"""
