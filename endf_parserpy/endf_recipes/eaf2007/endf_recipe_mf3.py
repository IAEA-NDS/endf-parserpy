############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/08/06
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF3 = """

for i=1 to 2:
    [MAT, 3,MT / DESCRIPTION[i]]TEXT
endfor
[MAT, 3, MT/ ZA, AWR, 0, LFS, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
SEND
"""
