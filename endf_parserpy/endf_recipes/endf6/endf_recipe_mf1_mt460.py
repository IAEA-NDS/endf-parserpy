############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/20
# Last modified:   2025/03/15
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF1_MT460 = """

if LO==1 [lookahead=1]:
    [MAT,1,460/ ZA, AWR, LO, 0, NG, 0]HEAD
    for i=1 to NG:
        [MAT,1,460/ E[i], 0.0, i, 0, NR, NP / tint / T ]TAB1 (table[i])
    endfor

elif LO==2 [lookahead=1]:
    [MAT,1,460/ ZA, AWR, LO, 0, 0, 0]HEAD
    [MAT,1,460/ 0.0, 0.0, 0, 0, NNF, 0 /
    {lambda[i]}{i=1 to NNF} ]LIST
endif

SEND
"""
