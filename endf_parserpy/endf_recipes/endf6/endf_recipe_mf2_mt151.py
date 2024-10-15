############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/10/15
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF2_MT151 = """

[MAT, 2,151/ ZA, AWR, 0, 0, NIS, 0]HEAD

for i=1 to NIS:
(isotope[i])
    [MAT, 2,151/ ZAI, ABN, 0, LFW, NER, 0]CONT
    for j=1 to NER:
    (range[j])
        [MAT, 2,151/ EL, EH, LRU, LRF, NRO, NAPS]CONT

        # Special case without resonance parameters and
        # only scatterin radius given (Chap 2.1. p.63)
        if NIS==1 and ZAI==ZA and ABN==1 and LFW==0 and NER==1:
            if LRU==0 and LRF==0 and NRO==0 and NAPS==0:
                if NLS==0 [lookahead=1]:
                    [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                endif
            endif
        endif

        # Resolved resonance data
        if LRU==1:

            # Single level Breit-Wigner (SLBW) or Multi level Breit-Wigner (MLBW)
            if LRF==1 or LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, 0, 0, NLS, 0]CONT
                else:
                    [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                endif

                for m=1 to NLS:
                (spingroup[m])
                    [MAT, 2,151/ AWRI, QX, L, LRX, 6*NRS, NRS /
                    {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRS} ]LIST
                (/spingroup[m])
                endfor

            # R-matrix Reich-Moore multi level parameters
            elif LRF==3:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, LAD, 0, NLS, NLSC]CONT
                else:
                    [MAT, 2,151/ SPI, AP, LAD, 0, NLS, NLSC]CONT
                endif

                for m=1 to NLS:
                (spingroup[m])
                    [MAT, 2,151/AWRI,APL, L, 0, 6*NRS, NRS/
                    {ER[k] , AJ[k] , GN[k], GG[k] , GFA[k],  GFB[k]}{k=1 to NRS} ]LIST
                (/spingroup[m])
                endfor

            elif LRF==7:
                [MAT,2,151/ 0.0, 0.0, IFG, KRM, NJS, KRL ]CONT
                [MAT,2,151/0.0, 0.0, NPP, 0, 12*NPP, 2*NPP /
                    {MA[k] , MB[k], ZA[k] , ZB[k] , IA[k] , IB[k] ,
                    Q[k], PNT [k], SHF[k] , MT[k] , PA[k] , PB[k]}{k=1 to NPP} ]LIST
                for k=1 to NJS:
                (spingroup[k])
                    [MAT,2,151/ AJ, PJ, KBK, KPS, 6*NCH, NCH /
                    {PPI[l] , L[l] , SCH[l] , BND [l] , APE[l] , APT[l]}{l=1 to NCH} ]LIST

                    if NRS > 0 [lookahead=1]:
                        NX := (1+NCH + (5-NCH) % 6) * NRS / 6
                        num_zeros := (5-NCH) % 6
                        [MAT,2,151/ 0.0, 0.0, 0, NRS, 6*NX, NX /
                            { ER[n], {GAM[m,n]}{m=1 to NCH},
                              {0.0}{p=1 to num_zeros} }{n=1 to NRS} ]LIST

                    # no resonances in the spin group
                    elif NRS==0 and NX==1 [lookahead=1]:
                        [MAT,2,151/ 0.0, 0.0, 0, NRS, 6*NX, NX /
                            {0.0}{m=1 to 6}]LIST
                    endif

                    if KBK > 0:
                        for n=1 to KBK:
                            [MAT,2,151/ 0.0, 0.0, LCH, LBK, 0, 0 ]CONT
                            if LBK == 1:
                                [MAT,2,151/ 0.0, 0.0, LCH, LBK, 0, 0 ]CONT
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / RBR]TAB1 (real_part[n])
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / RBI]TAB1 (imag_part[n])
                            elif LBK == 2:
                                [MAT,2,151/ ED, EU, 0, 0, 5, 0/ R0, R1, R2, S0, S1 ]LIST
                            elif LBK == 3:
                                [MAT,2,151/ ED, EU, 0, 0, 3, 0/ R0, S0, GA ]LIST
                            endif
                        endfor
                    endif
                    if KPS > 0:
                        for n=1 to NCH:
                            [MAT,2,151/ 0.0, 0.0, 0, 0, LPS, 1/
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.0]LIST
                            if LPS == 1:
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / PSR ]TAB1 (real_part[n])
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / PSI ]TAB1 (imag_part[n])
                            endif
                        endfor
                    endif

                (/spingroup[k])
                endfor
            endif

        # Unresolved resonance data
        elif LRU==2:

            # Case A (see Chap 2.3, p. 76)
            if LFW==0 and LRF==1:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP]TAB1
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, LSSF, 0, NLS, 0] CONT
                else:
                    [MAT, 2,151/ SPI, AP, LSSF, 0, NLS, 0] CONT
                endif

                for p=1 to NLS:
                (l_group[p])
                    [MAT, 2,151/AWRI, 0.0, L, 0, 6*NJS, NJS/
                    {D[m], AJ[m], AMUN[m], GN0[m], GG[m], 0.0}{m=1 to NJS}] LIST
                (/l_group[p])
                endfor

            # Case B (see Chap 2.3, p. 77)
            elif LFW==1 and LRF==1:
                [MAT, 2,151/ SPI, AP, LSSF, 0, NE, NLS /
                                {ES[p]}{p=1 to NE} ] LIST

                for p=1 to NLS:
                (j_group[p])
                    [MAT, 2,151/ AWRI, 0.0, L, 0, NJS, 0]CONT
                    for n=1 to NJS:
                    (subsec[n])
                        [MAT, 2,151/ 0.0, 0.0, L, MUF, NE+6, 0/
                            D, AJ, AMUN, GN0, GG, 0.0,
                            {GF[m]}{m=1 to NE} ] LIST
                    (/subsec[n])
                    endfor
                (/j_group[p])
                endfor

            # Case C (see Chap 2.3, p. 77)
            elif (LFW==0 or LFW==1) and LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP ] TAB1
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, LSSF, 0, NLS, 0]CONT
                else:
                    [MAT, 2,151/ SPI, AP, LSSF, 0, NLS, 0]CONT
                endif

                for p=1 to NLS:
                (l_group[p])
                    [MAT, 2,151/ AWRI, 0.0, L, 0, NJS, 0]CONT
                    for n=1 to NJS:
                    (subsec[n])
                        [MAT, 2,151/ AJ, 0.0, INT, 0, 6*NE+6, NE/
                            0.0, 0.0, AMUX, AMUN, AMUG, AMUF,
                            {ES[m], D[m] , GX[m] , GN0[m] , GG[m] , GF[m]}{m=1 to NE} ]LIST
                    (/subsec[n])
                    endfor
                (/l_group[p])
                endfor
            endif
        endif
    (/range[j])
    endfor
(/isotope[i])
endfor
SEND
"""
