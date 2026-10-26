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

"""The deprecated recipe-cache arguments emit a DeprecationWarning.

The arguments ``cache_dir`` and ``print_cache_info`` of ``EndfParserPy``
and ``EndfParserFactory.create`` have no effect anymore (the recipe cache
is gone). They are still accepted, but providing them emits a
``DeprecationWarning``; constructing a parser without them does not.
"""

import warnings

import pytest

from endf_parserpy import EndfParserFactory, EndfParserPy
from endf_parserpy.interpreter.endf_recipe_utils import (
    get_recipe_parser,
    get_recipe_parsetree,
    get_recipe_parsetree_dic,
)


def test_cache_dir_emits_deprecation_warning(tmp_path):
    with pytest.warns(DeprecationWarning, match="cache_dir"):
        EndfParserPy(cache_dir=str(tmp_path))


def test_print_cache_info_emits_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="print_cache_info"):
        EndfParserPy(print_cache_info=True)

    with pytest.warns(DeprecationWarning, match="print_cache_info"):
        EndfParserPy(print_cache_info=False)


def test_factory_passes_cache_arguments_through():
    with pytest.warns(DeprecationWarning, match="print_cache_info"):
        EndfParserFactory.create(select="python", print_cache_info=True)


def test_recipe_utils_legacy_arguments_emit_deprecation_warning(tmp_path):
    with pytest.warns(DeprecationWarning, match="recipe_grammar"):
        get_recipe_parser("dummy_grammar")

    parser = get_recipe_parser()
    recipe = "[MAT, 1,451/ ZA, AWR, 0, 0, 0, 0] HEAD\n"
    with pytest.warns(DeprecationWarning, match="grammar_hash"):
        get_recipe_parsetree(recipe, parser, grammar_hash="abc")
    with pytest.warns(DeprecationWarning, match="cache_dir"):
        get_recipe_parsetree(recipe, parser, cache_dir=str(tmp_path))
    with pytest.warns(DeprecationWarning, match="print_cache_info"):
        get_recipe_parsetree_dic({1: {451: recipe}}, print_cache_info=True)


def test_no_deprecation_warning_without_cache_arguments():
    recipe = "[MAT, 1,451/ ZA, AWR, 0, 0, 0, 0] HEAD\n"
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        EndfParserPy()
        EndfParserFactory.create(select="python")
        parser = get_recipe_parser()
        get_recipe_parsetree(recipe, parser)
        get_recipe_parsetree_dic({1: {451: recipe}})
