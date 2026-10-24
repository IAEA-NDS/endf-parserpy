############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# Abbreviations defined in a branch of an if-clause are not visible
# after it: X is redefined in the branch, and the record after the
# if-clause uses the abbreviation defined before it.

ENDF_RECIPE_MF5_MT1 = """
[MAT, 5, MT/ ZA, AWR, L1, L2, N1, N2]HEAD
X := L1
if L2 == 1:
    X := N1
    [MAT, 5, MT/ 0.0, 0.0, X, 0, 0, 0]CONT
else:
    X := N2
    [MAT, 5, MT/ 0.0, 0.0, X, 0, 0, 0]CONT
endif
[MAT, 5, MT/ 0.0, 0.0, X, 0, 0, 0]CONT
SEND
"""
