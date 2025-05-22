############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/09
# Last modified:   2025/05/22
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF5 = """

[MAT, 5, MT/ ZA, AWR, 0, 0, NK, 0]HEAD
for k=1 to NK:
    (contribution[k])
        # Arbitrary Tabulated Function (LF=1)
        if LF==1 [lookahead=1]:
            [MAT, 5, MT/ 0.0, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE / E ]TAB2 (E_interp)
            for l=1 to NE:
                [MAT, 5, MT/ 0.0, E[l], 0, 0, NR, NF/ Eout / g ]TAB1 (spectrum[l])
            endfor

        # General Evaporation Spectrum (LF=5)
        elif LF==5 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE/ E / theta] TAB1 (theta_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NF/ x / g ]TAB1 (g_table)

        # Simple Maxwellian Fission Spectrum (LF=7)
        elif LF==7 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE/ E / theta ]TAB1 (theta_table)

        # Evaporation Spectrum (LF=9)
        elif LF==9 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ 0.0, 0.0, 0, 0, NR, NE/ E / theta]TAB1 (theta_table)

        # Energy-Dependent Watt Spectrum (LF=11)
        elif LF==11 [lookahead=1]:
            [MAT, 5, MT/ U, 0.0, 0, LF, NR, NP / E / p ]TAB1
            # TODO
            stop("LF=11 case not implemented in ENDF recipe MF5")

        # Energy-Dependent Fission Neutron Spectrum (LF=12)
        elif LF==12 [lookahead=1]:
            [MAT, 5, MT/ 0.0, 0.0, 0, LF, NR, NP/ E / p ]TAB1 (p_table)
            [MAT, 5, MT/ EFL, EFH, 0, 0, NR, NE/ E / TM ]TAB1 (Tm_table)
        endif
    (/contribution[k])
endfor
SEND
"""
