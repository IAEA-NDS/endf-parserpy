endf_spec_mf1_mt451 = \
"""
[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT 
SEND
"""

endf_spec_mf1_mt451_forloop = \
"""
[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT 
for i=1..5:
    [MAT, 1,451/ ABC, DEF, 0, 0, NWD, NXC]CONT 
    for j=1..7:
        [MAT, 1,451/ XY, 0.0, (PI/3)+4, 0, NWD, HA]CONT 
    endfor
endfor
SEND
"""

endf_spec_mf3_mt = \
"""
[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
SEND
"""
