############################################################
#
# Maintainer:      José Ignacio Marquez Damian
# Email:           marquezj@ess.eu
# Creation date:   2022/09/13
# Last modified:   2024/05/29
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
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
elif LTHR==3:
    [MAT, 7, 2/ T0, 0.0, LT, 0, NR, NP/ Eint / S ] TAB1 (S_T0_table)
    for i=1 to LT:
        [MAT, 7, 2/ T[i], 0.0, LI, 0, NP, 0/
            {S[q,i]}{q=1 to NP} ] LIST
    endfor
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

if NI>=7 and B[7]==0:
    [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff1 ] TAB1 (teff1_table)
endif
if NI>=13 and B[13]==0.0:
    [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff2 ] TAB1 (teff2_table)
endif
if NI>=19 and B[19]==0.0:
    [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff3 ] TAB1 (teff3_table)
endif
SEND
"""

ENDF_RECIPE_MF7_MT451 = """

# Generalized Information File
[MAT, 7, 451 / ZA, AWR, NA, 0, 0, 0]HEAD
for i=1 to NA:
    [MAT, 7, 451 / 0, 0, NAS, 0, 6*NI[i], NI[i]/
          {ZAI[i,j], LISI[i,j], AFI[i,j], AWRI[i,j], SFI[i,j], 0}{j=1 to NI[i]} ] LIST
endfor
SEND
"""
