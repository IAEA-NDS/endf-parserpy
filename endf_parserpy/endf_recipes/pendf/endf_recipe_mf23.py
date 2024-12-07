##############################################################
#
# Author(s):       Georg Schnabel & Daniel L. Aldama
# Email:           g.schnabel@iaea.org, dlopezaldama@gmail.com
# Creation date:   2024/11/15
# Last modified:   2024/12/07
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
##############################################################

ENDF_RECIPE_MF23 = """

# Description of MF23 for a PENDF tape. MF23 contains lin-lin interpolable
# cross sections
#
# var ZA:   ZA = (1000.0 * Z) + A
#           Z ... charge number of material
#           A ... mass number of material
#
# var AWR:  ratio of the mass of the material to that of the neutron
#
# var LMTR: flag for redundant reaction, calculated by sum of partials
#           LMTR=99 redundant, 0 otherwise
#
# var EPE:  Subshell binding energy (equal to the photoelectric edge energy)
#           in eV. The value is zero if MT is not in the 534-599 range
#
# var EFL:  Fluorescence yield (eV/photoionization)
#           Value is zero if not a photoelectric subshell ionization cross section
#
# var E:    list of incident energies (eV) associated with the cross sections
# var xs:   list of cross sections (barn)
# var NBT:  list that contains the indices separating the interpolation regions
# var INT:  list with interpolation scheme identifier for the each interpolation region
#

[MAT, 23, MT/ ZA, AWR, 0, LMTR, 0, 0] HEAD
[MAT, 23, MT/ EPE, EFL, 0, 0, NR, NP/ E / xs] TAB1
SEND
"""
