############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/12
# Last modified:   2026/10/13
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################


# These recipes use arithmetic in the various places of a recipe where
# expressions are evaluated. They can be used to check that the Python
# and the C++ parser agree on the arithmetic of the recipe language:
# - integers and decimal literals are exact; a division of exact numbers
#   gives an exact fraction, e.g. 13/6, and decimal literals are exact,
#   e.g. 0.1 is 1/10,
# - only where an integer is needed (an integer field, a loop bound, an
#   index) must the value be an integer,
# - values of float fields are floats; arithmetic with a float gives a
#   float,
# - the result of a modulo operation has the sign of the divisor,
#   e.g. (5-7)%6 == 4.


# solving a field for an unknown variable: 6*NX
ENDF_RECIPE_MF2_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 6*NX, 0] CONT
SEND
"""


# field value computed from a known variable
ENDF_RECIPE_MF2_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, N/6, 0, 0] CONT
SEND
"""


# upper bound of a for-loop
ENDF_RECIPE_MF2_MT3 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
for k=1 to N/6:
    [MAT,MF,MT/ X[k], 0.0, 0, 0, 0, 0] CONT
endfor
SEND
"""


# abbreviation
ENDF_RECIPE_MF2_MT4 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
M := N/6
[MAT,MF,MT/ 0.0, 0.0, M, 0, 0, 0] CONT
SEND
"""


# modulo with a left operand that may be negative,
# as in the padding of the records of the R-Matrix Limited format
ENDF_RECIPE_MF2_MT5 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
[MAT,MF,MT/ 0.0, 0.0, (5-N)%6, 0, 0, 0] CONT
SEND
"""


# division with a numerator that may be negative
ENDF_RECIPE_MF2_MT6 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
[MAT,MF,MT/ 0.0, 0.0, (N-12)/6, 0, 0, 0] CONT
SEND
"""


# division and modulo in an if-condition
ENDF_RECIPE_MF2_MT7 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
if N/6 == 2 or (5-N)%4 == 3:
    [MAT,MF,MT/ 0.0, 0.0, 1, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, 2, 0, 0, 0] CONT
endif
SEND
"""


# addition, subtraction and multiplication in an if-condition
ENDF_RECIPE_MF2_MT8 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
if 2*N-1 == N+6:
    [MAT,MF,MT/ 0.0, 0.0, 1, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, 2, 0, 0, 0] CONT
endif
SEND
"""


# solving a field in a lookahead: the record is read to decide whether
# the branch applies, so a field value inconsistent with the branch must
# not cause an error there (as in the MF33 recipe, where the LB=0-4
# branch with 2*NP is tried on records of LB=5 with odd NT).
# Within the selected branch, the solution must be an integer.
ENDF_RECIPE_MF2_MT9 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
if L==1 [lookahead=1]:
    [MAT,MF,MT/ 0.0, 0.0, L, 0, 2*NP, NP] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, L, 0, NT, 0] CONT
endif
SEND
"""


# solving fields with the unknown inside a division
ENDF_RECIPE_MF2_MT10 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N/6, 0, 0, 0] CONT
SEND
"""


ENDF_RECIPE_MF2_MT11 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, 2*N/3, 0, 0, 0] CONT
SEND
"""


ENDF_RECIPE_MF2_MT12 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, (2*N+1)/3, 0, 0, 0] CONT
SEND
"""


# a fraction as intermediate result: N=6 gives 2*(6/4) == 3
ENDF_RECIPE_MF2_MT13 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, 2*(N/4), 0, 0, 0] CONT
SEND
"""


# solving with the unknown inside a division in a lookahead
ENDF_RECIPE_MF2_MT14 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
if L==1 [lookahead=1]:
    [MAT,MF,MT/ 0.0, 0.0, L, 0, 2*NP/3, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, L, 0, NT, 0] CONT
endif
SEND
"""


# array elements as unknown variables
ENDF_RECIPE_MF2_MT15 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
for k=1 to 2:
    [MAT,MF,MT/ 0.0, 0.0, 2*M[k]/3, 0, 0, 0] CONT
endfor
SEND
"""


# decimal literals are exact: (N+1)/10.0 == 2 for N=19
ENDF_RECIPE_MF2_MT16 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, (N+1)/10.0, 2*(K/4.0), 0, 0] CONT
SEND
"""


# float field computed from an integer variable
ENDF_RECIPE_MF2_MT17 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 0.0, 0.0, N, 0, 0, 0] CONT
[MAT,MF,MT/ N/4, 0.0, 0, 0, 0, 0] CONT
SEND
"""


# arithmetic with the value of a float field
ENDF_RECIPE_MF2_MT18 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ X, X/2, 0, 0, 0, 0] CONT
SEND
"""


# solving a float field for an unknown float variable
ENDF_RECIPE_MF2_MT19 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ 2*X, 0.0, 0, 0, 0, 0] CONT
SEND
"""


# integer field computed from the value of a float field
ENDF_RECIPE_MF2_MT20 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ X, 0.0, 0, 0, 0, 0] CONT
[MAT,MF,MT/ 0.0, 0.0, 2*(X/4), 0, 0, 0] CONT
SEND
"""


# comparison of the value of a float field with a fraction
ENDF_RECIPE_MF2_MT21 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD
[MAT,MF,MT/ X, 0.0, N, 0, 0, 0] CONT
if X > N/4:
    [MAT,MF,MT/ 0.0, 0.0, 1, 0, 0, 0] CONT
else:
    [MAT,MF,MT/ 0.0, 0.0, 2, 0, 0, 0] CONT
endif
SEND
"""
