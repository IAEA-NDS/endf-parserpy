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

# The values KIJ of INTG records in loops (array_type="numpy"). The number
# of values per record is a fixed function of NDIGIT, so that the values
# are the innermost dimension of a regular block if NDIGIT is known before
# the loop and does not change in it.
#
# MT1: KIJ[i,k] is a list with one array of shape (NM[i], n(NDIGIT)) per i
# (the loop over k and the values form the block).
# MT2: NDIGIT is first read in the loop (and only checked in the following
# iterations), so it is not known before the loop: KIJ is a list of
# one-dimensional arrays.
# MT3: an if-clause between the loop and the record: KIJ is a list of
# one-dimensional arrays.
# MT4: the branches of the if-clause exclude each other: KIJ is one array
# of shape (NM, n(NDIGIT)) if L == 1, otherwise a list of one-dimensional
# arrays.
# MT5: KIJ is read twice, so that the second loop checks the values of
# the first: KIJ is a list of one-dimensional arrays.

ENDF_RECIPE_MF9_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, NDIGIT, 0, N, 0] HEAD
for i=1 to N:
    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NM[i], 0] CONT
    for k=1 to NM[i]:
        [MAT,MF,MT/ II[i,k], JJ[i,k], KIJ[i,k]{NDIGIT} ]INTG
    endfor
endfor
SEND
"""

ENDF_RECIPE_MF9_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, NM, 0] HEAD
for k=1 to NM:
    [MAT,MF,MT/ 0.0, 0.0, NDIGIT, 0, 0, 0] CONT
    [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
endfor
SEND
"""

ENDF_RECIPE_MF9_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, NDIGIT, 0, NM, 0] HEAD
for k=1 to NM:
    if NDIGIT > 0:
        [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
    endif
endfor
SEND
"""

ENDF_RECIPE_MF9_MT4 = """
[MAT,MF,MT/ 0.0, 0.0, NDIGIT, L, NM, 0] HEAD
if L == 1:
    for k=1 to NM:
        [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
    endfor
else:
    for k=1 to NM:
        if NDIGIT > 0:
            [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
        endif
    endfor
endif
SEND
"""

ENDF_RECIPE_MF9_MT5 = """
[MAT,MF,MT/ 0.0, 0.0, NDIGIT, 0, NM, 0] HEAD
for k=1 to NM:
    [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
endfor
for k=1 to NM:
    [MAT,MF,MT/ II[k], JJ[k], KIJ[k]{NDIGIT} ]INTG
endfor
SEND
"""
