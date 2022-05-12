spec_dic = {}

spec_dic.setdefault(0, {})
spec_dic[0][0] = \
"""
[MAT, 0, 0/ TAPEDESCR]TEXT
"""

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

        # Resolved resonance data
        if LRU==1:
            # Single level Breit-Wigner (SLBW) or Multi level Breit-Wigner (MLBW)
            if LRF==1 or LRF==2:
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
            # R-matrix Reich-Moore multi level parameters
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

        # Unresolved resonance data
        if LRU==2:
            if LFW == 0 and LRF==2:
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
            endif
        endif
    (/range[j])
    endfor
(/isotope[i])
endfor
SEND
"""

spec_dic.setdefault(4, {})
spec_dic[4] = \
"""
[MAT, 4, MT/ ZA, AWR, 0, LTT, 0, 0]HEAD
[MAT, 4, MT/ 0.0, AWR, LI, LCT, 0, 0]CONT

# Legendre coefficients
if LTT == 1 and LI == 0:
    [MAT, 4, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
    for i=1 to NE:
        [MAT, 4, MT/ T, E[i] , LT, 0, NL[i], 0/ {a[i,l]}{l=1 to NL[i]} ]LIST
    endfor
endif

# Angular distributions over two energy ranges.
if LTT==3 and LI==0:
    # lower range given by Legendre coefficients
    [MAT, 4, MT/ 0.0, 0.0, 0, 0, NR, NE1/ Eint ]TAB2 (leg_int)
    for i=1 to NE1:
        [MAT, 4, MT/ T, E[i], LT, 0, NL[i], 0/
                     {al[i,j]}{j=1 to NL[i]} ]LIST
    endfor
    # higher range represented by probability distribution
    [MAT, 4, MT/ 0.0, 0.0, 0, 0, NR, NE2/ Eint ]TAB2 (ang_int)
    for i=NE1 to NE1+NE2-1:
        [MAT, 4, MT/ T,  E[i] , LT, 0, NR, NP/ mu / f ]TAB1 (angtable[i])
    endfor
endif
SEND
"""

spec_dic.setdefault(6, {})
spec_dic[6] = \
"""
[MAT, 6, MT/ ZA, AWR, JP, LCT, NK, 0]HEAD
for i=1 to NK:
    (subsection[i])
        [MAT, 6, MT/ ZAP, AWP, LIP, LAW, NR, NP/ Eint / yi]TAB1 (tmp)
        if LAW == 1:
            [MAT, 6, MT/ 0.0, 0.0, LANG, LEP, NR, NE/ Eint ]TAB2
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j] , ND[j], NA[j], NW[j], NEP[j]/
                             {Ep[j,k], {b[m,j,k]}{m=0 to NA[j]}}{k=1 to NEP[j]} ]LIST
            endfor
        endif
        # Discrete Two-Body Scattering
        if LAW == 2:
            [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j], LANG, 0, NLW[j], NL[j] / {A[j,l]}{l=1 to NLW[j]} ]LIST
            endfor
        endif
        # Laboratory Angle-Energy Law (LAW=7) (manual 6.2.9, p. 146)
        if LAW == 7:
            [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE / E]TAB2 (E_interpol)
            for j=1 to NE:
                [MAT, 6, MT/ 0.0, E[j], 0, 0, NRM, NMU[j] / mu ]TAB2 (mu_interpol)
                for k=1 to NMU[j]:
                    [MAT, 6, MT/ 0.0, mu[k] , 0, 0, NRP[k], NEP[k]/ Ep / f ]TAB1 (table[j,k])
                endfor
            endfor
        endif
    (/subsection[i])
endfor
SEND
"""

spec_dic.setdefault(12, {})
spec_dic[12] = """
# Photon Production Multiplicities (12.2.1, p. 194)
if LO == 1 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, 0, NK, 0]HEAD
    if NK > 1:
        [MAT, 12, MT/ 0.0, 0.0, 0, 0, NR, NP/ Eint / Y] TAB1
    endif
    for k=1 to NK:
        [MAT, 12, MT/ Eg[k] , ES[k], LP, LF, NR, NP/ Eint / y[k] ] TAB1
    endfor
endif
# Transition Probability Arrays (12.2.2, p. 196)
if LO == 2 [lookahead=1]:
    [MAT, 12, MT/ ZA, AWR, LO, LG, NS, 0]HEAD
    if LG == 1:
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, 2*NT, NT/
                      {ES[i], TP[i]}{i=1 to NT} ]LIST
    endif
    if LG == 2:
        # TODO: (LG+1)*NT instead of 3*NT does not work at the moment
        [MAT, 12, MT/ ES_NS , 0.0, LP, 0, 3*NT, NT/
                      {ES[i], TP[i], GP[i]}{i=1 to NT} ]LIST
    endif
endif
SEND
"""

spec_dic.setdefault(14, {})
spec_dic[14] = """
# FILE 14: Photon Angular Distributions (Chap. 14, 203)
# Isotropic distributions (14.2.1, p. 205)
if LI == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, 0, NK, 0]HEAD
endif
# Anisotropic distribution with Legendre Coefficients Representation (14.2.2, p. 205)
if LI == 0 and LTT == 1 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI]HEAD
    # TODO: implement
endif
# Anisotropic distribution with Tabulated Angular Distributions
if LI == 0 and LTT == 2 [lookahead=1]:
    [MAT, 14, MT/ ZA, AWR, LI, LTT, NK, NI] HEAD
    # TODO: implement
endif
SEND
"""

spec_dic.setdefault(15, {})
spec_dic[15] = """
# FILE 15: Continuous Photon Energy Spectra
[MAT, 15, MT/ ZA, AWR, 0, 0, NC, 0] HEAD
for j=1 to NC:
    (subsection[j])
        # ATTENTION: This if must be inside subsection
        #            otherwise LF variable will not be
        #            in scope for the evaluation of the
        #            if statement.
        if LF == 1 [lookahead=1]:
            [MAT, 15, MT/ 0.0, 0.0, 0, LF, NR, NP/ Eint / p] TAB1 (rtfm_tab1)
            [MAT, 15, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ] TAB2
            for k=1 to NE:
                [MAT, 15, MT/ 0.0, E[k] , 0, 0, NR, NP / Egamma / g] TAB1 (rtfm1_tab[k])
            endfor
        endif
    (/subsection[j])
endfor
SEND
"""
