############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/10
# Last modified:   2024/04/27
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF8_MT457 = """

# radiactive nucleus
if NST==0 [lookahead=1]:
    [MAT, 8,457/ ZA, AWR, LIS, LISO, NST, NSP]HEAD
    [MAT, 8,457/ Thalf , dThalf , 0, 0, 2*NC, 0 /
        {Ebar_x[k] ,dEbar_x[k]}{k=1 to NC} ]LIST
    [MAT, 8,457/ SPI, PAR, 0, 0, 6*NDK, NDK/
        {RTYP[k] , RFS[k] , Q[k] , dQ[k] , BR[k] , dBR[k]}{k=1 to NDK} ]LIST
    for k=1 to NSP:
    (spectrum[k])
        [MAT, 8,457/ 0.0, STYP, LCON, LCOV, 6, NER/
            FD, dFD, ERAV , dERAV , FC, dFC] LIST

        if LCON != 1:
            (discrete)
              for i=1 to NER:
                (energysec[i])
                  if NT == 6 [lookahead=1]:
                      [MAT, 8,457/ ER , dER, 0, 0, NT, 0/
                      RTYP , TYPE , RI , dRI,   RIS , dRIS ]LIST
                  elif NT == 8 [lookahead=1]:
                      [MAT, 8,457/ ER , dER, 0, 0, NT, 0/
                      RTYP , TYPE , RI , dRI,   RIS , dRIS,
                      RICC, dRICC ]LIST
                  elif NT == 12 [lookahead=1]:
                      [MAT, 8,457/ ER , dER, 0, 0, NT, 0/
                      RTYP , TYPE , RI , dRI,   RIS , dRIS ,
                      RICC ,dRICC , RICK,dRICK, RICL ,dRICL ] LIST
                  endif
                (/energysec[i])
              endfor
            (/discrete)
        endif
        if LCON != 0:
            (continuous)
                [MAT, 8,457/ RTYP, 0.0, 0, 0, NR, NP/ Eint / RP ] TAB1
            (/continuous)
        endif
        if LCOV != 0 and LCOV != 2 and LCON != 0:
            (continuous)
                [MAT, 8,457/ 0.0, 0.0, 0, 2, 2*NPP, NPP/ {E[m] ,F[m]}{m=1 to NPP} ] LIST
            (/continuous)
        endif
        if LCOV != 0 and LCOV != 1:
            (discrete)
              (cov)
                [MAT, 8,457/ 0.0, 0.0, LS, 5, NE, NERP/
                    {E[m]}{m=1 to NERP}, {{F[m,n]}{n=m to NERP-2}}{m=1 to NERP-2} ] LIST
              (/cov)
            (/discrete)
        endif
    (/spectrum[k])
    endfor

# stable nucleus
elif NST==1 [lookahead=1]:
    [MAT, 8,457/ ZA, AWR, LIS, LISO, NST, 0]HEAD
    [MAT, 8,457/ 0.0, 0.0, 0, 0, 6, 0/
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0] LIST
    [MAT, 8,457/ SPI, PAR, 0, 0, 6, 0 /
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0] LIST
endif
SEND
"""
