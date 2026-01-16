############################################################
#
# Author(s):       Georg Schnabel, Daniel L. Aldama
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2026/01/08
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

        # Special case for a single isotope without
        # resonance parameters and scattering radius only given
        # or a multi-isotope material with some, but not all,
        # isotopes specified by a scattering radius only
        # ENDF-6 Manual (Chap 2.1. pp. 61-65)
        if LRU==0 and LRF==0 and NRO==0 and NAPS==0 and LFW==0 and NER==1:
            [MAT, 2,151/ SPI, AP, 0, 0, 0, 0]CONT

        # Resolved resonance data
        elif LRU==1:

            # Single level Breit-Wigner (SLBW) or Multi level Breit-Wigner (MLBW)
            if LRF==1 or LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1 (AP_table)
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, 0, 0, NLS, 0]CONT
                else:
                    [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                endif

                for m=1 to NLS:
                (l_group[m])
                    [MAT, 2,151/ AWRI, QX, L, LRX, 6*NRS, NRS /
                    {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRS} ]LIST
                (/l_group[m])
                endfor

            # R-matrix Reich-Moore multi level parameters
            elif LRF==3:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1 (AP_table)
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, LAD, 0, NLS, NLSC]CONT
                else:
                    [MAT, 2,151/ SPI, AP, LAD, 0, NLS, NLSC]CONT
                endif

                for m=1 to NLS:
                (l_group[m])
                    [MAT, 2,151/AWRI,APL, L, 0, 6*NRS, NRS/
                    {ER[k] , AJ[k] , GN[k], GG[k] , GFA[k],  GFB[k]}{k=1 to NRS} ]LIST
                (/l_group[m])
                endfor

            # Adler-Adler formalism (level-level and channel-channel interference)
            elif LRF==4:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1 (AP_table)
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, 0, 0, NLS, 0]CONT
                else:
                    [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                endif
                #
                # LI: Flag to indicate the kind of parameters given
                #     LI=1, total widths only
                #     LI=2, fission widths only
                #     LI=3, total and fission widths
                #     LI=4, radiative capture widths only
                #     LI=5, total and capture widths
                #     LI=6, fission and capture widths
                #     LI=7, total, fission, and capture widths
                #
                # Only LI=5 (for not fissionable only)
                # and  LI=7  should be used for
                # complete evaluations.
                #
                # NX: Flag to indicate the background data
                #     NX=1, total background data only
                #     NX=2, total and capture background data given
                #     NX=3, total, fission and capture background data given
                #
                # The evaluator must select the appropriate NX value
                # according to the data provided in the evaluation.
                #
                if NX==1 [lookahead=1]:
                    [MAT, 2,151/ AWRI, 0.0, LI, 0, 6*NX, NX /
                        {AT[k]}{k=1 to 4}, {BT[k]}{k=1 to 2}]LIST
                elif NX==2 [lookahead=1]:
                    [MAT, 2,151/ AWRI, 0.0, LI, 0, 6*NX, NX /
                        {AT[k]}{k=1 to 4}, {BT[k]}{k=1 to 2},
                        {AC[k]}{k=1 to 4}, {BC[k]}{k=1 to 2}]LIST
                elif NX==3 [lookahead=1]:
                    [MAT, 2,151/ AWRI, 0.0, LI, 0, 6*NX, NX /
                        {AT[k]}{k=1 to 4}, {BT[k]}{k=1 to 2},
                        {AF[k]}{k=1 to 4}, {BF[k]}{k=1 to 2},
                        {AC[k]}{k=1 to 4}, {BC[k]}{k=1 to 2}]LIST
                else:
                    stop("Format error: NX<1 or NX>3 for LRF=4 (Adler-Adler)")
                endif
                #
                # DET=DEF=DEC: Resonance energy
                # DWT=DWF=DWC: Resonance width
                # GRT,GRF,GRC: symmetrical contribution for total,fission and capture
                # GIT,GIF,GIC: asymmetrical contribution for total,fission and capture
                #
                # For LI < 7 some fields for reactions not given must be set
                # to 0.0 within each (L,J) group in the LIST records below.
                #
                for m=1 to NLS:
                (l_group[m])
                    [MAT, 2,151/0.0, 0.0, L, 0, NJS, 0] CONT
                    for n=1 to NJS:
                    (j_group[n])
                        [MAT, 2,151/ AJ, 0.0, 0, 0, 12*NLJ, NLJ/
                            {DET[k],DWT[k],GRT[k],GIT[k],DEF[k],DWF[k],
                            GRF[k],GIF[k],DEC[k],DWC[k],GRC[k],GIC[k]}{k=1 to NLJ}] LIST
                    (/j_group[n])
                    endfor
                (/l_group[m])
                endfor

            # R-matrix Limited (RML)
            elif LRF==7:
                [MAT,2,151/ 0.0, 0.0, IFG, KRM, NJS, KRL ]CONT
                [MAT,2,151/0.0, 0.0, NPP, 0, 12*NPP, 2*NPP /
                    {MA[k] , MB[k], ZA[k] , ZB[k] , IA[k] , IB[k] ,
                    Q[k], PNT [k], SHF[k] , MT[k] , PA[k] , PB[k]}{k=1 to NPP} ]LIST
                for k=1 to NJS:
                (j_group[k])
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
                        #
                        # The description given in the ENDF-6 Manual
                        # (Chapter 2, Section 2.2.1.6, pp. 76-77) may
                        # lead to an inconsistency when LPS = 0.
                        #
                        # According to ENDF-6 rules, the value of LPS
                        # should also correspond to the number of
                        # listed values (the NPL field of a LIST record).
                        #
                        # Possible alternative representations include:
                        #
                        # 1) Using a CONT record:
                        #    [MAT, 2, 151 / 0.0, 0.0, 0, 0, LPS, 1] CONT
                        #
                        # 2) Storing LPS in a different integer position:
                        #    [MAT, 2, 151 / 0.0, 0.0, 0, LPS, 6, 1 /
                        #     0.0, 0.0, 0.0, 0.0, 0.0, 0.0] LIST
                        #
                        # Nevertheless, this implementation follows
                        # the ENDF-6 Manual literally.
                        #
                        # To date (January 5, 2026), there are no known
                        # evaluations using KPS > 0.
                        #
                        for n=1 to NCH:
                            [MAT,2,151/ 0.0, 0.0, 0, 0, LPS, 1/
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.0]LIST
                            if LPS == 1:
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / PSR ]TAB1 (real_part[n])
                                [MAT,2,151/ 0.0, 0.0, 0, 0, NR, NP/ E / PSI ]TAB1 (imag_part[n])
                            endif
                        endfor
                    endif

                (/j_group[k])
                endfor
            endif

        # Unresolved resonance data
        elif LRU==2:

            # Case A (see Chap 2.3, p. 76)
            if LFW==0 and LRF==1:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP]TAB1 (AP_table)
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
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP]TAB1 (AP_table)
                endif

                if NRO!=0 and (NAPS==0 or NAPS==1):
                    [MAT, 2,151/ SPI, 0.0, LSSF, 0, NE, NLS /
                                {ES[p]}{p=1 to NE} ] LIST
                else:
                    [MAT, 2,151/ SPI, AP, LSSF, 0, NE, NLS /
                                {ES[p]}{p=1 to NE} ] LIST
                endif

                for p=1 to NLS:
                (l_group[p])
                    [MAT, 2,151/ AWRI, 0.0, L, 0, NJS, 0]CONT
                    for n=1 to NJS:
                    (j_group[n])
                        [MAT, 2,151/ 0.0, 0.0, L, MUF, NE+6, 0/
                            D, AJ, AMUN, GN0, GG, 0.0,
                            {GF[m]}{m=1 to NE} ] LIST
                    (/j_group[n])
                    endfor
                (/l_group[p])
                endfor

            # Case C (see Chap 2.3, p. 77)
            elif (LFW==0 or LFW==1) and LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP] TAB1 (AP_table)
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
                    (j_group[n])
                        [MAT, 2,151/ AJ, 0.0, INT, 0, 6*NE+6, NE/
                            0.0, 0.0, AMUX, AMUN, AMUG, AMUF,
                            {ES[m], D[m] , GX[m] , GN0[m] , GG[m] , GF[m]}{m=1 to NE} ]LIST
                    (/j_group[n])
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
