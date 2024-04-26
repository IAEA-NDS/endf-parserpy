############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

ENDF_RECIPE_MF3 = """

# var ZA:   ZA = (1000.0 * Z) + A
#           Z ... charge number of material
#           A ... mass number of material
# var AWR:  ratio of the mass of the material to that of the neutron
#
# var QM:   Mass-difference Q value (eV): defined as the mass of the
#           projectile and the ground state of the target minus the
#           mass of the residual nucleus in the ground state and masses
#           of all other reaction products; that is, for the
#           reaction a+A → b+c+...+B,
#
#           QM = [(ma + mA ) − (mb + mc + ... + mB )] × (eV /amu/c2)
#
#           where the masses are atomic masses in amu. (See Section 3.3.2 and
#           Apppendix H for the mass conversion constant).
#
# var QI:   Reaction Q value for the (lowest energy) states defined by the given MT
#           value in a simple two-body reaction or a breakup reaction. For reactions on
#           an excited nucleus (so ELIS>0.0) proceeding to residual nucleus also in an
#           excited state, we have
#
#           QM = [(ma + mA + ELIS) − (mb + mc + ... + mB + Ex )] × (eV /amu/c2)
#
#           Therefore, for a reaction on the ground state of a nucleus (ELIS=0.0), QI is
#           defined as QM for the ground state of the residual nucleus (or intermediate
#           system before breakup) minus the energy of the excited level in this system.
#           Use QI=QM for reactions with no intermediate states in the residual nucleus
#           and without complex breakup (LR=0). (See Section 3.3.2)
#
# var LR:   Complex or “breakup” reaction flag, which indicates that additional
#           particles not specified by the MT number will be emitted.
#           See Sections 0.4.3.4 and 3.4.4.
#
# var xstable/E:    list of incident energies (eV) associated with the cross sections
# var xstable/xs:   list of cross sections (barn)
# var xstable/NBT:  list that contains the indices separating the interpolation regions
# var xstable/INT:  list with interpolation scheme identifier for the each interpolation region


[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
SEND
"""
