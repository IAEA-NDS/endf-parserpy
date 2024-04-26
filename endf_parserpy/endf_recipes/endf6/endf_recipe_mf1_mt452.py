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

ENDF_RECIPE_MF1_MT452 = """

[MAT, 1, 452/ ZA, AWR, 0, LNU, 0, 0]HEAD
if LNU == 1:
    [MAT, 1, 452/ 0.0, 0.0, 0, 0, NC, 0/ {C[k]}{k=1 to NC} ] LIST
elif LNU == 2:
    [MAT, 1, 452/ 0.0, 0.0, 0, 0, NR, NP/ Eint / nu ]TAB1
endif
SEND
"""
