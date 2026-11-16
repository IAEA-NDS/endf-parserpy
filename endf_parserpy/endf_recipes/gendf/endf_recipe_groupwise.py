###################################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/16
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
###################################################################

_GROUPWISE_COMMENT = """
# Recipe of a section of multigroup data on a GENDF tape (file) prepared
# by the NJOY2016 modules GROUPR or GAMINR: cross sections and ratio
# quantities (MF3, MF12, MF13, GAMINR MF23), spectra (MF5) and transfer
# matrices (MF6, MF16, MF21 to MF26, GAMINR MF26). The source of the
# layout is the code of the modules (groupr.f90, subroutines groupr and
# displa; gaminr.f90, subroutines gaminr and dspla).
#
# The HEAD record is followed by one LIST record per incident energy
# group IG[i] written. NJOY omits the groups below the threshold, above
# the highest energy of the evaluation and those whose values are all
# zero, but always writes the record of the last group (IG = NGI),
# which ends the section.
#
# The values ANS of a record are in the order of the array ans(il,iz,it)
# of GROUPR: il (Legendre order il-1) varies fastest, then iz (sigma
# zero SIGZ[iz] of MF1/MT451), then it (position). Position it=1 is the
# group flux, the positions it >= 2 the values divided by the flux:
#   - cross sections (MF3, MF12, MF13, MF23): it=2 is the cross section;
#     for the ratio quantities MT251, MT252, MT253, MT452, MT455, MT456
#     (NG2=3), it=2 is the ratio and it=3 the reaction cross section;
#   - transfer matrices: it is the cross section from group IG[i] to the
#     secondary group IG2LO[i]+it-2;
#   - IG2LO[i]=0 (spectrum constant below an energy): it=2 is the total
#     production cross section; the matrix row is this value times the
#     spectrum of the record with IG[i]=0;
#   - IG[i]=0: the spectrum for the secondary groups IG2LO[i]+it-1,
#     without a flux at it=1;
#   - MF5 (one record, IG[i]=NGI): MT18 the spectrum for the groups
#     IG2LO[i]+it-1 without a flux; MT455 (NL = number of families of
#     delayed neutrons) the decay constants at it=1 and the spectra of
#     the families for the groups it-1.

# var MAT:     Material number
# var MT:      Reaction number
# var ZA:      ZA = (1000.0 * Z) + A = ZA number
# var NL:      Number of Legendre orders (MF5/MT455: number of families
#              of delayed neutrons)
# var NZ:      Number of sigma zero values of this section (1 or the NZ
#              of MF1/MT451)
# var LRFLAG:  LR flag of the reaction in MF3 of the evaluation (0 for
#              data not from MF3, and for GAMINR)
# var NGI:     Number of groups of the incident particle
# var TEMPIN:  Temperature in Kelvin (GAMINR: 0), the same in every
#              record of the section
# var IG[i]:   Incident energy group of record i
# var NG2[i]:  Number of positions it of record i
# var IG2LO[i]: Group of the first secondary group of record i, 0 for
#              a production record
# var ANS[i,it,iz,il]: Value of record i at position it, sigma zero iz
#              and Legendre order il-1
"""

_GROUPWISE_RECORDS = """
repeat [i=1]:
    [MAT, MF, MT/ TEMPIN, 0.0, NG2[i], IG2LO[i], NL*NZ*NG2[i], IG[i]/
        {{{ANS[i,it,iz,il]}{il=1 to NL}}{iz=1 to NZ}}{it=1 to NG2[i]} ] LIST
until IG[i] == NGI
SEND
"""

# GROUPR: the second field of the HEAD record is the ZA*10+isomer of
# the product of a nuclide production (izam), else 0
ENDF_RECIPE_GROUPWISE = (
    _GROUPWISE_COMMENT
    + """
# var IZAM:    ZAM of the product for nuclide production (MF3 from
#              MF8, MF9 or MF10 of the evaluation), -1 for fission
#              products, else 0

[MAT, MF, MT/ ZA, IZAM, NL, NZ, LRFLAG, NGI] HEAD
"""
    + _GROUPWISE_RECORDS
)

# MF23 and MF26 are the numbers of the photo-atomic data of GAMINR, which
# writes the AWR into the second field of the HEAD record (GROUPR writes
# 0 there for its triton and residual nucleus production matrices)
ENDF_RECIPE_GROUPWISE_AWR = (
    _GROUPWISE_COMMENT
    + """
# var AWR:     Ratio of the mass of the material to that of the neutron
#              (GAMINR); 0.0 for the production matrices of GROUPR

[MAT, MF, MT/ ZA, AWR, NL, NZ, LRFLAG, NGI] HEAD
"""
    + _GROUPWISE_RECORDS
)


def groupwise_recipe(recipe, mf):
    """Return the recipe of the sections of one MF number.

    The recipes above use MF as a variable. The recipe of each MF gets
    the number itself, so that the recipe of each MF has a text of its
    own: the C++ code generator emits the parse and write functions of
    identical recipe texts only once, specialized for the first MF number
    it meets.
    """
    return recipe.replace("[MAT, MF, MT/", f"[MAT, {mf}, MT/")
