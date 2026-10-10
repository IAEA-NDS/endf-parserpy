############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/12/14
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF26 = """

[MAT,26, MT/ ZA, AWR, 0, 0, NK, 0]HEAD

for i=1 to NK:
    (subsection[i])
        [MAT,26, MT/ZAP, AWI, 0, LAW, NR, NP/ Eint / yi] TAB1 (yields)
        if LAW == 1:
            [MAT, 26, MT/ 0.0, 0.0, LANG, LEP, NR, NE/ Eint ]TAB2
            if LANG != 1:
                stop("Only LANG=1 is permitted in MF26/LAW1.")
            endif
            for j=1 to NE:
                NW := NEP[j] * (NA[j]+2)
                [MAT, 26, MT/ 0.0, E[j] , ND[j], NA[j], NW, NEP[j]/
                    {Ep[j,k], {b[j,k,m]}{m=0 to NA[j]}}{k=1 to NEP[j]} ]LIST
                if NA[j] != 0:
                    stop("Only NA[j]=0 is permitted in MF26/LAW1.")
                endif
            endfor
        elif LAW == 2:
            [MAT, 26, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
            for j=1 to NE:
                [MAT, 26, MT/ 0.0, E[j], LANG, 0, NLW[j], NL[j] / {A[j,l]}{l=1 to NLW[j]} ]LIST
            endfor
            if LANG < 11 or LANG > 15:
                stop("Only 11 <= LANG <= 15 is permitted in MF26/LAW2")
            endif
        elif LAW == 8:
            [MAT,26, MT/ 0.0, 0.0, 0, 0, NR, NP/ Eint / ET] TAB1
        else:
            stop("Invalid LAW present in MF26")
        endif
    (/subsection[i])
endfor
SEND
"""
