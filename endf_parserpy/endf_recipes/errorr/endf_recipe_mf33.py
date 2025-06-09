###################################################################
#
# Author(s):       Daniel L. Aldama, Georg Schnabel
# Email:           dlopezaldama@gmail.com
# Creation date:   2025/05/21
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
###################################################################

ENDF_RECIPE_MF33 = """
# MF33 recipe for and ERRORR covariance tape (file) prepared using NJOY2016.
# MF33/MT is used to specify the group averaged covariance matrix.

# var MAT:  Material number
# var MT:   Reaction number according to ENDF conventions
# var ZA:   ZA = (1000.0 * Z) + A = ZA number
#           Z ... charge number of material
#           A ... mass number of material
# var AWR:  Ratio of the mass of the material to that of the neutron
# var MTL:  Non-zero value of MTL is used as a flag to indicate that reaction MT is
#           one component of the evaluator-defined lumped reaction MTL, as discussed
#           in paragraphs at the end of Section 33.2 and 33.3 below; in this case, no
#           covariance information subsections are given for reaction MT and NL=0.
# var NK:   Number of sections (MAT,MT; MAT1,MT1)
#
# var subsection/*/MAT1:      MAT number of the second reaction in the pair
# var subsection/*/MT1:       MT number of the second reaction in the pair
# var subsection/*/NG:        Number of energy groups
# var subsection/*/NG1[i]:    Number of consecutive energy groups for reaction MT1 of MAT1
#                             for which covariances will be given explicitly
# var subsection/*/IG1[i]:    Initial energy group index for reaction MT1 of MAT1
# var subsection/*/IG[i]:     Energy group index of reaction MT of MAT
# var subsection/*/COV[i,j]:  Covariance between the energy group IG[i] of (MAT,MT) and
#                             the energy group IG1[j] of (MAT1,MT1)

# The entry MAT1=0 is a flag to indicate that MAT1=MAT.
# The last row of the covariance matrix is always given explicitly, even if
# it does contain only zeros. The occurrence of the last row terminates a
# given covariance matrix and signals that the next card (line) will name a
# new reaction pair.

[MAT, 33, MT/ ZA, AWR, 0, MTL, 0, NK] CONT
for k=1 to NK:
    (subsection[k])
        [MAT, 33, MT/ 0.0, 0.0, MAT1, MT1, 0, NG] CONT
        repeat [i=1]:
          [MAT, 33, MT/ 0.0, 0.0, NG1[i], IG1[i], NG1[i], IG[i] /
              {COV[i,j]}{j=1 to NG1[i]}] LIST
        until IG[i] == NG
    (/subsection[k])
endfor
SEND
"""
