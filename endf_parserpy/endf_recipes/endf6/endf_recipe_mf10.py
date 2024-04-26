############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/11
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF10 = """
[MAT, 10, MT/ ZA, AWR, LIS, 0, NS, 0]HEAD
for k=1 to NS:
(subsection[k])
    [MAT, 10, MT/ QM, QI, IZAP, LFS, NR, NP/ E / sigma ]TAB1
(/subsection[k])
endfor
SEND
"""
