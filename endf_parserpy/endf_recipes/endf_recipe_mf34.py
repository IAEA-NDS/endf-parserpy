############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/12
# Last modified:   2022/09/12
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF34 = """
[MAT,34,MT/ ZA, AWR, 0, LTT, 0, NMT1]HEAD
for k=1 to NMT1:
    (subsection[k])
        [MAT,34,MT/ 0.0, 0.0, MAT1, MT1, NL, NL1]CONT
        for n=1 to NL: 
            [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n], LCT, NI[n] ]CONT
            for j=1 to NI[n]:
                [MAT,34,MT/ 0.0, 0.0, LS[n,j] , LB[n,j], NT[n,j] , NE[n,j] / 
                    {Data[n,j,q]}{q=1 to NT[n,j]} ] LIST
            endfor
        endfor
    (/subsection[k])
endfor
SEND
"""
