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

ENDF_RECIPE_MF15 = """

# FILE 15: Continuous Photon Energy Spectra
[MAT, 15, MT/ ZA, AWR, 0, 0, NC, 0] HEAD
for j=1 to NC:
    (subsection[j])
        # ATTENTION: This if must be inside subsection
        #            otherwise LF variable will not be
        #            in scope for the evaluation of the
        #            if statement.
        if LF == 1 [lookahead=1]:
            [MAT, 15, MT/ 0.0, 0.0, 0, LF, NR, NP/ Eint / p] TAB1 (rtfm_tab1)
            [MAT, 15, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ] TAB2
            for k=1 to NE:
                [MAT, 15, MT/ 0.0, E[k] , 0, 0, NR, NP / Egamma / g] TAB1 (rtfm1_tab[k])
            endfor
        endif
    (/subsection[j])
endfor
SEND
"""
