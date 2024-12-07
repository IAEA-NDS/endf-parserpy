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

ENDF_RECIPE_MF2_MT153 = """

# The specially-defined section MF2/MT153 for PENDF tapes contains probability
# tables to describe the self-shielding in the unresolved resonance region(URR)
#
# var ZA:   ZA = (1000.0 * Z) + A
#           Z ... charge number of material
#           A ... mass number of material
#
# var AWR:  ratio of the mass of the material to that of the neutron
#
# var IINEL: inelastic competion flag
#            IINEL=-1 no competion in the URR
#            IINEL=0  more than one reaction competes in the URR
#            IINEL=MT only the reaction defined by MT competes in the URR
#
# var IABSO: absorption competion flag
#            IABSO=-1 no competion in the URR
#            IABSO=0  more than one reaction competes in the URR
#            IABSO=MT only the reaction defined by MT competes in the URR
#
#            In versions of NJOY prior to NJOY-2016.35, IINEL and IABSO were
#            defined in a different way and stored in a single lumped field
#
# var INTUNR: Interpolation law in the unresolved resonance range
#
# var NBIN: Number of the total cross-section bins for the probability tables
#
# var TEMZ: temperature in Kelvin
#
# var LSSF: flag for interpreting the self-shielded data given in MF2/MT153
#           LSSF=0: Probability tables define self-shielded cross sections
#                   in barns
#           LSSF=1: Probability tables define self-shielding factors to be
#                   applied to the corresponding infinite-dilute cross sections
#                   from File 3(MF3)
#
# var NUNR: Number of incident energy nodes in URR
#
# var NW: Number of elements in the LIST record
#         NW=(1+6*NBIN)*NUNR
#
# var EUNR[i]: incident energy value in eV for the i-th energy node
#
# var PROB[i,j]: probability that the total cross section value lies in
#                the j-th bin for the i-th energy node
#
# var TOTL[i,j]: averaged total cross section(LSSS=0) or self-shielding
#                factor(LSSF=1) for the j-th bin and i-th energy node
#
# var ELAS[i,j]: averaged elastic cross section(LSSS=0) or self-shielding
#                factor(LSSF=1) for the j-th bin and i-th energy node
#
# var FISS[i,j]: averaged fission cross section(LSSS=0) or self-shielding
#                factor(LSSF=1) for the j-th bin and i-th energy node
#
# var CAPT[i,j]: averaged capture cross section(LSSS=0) or self-shielding
#                factor(LSSF=1) for the j-th bin and i-th energy node
#
# var HEAT[i,j]: averaged heating numbers(LSSS=0) or self-shielding
#                factor(LSSF=1) for the j-th bin and i-th energy node
#

[MAT, 2,153/ ZA, AWR, IINEL, IABSO, INTUNR, NBIN]HEAD
 NW := (1+6*NBIN)*NUNR
[MAT, 2,153/ TEMZ, 0, LSSF, 0, NW, NUNR /
    {EUNR[i], {PROB[i,j]}{j=1 to NBIN},
              {TOTL[i,j]}{j=1 to NBIN},
              {ELAS[i,j]}{j=1 to NBIN},
              {FISS[i,j]}{j=1 to NBIN},
              {CAPT[i,j]}{j=1 to NBIN},
              {HEAT[i,j]}{j=1 to NBIN}}{i=1 to NUNR} ] LIST
SEND
"""
