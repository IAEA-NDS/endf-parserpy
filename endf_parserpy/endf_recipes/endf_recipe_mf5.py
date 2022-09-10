############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/09
# Last modified:   2022/09/09
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF5 = """

[MAT, 5, MT/ ZA, AWR, 0, 0, NK, 0]HEAD
for k=1 to NK:
    (contribution[k])
        # Arbitrary Tabulated Function (LF=1)
        if LF==1 [lookahead=1]:
            [MAT, 5, MT/ 0.0?, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE / E ]TAB2 (E_interp)
            for l=1 to NE:
                [MAT, 5, MT/ 0.0, E[l], 0, 0?, NR, NF/ Eout / g ]TAB1 (spectrum[l])
            endfor
        endif
        # General Evaporation Spectrum (LF=5)
        if LF==5 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table) 
            [MAT, 5, MT/ 0.0, 0.0, 0?, 0?, NR, NE/ E / theta] TAB1 (theta_table)
            [MAT, 5, MT/ 0.0, 0.0, 0?, 0?, NR, NF/ x / g ]TAB1 (g_table)
        endif
        # Simple Maxwellian Fission Spectrum (LF=7)
        if LF==7 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE/ E / theta ]TAB1 (theta_table)
        endif
        # Evaporation Spectrum (LF=9)
        if LF==9 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE/ E / theta]TAB1 (theta_table)
        endif
        # Energy-Dependent Watt Spectrum (LF=11)
        if LF==11 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP / E / p ]TAB1
            # TODO
        endif
        # Energy-Dependent Fission Neutron Spectrum (LF=12)
        if LF==12 [lookahead=1]:
            [MAT, 5, MT/ 0.0, 0.0, 0, LF, NR, NP/ E / p ]TAB1
            # TODO
        endif
    (/contribution[k])
endfor
SEND
"""
