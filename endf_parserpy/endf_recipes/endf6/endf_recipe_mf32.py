############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/12
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF32 = """

[MAT,32,151/ ZA, AWR, 0, 0, NIS, 0]HEAD
for i=1 to NIS:
(isotope[i])
    [MAT,32,151/ ZAI, ABN, 0, LFW, NER, 0]CONT
    for j=1 to NER:
    (range[j])
        [MAT,32,151/ EL, EH, LRU, LRF, NRO, NAPS]CONT

        if NRO != 0:
            [MAT,32,151/ 0.0, 0.0, 0, 0, 0, NI]CONT
            # TODO
            stop("NRO != 0 branch not implemented in ENDF recipe MF32")
        endif

        # LCOMP == 0 cases

        if LCOMP==0 and LRU==1 and (LRF==1 or LRF==2) [lookahead=1]:
            [MAT,32,151/ SPI, AP, 0, LCOMP, NLS, ISR]CONT
            if ISR != 0:
                [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
            endif
            for k=1 to NLS:
                (somesec[k])
                    [MAT,32,151/AWRI, 0.0, L, 0, 18*NRS, NRS /
                        {ER[m],  AJ[m],   GT[m],   GN[m],    GG[m],  GF[m],
                         DE2[m], DN2[m],  DNDG[m], DG2[m],  DNDF[m], DGDF[m],
                         DF2[m], DJDN[m], DJDG[m], DJDF[m], DJ2[m],  0.0}{m=1 to NRS} ]LIST
                (/somesec[k])
            endfor

        # LCOMP == 1 cases
        elif LCOMP==1 and LRU==1 and (LRF==1 or LRF==2) [lookahead=1]:
            [MAT,32,151/ SPI, AP, 0, LCOMP, NLS, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
            endif
            [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, NLRS]CONT
            for p=1 to NSRS:
                (nsrs_subsec[p])
                    [MAT,32,151/ 0.0, 0.0, MPAR, 0, 6*NRB+(MPAR*NRB)*(MPAR*NRB+1)/2, NRB/
                        {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRB},
                        {{V[m,n]}{n=m to MPAR*NRB}}{m=1 to MPAR*NRB} ] LIST
                (/nsrs_subsec[p])
            endfor

        elif LCOMP==1 and LRU==1 and LRF==3 [lookahead=1]:
            [MAT,32,151/ SPI, AP, 0, LCOMP, NLS, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, MLS, 1 /
                    {DAP[k]}{k=1 to MLS} ]LIST
            endif
            [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, NLRS]CONT
            for p=1 to NSRS:
                (nsrs_subsec[p])
                    [MAT,32,151/ 0.0, 0.0, MPAR, 0, 6*NRB+(MPAR*NRB)*(MPAR*NRB+1)/2, NRB/
                        {ER[k], AJ[k], GN[k], GG[k], GFA[k], GFB[k]}{k=1 to NRB},
                        {{V[m,n]}{n=m to MPAR*NRB}}{m=1 to MPAR*NRB} ] LIST
                (/nsrs_subsec[p])
            endfor
        elif LCOMP==1 and LRU==1 and LRF==7 [lookahead=1]:
            [MAT,32,151/ 0.0, 0.0, 0, LCOMP, 0, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, JCH, (1+(NCH-1)/6) /
                    {{DAP[m,n]}{n=1 to NCH}}{m=1 to JCH/NCH} ] LIST
            endif
            [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, 0]CONT
            for k=1 to NSRS:
                (nsrs_subsec[k])
                    [MAT,32,151/ 0.0, 0.0, NJSX, 0, 0, 0]CONT
                    for m=1 to NJSX:
                        (J_pi_group[m])
                            NX := (1+NCH + (5-NCH) % 6) * NRB / 6
                            num_zeros := (5-NCH) % 6
                            [MAT,32,151/ 0.0, 0.0, NCH, NRB, 6*NX, NX/
                                { ER[p], {GAM[q,p]}{q=1 to NCH}
                                  {0.0}{r=1 to num_zeros} }{p=1 to NRB} ]LIST
                        (/J_pi_group[m])
                    endfor
                    [MAT,32,151/ 0.0, 0.0, 0, 0, N, NPARB/
                       {{V[p,q]}{q=p to NPARB}}{p=1 to NPARB} ] LIST
                (/nsrs_subsec[k])
            endfor

        # LCOMP == 2 cases

        elif LCOMP==2 and LRU==1 and (LRF==1 or LRF==2) [lookahead=1]:
            [MAT,32,151/ SPI, AP, 0, LCOMP, 0, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
            endif
            [MAT,32,151/AWRI, QX, 0, LRX, 12*NRSA, NRSA/
                {ER[k],  AJ[k], GT[k], GN[k],  GG[k],  GF[k],
                 DER[k], 0.0,   0.0,   DGN[k], DGG[k], DGF[k]}{k=1 to NRSA} ]LIST
            [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
            for k=1 to NM:
                [MAT,32,151/ II[k], JJ[k], KIJ[k] {NDIGIT} ]INTG
            endfor

        elif LCOMP==2 and LRU==1 and LRF==3 [lookahead=1]:
            [MAT,32,151/ SPI, AP, LAD, LCOMP, 0, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, MLS, 1 /
                    {DAP[k]}{k=1 to MLS} ]LIST
            endif
            [MAT,32,151/AWRI, APL, 0, 0, 12*NRSA, NRSA/
                {ER[k],  AJ[k], GN[k],  GG[k],  GFA[k],  GFB[k],
                 DER[k], 0.0,   DGN[k], DGG[k], DGFA[k], DGFB[k]}{k=1 to NRSA} ]LIST
             [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
             for k=1 to NM:
                [MAT,32,151/ II[k], JJ[k], KIJ[k]{NDIGIT}]INTG
             endfor

        elif LCOMP==2 and LRU==1 and LRF==7 [lookahead=1]:
            [MAT,32,151/ 0.0, 0.0, IFG, LCOMP, NJS, ISR ]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, NJCH, (1+(NJCH-1)/6) /
                    {{DAP[m,n]}{n=1 to NJCH/NJS}}{m=1 to NJCH/NJS} ] LIST
            endif
            [MAT,32,151/ 0.0, 0.0, NPP, NJSX, 12*NPP, 2*NPP/
                {MA[k], MB[k],  ZA[k],  ZB[k], IA[k], IB[k],
                 Q[k],  PNT[k], SHF[k], MT[k], PA[k], PB[k]}{k=1 to NPP} ]LIST

            for q=1 to NJS:
                (somesec[q])
                    [MAT,32,151/ AJ, PJ, 0, 0, 6*NCH, NCH/
                        {PPI[k], L[k], SCH[k], BND[k], APE[k], APT[k]}{k=1 to NCH} ]LIST
                    NX := (2*(NCH+1) + 2*((5-NCH) % 6)) * NRSA / 12
                    num_zeros := (5-NCH) % 6
                    [MAT,32,151/0.0, 0.0, 0, NRSA, 12*NX, NX?/
                        { ER[k], {GAM[p,k]}{p=1 to NCH}, {0.0}{r=1 to num_zeros}
                          DER[k], {DGAM[p,k]}{p=1 to NCH}, {0.0}{r=1 to num_zeros}
                        }{k=1 to NRSA} ]LIST
                (/somesec[q])
            endfor
            [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
            for q=1 to NM:
                [MAT,32,151/ II[q], JJ[q], KIJ[q]{NDIGIT} ]INTG
            endfor

        # LRU == 2 (Unresolved Resonance Format)

        elif LRU == 2:
            [MAT,32,151/ SPI, AP, 0, 0, NLS, 0]CONT
            for q=1 to NLS:
                (l_group[q])
                    [MAT,32,151/ AWRI, 0.0, L, 0, 6*NJS, NJS/
                        {D[k], AJ[k], GNO[k], GG[k], GF[k], GX[k]}{k=1 to NJS}]LIST
                (/l_group[q])
            endfor
            [MAT,32,151/ 0.0, 0.0, MPAR, 0, (NPAR*(NPAR+1))/2, NPAR/
                {{RV[p,q]}{q=p to NPAR}}{p=1 to NPAR} ]LIST
        endif

    (/range[j])
    endfor
(/isotope[i])
endfor
SEND
"""
