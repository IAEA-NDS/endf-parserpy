##############################################################
#
# Author(s):       Georg Schnabel & Daniel L. Aldama
# Email:           g.schnabel@iaea.org, dlopezaldama@gmail.com
# Creation date:   2022/05/30
# Last modified:   2024/12/07
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
##############################################################

ENDF_RECIPE_MF6 = """

# MF6 recipe for a PENDF tape prepared by NJOY
# It can include special MF6 sections for the thermal scattering law (TSL)
#
# var ZA:   ZA = (1000.0 * Z) + A
#           Z ... charge number of material
#           A ... mass number of material
#
# var AWR:  ratio of the mass of the material to that of the neutron
#
# var JP:   An integer that is “overloaded” to provide information about
#           both prompt fission neutrons and photons. When not storing fission
#           observables, set JP=0.
#           JP=JPP*10+JPN where JPP and JPN are flags for photons and neutrons
#           respectively. The flags JPP and JPN take values 0, 1 or 2.
#           For JPX=JPN or JPP:
#
#               - JPX=0  This indicates that the usual MF=6 interpretation
#                        of yi and fi holds.
#
#               - JPX=1  This indicates the probability functions P̃i (ν, E)
#                        for each particle i are given in the spot reserved
#                        for the particle yields yi. In this case, fi is
#                        not given explicitly in MF=6 as is indicated by the
#                        LAW flag. P̃i(ν, E) is the probability of emitting ν
#                        particles of type i divided by the average
#                        multiplicity of particle i as a function of energy.
#
#               - JPX=2  This indicates that only the probability functions
#                        and individual spectra are given. In this case, yi
#                        stores the probability functions P̃i(ν, E), and
#                        fi stores the average spectrum for the ν particles
#                        of type i.
#
#           Note, when JP>0, the LAW values may take unusual, negative,
#           values. In such cases the format is equal to LAW=0, giving only
#           the incident energy-dependent probability table. See the definition
#           of LAW below and Section 6.3.9 for further discussion.
#
# var LCT:  Reference system for secondary energy and angle (incident energy
#           is always given in the LAB system).
#
#               - LCT=1  laboratory (LAB) coordinates used for secondary
#                        energy and angle for all reaction products;
#
#               - LCT=2  center-of-mass (CM) system used for secondary energy
#                        and angle for all reaction products;
#
#               - LCT=3  LCT=3 center-of-mass system for both angle and
#                        secondary energy for light particles (A≤ 4) and
#                        laboratory system for heavy recoils (A>4).
#
#               - LCT=4  center-of-mass system for initial reaction products,
#                        and laboratory system for any subsequent breakup
#                        products. Intended for use with breakup reactions
#                        (see section 0.4.3.4).
#
# var NK:   Number of subsections in this section (MT). Each subsection
#           describes one reaction product. There can be more than one
#           subsection for a given particle or residual nucleus (see LIP).
#           For the limit on NK see Appendix G.
#
# var subsection/*/ZAP:
#           Product identifier 1000 ∗ Z + A with Z = 0 for photons and
#           A = 0 for electrons and positrons. A section with A = 0 can also
#           be used to represent the average recoil energy or spectrum for an
#           elemental target (see text).
#
# var subsection/*/AWP:
#           Product mass in neutron units. When ZAP=0, this field can contain
#           the energy of a primary photon. In that case, this section will
#           contain an angular distribution (LAW=2) for the primary photon.
#
# var subsection/*/LIP:
#           Product modifier flag.
#
#           *Isomeric states*: Its main use is to identify the isomeric state
#           of a product nucleus. In this case, LIP=0 for the ground state,
#           LIP=1 for the first isomeric state, etc. These values should be
#           consistent with LISO in File 8, MT=457.
#
#           *Multiple emission*: In some cases, it may be useful to use LIP
#           to distinguish between different subsections with the same value of
#           ZAP for light particles. For example, LIP=0 could be the first
#           neutron out for a sequential reaction, LIP=1 could be the second
#           neutron, and so on. Other possible uses might be to indicate which
#           compound system emitted the particles, or to distinguish
#           between the neutron from the (n,np) channel and that from the
#           (n,pn) channel. The exact meaning assigned to LIP should be
#           explained in the File 1, MT=451 comments.
#
#           *Fission*: LIP may be used to denote which particle out of
#           ν particles the current set describes. See Section 6.3.9 for
#           further discussion.
#
# var subsection/*/LAW:
#           Flag to distinguish between different representations of the
#           distribution function, fi :
#
#              LAW=0  LIP non negative unknown distribution;
#              LAW=0  LIP=-NBRAGG special case for thermal coherent elastic scattering
#              LAW=1  continuum energy-angle distribution;
#              LAW=1  LIP=-1 special case for thermal inelastic scattering
#              LAW=1  LIP=-2 special case for thermal incoherent elastic scattering
#              LAW=2  two-body reaction angular distribution;
#              LAW=3  isotropic two-body distribution;
#              LAW=4  recoil distribution of a two-body reaction;
#              LAW=5  charged-particle elastic scattering;
#              LAW=6  n-body phase-space distribution; and
#              LAW=7  laboratory angle-energy law.
#              LAW<0  (For Fission only with JP>0) the average particle
#                     distributions are given in MF=4/5 (for neutrons) or
#                     MF=14/15 (for photons). The format here is equivalent
#                     to LAW=0, giving only the incident energy-dependent
#                     probability table. See Sections 6.2.1 and 6.3.9 for
#                     further discussion.


[MAT, 6, MT/ ZA, AWR, JP, LCT, NK, 0]HEAD
for i=1 to NK:
    (subsection[i])
        if LAW == 0 and NBRAGG > 0 [lookahead=1]:

            # special case for thermal coherent elastic scattering (NJOY/THERMR)
            [MAT, 6, MT/ ZAP, AWP, -NBRAGG, LAW, NR, NP/ Eint / yi]TAB1 (yields)
        else:

            [MAT, 6, MT/ ZAP, AWP, LIP, LAW, NR, NP/ Eint / yi]TAB1 (yields)

            if LAW == 1 and LIP != -1 and LIP != -2:

                # var LANG:
                #    Indicator which selects the angular representation
                #    to be used; if
                #        - LANG=1,     Legendre coefficients are used,
                #        - LANG=2,     Kalbach-Mann systematics are used,
                #        - LANG=11-15, a tabulated angular distribution
                #                      is given using NA/2 cosines and the
                #                      interpolation scheme specified
                #                      by LANG-10 (for example, LANG=12
                #                      selects linear-linear interpolation).
                # var LEP:
                #    Interpolation scheme for secondary energy;
                #    LEP=1 for histogram,
                #    LEP=2 for linear-linear, etc.
                #
                # var NE:
                #    Number of secondary energy points given in E
                #
                # var INT:
                #    (TAB2) INT array to specify interpolation
                #    schemes to interpolate between energies in E.
                #
                # var NBT:
                #    (TAB2) NBT array to specify breaks between
                #    interpolation domains associated with E.
                #
                # var NEP:
                #    Number of secondary energy points in the distribution.
                #
                # var ND:
                #     Number of discrete energies given.
                #     The first ND≥0 entries in the list of NEP energies are discrete, and the
                #     remaining (NEP-ND)≥ 0 entries are to be used with LEP to describe a
                #     continuous distribution. Discrete primary photons should be flagged with
                #     negative energies.
                #
                # var NA:
                #     Number of angular parameters.
                #     Use NA=0 for isotropic distributions (note that all options are identical if
                #     NA=0).
                #     Use NA=1 or 2 with LANG=2 (Kalbach-Mann).

                [MAT, 6, MT/ 0.0, 0.0, LANG, LEP, NR, NE/ Eint ]TAB2
                for j=1 to NE:
                    NW := NEP[j] * (NA[j]+2)
                    [MAT, 6, MT/ 0.0, E[j] , ND[j], NA[j], NW, NEP[j]/
                                 {Ep[j,k], {b[j,k,m]}{m=0 to NA[j]}}{k=1 to NEP[j]} ]LIST
                endfor

            # Discrete Two-Body Scattering
            elif LAW == 2:
                [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint ]TAB2
                for j=1 to NE:
                    [MAT, 6, MT/ 0.0, E[j], LANG, 0, NLW[j], NL[j] / {A[j,l]}{l=1 to NLW[j]} ]LIST
                endfor

            # Charged-Particle Elastic Scattering (LAW=5)
            elif LAW == 5:
                [MAT, 6, MT/ SPI, 0.0, LIDP, 0, NR, NE / Eint ]TAB2
                for j=1 to NE:
                    [MAT, 6, MT/ 0.0, E[j] , LTP[j], 0, NW[j], NL[j]/
                                 {A[j,k]}{k=1 to NW[j]} ]LIST
                endfor

            # N-body Phase-Space distribution (LAW=6) (manual 6.2.7, p. 136)
            elif LAW == 6:
                [MAT, 6, MT/ APSX, 0.0, 0, 0, 0, NPSX]CONT

            # Laboratory Angle-Energy Law (LAW=7) (manual 6.2.9, p. 146)
            elif LAW == 7:
                [MAT, 6, MT/ 0.0, 0.0, 0, 0, NR, NE / E]TAB2 (E_interpol)
                for j=1 to NE:
                    [MAT, 6, MT/ 0.0, E[j], 0, 0, NRM, NMU[j] / mu ]TAB2 (mu_interpol[j])
                    for k=1 to NMU[j]:
                        [MAT, 6, MT/ 0.0, mu[j,k] , 0, 0, NRP, NEP / Ep / f ]TAB1 (table[j,k])
                    endfor
                endfor

            # Special case for thermal inelastic scattering (NJOY/THERMR)
            elif LAW == 1 and LIP == -1:
                [MAT, 6, MT/ TEMP, 0.0, 3, 1, NR, NE / E]TAB2 (E_interpol)
                for j=1 to NE:
                    [MAT, 6, MT/ 0.0, E[j], 0, 0, NEP[j]*(NU+2), NU+2/
                                 {Ep[j,k], PDF[j,k], {u[j,k,m]}{m=1 to NU}}{k=1 to NEP[j]} ] LIST
                endfor

            # Special case for thermal incoherent elastic scattering (NJOY/THERMR)
            elif LAW == 1 and LIP == -2:
                [MAT, 6, MT/ TEMP, 0.0, 3, 1, NR, NE / E]TAB2 (E_interpol)
                for j=1 to NE:
                    [MAT, 6, MT/ 0.0, E[j], 0, 0, NU+2, NU+2/
                                E[j], 1.0, {u[j,m]}{m=1 to NU} ] LIST
                endfor
            endif

        endif
    (/subsection[i])
endfor
SEND
"""
