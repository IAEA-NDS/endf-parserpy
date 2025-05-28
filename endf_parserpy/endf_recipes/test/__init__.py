from ..utils import defdic

# NJOY PENDF specific alterations
from .endf_recipe_mf1_mt1 import ENDF_RECIPE_MF1_MT1

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (1, 1), ENDF_RECIPE_MF1_MT1)
