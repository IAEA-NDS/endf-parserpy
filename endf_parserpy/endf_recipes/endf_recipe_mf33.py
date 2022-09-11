############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF33 = """
[MAT, 33, MT/ ZA, AWR, 0, MTL, 0, NL] HEAD

# MTL != 0 indicates a lumped contribution and nothing more to read
if MTL == 0:
    for n=1 to NL:
    (subsection[n])
        [MAT,33,MT/ XMF1, XLFS1, MAT1, MT1, NC, NI]CONT

        # definition of NC type subsections
        for m=1 to NC:
            (nc_subsection[m])
                if LTY==0 [lookahead=1]:
                    [MAT,33,MT/ 0.0, 0.0, 0, LTY, 0, 0]CONT
                    [MAT,33,MT/ E1, E2, 0, 0, 2*NCI, NCI/
                        {C[i], XMT[i]}{i=1 to NCI} ]LIST

                elif LTY==1 or LTY==2 or LTY==3 [lookahead=1]:
                    [MAT,33,MT/ 0.0, 0.0, 0, LTY, 0, 0]CONT
                    [MAT,33,MT/ E1, E2, MATS, MTS, 2*NEI+2, NEI/
                        XMFS,XLFSS, {E[i],WE[i]}{i=1 to NEI} ]LIST
                endif
            (/nc_subsection[m])
        endfor

        # definition of NI type subsections
        for m=1 to NI:
            (ni_subsection[m])
                if LB>=0 and LB<=4 [lookahead=1]:
                    [MAT,33,MT/ 0.0?, 0.0?, LT, LB, 2*NP, NP/
                        {Ek[k] , Fk[k]}{k=1 to (NP-LT)}
                        {El[k] , Fl[k]}{k=1 to LT} ]LIST

                elif LB==5 and LS==0 [lookahead=1]:
                    # asymmetric matrix
                    [MAT,33,MT/ 0.0, 0.0, LS, LB, NT, NE/
                        {E[k]}{k=1 to NE} {{F[k,kp]}{kp=1 to NE-1}}{k=1 to NE-1} ]LIST

                elif LB==5 and LS==1 [lookahead=1]:
                    # symetric matrix
                        [MAT,33,MT/ 0.0, 0.0, LS, LB, NT, NE/
                            {E[k]}{k=1 to NE} {{F[k,kp]}{kp=k to NE-1}}{k=1 to NE-1} ]LIST

                elif LB==6 [lookahead=1]:
                    # NEC = (NT-1)/NER
                    [MAT,33,MT/ 0.0, 0.0, 0, LB, NT, NER/
                        {ER[k]}{k=1 to NER} {EC[k]}{k=1 to (NT-1)/NER}
                        {{F[k,l]}{l=1 to (NT-1)/NER-1}}{k=1 to NER-1} ]LIST

                elif (LB==8 or LB==9) and LT==0 [lookahead=1]:
                    [MAT,33,MT/ 0.0, 0.0, LT, LB, 2*NP, NP/
                        {E[k], F[k]}{k=1 to NP} ]LIST
                endif

            (/ni_subsection[m])
        endfor

    (/subsection[n])
    endfor
endif
SEND
"""
