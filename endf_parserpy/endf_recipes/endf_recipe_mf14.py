ENDF_RECIPE_MF14 = """

# FILE 14: Photon Angular Distributions (Chap. 14, 203)
# Isotropic distributions (14.2.1, p. 205)
if LI == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, 0, NK, 0]HEAD
endif
# Anisotropic distribution with Legendre Coefficients Representation (14.2.2, p. 205)
if LI == 0 and LTT == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI]HEAD
    # TODO: implement
endif
# Anisotropic distribution with Tabulated Angular Distributions
if LI == 0 and LTT == 2 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI] HEAD
    # TODO: implement
endif
SEND
"""
