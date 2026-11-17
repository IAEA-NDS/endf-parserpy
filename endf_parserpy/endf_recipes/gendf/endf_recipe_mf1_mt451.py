###################################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
###################################################################

ENDF_RECIPE_MF1_MT451 = """

# MF1/MT451 recipe for a GENDF tape (file) prepared by the NJOY2016
# modules GROUPR (neutron and photon production data) or GAMINR
# (photo-atomic data). The section gives the group structures and the
# sigma zero values of the multigroup data of the material. The number
# -1 in the HEAD record marks the tape as a GENDF tape. The source of
# the layout is the code of the modules (groupr.f90, subroutine groupr,
# the head record of the material; gaminr.f90, subroutine gaminr).
#
# NJOY writes no SEND record after this section, but directly the FEND
# record; the other sections of the material end with their SEND record
# and are not separated by FEND records. The recipe therefore ends without
# SEND, as the tape structure of the flavor (see __init__.py) has it.

# var MAT:     Material number
# var ZA:      ZA = (1000.0 * Z) + A = ZA number
#              Z ... charge number of material
#              A ... mass number of material
# var AWR:     Ratio of the mass of the material to that of the neutron
# var NZ:      Number of sigma zero values (GAMINR: 1)
# var NTW:     Number of title words (always 1)
# var TEMPIN:  Temperature of the processed data in Kelvin (GAMINR: 0)
# var NGN:     Number of groups of the first group structure: the
#              neutron groups (GAMINR: the photon groups)
# var NGG:     Number of photon groups (0 if none, and for GAMINR)
# var TITLE[i]: Title word i (i=1 to NTW); GROUPR writes 0.0, GAMINR
#              the bytes of its title card read as a number, a value
#              without meaning
# var SIGZ[i]: i-th sigma zero value in barn (i=1 to NZ); GAMINR 1e12
# var EGN[i]:  i-th group boundary in eV of the first group structure
#              (i=1 to NGN+1, ascending)
# var EGG[i]:  i-th photon group boundary in eV (i=1 to NGG+1); with
#              NGG=0, one value 0.0

[MAT, 1, 451/ ZA, AWR, 0, NZ, -1, NTW] HEAD
[MAT, 1, 451/ TEMPIN, 0.0, NGN, NGG, NTW+NZ+NGN+NGG+2, 0/
    {TITLE[i]}{i=1 to NTW}
    {SIGZ[i]}{i=1 to NZ}
    {EGN[i]}{i=1 to NGN+1}
    {EGG[i]}{i=1 to NGG+1} ] LIST
"""
