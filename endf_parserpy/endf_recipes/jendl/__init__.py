from copy import deepcopy
from ..utils import defdic
from ..endf6 import endf_recipe_dictionary as base_recipe_dictionary

# JENDL-5 specific alterations
from .endf_recipe_mf8_mt457 import ENDF_RECIPE_MF8_MT457


endf_recipe_dictionary = deepcopy(base_recipe_dictionary)
defdic(endf_recipe_dictionary, (8, 457), ENDF_RECIPE_MF8_MT457)
