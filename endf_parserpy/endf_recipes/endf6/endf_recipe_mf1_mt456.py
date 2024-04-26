############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/11/20
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF1_MT456 = """

[MAT, 1,456/ ZA, AWR, 0, LNU, 0, 0] HEAD
if LNU==2:
    [MAT, 1,456/ 0.0, 0.0, 0, 0, NR, NP/ Eint / nubar_p ]TAB1
elif LNU==1:
    [MAT, 1,456/ 0.0, 0.0, 0, 0, 1, 0/ nubar_p ]LIST
endif
SEND
"""
