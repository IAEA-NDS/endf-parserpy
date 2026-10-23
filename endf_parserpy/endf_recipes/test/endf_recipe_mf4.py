############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################


# Regular blocks of three trailing indices (see find_block in
# compiler/cpp_types/cpp_type_nested_array/assign.py): with
# array_type="numpy", the block is a numpy array with three dimensions.
# The recipes can be used to check the reading and the writing of such
# arrays in both parsers.


# X[i,j,k] is one block of shape (NI, NJ, NK): the whole variable
ENDF_RECIPE_MF4_MT1 = """
[MAT,MF,MT/ 0.0, 0.0, NI, NJ, NK, 0] HEAD
for i=1 to NI:
    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NW[i], 0/
        {{X[i,j,k]}{k=1 to NK}}{j=1 to NJ} ] LIST
endfor
SEND
"""


# Y[i,j,k,l] is a list of blocks of shape (NJ[i], NK[i], NL[i]),
# one for each i
ENDF_RECIPE_MF4_MT2 = """
[MAT,MF,MT/ 0.0, 0.0, 0, 0, NI, 0] HEAD
for i=1 to NI:
    [MAT,MF,MT/ 0.0, 0.0, NJ[i], NK[i], NL[i], 0] CONT
    for j=1 to NJ[i]:
        [MAT,MF,MT/ 0.0, 0.0, 0, 0, NW[i,j], 0/
            {{Y[i,j,k,l]}{l=1 to NL[i]}}{k=1 to NK[i]} ] LIST
    endfor
endfor
SEND
"""
