############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

# Text fields of TEXT records: a single field without a length spans the
# 66 text columns, otherwise the lengths of the fields add up to 66.

ENDF_RECIPE_MF6_MT1 = """
[MAT, 6, MT/ A{33}, B{33} ]TEXT
SEND
"""

ENDF_RECIPE_MF6_MT2 = """
[MAT, 6, MT/ {10}, A{56} ]TEXT
SEND
"""

ENDF_RECIPE_MF6_MT3 = """
[MAT, 6, MT/ HL ]TEXT
SEND
"""
