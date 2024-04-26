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

ENDF_RECIPE_MF35 = """
[MAT,35,MT/ ZA, AWR, 0, 0, NK, 0] HEAD
for k=1 to NK:
    (subsection[k])
        if LS==1 and LB==7 [lookahead=1]:
            [MAT,35,MT/ E1 , E2, LS, LB, NT, NE/
                {E[i]}{i=1 to NE}, {{F[i,j]}{j=i to NE-1}}{i=1 to NE-1} ] LIST
        endif
    (/subsection[k])
endfor
SEND
"""
