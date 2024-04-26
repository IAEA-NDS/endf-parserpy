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

ENDF_RECIPE_MF14 = """

# FILE 14: Photon Angular Distributions (Chap. 14, 203)
# Isotropic distributions (14.2.1, p. 205)
if LI == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, 0, NK, 0]HEAD

# Anisotropic distribution with Legendre Coefficients Representation (14.2.2, p. 205)
elif LI == 0 and LTT == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI]HEAD
    for k=1 to NI:
        [MAT, 14, MT/ EG[k] , ES[k] , 0, 0, 0, 0] CONT
    endfor
    for k=NI+1 to NI+(NK-NI):
        [MAT, 14, MT/ EG[k] , ES[k] , 0, 0, NR, NE[k]/ E ] TAB2 (E_interpol[k])
        for l=1 to NE[k]:
            [MAT, 14, MT/ 0.0, E[k,l] , 0, 0, NL[k,l] , 0/
                                {a[k,l,m]}{m=1 to NL[k,l]} ] LIST
        endfor
    endfor

# Anisotropic distribution with Tabulated Angular Distributions
elif LI == 0 and LTT == 2 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI] HEAD
    # TODO
    stop("Case LI=0, LTT=2 not implemented in ENDF recipe for MF14")
endif
SEND
"""
