from ..utils import defdic

# GENDF tapes of the NJOY2016 modules GROUPR and GAMINR
from .endf_recipe_mf0_mt0 import ENDF_RECIPE_MF0_MT0
from .endf_recipe_mf1_mt451 import ENDF_RECIPE_MF1_MT451
from .endf_recipe_groupwise import (
    ENDF_RECIPE_GROUPWISE,
    ENDF_RECIPE_GROUPWISE_AWR,
    groupwise_recipe,
)

# the MF numbers that GROUPR (3, 5, 6, 12, 13, 16, 21 to 26) and GAMINR
# (23, 26) write
GROUPWISE_MF = (3, 5, 6, 12, 13, 16, 21, 22, 24, 25)
GROUPWISE_AWR_MF = (23, 26)

endf_recipe_dictionary = {}
defdic(endf_recipe_dictionary, (0, 0), ENDF_RECIPE_MF0_MT0)
defdic(endf_recipe_dictionary, (1, 451), ENDF_RECIPE_MF1_MT451)
for _mf in GROUPWISE_MF:
    defdic(endf_recipe_dictionary, (_mf,), groupwise_recipe(ENDF_RECIPE_GROUPWISE, _mf))
for _mf in GROUPWISE_AWR_MF:
    defdic(
        endf_recipe_dictionary, (_mf,), groupwise_recipe(ENDF_RECIPE_GROUPWISE_AWR, _mf)
    )

# The tape structure of the flavor (see endf_parserpy.utils.tape_structure),
# as the NJOY2016 modules GROUPR and GAMINR write their tapes:
# - the sections come in the order of the input cards, not in ascending
#   order, and MF23 and MF26 alternate (GROUPR: the loop over the
#   reactions in subroutine groupr, which reads a card `mfd mtd` for each
#   section; GAMINR: the same, or its built-in list mflst/mtlst);
# - a section MF/MT may occur several times in a material: GROUPR writes
#   the production of each product nuclide as an MF3 section with the MT
#   of the reaction (mfh=3 for mfd>=10000000), and maps mfd=8 to MF6,
#   mfd=17 and 18 to MF16 and mfd=31-36 to MF21-26;
# - MF1/MT451 ends without SEND record, directly with the FEND record
#   (call afend after the LIST record of the section); every other
#   section ends with its SEND record (call asend), and there is no other
#   FEND record; every material ends with its MEND record (call amend) and
#   the tape with the TEND record (call atend);
# - NJOY writes the columns 1-66 of the end records blank.
# A material is returned as the list of its sections (material_form).
TAPE_STRUCTURE = {
    "mf_order": "free",
    "mt_order": "free",
    "repeat": True,
    "fend": False,
    "mf": {1: {"fend": True}},
    "section": {(1, 451): {"send": False}},
    "material_form": "list",
    "end_record_fill": "blank",
}
