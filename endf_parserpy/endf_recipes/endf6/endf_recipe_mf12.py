############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF12 = """

# Photon Production Multiplicities (12.2.1, p. 194)
if LO == 1 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, 0, NK, 0]HEAD
    if NK > 1:
        [MAT, 12, MT/ 0.0, 0.0, 0, 0, NR, NP/ Eint / Y] TAB1
    endif
    for k=1 to NK:
        [MAT, 12, MT/ Eg[k] , ES[k], LP[k], LF[k], NR, NP/ Eint / y ] TAB1 (table[k])
    endfor

# Transition Probability Arrays (12.2.2, p. 196)
elif LO == 2 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, LG, NS, 0]HEAD
    if LG == 1:
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, 2*NT, NT/
                      {ES[i], TP[i]}{i=1 to NT} ]LIST
    elif LG == 2:
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, (LG+1)*NT, NT/
                      {ES[i], TP[i], GP[i]}{i=1 to NT} ]LIST
    endif
endif
SEND
"""
