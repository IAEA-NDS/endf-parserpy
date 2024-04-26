############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/12
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF34 = """
[MAT,34,MT/ ZA, AWR, 0, LTT, 0, NMT1]HEAD
for k=1 to NMT1:
    (subsection[k])
        if MT1==0 or MT==MT1 [lookahead=1]:
            [MAT,34,MT/ 0.0, 0.0, MAT1, MT1, NL, NL]CONT
            for n=1 to NL*(NL+1)/2:
                if n == 1:
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n], LCT, NI[n] ]CONT
                else:
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n], 0, NI[n] ]CONT
                endif
                for m=1 to NI[n]:
                    [MAT,34,MT/ 0.0, 0.0, LS[n,m] , LB[n,m], NT[n,m] , NE[n,m] /
                        {Data[n,m,q]}{q=1 to NT[n,m]} ] LIST
                endfor
            endfor
        else:
            [MAT,34,MT/ 0.0, 0.0, MAT1, MT1, NL, NL1]CONT
            for n=1 to NL*NL1:
                if n == 1:
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n], LCT, NI[n] ]CONT
                else:
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n], 0, NI[n] ]CONT
                endif
                for m=1 to NI[n]:
                    [MAT,34,MT/ 0.0, 0.0, LS[n,m] , LB[n,m], NT[n,m] , NE[n,m] /
                        {Data[n,m,q]}{q=1 to NT[n,m]} ] LIST
                endfor
            endfor
        endif
    (/subsection[k])
endfor
SEND
"""
