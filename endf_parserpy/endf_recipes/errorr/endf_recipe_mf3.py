###################################################################
#
# Author(s):       Daniel L. Aldama, Georg Schnabel
# Email:           dlopezaldama@gmail.com
# Creation date:   2025/05/21
# Last modified:   2025/05/22
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
###################################################################

ENDF_RECIPE_MF3 = """
# MF3 recipe for an ERRORR covariance tape (file) prepared using NJOY2016
# MF3/MT  is used to specify the group averaged cross sections.

# var MAT:     Material number
# var MT:      Reaction number according to ENDF convention
# var ZA:      ZA = (1000.0 * Z) + A = ZA number
#              Z ... charge number of material
#              A ... mass number of material
# var AWR:     Ratio of the mass of the material to that of the neutron
# var NG:      Number of energy groups
# var SIG[i]:  Averaged cross section of i-th group in barns (SIG(i), i=1 to NG)

[MAT, 3, MT/ ZA, 0.0?, 0, 0, NG, 0 /
  {SIG[i]}{i=1 to NG}] LIST
SEND
"""
