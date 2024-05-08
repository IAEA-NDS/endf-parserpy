from ..utils import defdic

from .endf_recipe_mf0_mt0 import ENDF_RECIPE_MF0_MT0_TAPEHEAD
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_mf1_mt452 import ENDF_RECIPE_MF1_MT452
from .endf_recipe_mf1_mt455 import ENDF_RECIPE_MF1_MT455
from .endf_recipe_mf1_mt456 import ENDF_RECIPE_MF1_MT456
from .endf_recipe_mf1_mt458 import ENDF_RECIPE_MF1_MT458
from .endf_recipe_mf1_mt460 import ENDF_RECIPE_MF1_MT460
from .endf_recipe_mf2_mt151 import ENDF_RECIPE_MF2_MT151
from .endf_recipe_mf3 import ENDF_RECIPE_MF3
from .endf_recipe_mf4 import ENDF_RECIPE_MF4
from .endf_recipe_mf5 import ENDF_RECIPE_MF5
from .endf_recipe_mf6 import ENDF_RECIPE_MF6
from .endf_recipe_mf7 import ENDF_RECIPE_MF7_MT2, ENDF_RECIPE_MF7_MT4, ENDF_RECIPE_MF7_MT451
from .endf_recipe_mf8 import ENDF_RECIPE_MF8
from .endf_recipe_mf8_mt454 import ENDF_RECIPE_MF8_MT454
from .endf_recipe_mf8_mt457 import ENDF_RECIPE_MF8_MT457
from .endf_recipe_mf8_mt459 import ENDF_RECIPE_MF8_MT459
from .endf_recipe_mf9 import ENDF_RECIPE_MF9
from .endf_recipe_mf10 import ENDF_RECIPE_MF10
from .endf_recipe_mf12 import ENDF_RECIPE_MF12
from .endf_recipe_mf13 import ENDF_RECIPE_MF13
from .endf_recipe_mf14 import ENDF_RECIPE_MF14
from .endf_recipe_mf15 import ENDF_RECIPE_MF15
from .endf_recipe_mf23 import ENDF_RECIPE_MF23
from .endf_recipe_mf26 import ENDF_RECIPE_MF26
from .endf_recipe_mf27 import ENDF_RECIPE_MF27
from .endf_recipe_mf28 import ENDF_RECIPE_MF28
from .endf_recipe_mf31_mt452_455_456 import ENDF_RECIPE_MF31_MT452_455_456
from .endf_recipe_mf32 import ENDF_RECIPE_MF32
from .endf_recipe_mf33 import ENDF_RECIPE_MF33
from .endf_recipe_mf34 import ENDF_RECIPE_MF34
from .endf_recipe_mf35 import ENDF_RECIPE_MF35
from .endf_recipe_mf40 import ENDF_RECIPE_MF40


# create a nested dictionary with all the
# endf recipes to read and write the various mf/mt sections.
# both (MF,) and (MF,-1) defines a recipe for the complete MF section.
# The second option allows to define special recipes for MT sections,
# see e.g. MF8 recipes below.
endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (0, 0), ENDF_RECIPE_MF0_MT0_TAPEHEAD)
defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)
defdic(endf_recipe_dictionary, (1, 452), ENDF_RECIPE_MF1_MT452)
defdic(endf_recipe_dictionary, (1, 455), ENDF_RECIPE_MF1_MT455)
defdic(endf_recipe_dictionary, (1, 456), ENDF_RECIPE_MF1_MT456)
defdic(endf_recipe_dictionary, (1, 458), ENDF_RECIPE_MF1_MT458)
defdic(endf_recipe_dictionary, (1, 460), ENDF_RECIPE_MF1_MT460)
defdic(endf_recipe_dictionary, (2, 151), ENDF_RECIPE_MF2_MT151)
defdic(endf_recipe_dictionary, (3,), ENDF_RECIPE_MF3)
defdic(endf_recipe_dictionary, (4,), ENDF_RECIPE_MF4)
defdic(endf_recipe_dictionary, (5,), ENDF_RECIPE_MF5)
defdic(endf_recipe_dictionary, (6,), ENDF_RECIPE_MF6)
defdic(endf_recipe_dictionary, (7, 2), ENDF_RECIPE_MF7_MT2)
defdic(endf_recipe_dictionary, (7, 4), ENDF_RECIPE_MF7_MT4)
defdic(endf_recipe_dictionary, (7, 451), ENDF_RECIPE_MF7_MT451)
defdic(endf_recipe_dictionary, (8, -1), ENDF_RECIPE_MF8)
defdic(endf_recipe_dictionary, (8, 454), ENDF_RECIPE_MF8_MT454)
defdic(endf_recipe_dictionary, (8, 457), ENDF_RECIPE_MF8_MT457)
defdic(endf_recipe_dictionary, (8, 459), ENDF_RECIPE_MF8_MT459)
defdic(endf_recipe_dictionary, (9,), ENDF_RECIPE_MF9)
defdic(endf_recipe_dictionary, (10,), ENDF_RECIPE_MF10)
defdic(endf_recipe_dictionary, (12,), ENDF_RECIPE_MF12)
defdic(endf_recipe_dictionary, (13,), ENDF_RECIPE_MF13)
defdic(endf_recipe_dictionary, (14,), ENDF_RECIPE_MF14)
defdic(endf_recipe_dictionary, (15,), ENDF_RECIPE_MF15)
defdic(endf_recipe_dictionary, (23,), ENDF_RECIPE_MF23)
defdic(endf_recipe_dictionary, (26,), ENDF_RECIPE_MF26)
defdic(endf_recipe_dictionary, (27,), ENDF_RECIPE_MF27)
defdic(endf_recipe_dictionary, (28,), ENDF_RECIPE_MF28)
defdic(endf_recipe_dictionary, (31, 452), ENDF_RECIPE_MF31_MT452_455_456)
defdic(endf_recipe_dictionary, (31, 455), ENDF_RECIPE_MF31_MT452_455_456)
defdic(endf_recipe_dictionary, (31, 456), ENDF_RECIPE_MF31_MT452_455_456)
defdic(endf_recipe_dictionary, (31,), ENDF_RECIPE_MF31_MT452_455_456)
defdic(endf_recipe_dictionary, (32,), ENDF_RECIPE_MF32)
defdic(endf_recipe_dictionary, (33,), ENDF_RECIPE_MF33)
defdic(endf_recipe_dictionary, (34,), ENDF_RECIPE_MF34)
defdic(endf_recipe_dictionary, (35,), ENDF_RECIPE_MF35)
defdic(endf_recipe_dictionary, (40,), ENDF_RECIPE_MF40)
