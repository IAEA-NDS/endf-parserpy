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

# regular blocks of three trailing indices (array_type="numpy")
from .endf_recipe_mf4 import ENDF_RECIPE_MF4_MT1
from .endf_recipe_mf4 import ENDF_RECIPE_MF4_MT2

# lengths of the text fields of TEXT records
from .endf_recipe_mf6 import ENDF_RECIPE_MF6_MT1
from .endf_recipe_mf6 import ENDF_RECIPE_MF6_MT2
from .endf_recipe_mf6 import ENDF_RECIPE_MF6_MT3

# abbreviations defined in a branch of an if-clause
from .endf_recipe_mf5 import ENDF_RECIPE_MF5_MT1

# elements of array variables in loops (accessors of the C++ writer)
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT1
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT2
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT3
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT4
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT5
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT6

# variables assigned values of different types (type checks)
from .endf_recipe_mf8 import ENDF_RECIPE_MF8_MT1
from .endf_recipe_mf8 import ENDF_RECIPE_MF8_MT2
from .endf_recipe_mf8 import ENDF_RECIPE_MF8_MT3

# values of INTG records in loops (array_type="numpy")
from .endf_recipe_mf9 import ENDF_RECIPE_MF9_MT1
from .endf_recipe_mf9 import ENDF_RECIPE_MF9_MT2
from .endf_recipe_mf9 import ENDF_RECIPE_MF9_MT3
from .endf_recipe_mf9 import ENDF_RECIPE_MF9_MT4
from .endf_recipe_mf9 import ENDF_RECIPE_MF9_MT5

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
defdic(endf_recipe_dictionary, (4, 1), ENDF_RECIPE_MF4_MT1)
defdic(endf_recipe_dictionary, (4, 2), ENDF_RECIPE_MF4_MT2)
defdic(endf_recipe_dictionary, (6, 1), ENDF_RECIPE_MF6_MT1)
defdic(endf_recipe_dictionary, (6, 2), ENDF_RECIPE_MF6_MT2)
defdic(endf_recipe_dictionary, (6, 3), ENDF_RECIPE_MF6_MT3)
defdic(endf_recipe_dictionary, (5, 1), ENDF_RECIPE_MF5_MT1)
defdic(endf_recipe_dictionary, (7, 1), ENDF_RECIPE_MF7_MT1)
defdic(endf_recipe_dictionary, (7, 2), ENDF_RECIPE_MF7_MT2)
defdic(endf_recipe_dictionary, (7, 3), ENDF_RECIPE_MF7_MT3)
defdic(endf_recipe_dictionary, (7, 4), ENDF_RECIPE_MF7_MT4)
defdic(endf_recipe_dictionary, (7, 5), ENDF_RECIPE_MF7_MT5)
defdic(endf_recipe_dictionary, (7, 6), ENDF_RECIPE_MF7_MT6)
defdic(endf_recipe_dictionary, (8, 1), ENDF_RECIPE_MF8_MT1)
defdic(endf_recipe_dictionary, (8, 2), ENDF_RECIPE_MF8_MT2)
defdic(endf_recipe_dictionary, (8, 3), ENDF_RECIPE_MF8_MT3)
defdic(endf_recipe_dictionary, (9, 1), ENDF_RECIPE_MF9_MT1)
defdic(endf_recipe_dictionary, (9, 2), ENDF_RECIPE_MF9_MT2)
defdic(endf_recipe_dictionary, (9, 3), ENDF_RECIPE_MF9_MT3)
defdic(endf_recipe_dictionary, (9, 4), ENDF_RECIPE_MF9_MT4)
defdic(endf_recipe_dictionary, (9, 5), ENDF_RECIPE_MF9_MT5)
