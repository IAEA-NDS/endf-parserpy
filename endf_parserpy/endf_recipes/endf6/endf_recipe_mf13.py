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

ENDF_RECIPE_MF13 = """
[MAT, 13, MT/ ZA, AWR, 0, 0, NK, 0]HEAD
if NK>1:
    [MAT, 13, MT/ 0.0, 0.0, 0, 0, NR, NP/ E / sigma_tot ] TAB1
endif
for k=1 to NK:
(subsection[k])
    [MAT, 13, MT/ EG , ES , LP, LF, NR, NP/ E / sigma ] TAB1
(/subsection[k])
endfor
SEND
"""
