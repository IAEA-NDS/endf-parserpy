############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/03
# Last modified:   2024/04/26
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from .endf_recipe_mf33 import ENDF_RECIPE_MF33

# Same recipe as for MF33 (only 33 in MT slot replaced by 31)
# TODO: Sponatenous fission case not covered yet
#       but I did not find files that use that option.

ENDF_RECIPE_MF31_MT452_455_456 = re.sub(
    r" *\[ *MAT *, *33 *, *MT */", "[MAT, 31, MT /", ENDF_RECIPE_MF33
)
