spec_dic = {} 

spec_dic.setdefault(1, {})
spec_dic[1][451] = \
"""
[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT 
for i=1 to NWD:
    [MAT, 1,451/ DESCRIPTION[i]]TEXT
endfor
for i=1 to NXC:
    [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
endfor
"""

spec_dic.setdefault(3, {})
spec_dic[3] = \
"""
[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
"""

# TODO: remove after successful development
spec_dic.setdefault(99, {})
spec_dic[99] = \
"""
[MAT,99, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT,99, MT/ A, B, C, D, E, F / 
   {{U[i,j]}{i=1 to 3}}{j=1 to 3}, bla
]LIST
"""

spec_dic.setdefault(98, {})
spec_dic[98] = \
"""
[MAT,98, MT/ ZA*3, 5*ZA, 5+6*6/6-11, 0, 0, 0] HEAD
"""
