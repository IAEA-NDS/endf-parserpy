from ..utils import defdic

# GENDF tapes of the NJOY2016 modules GROUPR and GAMINR
from .endf_recipe_mf0_mt0 import ENDF_RECIPE_MF0_MT0
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_groupwise import (
    ENDF_RECIPE_GROUPWISE,
    ENDF_RECIPE_GROUPWISE_AWR,
    groupwise_recipe,
)

# the MF numbers that GROUPR (3, 5, 6, 12, 13, 16, 21 to 26) and GAMINR
# (23, 26) write
GROUPWISE_MF = (3, 5, 6, 12, 13, 16, 21, 22, 24, 25)
GROUPWISE_AWR_MF = (23, 26)

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (0, 0), ENDF_RECIPE_MF0_MT0)
defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)
for _mf in GROUPWISE_MF:
    defdic(endf_recipe_dictionary, (_mf,), groupwise_recipe(ENDF_RECIPE_GROUPWISE, _mf))
for _mf in GROUPWISE_AWR_MF:
    defdic(
        endf_recipe_dictionary, (_mf,), groupwise_recipe(ENDF_RECIPE_GROUPWISE_AWR, _mf)
    )
