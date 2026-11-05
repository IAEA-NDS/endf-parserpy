############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# Bodies of LIST records read in the bulk form of EndfParserCpp (see
# ListBulkForm in compiler/endf2cpp_aux.py).
#
# MT1: a regular layout: scalars before a loop, a list (X), a value that is
# checked (0.0) and a block (Y) in the loop; delivered by strided copies.
# MT2: a triangular matrix (the bounds of the inner loop depend on the
# outer one): delivered by one strided copy per row.
# MT3: a variable read before the LIST (N), checked in each iteration:
# delivered by the code of the per-field form.
# MT4: a list for each iteration of the loop around the LIST (W) and a
# value checked after the loop of the body; delivered by strided copies.
# MT5: a list in a loop whose number of iterations may be zero (also with
# NPL=0); delivered by strided copies.
#
# Rows (one strided copy per iteration of the row loops):
# MT6: a value per row (X) before the row of a triangular matrix.
# MT7: three nested loops, the two outer ones row loops.
# MT8: a value checked (0.0) after each row.
# MT9: lists in the innermost of three loops (a list per iteration of the
# two outer loops, the bounds of the middle one depend on the outer one).
# MT10: rows of the lower triangle (l=1 to k) between two scalars.
# MT11: bounds that are expressions of the variable of the row loop.

ENDF_RECIPE_MF10_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, N, M, NPL, 0/
    A, B, {X[k], 0.0, {Y[k,m]}{m=1 to M}}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {{F[k,l]}{l=k to N}}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {N, Z[k]}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT4 = """
[MAT,MF,MT/ 0.0, 0.0, NI, NK, 0, 0] HEAD
for i=1 to NI:
    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL[i], 0/ {W[i,k]}{k=1 to NK}, 0.0 ] LIST
endfor
SEND
"""

ENDF_RECIPE_MF10_MT5 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {U[k]}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT6 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {X[k], {F[k,l]}{l=k to N}}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT7 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {{{G[i,j,l]}{l=j to N}}{j=i to N}}{i=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT8 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {{F[k,l]}{l=k to N}, 0.0}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT9 = """
[MAT,MF,MT/ 0.0, 0.0, N, M, NPL, 0/ {{{Y[k,l,m]}{m=1 to M}}{l=k to N}}{k=1 to N} ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT10 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ A, {{F[k,l]}{l=1 to k}}{k=1 to N}, B ] LIST
SEND
"""

ENDF_RECIPE_MF10_MT11 = """
[MAT,MF,MT/ 0.0, 0.0, N, 0, NPL, 0/ {{F[k,l]}{l=2*k to N+k}}{k=1 to N} ] LIST
SEND
"""
