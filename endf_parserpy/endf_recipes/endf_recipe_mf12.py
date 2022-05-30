ENDF_RECIPE_MF12 = """

# Photon Production Multiplicities (12.2.1, p. 194)
if LO == 1 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, 0, NK, 0]HEAD
    if NK > 1:
        [MAT, 12, MT/ 0.0, 0.0, 0, 0, NR, NP/ Eint / Y] TAB1
    endif
    for k=1 to NK:
        [MAT, 12, MT/ Eg[k] , ES[k], LP, LF[k], NR, NP/ Eint / y ] TAB1 (table[k])
    endfor
endif
# Transition Probability Arrays (12.2.2, p. 196)
if LO == 2 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, LG, NS, 0]HEAD
    if LG == 1:
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, 2*NT, NT/
                      {ES[i], TP[i]}{i=1 to NT} ]LIST
    endif
    if LG == 2:
        # TODO: (LG+1)*NT instead of 3*NT does not work at the moment
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, 3*NT, NT/
                      {ES[i], TP[i], GP[i]}{i=1 to NT} ]LIST
    endif
endif
SEND
"""
