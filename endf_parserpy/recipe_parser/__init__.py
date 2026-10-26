############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Parsing of ENDF recipes without third-party dependencies.

:func:`parse_recipe` converts a recipe written in the ENDF recipe
language into a parse tree made of :class:`Tree` and :class:`Token`
nodes.
"""

from .tree import Tree, Token, Meta
from .parser import (
    parse_recipe,
    get_recipe_parser,
    RecipeParser,
    RecipeSyntaxError,
)
