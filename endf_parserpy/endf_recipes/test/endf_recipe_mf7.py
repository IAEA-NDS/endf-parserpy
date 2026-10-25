############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# Elements of array variables in loops, which the C++ writer retrieves
# with an accessor declared before the loop (CppArrayAccessor in
# compiler/cpp_templates/index_shifter.hpp) if the variable occurs only
# once in the loop. The recipes MT2 and MT4 are the same as MT1 and MT3,
# except for an additional record in an if-clause that is never executed
# (NI is not negative), which contains the variables again, so that no
# accessor is used. The output and the errors of writing must be the same.
# MT5 has accessors for the elements of LIST records.

# A[i] and K[i]: one index, starting at I0; T[i,j]: accessed with the
# first index in the inner loop
ENDF_RECIPE_MF7_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, NI, NJ, I0, J0] HEAD
for i=I0 to I0+NI-1:
    [MAT,MF,MT/ A[i], 0.0, K[i], 0, 0, 0] CONT
endfor
for j=J0 to J0+NJ-1:
    for i=I0 to I0+NI-1:
        [MAT,MF,MT/ T[i,j], 0.0, 0, 0, 0, 0] CONT
    endfor
endfor
SEND
"""

ENDF_RECIPE_MF7_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, NI, NJ, I0, J0] HEAD
for i=I0 to I0+NI-1:
    [MAT,MF,MT/ A[i], 0.0, K[i], 0, 0, 0] CONT
    if NI < 0:
        [MAT,MF,MT/ A[i], 0.0, K[i], 0, 0, 0] CONT
    endif
endfor
for j=J0 to J0+NJ-1:
    for i=I0 to I0+NI-1:
        [MAT,MF,MT/ T[i,j], 0.0, 0, 0, 0, 0] CONT
        if NI < 0:
            [MAT,MF,MT/ T[i,j], 0.0, 0, 0, 0, 0] CONT
        endif
    endfor
endfor
SEND
"""

# C[i,j], L[i,j] and B[i,j,k] in nested loops of varying lengths;
# NJ[i] and NW[i,j] occur twice in the loops (no accessor)
ENDF_RECIPE_MF7_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, NI, 0, 0, 0] HEAD
for i=1 to NI:
    [MAT,MF,MT/ 0.0, 0.0, NJ[i], 0, 0, 0] CONT
    for j=1 to NJ[i]:
        [MAT,MF,MT/ C[i,j], 0.0, L[i,j], NW[i,j], 0, 0] CONT
        for k=1 to NW[i,j]:
            [MAT,MF,MT/ B[i,j,k], 0.0, 0, 0, 0, 0] CONT
        endfor
    endfor
endfor
SEND
"""

ENDF_RECIPE_MF7_MT4 = """
[MAT,MF,MT/ 0.0, 0.0, NI, 0, 0, 0] HEAD
for i=1 to NI:
    [MAT,MF,MT/ 0.0, 0.0, NJ[i], 0, 0, 0] CONT
    for j=1 to NJ[i]:
        [MAT,MF,MT/ C[i,j], 0.0, L[i,j], NW[i,j], 0, 0] CONT
        if NI < 0:
            [MAT,MF,MT/ C[i,j], 0.0, L[i,j], NW[i,j], 0, 0] CONT
        endif
        for k=1 to NW[i,j]:
            [MAT,MF,MT/ B[i,j,k], 0.0, 0, 0, 0, 0] CONT
            if NI < 0:
                [MAT,MF,MT/ B[i,j,k], 0.0, 0, 0, 0, 0] CONT
            endif
        endfor
    endfor
endfor
SEND
"""

# the elements of LIST records: Ep[j,k] and b[j,k,m] as in MF6/LAW=1
ENDF_RECIPE_MF7_MT5 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, NE] HEAD
for j=1 to NE:
    [MAT,MF,MT/ 0.0, E[j], 0, NA[j], NEP[j]*(NA[j]+2), NEP[j]/
        {Ep[j,k], {b[j,k,m]}{m=0 to NA[j]}}{k=1 to NEP[j]} ] LIST
endfor
SEND
"""
