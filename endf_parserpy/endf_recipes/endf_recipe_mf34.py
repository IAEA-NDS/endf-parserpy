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
            if MT == MT1:
                for j=n to NL1:
                    # QUESTION: The NI variable is quite pointless, isn't it?
                    # According to ENDF manual: NI ...Number of LIST records in this
                    # sub-subsection.
                    # If a sub-subsection is given by the two records below, there
                    # is always exactly one LIST record.
                    # TODO: Need to check the meaning of NI.
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n,j], LCT, NI[n] ]CONT
                    [MAT,34,MT/ 0.0, 0.0, LS[n,j] , LB[n,j], NT[n,j] , NE[n,j] /
                        {Data[n,j,q]}{q=1 to NT[n,j]} ] LIST
                endfor
            else:
                for j=1 to NL1:
                    [MAT,34,MT/ 0.0, 0.0, L[n] , L1[n,j], LCT, NI[n] ]CONT
                    [MAT,34,MT/ 0.0, 0.0, LS[n,j] , LB[n,j], NT[n,j] , NE[n,j] /
                        {Data[n,j,q]}{q=1 to NT[n,j]} ] LIST
                endfor
            endif
        endfor
    (/subsection[k])
endfor
SEND
"""
