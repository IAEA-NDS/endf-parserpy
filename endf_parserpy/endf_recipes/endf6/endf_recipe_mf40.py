############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/14
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF40 = """

[MAT,40,MT/ ZA, AWR, LIS, 0, NS, 0] HEAD
for k=1 to NS:
    (subsection[k])
        [MAT,40, MT/ QM, QI, IZAP, LFS, 0, NL]CONT
        for i=1 to NL:
            (subsubsec[i])
                [MAT,40,MT/ XMF1, XLFS1, MAT1, MT1, NC, NI] CONT
                for j=1 to NC:
                    # NC subsections exactly as in MF33
                    (nc_subsubsubsec[j])
                        if LTY==0 [lookahead=1]:
                            [MAT,40,MT/ 0.0, 0.0, 0, LTY, 0, 0]CONT
                            [MAT,40,MT/ E1, E2, 0, 0, 2*NCI, NCI/
                                {C[i], XMT[i]}{i=1 to NCI} ]LIST

                        elif LTY==1 or LTY==2 or LTY==3 [lookahead=1]:
                            [MAT,40,MT/ 0.0, 0.0, 0, LTY, 0, 0]CONT
                            [MAT,40,MT/ E1, E2, MATS, MTS, 2*NEI+2, NEI/
                                XMFS,XLFSS, {E[i],WE[i]}{i=1 to NEI} ]LIST
                        endif
                    (/nc_subsubsubsec[j])
                endfor

                for j=1 to NI:
                    # NI subsections exactly as in MF33
                    (ni_subsubsubsec[j])
                        if LB>=0 and LB<=4 [lookahead=1]:
                            [MAT,40,MT/ 0.0, 0.0, LT, LB, 2*NP, NP/
                                {Ek[q] , Fk[q]}{q=1 to (NP-LT)}
                                {El[q] , Fl[q]}{q=1 to LT} ]LIST

                        elif LB==5 and LS==0 [lookahead=1]:
                            # asymmetric matrix
                            [MAT,40,MT/ 0.0, 0.0, LS, LB, NT, NE/
                                {E[q]}{q=1 to NE} {{F[q,qp]}{qp=1 to NE-1}}{q=1 to NE-1} ]LIST

                        elif LB==5 and LS==1 [lookahead=1]:
                            # symetric matrix
                                [MAT,40,MT/ 0.0, 0.0, LS, LB, NT, NE/
                                    {E[q]}{q=1 to NE} {{F[q,qp]}{qp=q to NE-1}}{q=1 to NE-1} ]LIST

                        elif LB==6 [lookahead=1]:
                            # NEC = (NT-1)/NER
                            [MAT,40,MT/ 0.0, 0.0, 0, LB, NT, NER/
                                {ER[q]}{q=1 to NER} {EC[q]}{q=1 to (NT-1)/NER}
                                {{F[q,l]}{l=1 to (NT-1)/NER-1}}{q=1 to NER-1} ]LIST

                        elif (LB==8 or LB==9) and LT==0 [lookahead=1]:
                            [MAT,40,MT/ 0.0, 0.0, LT, LB, 2*NP, NP/
                                {E[q], F[q]}{q=1 to NP} ]LIST
                        endif
                    (/ni_subsubsubsec[j])
                endfor
            (/subsubsec[i])
        endfor
    (/subsection[k])
endfor
SEND
"""
