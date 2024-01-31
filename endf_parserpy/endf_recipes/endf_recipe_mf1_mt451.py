############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF1_MT451 = """

[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT

[MAT, 1,451/ ZSYMAM{11}, ALAB{11}, EDATE{10}, {1}, AUTH{33} ]TEXT
[MAT, 1,451/ {1}, REF{21}, DDATE{10}, {1},
             RDATE{10}, {12}, ENDATE{8}, {3} ]TEXT
for i=1 to 3:
    [MAT, 1,451/ HSUB[i]] TEXT
endfor
for i=1 to NWD-5:
    [MAT, 1,451/ DESCRIPTION[i]]TEXT
endfor
for i=1 to NXC:
    [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
endfor
SEND
"""
