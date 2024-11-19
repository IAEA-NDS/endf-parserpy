###################################################################
#
# Author(s):       Georg Schnabel & Daniel L. Aldama
# Email:           g.schnabel@iaea.org, dlopezaldama@gmail.com
# Creation date:   2024/11/15
# Last modified:   2024/11/16
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
###################################################################

ENDF_RECIPE_MF1_MT451 = """

# Description of file MF1 for a PENDF tape prepared by NJOY.
# A PENDF is a kind of tape where the cross sections have been
# reconstructed from resonance parameters in MF2/MT151, linearized
# and written back to the corresponding MF/MT section.
# The parameter LRP in MF1/MT451 is set equal to 2.
# The directory information is updated.
# The PENDF tape could include several temperatures.
# Each temperature is treated as a new material instance (MAT,TEMP) on the tape.
# The following sections could be available for each (MAT,TEMP) instance:
# MF1/MT451:  A modified version of the ENDF-6 MF1/MT451 section prepared by
#             RECONR and made available for others NJOY modules.
#             Includes an updated directory.
# MF2/MT151:  A simple version of MF2/MT151 prepared by RECONR containing the
#             scattering radius. No resonance data available.
# MF2/MT152:  Special section for self-shielded cross sections in the unresolved
#             resonance region(URR) prepared by RECONR or UNRESR or PURR.
# MF2/MT153:  Special section for probability tables used for self-shielding in
#             the unresolved resonance region prepared by PURR
# MF3/MTx:    Pointwise lin-lin interpolable cross sections including resonance
#             contribution prepared by RECONR or Doppler broadened cross
#             sections prepared by BROADR or heating data by HEATR or gas
#             production data by GASPR.
# MF4/MTx:    Angular distribution data reconstructed from the resonance
#             parameters by RECONR, if the option is available and requested
# MF6/MTx:    thermal scatering cross section reconstructed by THERMR from the
#             corresponding thermal scattering law (TSL). The section could use
#             special NJOY formats for MF6
# MF10/MTx:   cross sections for production of radiactive nuclides written
#             by RECONR
# MF12/MTx:   photon production multiplicities (LO=1) written by RECONR
# MF13/MTx:   photon production cross sections written by RECONR
# MF23/MTx:   photoatomic cross sections written by RECONR
#
# var ZA:     ZA = (1000.0 * Z) + A
#             Z ... charge number of material
#             A ... mass number of material
# var AWR:    ratio of the mass of the material to that of the neutron
# var LRP:    Flag indicating whether resolved and/or unresolved
#             resonance parameters are given in File 2
#             LRP=-1, no File 2 is given (not allowed for incident neutrons);
#             LRP=0, no resonance parameter data are given, but a File 2
#             is present containing the effective scattering radius;
#             LRP=1, resolved and/or unresolved parameter data are given
#             in File 2 and cross sections computed from them must be added
#             to background cross sections given in File 3;
#             LRP=2, parameters are given in File 2, but cross sections derived
#             from them are not to be added to the cross sections in File 3. The
#             option LRP=2 is to be used for derived files only and is typical in
#             the so-called PENDF files, in which the cross sections are already
#             reconstructed from the resonances parameters and written in File 3.
# var LFI:    Flag indicating whether this material fissions:
#             LFI=0, this material does not fission;
#             LFI=1, this material fissions.
# var NLIB:   Library identifier (e.g. NLIB= 0 for ENDF/B). Additional
#             values have been assigned to identify other libraries using
#             ENDF format. See Section 0.3.1 for details.
# var NMOD:   Modification number for this material:
#             NMOD=0, evaluation converted from a previous version;
#             NMOD=1, new or revised evaluation for the current library version;
#             NMOD≥ 2, for successive modifications
# var ELIS:   Excitation energy of the target nucleus relative to 0.0 for the
#             ground state.
# var STA:    Target stability flag:
#             STA=0, stable nucleus;
#             STA=1 unstable nucleus. If the target is unstable, radioactive decay data
#             should be given in the decay data sub-library (NSUB=4).
# var LIS:    State number of the target nucleus. The ground state is indicated by LIS=0.
# var LISO:   Isomeric state number. The ground state is indicated by LISO=0. LIS is
#             greater than or equal to LISO.
# var NFOR:   Library format.
#             NFOR=6 for all libraries prepared according to the specifications
#             given in this manual.
# var AWI:    Mass of the projectile in neutron mass units. For incident photons or decay
#             data sub-libraries, use AWI=0.
# var EMAX:   Upper limit of the energy range for evaluation.
# var LREL:   Library release number; for example, LREL=2 for the ENDF/B-VI.2 library.
# var NSUB:   Sub-library number. See Table 3 in Section 0.3.1 for a description
#             of sublibraries.
# var NVER:   Library version number; for example, NVER=7 for version ENDF/B-VII.
# var TEMP:   Target temperature (Kelvin) for data that have been generated by
#             Doppler broadening.
# var TOL:    Fractional tolerance used for resonance reconstruction and
#             cross sections linearization. (TOL=0.0 means unknown tolerance)
# var LDRV:   Special derived material flag that distinguishes between different evaluations
#             with the same material keys (i.e., MAT, NMOD, NSUB):
#             LDRV=0, primary evaluation:
#             LDRV≥ 1, special derived evaluation (for example, a dosimetry evaluation
#             using sections (MT) extracted from the primary evaluation).
# var NWD:    Number of records with descriptive text for this material.
#             Each record contains up to 66 characters.
# var NXC:    Number of records in the directory for this material. Each section (MT) in
#             the material has a corresponding line in the directory that contains MF, MT,
#             NC, and MOD. NC is a count of the number of records in the section (not
#             including SEND), and MOD is the modification flag (see below).
# var DESCRIPTION[i]: Lines with descriptive text
# var MFx[i]: ENDF file number of the i-th section
# var MTx[i]: ENDF reaction designation of the i-th section.
# var NCx[i]: Number of records in the i-th section.
#             This count does not include the SEND record.
# var MOD[i]: Modification indicator for the i-th section.
#             The value of MOD[i] is equal to NMOD if the corresponding section
#             was changed in this revision. MOD[i] must always be less than
#             or equal to NMOD.
#

[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, TOL, LDRV, 0, NWD, NXC]CONT
for i=1 to NWD:
    [MAT, 1,451/ DESCRIPTION[i]]TEXT
endfor
for i=1 to NXC:
    [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
endfor
SEND
"""
