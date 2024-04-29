from copy import deepcopy
from ..utils import defdic

from ..endf6 import endf_recipe_dictionary as base_recipe_dictionary
from ..jendl.endf_recipe_mf8_mt457 import ENDF_RECIPE_MF8_MT457
from .endf_recipe_mf4 import ENDF_RECIPE_MF4


endf_recipe_dictionary = deepcopy(base_recipe_dictionary)
defdic(endf_recipe_dictionary, (8, 457), ENDF_RECIPE_MF8_MT457)
defdic(endf_recipe_dictionary, (4,), ENDF_RECIPE_MF4)
