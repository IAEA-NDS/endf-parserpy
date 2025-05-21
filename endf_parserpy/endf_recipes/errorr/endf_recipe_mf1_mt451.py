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

ENDF_RECIPE_MF1_MT451 = """

# MF1/MT451 recipe for an ERRORR covariance tape (file) prepared using NJOY2016
#
# MF1/MT451 is used to specify the boundaries of the multigroup structure
# used for the processed data. The number -11 in the CONT record below
# indicates that it is an ERRORR covariance output tape containing MF33.

# var MAT:     Material number
# var MT:      Reaction number according to ENDF convention
# var ZA:      ZA = (1000.0 * Z) + A = ZA number
#              Z ... charge number of material
#              A ... mass number of material
# var AWR:     Ratio of the mass of the material to that of the neutron
# var IVER:    Format specification (IVER=6 for ENDF-6)
# var IRELCO:  Flag to indicate whether relative covariance (IRELCO=1)
#              or absolute covariance matrix (IRELCO=0) provided.
#              At present, not implemented by official LANL NJOY2016.
# var TEMPIN:  Temperature of processed data in Kelvin
# var NG:      Number of energy groups (NG+1 energy boundaries)
# var EG[i]:   i-th boundary energy in eV (EG(i), i=1 to NG+1)

[MAT, 1, MT/ ZA, AWR, IVER, IRELCO, -11, 0 ] CONT
[MAT, 1, MT/ TEMPIN, 0.0, NG, 0, NG+1, 0 / {EG[i]}{i=1 to NG+1}] LIST
SEND
"""
