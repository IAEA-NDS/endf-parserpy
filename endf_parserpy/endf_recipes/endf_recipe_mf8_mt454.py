############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/10
# Last modified:   2022/09/10
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF8_MT454 = """

[MAT, 8, MT/ ZA, AWR, LE+1, 0, 0, 0]HEAD
[MAT, 8, MT/ E[0], 0.0, LE, 0, NN[0], NFP[0]/
    {ZAFP[0,m], FPS[0,m], YI[0,m], DYI[0,m]}{m=1 to NFP[0]} ]LIST
for k=1 to LE:
    [MAT, 8, MT/ E[k], 0.0, I[k], 0, NN[k], NFP[k]/
        {ZAFP[k,m], FPS[k,m], YI[k,m], DYI[k,m]}{m=1 to NFP[k]} ]LIST
endfor
SEND
"""
