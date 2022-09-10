from .endf_recipe_mf0_mt0 import ENDF_RECIPE_MF0_MT0_TAPEHEAD
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_mf2_mt151 import ENDF_RECIPE_MF2_MT151
from .endf_recipe_mf3 import ENDF_RECIPE_MF3
from .endf_recipe_mf4 import ENDF_RECIPE_MF4
from .endf_recipe_mf5 import ENDF_RECIPE_MF5
from .endf_recipe_mf6 import ENDF_RECIPE_MF6
from .endf_recipe_mf8 import ENDF_RECIPE_MF8
from .endf_recipe_mf8_mt454 import ENDF_RECIPE_MF8_MT454
from .endf_recipe_mf8_mt457 import ENDF_RECIPE_MF8_MT457
from .endf_recipe_mf8_mt459 import ENDF_RECIPE_MF8_MT459
from .endf_recipe_mf12 import ENDF_RECIPE_MF12
from .endf_recipe_mf14 import ENDF_RECIPE_MF14
from .endf_recipe_mf15 import ENDF_RECIPE_MF15

# helper function to create a nested dictionary
def __defdic(dic, index, recipe):
    curdic = dic
    for idx in index[:-1]:
        curdic = curdic.setdefault(idx, {})
    curdic[index[-1]] = recipe

# create a nested dictionary with all the
# endf recipes to read and write the various mf/mt sections.
# both (MF,) and (MF,-1) defines a recipe for the complete MF section.
# The second option allows to define special recipes for MT sections,
# see e.g. MF8 recipes below.
endf_recipe_dictionary = {}
__defdic(endf_recipe_dictionary, ( 0,   0), ENDF_RECIPE_MF0_MT0_TAPEHEAD)
__defdic(endf_recipe_dictionary, ( 1, 451), ENDF_RECIPE_MF1_MT451)
__defdic(endf_recipe_dictionary, ( 2, 151), ENDF_RECIPE_MF2_MT151)
__defdic(endf_recipe_dictionary, ( 3,    ), ENDF_RECIPE_MF3)
__defdic(endf_recipe_dictionary, ( 4,    ), ENDF_RECIPE_MF4)
__defdic(endf_recipe_dictionary, ( 5,    ), ENDF_RECIPE_MF5)
__defdic(endf_recipe_dictionary, ( 6,    ), ENDF_RECIPE_MF6)
__defdic(endf_recipe_dictionary, ( 8,  -1), ENDF_RECIPE_MF8)
__defdic(endf_recipe_dictionary, ( 8, 454), ENDF_RECIPE_MF8_MT454)
__defdic(endf_recipe_dictionary, ( 8, 457), ENDF_RECIPE_MF8_MT457)
__defdic(endf_recipe_dictionary, ( 8, 459), ENDF_RECIPE_MF8_MT459)
__defdic(endf_recipe_dictionary, (12,    ), ENDF_RECIPE_MF12)
__defdic(endf_recipe_dictionary, (14,    ), ENDF_RECIPE_MF14)
__defdic(endf_recipe_dictionary, (15,    ), ENDF_RECIPE_MF15)

