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

ENDF_RECIPE_MF2_MT152 = """

# The specially-defined section MF2/MT152 for PENDF tapes contains the
# Bondarenko tables of self-shielded cross sections in the unresolved
# resonance region(URR)
#
# var ZA:   ZA = (1000.0 * Z) + A
#           Z ... charge number of material
#           A ... mass number of material
#
# var AWR:  ratio of the mass of the material to that of the neutron
#
# var LSSF: flag for ruling the use of self-shielded data given in MF2/MT152
#           LSSF=0 The given cross section values should be used directly as
#                  self-shielded cross-sections in the URR
#           LSSF=1 The given cross section values should be used to compute
#                  the self-shielding factor that must be applied to the
#                  cross section given in File 3(MF3) in the URR
#
# var INTUNR: ENDF-6 interpolation law for the incident energy grid in the URR
#
# var TEMZ: temperature in Kelvin
#
# var NREAC: Number of cross sections types (NREAC=5)
#
# var NSIGZ: Number of Bondarenko's lumped cross sections (sigma0s) for
#            describing self-shielding in MF2/MT152
#
# var NUNR: Number of incident energy nodes in URR
#
# var NW: Number of elements in the LIST record
#         NW=NSIGZ+NUNR*(1+NREAC*NSIGZ)=NSIGZ+NUNR*(1+5*NSIGZ)
#
# var SIGZ[i]: j-th Bondarenko's lumped cross section in barns (sigma0 value)
#              SIGZ(1)=1.0E10 implies infinite dilution
#
# var EUNR[i]: incident energy value in eV for the i-th energy node
#
# var STOT[i,j]: self-shielded total cross section for the j-th bin
#                and the i-th energy node
#
# var SELAS[i,j]: self-shielded elastic cross section for the j-th bin
#                and the i-th energy node
#
# var SFIS[i,j]: self-shielded fission cross section for the j-th bin
#                and the i-th energy node
#
# var SCAP[i,j]: self-shielded capture cross section for the j-th bin
#                and the i-th energy node
#
# var STRN[i,j]: self-shielded current-weighted total cross section for
#                the j-th bin and the i-th energy node
#

[MAT, 2,152/ ZA, AWR, LSSF, 0, 0, INTUNR]HEAD
 NW := NSIGZ+NUNR*(1+5*NSIGZ)
[MAT, 2, 152/ TEMZ, 0, 5, NSIGZ, NW, NUNR /
    {SIGZ[j]}{j=1 to NSIGZ},
    {EUNR[i], {STOT[i,j]}{j=1 to NSIGZ},
              {SELAS[i,j]}{j=1 to NSIGZ},
              {SFIS[i,j]}{j=1 to NSIGZ},
              {SCAP[i,j]}{j=1 to NSIGZ},
              {STRN[i,j]}{j=1 to NSIGZ}}{i=1 to NUNR} ] LIST
SEND
"""
