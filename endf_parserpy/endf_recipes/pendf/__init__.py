from copy import deepcopy
from ..utils import defdic
from ..endf6 import endf_recipe_dictionary as base_recipe_dictionary

# NJOY PENDF specific alterations
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_mf2_mt152 import ENDF_RECIPE_MF2_MT152
from .endf_recipe_mf2_mt153 import ENDF_RECIPE_MF2_MT153
from .endf_recipe_mf3 import ENDF_RECIPE_MF3
from .endf_recipe_mf6 import ENDF_RECIPE_MF6
from .endf_recipe_mf23 import ENDF_RECIPE_MF23

endf_recipe_dictionary = deepcopy(base_recipe_dictionary)
defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)
defdic(endf_recipe_dictionary, (2, 152), ENDF_RECIPE_MF2_MT152)
defdic(endf_recipe_dictionary, (2, 153), ENDF_RECIPE_MF2_MT153)
defdic(endf_recipe_dictionary, (3,), ENDF_RECIPE_MF3)
defdic(endf_recipe_dictionary, (6,), ENDF_RECIPE_MF6)
defdic(endf_recipe_dictionary, (23,), ENDF_RECIPE_MF23)
