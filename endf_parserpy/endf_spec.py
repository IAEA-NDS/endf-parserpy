spec_dic = {}

spec_dic.setdefault(1, {})
spec_dic[1][451] = \
"""
[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT
for i=1 to NWD:
    [MAT, 1,451/ DESCRIPTION[i]]TEXT
endfor
for i=1 to NXC:
    [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
endfor
SEND
"""

spec_dic.setdefault(3, {})
spec_dic[3] = \
"""
[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
SEND
"""

spec_dic.setdefault(2, {})
spec_dic[2][151] = \
"""
[MAT, 2,151/ ZA, AWR, 0, 0, NIS, 0]HEAD
for i=1 to NIS:
(isotope[i])
    [MAT, 2,151/ ZAI, ABN, 0, LFW, NER, 0]CONT
    for j=1 to NER:
    (range[j])
        [MAT, 2,151/ EL, EH, LRU, LRF, NRO, NAPS]CONT
        if LRU==1:
            if LRF==1:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1
                endif
                [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                for m=1 to NLS:
                (spingroup[m])
                    [MAT, 2,151/ AWRI, QX, L, LRX, 6*NRS, NRS /
                    {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRS} ]LIST
                (/spingroup[m])
                endfor
            endif
            if LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1
                endif
                [MAT, 2,151/ SPI, AP, 0, 0, NLS, 0]CONT
                for m=1 to NLS:
                (spingroup[m])
                    [MAT, 2,151/ AWRI, QX, L, LRX, 6*NRS, NRS /
                    {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRS} ]LIST
                (/spingroup[m])
                endfor
            endif
            if LRF==3:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint / AP]TAB1
                endif
                [MAT, 2,151/ SPI, AP, LAD, 0, NLS, NLSC]CONT
                for m=1 to NLS:
                (spingroup[m])
                    [MAT, 2,151/AWRI,APL, L, 0, 6*NRS, NRS/
                    {ER[k] , AJ[k] , GN[k], GG[k] , GFA[k],  GFB[k]}{k=1 to NRS} ]LIST
                (/spingroup[m])
                endfor
            endif
            if LRF==7:
                [MAT,2,151/ 0.0, 0.0, IFG, KRM, NJS, KRL ]CONT
                [MAT,2,151/0.0, 0.0, NPP, 0, 12*NPP, 2*NPP /
                    {MA[k] , MB[k], ZA[k] , ZB[k] , IA[k] , IB[k] ,
                    Q[k], PNT [k], SHF[k] , MT[k] , PA[k] , PB[k]}{k=1 to NPP} ]LIST
                for k=1 to NJS:
                (spingroup[k])
                    [MAT,2,151/ AJ, PJ, KBK, KPS, 6*NCH, NCH /
                    {PPI[l] , L[l] , SCH[l] , BND [l] , APE[l] , APT[l]}{l=1 to NCH} ]LIST
                    [MAT,2,151/ 0.0, 0.0, 0, NRS, 6*NX, NX /
                    {ER[n], {GAM[m,n]}{m=1 to NCH}}{n=1 to NRS} ]LIST
                (/spingroup[k])
                endfor
            endif
        endif
        if LRU==2:
            if LFW == 0: if LRF==2:
                if NRO != 0:
                    [MAT, 2,151/ 0.0, 0.0, 0, 0, NR, NP/ Eint /AP ] TAB1
                endif
                [MAT, 2,151/ SPI, AP, LSSF, 0, NLS, 0]CONT
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
            endif endif
        endif
    (/range[j])
    endfor
(/isotope[i])
endfor
SEND
"""



# TODO: remove after successful development
spec_dic.setdefault(99, {})
spec_dic[99] = \
"""
[MAT,99, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
for i=1 to 1:
    (testsec[i])
        [MAT,99, MT/ A, B, C, D, E, F /
           {{U[j,k]}{j=1 to 3}}{k=1 to 3}, bla
        ]LIST
    (/testsec[i])
endfor
"""

spec_dic.setdefault(98, {})
spec_dic[98] = \
"""
[MAT,98, MT/ ZA*3, 5*ZA, 5+6*6/6-11, 0, 0, 0] HEAD
"""
