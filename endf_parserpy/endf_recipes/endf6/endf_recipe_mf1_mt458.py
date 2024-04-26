############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/20
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF1_MT458 = """

if LFC==0 and NPLY==0 [lookahead=2]:
    [MAT, 1,458/ ZA, AWR, 0, LFC, 0, 0]HEAD
    [MAT, 1,458/ 0.0, 0.0, 0, NPLY, 18, 9/
        EFR, dEFR, ENP, dENP, END, dEND,
        EGP, dEGP, EGD, dEGD, EB,  dEB,
        ENU, dENU, ER,  dER,  ET,  dET ]LIST
elif LFC==0 and NPLY>0 [lookahead=2]:
    [MAT, 1,458/ ZA, AWR, 0, LFC, 0, 0]HEAD
    [MAT, 1,458/ 0.0, 0.0, 0, NPLY, 18*(NPLY+1), 9*(NPLY+1) /
       {c_EFR[k], dc_EFR[k], c_ENP[k], dc_ENP[k], c_END[k], dc_END[k],
        c_EGP[k], dc_EGP[k], c_EGD[k], dc_EGD[k], c_EB[k], dc_EB[k],
        c_ENU[k], dc_ENU[k], c_ER[k],  dc_ER[k],  c_ET[k], dc_ET[k]} {k=0 to NPLY} ]LIST
elif LFC==1 and NPLY==0 [lookahead=2]:
    [MAT, 1,458/ ZA, AWR, 0, LFC, 0, NFC]HEAD
    [MAT, 1,458/ 0.0, 0.0, 0, NPLY, 18, 9/
        EFR, dEFR, ENP, dENP, END, dEND,
        EGP, dEGP, EGD, dEGD, EB,  dEB,
        ENU, dENU, ER,  dER,  ET,  dET ]LIST
    for k=1 to NFC:
        [MAT, 1,458/ 0.0, 0.0, LDRV[k], IFC[k], NR, NP/ Eint / EIFC ]TAB1 (fiscomp[k])
    endfor
endif
SEND
"""
