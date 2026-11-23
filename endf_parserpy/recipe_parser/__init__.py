############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/11/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Parsing of ENDF recipes without third-party dependencies.

:func:`parse_recipe` converts a recipe written in the ENDF recipe
language into a parse tree made of :class:`Tree` and :class:`Token`
nodes.
"""

import importlib as _importlib

from .tree import Tree, Token, Meta

# The module parser is imported when it or one of these names is first
# accessed (PEP 562): the trees are also used without it, e.g.
# by EndfParserCpp and the multi-material interface.
_PARSER_NAMES = (
    "parse_recipe",
    "get_recipe_parser",
    "RecipeParser",
    "RecipeSyntaxError",
)


def __getattr__(name):
    if name in _PARSER_NAMES or name == "parser":
        module = _importlib.import_module(".parser", __name__)
        if name == "parser":
            return module
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_PARSER_NAMES) | {"parser"})
