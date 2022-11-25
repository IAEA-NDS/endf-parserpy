############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF6 = """

[MAT, 6, MT/ ZA, AWR, JP, LCT, NK, 0]HEAD
for i=1 to NK:
    (subsection[i])
        [MAT, 6, MT/ ZAP, AWP, LIP, LAW, NR, NP/ Eint / yi]TAB1 (yields)
        if LAW == 1:
            [MAT, 6, MT/ 0.0, 0.0, LANG, LEP, NR, NE/ Eint ]TAB2
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j] , ND[j], NA[j], NW[j], NEP[j]/
                             {Ep[j,k], {b[m,j,k]}{m=0 to NA[j]}}{k=1 to NEP[j]} ]LIST
            endfor

        # Discrete Two-Body Scattering
        elif LAW == 2:
            [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j], LANG, 0, NLW[j], NL[j] / {A[j,l]}{l=1 to NLW[j]} ]LIST
            endfor

        # Charged-Particle Elastic Scattering (LAW=5)
        elif LAW == 5:
            [MAT, 6, MT/ SPI, 0.0, LIDP, 0, NR, NE / Eint ]TAB2
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j] , LTP[j], 0, NW[j], NL[j]/
                             {A[j,k]}{k=1 to NW[j]} ]LIST
            endfor

        # N-body Phase-Space distribution (LAW=6) (manual 6.2.7, p. 136)
        elif LAW == 6:
            [MAT, 6, MT/ APSX, 0.0, 0, 0, 0, NPSX]CONT

        # Laboratory Angle-Energy Law (LAW=7) (manual 6.2.9, p. 146)
        elif LAW == 7:
            [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE / E]TAB2 (E_interpol)
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j], 0, 0, NRM, NMU[j] / mu ]TAB2 (mu_interpol[j])
                for k=1 to NMU[j]:
                    [MAT, 6, MT/ 0.0, mu[j,k] , 0, 0, NRP, NEP / Ep / f ]TAB1 (table[j,k])
                endfor
            endfor
        endif
    (/subsection[i])
endfor
SEND
"""
