from ..utils import defdic

# arithmetic of expressions
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT1
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT2
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT3
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT4
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT5
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT6
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT7
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT8
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT9
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT10
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT11
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT12
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT13
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT14
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT15
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT16
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT17
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT18
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT19
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT20
from .endf_recipe_mf2 import ENDF_RECIPE_MF2_MT21

# variables in if-conditions that may not have been read
from .endf_recipe_mf3 import ENDF_RECIPE_MF3_MT1
from .endf_recipe_mf3 import ENDF_RECIPE_MF3_MT2
from .endf_recipe_mf3 import ENDF_RECIPE_MF3_MT3

# NJOY PENDF specific alterations
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT1
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT2
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT3
from .endf_recipe_mf1 import ENDF_RECIPE_MF1_MT4

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (2, 1), ENDF_RECIPE_MF2_MT1)
defdic(endf_recipe_dictionary, (2, 2), ENDF_RECIPE_MF2_MT2)
defdic(endf_recipe_dictionary, (2, 3), ENDF_RECIPE_MF2_MT3)
defdic(endf_recipe_dictionary, (2, 4), ENDF_RECIPE_MF2_MT4)
defdic(endf_recipe_dictionary, (2, 5), ENDF_RECIPE_MF2_MT5)
defdic(endf_recipe_dictionary, (2, 6), ENDF_RECIPE_MF2_MT6)
defdic(endf_recipe_dictionary, (2, 7), ENDF_RECIPE_MF2_MT7)
defdic(endf_recipe_dictionary, (2, 8), ENDF_RECIPE_MF2_MT8)
defdic(endf_recipe_dictionary, (2, 9), ENDF_RECIPE_MF2_MT9)
defdic(endf_recipe_dictionary, (2, 10), ENDF_RECIPE_MF2_MT10)
defdic(endf_recipe_dictionary, (2, 11), ENDF_RECIPE_MF2_MT11)
defdic(endf_recipe_dictionary, (2, 12), ENDF_RECIPE_MF2_MT12)
defdic(endf_recipe_dictionary, (2, 13), ENDF_RECIPE_MF2_MT13)
defdic(endf_recipe_dictionary, (2, 14), ENDF_RECIPE_MF2_MT14)
defdic(endf_recipe_dictionary, (2, 15), ENDF_RECIPE_MF2_MT15)
defdic(endf_recipe_dictionary, (2, 16), ENDF_RECIPE_MF2_MT16)
defdic(endf_recipe_dictionary, (2, 17), ENDF_RECIPE_MF2_MT17)
defdic(endf_recipe_dictionary, (2, 18), ENDF_RECIPE_MF2_MT18)
defdic(endf_recipe_dictionary, (2, 19), ENDF_RECIPE_MF2_MT19)
defdic(endf_recipe_dictionary, (2, 20), ENDF_RECIPE_MF2_MT20)
defdic(endf_recipe_dictionary, (2, 21), ENDF_RECIPE_MF2_MT21)
defdic(endf_recipe_dictionary, (3, 1), ENDF_RECIPE_MF3_MT1)
defdic(endf_recipe_dictionary, (3, 2), ENDF_RECIPE_MF3_MT2)
defdic(endf_recipe_dictionary, (3, 3), ENDF_RECIPE_MF3_MT3)
defdic(endf_recipe_dictionary, (1, 1), ENDF_RECIPE_MF1_MT1)
defdic(endf_recipe_dictionary, (1, 2), ENDF_RECIPE_MF1_MT2)
defdic(endf_recipe_dictionary, (1, 3), ENDF_RECIPE_MF1_MT3)
defdic(endf_recipe_dictionary, (1, 4), ENDF_RECIPE_MF1_MT4)
