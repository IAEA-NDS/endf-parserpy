############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/03
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from .endf_recipe_mf33 import ENDF_RECIPE_MF33

# Same recipe as for MF33 (only 33 in MT slot replaced by 31)
#
# The subsubsections for spontaneous fission (ENDF-102, Section 31.2)
# carry no energy dependence but are special cases of the
# particle-induced formats and are therefore also covered:
#   - NC-type, LTY=0: E1 = E2 = 0.0
#   - NC-type, LTY=1,2,3: NEI=1 with E[1]=0.0 and WE[1] = Weight
#   - NI-type, LB=0,1: LT=0 and NP=1 with Ek[1]=0.0 and Fk[1] = F

ENDF_RECIPE_MF31_MT452_455_456 = re.sub(
    r" *\[ *MAT *, *33 *, *MT */", "[MAT, 31, MT /", ENDF_RECIPE_MF33
)
