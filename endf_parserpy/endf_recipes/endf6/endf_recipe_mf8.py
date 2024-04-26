############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/10
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF8 = """
[MAT, 8, MT/ ZA, AWR, LIS, LISO, NS, NO] HEAD
if NO==0:
    for k=1 to NS:
        (subsection[k])
            [MAT, 8, MT/ ZAP, ELFS, LMF, LFS, 6*ND, 0/
            { HL[l] , RTYP[l], ZAN[l] , BR[l] , END[l], CT[l] }{l=1 to ND} ] LIST
        (/subsection[k])
    endfor

elif NO==1:
    for k=1 to NS:
        (subsection[k])
            [MAT, 8, MT/ ZAP, ELFS, LMF, LFS, 0, 0] CONT
        (/subsection[k])
    endfor
endif
SEND
"""
