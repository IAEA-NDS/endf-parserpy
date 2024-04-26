############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/20
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF1_MT455 = """

[MAT, 1,455/ ZA, AWR, LDG, LNU, 0, 0]HEAD
if LDG==0 and LNU==2:
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NNF, 0/
        {lambda[k]}{k=1 to NNF} ]LIST
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NR, NP/ Eint / nubar_d ]TAB1
elif LDG==1 and LNU==2:
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
    for k=1 to NE:
    [MAT, 1,455/ 0.0, E[k], 0, 0, NNF*2, 0/
        {lambda[k,l], alpha[k,l]}{l=1 to NNF} ]LIST
    endfor
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NR, NP/ Eint / nubar_d]TAB1
elif LDG==0 and LNU==1:
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NNF, 0/ {lambda[k]}{k=1 to NNF} ]LIST
    [MAT, 1,455/ 0.0, 0.0, 0, 0, 1, 0/ nubar_d]LIST
elif LDG==1 and LNU==1:
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
    for k=1 to NE:
        [MAT, 1,455/ 0.0, E1 , 0, 0, NNF*2, 0/
            {lambda[k,l], alpha[k,l]}{l=1 to NNF} ]LIST
    endfor
    [MAT, 1,455/ 0.0, 0.0, 0, 0, NC, 0/ {nubar_d[k]}{k=1 to NC} ]LIST
endif
SEND
"""
