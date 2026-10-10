############################################################
#
# Maintainer:      José Ignacio Marquez Damian
# Email:           marquezj@ess.eu
# Creation date:   2022/09/13
# Last modified:   2026/10/19
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
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
# B(1)=0.0 indicates that there is no principal scattering atom and the
# scattering law is completely described by the analytic functions of
# the non-principal atoms (ENDF-102, Section 7.5.1). In this case the
# tabulated S(alpha,beta) and the effective temperature table of the
# principal atom (Teff0) are omitted; the effective temperatures of the
# non-principal atoms below are given whenever B(6i+1)=0 selects the
# short-collision-time approximation.
if B[1] != 0.0:
    [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NB/ beta_int] TAB2 (beta_interp)
    for i=1 to NB:
        [MAT, 7, 4 / T0, beta[i], LT[i], 0, NR, NP / alpha / S ] TAB1 (S_table[i])
        for j=1 to LT[i]:
            [MAT, 7, 4 / T[j] , beta[i], LI[j], 0, NP, 0 / {S[q,i,j]}{q=1 to NP} ] LIST
        endfor
    endfor
    [MAT, 7, 4 / 0.0, 0.0, 0, 0, NR, NT/ Tint / Teff0 ] TAB1 (teff0_table)
endif

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
    # ENDF-102 (Section 7.6.1) writes NAS without a subscript, but one
    # NAS field is given per element; keep the scalar name in the
    # single-element case so that existing downstream code is unaffected.
    if NA == 1:
        [MAT, 7, 451 / 0, 0, NAS, 0, 6*NI[i], NI[i]/
              {ZAI[i,j], LISI[i,j], AFI[i,j], AWRI[i,j], SFI[i,j], 0}{j=1 to NI[i]} ] LIST
    else:
        [MAT, 7, 451 / 0, 0, NAS[i], 0, 6*NI[i], NI[i]/
              {ZAI[i,j], LISI[i,j], AFI[i,j], AWRI[i,j], SFI[i,j], 0}{j=1 to NI[i]} ] LIST
    endif
endfor
SEND
"""
