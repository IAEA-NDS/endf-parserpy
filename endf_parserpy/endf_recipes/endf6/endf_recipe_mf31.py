############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/12/14
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF31 = """

[MAT,31, MT/ 0.0, 0.0, 0, LTY, 0, 0]CONT
if LTY==0:
    [MAT,31, MT/ 0.0, 0.0, 0, 0, 2*NCI, NCI/
        {CI[k], XMTI[k]}{k=1 to NCI}]LIST

elif LTY==1 or LTY==2 or LTY==3:
    [MAT,31, MT/ 0.0, 0.0, MATS, MTS, 4, 1/
        XMFS, XLFSS, 0.0, Weight ]LIST

else:
    stop("The variable LTY contains an invalid value")

endif
SEND
"""
