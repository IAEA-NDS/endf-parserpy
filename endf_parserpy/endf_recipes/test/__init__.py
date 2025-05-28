from ..utils import defdic

# NJOY PENDF specific alterations
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT1
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT2
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT3

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (1, 1), ENDF_RECIPE_MF1_MT1)
defdic(endf_recipe_dictionary, (1, 2), ENDF_RECIPE_MF1_MT2)
defdic(endf_recipe_dictionary, (1, 3), ENDF_RECIPE_MF1_MT3)
