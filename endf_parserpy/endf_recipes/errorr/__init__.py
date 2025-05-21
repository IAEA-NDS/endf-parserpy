from copy import deepcopy
from ..utils import defdic

# NJOY PENDF specific alterations
from .endf_recipe_mf0_mt0 import ENDF_RECIPE_MF0_MT0
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_mf3 import ENDF_RECIPE_MF3
from .endf_recipe_mf33 import ENDF_RECIPE_MF33

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (0, 0), ENDF_RECIPE_MF0_MT0)
defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)
defdic(endf_recipe_dictionary, (3,), ENDF_RECIPE_MF3)
defdic(endf_recipe_dictionary, (33,), ENDF_RECIPE_MF33)
