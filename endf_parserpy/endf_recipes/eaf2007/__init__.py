from copy import deepcopy
from ..utils import defdic

from ..endf6 import endf_recipe_dictionary as base_recipe_dictionary
from .endf_recipe_mf3 import ENDF_RECIPE_MF3


endf_recipe_dictionary = deepcopy(base_recipe_dictionary)
defdic(endf_recipe_dictionary, (3,), ENDF_RECIPE_MF3)
