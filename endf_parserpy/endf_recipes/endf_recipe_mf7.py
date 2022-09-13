############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/13
# Last modified:   2022/09/13
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF7_MT2 = """

# Coherent Elastic Scattering
[MAT, 7, 2/ ZA, AWR, LTHR, 0, 0, 0]HEAD
if LTHR==1:
    [MAT, 7, 2/ T0, 0.0, LT, 0, NR, NP/ Eint / S ] TAB1 (S_T0_table)
    for i=1 to LT:
        [MAT, 7, 2/ T[i], 0.0, LI, 0, NP, 0/
            {S[q,i]}{q=1 to NP} ] LIST
    endfor
# Incoherent Elastic Scattering
elif LTHR==2:
    [MAT, 7, 2/ SB, 0.0, 0, 0, NR, NP/ Tint / Wp ]TAB1
endif
SEND
"""


ENDF_RECIPE_MF7_MT4 = """

# Incoherent Inelastic Scattering
[MAT, 7, 4 / ZA, AWR, 0, LAT, LASYM, 0]HEAD
[MAT, 7, 4 / 0.0, 0.0, LLN, 0, NI, NS/ {B[n]}{n=1 to NI} ] LIST
[MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NB/ beta_int] TAB2 (beta_interp)
for i=1 to NB:
    [MAT, 7, 4 / T0, beta[i], LT[i], 0, NR, NP / alpha / S ] TAB1 (S_table[i])
    for j=1 to LT[i]:
        [MAT, 7, 4 / T[j] , beta[i], LI[j], 0, NP, 0 / {S[q,i,j]}{q=1 to NP} ] LIST
    endfor
endfor
[MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff0 ] TAB1 (teff0_table)

# the for loops are hacks, because directly writing B[7] etc. does not work at the moment :-( 
if NI >= 7:
    for q=7 to 7:
        if B[q] == 0.0: 
            [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff1 ] TAB1 (teff1_table)
        endif
    endfor
endif
if NI >= 13:
    for q=13 to 13:
        if B[q] == 0.0:
            [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff2 ] TAB1 (teff2_table)
        endif
    endfor
endif
if NI >= 19:
    for q=19 to 19:
        if B[q] == 0.0:
            [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff3 ] TAB1 (teff3_table)
        endif
    endfor
endif
SEND
"""
