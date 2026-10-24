############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Abbreviations defined in a branch of an if-clause.

An abbreviation defined (or redefined) in a branch of an if-clause is not
visible after the if-clause. The parsers used the abbreviation of the
branch after it: EndfParserPy the one of the evaluated branch,
EndfParserCpp the one of the last branch in the recipe.

Test recipe (endf_recipes/test/endf_recipe_mf5.py, MF5/MT1):
X := L1 before the if-clause, X := N1 if L2 == 1, X := N2 otherwise,
and the record after the if-clause contains X.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSERS = [EndfParserCpp, EndfParserPy]


def _parser(ParserCls):
    kwargs = dict(endf_format="test", ignore_missing_tpid=True)
    kwargs["ignore_send_records"] = True
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


def _section(L2):
    return {
        "MAT": 125,
        "MF": 5,
        "MT": 1,
        "ZA": 1.0,
        "AWR": 2.0,
        "L1": 7,
        "L2": L2,
        "N1": 3,
        "N2": 4,
    }


def _l1_field(line):
    return int(line[22:33])


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("L2, inner", [(1, 3), (0, 4)])
def test_abbreviation_of_branch_not_visible_after_if(ParserCls, L2, inner):
    parser = _parser(ParserCls)
    lines = parser.write({5: {1: _section(L2)}})
    if isinstance(lines, str):
        lines = lines.splitlines()
    # the record in the branch uses the abbreviation of the branch,
    # the record after the if-clause the one defined before it
    assert _l1_field(lines[1]) == inner
    assert _l1_field(lines[2]) == 7
    assert parser.parse(lines)[5][1] == _section(L2)


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_value_of_abbreviation_validated_after_if(ParserCls):
    parser = _parser(ParserCls)
    lines = parser.write({5: {1: _section(1)}})
    if isinstance(lines, str):
        lines = lines.splitlines()
    lines = list(lines)
    # the branch value of X after the if-clause is inconsistent
    lines[2] = lines[2][:22] + f"{3:11d}" + lines[2][33:]
    with pytest.raises(Exception):
        parser.parse(lines)
