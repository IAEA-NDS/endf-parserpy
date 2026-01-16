############################################################
#
# Author(s):       Georg Schnabel, Daniel L. Aldama
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/12
# Last modified:   2026/01/17
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
        #
        # Energy-dependent covariance data for the scattering radius AP(E)
        # must be provided when NRO != 0.
        # According to the ENDF-6 Manual (Chapter 32, Section 32.2, pp. 253-254),
        # the NI-type sub-subsections are defined in the same manner as those
        # used for cross-section covariances in MF=33
        # (ENDF-6 Manual, Chapter 33, Section 33.2.1).
        # In this implementation, it is assumed that NI-type sub-subsections
        # with LB = 0, 1, 2, 3, 4, or 5 may be used to represent scattering
        # radius covariances.
        #
        if NRO != 0:
            [MAT,32,151/ 0.0, 0.0, 0, 0, 0, NI]CONT
            for m=1 to NI:
            (AP_subsec[m])
                if LB>=0 and LB<=4 [lookahead=1]:
                    [MAT,32,151/ 0.0, 0.0, LT, LB, 2*NP, NP/
                        {Ek[k] , Fk[k]}{k=1 to (NP-LT)}
                        {El[k] , Fl[k]}{k=1 to LT} ]LIST
                elif LB==5 and LS==0 [lookahead=1]:
                    # asymmetric matrix
                    NT := NE*(NE-1)+1
                    [MAT,32,151/ 0.0, 0.0, LS, LB, NT, NE/
                        {E[k]}{k=1 to NE} {{F[k,kp]}{kp=1 to NE-1}}{k=1 to NE-1} ]LIST
                elif LB==5 and LS==1 [lookahead=1]:
                    # symmetric matrix
                    NT := NE*(NE+1)/2
                    [MAT,32,151/ 0.0, 0.0, LS, LB, NT, NE/
                        {E[k]}{k=1 to NE} {{F[k,kp]}{kp=k to NE-1}}{k=1 to NE-1} ]LIST
                else:
                    stop("LB<0 and LB>5 not implemented for the scattering radius covariance")
                endif
            (/AP_subsec[m])
            endfor
        endif

        # LCOMP == 0 cases (Compatible Resolved Resonance Format)

        if LCOMP==0 and LRU==1 and (LRF==1 or LRF==2) [lookahead=1]:
            [MAT,32,151/ SPI, AP, 0, LCOMP, NLS, ISR]CONT
            if ISR != 0:
                [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
            endif
            for k=1 to NLS:
                (l_group[k])
                    [MAT,32,151/AWRI, 0.0, L, 0, 18*NRS, NRS /
                        {ER[m],  AJ[m],   GT[m],   GN[m],    GG[m],  GF[m],
                         DE2[m], DN2[m],  DNDG[m], DG2[m],  DNDF[m], DGDF[m],
                         DF2[m], DJDN[m], DJDG[m], DJDF[m], DJ2[m],  0.0}{m=1 to NRS} ]LIST
                (/l_group[k])
            endfor

        # LCOMP == 1 cases (General Resolved Resonance Format)

        elif LCOMP==1 and LRU==1 and LRF != 7 [lookahead=1]:

            [MAT,32,151/ SPI, AP, 0, LCOMP, NLS, ISR]CONT

            if LRF==1 or LRF==2:
                # SLBW and MLBW formalism
                if ISR > 0:
                    [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
                endif
                [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, NLRS]CONT
                # Short range components for SLBW and MLBW
                #
                # The maximum number of MPAR is 5 and for a given resonance
                # the covariance matrix indexing is in the order:
                #   1. ER: Resonance energy
                #   2. GN: neutron width
                #   3. GG: capture width
                #   4. GF: fission width
                #   5. GX: competitive width (GX = GT - GN - GG - GF)
                #
                # Covariance data for the total should be calculated
                #
                # For the symmetric covariance matrix V, only the upper triangular
                # elements are stored and provided in the LIST record
                #
                # For the parameter index j<=MPAR and resonance k<=NRB,
                # the index corresponding to m or n in the V array should be
                # calculated as m=j+(k-1)*MPAR (same for n)
                #
                # The covariance between the jp-th parameter of the
                # kr-th resonance and the ip-th parameter of the lr-th
                # resonance for jp<=MPAR, ip<=MPAR, kr<=lr, lr<=NRB
                # is V[m,n], where:
                #    m=jp+(kr-1)*MPAR
                #    n=ip+(lr-1)*MPAR
                #
                for p=1 to NSRS:
                    (sr_subsec[p])
                        [MAT,32,151/ 0.0, 0.0, MPAR, 0, 6*NRB+(MPAR*NRB)*(MPAR*NRB+1)/2, NRB/
                            {ER[k], AJ[k], GT[k], GN[k], GG[k], GF[k]}{k=1 to NRB},
                            {{V[m,n]}{n=m to MPAR*NRB}}{m=1 to MPAR*NRB} ] LIST
                    (/sr_subsec[p])
                endfor

            elif LRF==3:
                # REICH-MOORE formalism
                #
                # Scattering radius uncertainty.
                # According to the ENDF-6 Manual (Chapter 32, Section 32.2.2.2, p. 257),
                # the k index of the last DAPk entry should be k = MLS - 1 rather than MLS.
                # This is because the first value of DAP is included explicitly in the
                # LIST record, and the fifth field of the LIST record is set to MLS.
                #
                # In the implementation adopted here for ISR > 0, the array DAP[k] is
                # interpreted as follows:
                #
                #  DAP[1] = DAP          (default DAP value)
                #  DAP[2] = DAP1         (DAP for channel 1)
                #  DAP[3] = DAP2         (DAP for channel 2)
                #     ...
                #  DAP[k] = DAPL,        (DAP for channel L=k-1)
                #     ...
                #  DAP[MLS-1] = DAPmls-2 (DAP for channel MLS-2, equal to NLS-1, if MLS=NLS+1)
                #  DAP[MLS]   = DAPmls-1 (DAP for channel MLS-1, equal to NLS, if MLS=NLS+1)
                #
                # with the constraint:
                #
                #  1 <= MLS <= NLS + 1
                #
                # If MLS=1, then DAP is assumed to be the uncertainty for all APL (channels)
                # If 1 < MLS <= NLS + 1 and DAP != 0.0, then DAP is the uncertainty
                # for any DAP[k] with k>1 not explicitly defined in the list.
                # If DAP=0.0, then MLS=NLS+1 and all DAP[k] with k>1 must be specified.
                #
                if ISR > 0:
                    [MAT,32,151/ 0.0, 0.0, 0, 0, MLS, 1 /
                        {DAP[k]}{k=1 to MLS} ]LIST
                endif

                [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, NLRS]CONT
                # Short range components for REICH-MOORE
                #
                # The maximum number of MPAR is 5 and for a given resonance
                # the covariance matrix indexing is in the order:
                #   1. ER: Resonance energy
                #   2. GN: neutron width
                #   3. GG: capture width
                #   4. GFA: fission width for first fission channel
                #   5. GFB: fission width for second fission channel
                #
                #   GT = GN + GG + GFA + GFB
                #
                # Covariance data for total should be calculated
                #
                # For the symmetric covariance matrix V, only the upper triangular
                # elements are stored and provided in the LIST record
                #
                # For the parameter index j<=MPAR and resonance k<=NRB,
                # the index corresponding to m or n in the V array should be
                # calculated as m=j+(k-1)*MPAR (same for n)
                #
                # The covariance between the jp-th parameter of the
                # kr-th resonance and the ip-th parameter of the lr-th
                # resonance for jp<=MPAR, ip<=MPAR, kr<=lr, lr<=NRB
                # is V[m,n], where:
                #    m=jp+(kr-1)*MPAR
                #    n=ip+(lr-1)*MPAR
                #
                for p=1 to NSRS:
                    (sr_subsec[p])
                        [MAT,32,151/ 0.0, 0.0, MPAR, 0, 6*NRB+(MPAR*NRB)*(MPAR*NRB+1)/2, NRB/
                            {ER[k], AJ[k], GN[k], GG[k], GFA[k], GFB[k]}{k=1 to NRB},
                            {{V[m,n]}{n=m to MPAR*NRB}}{m=1 to MPAR*NRB} ] LIST
                    (/sr_subsec[p])
                endfor

            elif LRF==4:
                # ADLER-ADLER formalism. LI=7 is assumed (ENDF-6 Manual 32.2.2.3).
                if ISR > 0:
                    [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
                endif
                [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, NLRS]CONT
                # Short range components for ADLER-ADLER
                #
                # According to the ENDF-6 Manual (Chapter 32, Section 32.2.2.3, p. 258),
                # the fifth field of the LIST record should be equal to
                #
                #   6*NRB + (MPAR*NRB)*(MPAR*NRB + 1)/2
                #
                # However, when the Adler–Adler formalism is taken into account,
                # this value must be
                #
                #   12*NRB + (MPAR*NRB)*(MPAR*NRB + 1)/2
                #
                # which is the expression used in this implementation.
                #
                # The maximum value of MPAR is 8 and for a given resonance
                # the covariance matrix indexing is in the order:
                #   1. DET=DEF=DEC: Resonance Energy
                #   2. DWT=DWF=DWD: Resonance width
                #   3. GRT: symmetrical contribution for total
                #   4. GIT: asymmetrical contribution for total
                #   5. GRF: symmetrical contribution for fission
                #   6. GIF: asymmetrical contribution for fission
                #   7. GRC: symmetrical contribution for capture
                #   8. GIC: asymmetrical contribution for capture
                #
                # For the symmetric covariance matrix V, only the upper triangular
                # elements are stored and provided in the LIST record
                #
                # For the parameter index j<=MPAR and resonance k<=NRB,
                # the index corresponding to m or n in the V array should be
                # calculated as m=j+(k-1)*MPAR (same for n)
                #
                # The covariance between the jp-th parameter of the
                # kr-th resonance and the ip-th parameter of the lr-th
                # resonance for jp<=MPAR, ip<=MPAR, kr<=lr, lr<=NRB
                # is V[m,n], where:
                #    m=jp+(kr-1)*MPAR
                #    n=ip+(lr-1)*MPAR
                #
                for p=1 to NSRS:
                    (sr_subsec[p])
                        [MAT,32,151/ 0.0, 0.0, MPAR, 0, 12*NRB+(MPAR*NRB)*(MPAR*NRB+1)/2, NRB/
                            {DET[k],DWT[k],GRT[k],GIT[k],DEF[k],DWF[k],
                             GRF[k],GIF[k],DEC[k],DWC[k],GRC[k],GIC[k]}{k=1 to NRB},
                            {{V[m,n]}{n=m to MPAR*NRB}}{m=1 to MPAR*NRB} ] LIST
                    (/sr_subsec[p])
                endfor

            endif

            # Long range components if NLRS>0 for LCOMP=1 and LRU=1 and LRF=1,2,3,4
            if NLRS > 0:
                #
                # The IDP parameter identification is consistent with the parameter
                # descriptions and ordering used in the corresponding short-range
                # subsections (LCOMP = 1, LRF = 1, 2, 3, 4).
                #
                for p=1 to NLRS:
                (lr_subsec[p])
                    if LB >= -1 and LB <= 2 [lookahead=1]:
                        [MAT,32,151/ 0.0, 0.0, IDP, LB, 2*NEB, NEB/
                             {Ek[k] , Fk[k]}{k=1 to NEB}] LIST
                    elif LB==5 [lookahead=1]:
                        [MAT,32,151/ 0.0, 0.0, IDP, LB, NEB*(NEB+1)/2, NEB/
                             {E[k]}{k=1 to NEB} {{F[k,kp]}{kp=k to NEB-1}}{k=1 to NEB-1} ]LIST
                    else:
                        stop("LB < -1, LB = 3,4 and LB > 5 not allowed for long-range components")
                    endif
                (/lr_subsec[p])
                endfor
            endif

        elif LCOMP==1 and LRU==1 and LRF==7 [lookahead=1]:
            # R-Matrix Limited formalism
            [MAT,32,151/ 0.0, 0.0, 0, LCOMP, 0, ISR]CONT
            #
            # In the ENDF-6 Manual (Chapter 32, Section 32.2.2.4, p. 258),
            # the sixth field of the LIST record for ISR > 0 is given as
            #
            #   (1 + (NJCH - 1)/6)
            #
            # This appears to be a typographical error. In this implementation,
            # the value
            #
            #   (1 + (NCH - 1)/6)
            #
            # is adopted instead.
            #
            # One alternative (and potentially preferable) interpretation is
            # to specify NCH directly or to provide NJS elsewhere, since the
            # value in the fifth field (JCH) should be equal to NJS*NCH or
            # to apply the same format used for LCOMP=2 LRF=7.
            #
            #
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, JCH, (1+(NCH-1)/6) /
                    {{DAP[m,n]}{n=1 to NCH}}{m=1 to JCH/NCH} ] LIST
            endif
            [MAT,32,151/ AWRI, 0.0, 0, 0, NSRS, 0]CONT
            # Short range component for R-Matrix Limited
            #
            # Parameters are numbered in the order in which they appear
            # in the listing; the total number of parameters (NPARB) is the
            # sum (over all included j_groups) of (NCH+1)*NRB, where NRB is
            # the number of resonances and NCH the number of channels
            # from the j_group in the covariance block.
            #
            for k=1 to NSRS:
                (sr_subsec[k])
                    [MAT,32,151/ 0.0, 0.0, NJSX, 0, 0, 0]CONT
                    for m=1 to NJSX:
                        (j_group[m])
                            NX := (1+NCH + (5-NCH) % 6) * NRB / 6
                            num_zeros := (5-NCH) % 6
                            [MAT,32,151/ 0.0, 0.0, NCH, NRB, 6*NX, NX/
                                { ER[p], {GAM[q,p]}{q=1 to NCH}
                                  {0.0}{r=1 to num_zeros} }{p=1 to NRB} ]LIST
                        (/j_group[m])
                    endfor
                    N := (NPARB*(NPARB+1))/2
                    [MAT,32,151/ 0.0, 0.0, 0, 0, N, NPARB/
                       {{V[p,q]}{q=p to NPARB}}{p=1 to NPARB} ] LIST
                (/sr_subsec[k])
            endfor

        # LCOMP == 2 cases (Resolved Resonance Compact Covariance Format)
        #
        # The correlation coefficients (whose values range from -1 to 1) are
        # presented in a compact representation as an integer with NDIGIT
        # digits plus a sign; each approximated correlation coefficient differs
        # from the original value by at most 0.5*10**(-NDIGIT), it means
        # 0.005 if NDIGIT = 2 and 0.0000005 if NDIGT=6.
        # Allowed values for NDIGIT are 2 through 6.
        #
        # The information stored in the INTG records below may be summarized as
        # follows: Let II and JJ represent two of the parameters in the numbering
        # scheme (NNN total number of parameters), with II > JJ. All those
        # correlation coefficients mapped to non-zero integers KIJ are printed
        # in File 32; zero-valued KIJ are printed (as blanks or zeros) only when
        # they occur on the same record with non-zero values.
        #
        # Each line (record) in the file begins by specifying the location
        # II and JJ (with II > JJ) and the compacted value of correlation
        # coefficient at (II,JJ). Others KIJs on the same line correspond to the
        # correlation coeffients at (II, JJ+1), (II, JJ+2), ... (II, JJ+NROW-1)
        # [so long as JJ + NROW - 1 < II ]. If there are more non-zero KIJs
        # for the same II, they are given on another line, again beginning
        # with the next non-zero KIJ.
        #
        # The format depends on the values of LRU and LRF
        #

        elif LCOMP==2 and LRU==1 and (LRF==1 or LRF==2) [lookahead=1]:

            #
            # SLBW and MLBW formalism
            [MAT,32,151/ SPI, AP, 0, LCOMP, 0, ISR]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, DAP, 0, 0, 0, 0]CONT
            endif
            #
            # NNN is the total number of unique resonance parameters included
            # in this listing, excluding AJ and GT.
            # The number of parameters per resonance is therefore
            #
            #   NPAR = NNN / NRSA
            #
            # The parameter ordering follows the ENDF-6 convention for
            # LCOMP = 1 with LRF = 1 or LRF = 2.
            #
            [MAT,32,151/AWRI, QX, 0, LRX, 12*NRSA, NRSA/
                {ER[k],  AJ[k], GT[k], GN[k],  GG[k],  GF[k],
                 DER[k], 0.0,   0.0,   DGN[k], DGG[k], DGF[k]}{k=1 to NRSA} ]LIST
            [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
            for k=1 to NM:
                [MAT,32,151/ II[k], JJ[k], KIJ[k] {NDIGIT} ]INTG
            endfor

        elif LCOMP==2 and LRU==1 and LRF==3 [lookahead=1]:
            # REICH-MOORE formalism
            [MAT,32,151/ SPI, AP, LAD, LCOMP, 0, ISR]CONT
            #
            # see comments on scattering radius uncertainties DAP[k]
            # given above for LCOMP=1 LRF=3 (REICH-MOORE)
            #
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, MLS, 1 /
                    {DAP[k]}{k=1 to MLS} ]LIST
            endif
            #
            # NNN is the total number of unique resonance parameters included
            # in this listing, excluding AJ.
            # The number of parameters per resonance is therefore
            #
            #   NPAR = NNN / NRSA
            #          3 for non-fissionable
            #          4 if only one fission channel is used
            #          5 if both fission channels are specified
            #
            # The parameter ordering follows the ENDF-6 convention for
            # LCOMP = 1 with LRF = 3.
            #
            [MAT,32,151/AWRI, APL, 0, 0, 12*NRSA, NRSA/
                {ER[k],  AJ[k], GN[k],  GG[k],  GFA[k],  GFB[k],
                 DER[k], 0.0,   DGN[k], DGG[k], DGFA[k], DGFB[k]}{k=1 to NRSA} ]LIST
             [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
             for k=1 to NM:
                [MAT,32,151/ II[k], JJ[k], KIJ[k]{NDIGIT}]INTG
             endfor

        elif LCOMP==2 and LRU==1 and LRF==7 [lookahead=1]:
            # R-Matrix Limited formalism
            [MAT,32,151/ 0.0, 0.0, IFG, LCOMP, NJS, ISR ]CONT
            if ISR > 0:
                [MAT,32,151/ 0.0, 0.0, 0, 0, NJCH, (1+(NJCH-1)/6) /
                    {{DAP[m,n]}{n=1 to NJCH/NJS}}{m=1 to NJS} ] LIST
            endif
            [MAT,32,151/ 0.0, 0.0, NPP, NJSX, 12*NPP, 2*NPP/
                {MA[k], MB[k],  ZA[k],  ZB[k], IA[k], IB[k],
                 Q[k],  PNT[k], SHF[k], MT[k], PA[k], PB[k]}{k=1 to NPP} ]LIST
            #
            # For LRF=7 (unlike other formats), the number of channels may vary
            # from one spin group to another. The number of resonance parameters
            # NNN is therefore given by the sum (from 1 to NJS) of (NCH+1)*NRSA.
            #
            # Note: In the ENDF-6 Manual (chapter 32, item 32.2.3.3), NCH*NRSA is
            #       written instead of (NCH+1)*NRSA due to a typographical error.
            #
            for q=1 to NJS:
                (j_group[q])
                    [MAT,32,151/ AJ, PJ, 0, 0, 6*NCH, NCH/
                        {PPI[k], L[k], SCH[k], BND[k], APE[k], APT[k]}{k=1 to NCH} ]LIST
                    NX := (2*(NCH+1) + 2*((5-NCH) % 6)) * NRSA / 12
                    num_zeros := (5-NCH) % 6
                    [MAT,32,151/0.0, 0.0, 0, NRSA, 12*NX, NX?/
                        { ER[k], {GAM[p,k]}{p=1 to NCH}, {0.0}{r=1 to num_zeros}
                          DER[k], {DGAM[p,k]}{p=1 to NCH}, {0.0}{r=1 to num_zeros}
                        }{k=1 to NRSA} ]LIST
                (/j_group[q])
            endfor
            [MAT,32,151/ 0.0, 0.0, NDIGIT, NNN, NM, 0 ]CONT
            for q=1 to NM:
                [MAT,32,151/ II[q], JJ[q], KIJ[q]{NDIGIT} ]INTG
            endfor

        # LRU == 2 (Unresolved Resonance Format)

        elif LRU == 2:
            [MAT,32,151/ SPI, AP, 0, 0, NLS, 0]CONT
            #
            # MPAR is the number of average parameters for which relative
            # covariance data are given for each L and J, in the order
            # D, GN0, GG, GF, and GX, for a maximum of 5. That is, relative
            # covariance values for the first MPAR of these are tabulated for
            # each (L,J) combination.
            # If MPAR is given as 4 when LFW=0 (no fission width) on the
            # CONT (isotope) record, then the four covariance matrix indices
            # per (L,J) combination represent D, GN0, GG, and GX. Additionally,
            # NPAR=MPAR*(sum of the values of NJS for each L)
            #
            for q=1 to NLS:
                (l_group[q])
                    [MAT,32,151/ AWRI, 0.0, L, 0, 6*NJS, NJS/
                        {D[k], AJ[k], GN0[k], GG[k], GF[k], GX[k]}{k=1 to NJS}]LIST
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
