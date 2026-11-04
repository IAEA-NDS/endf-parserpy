############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Sections without a recipe are read verbatim and completely.

The master parse function of the C++ parser reads an MF/MT section for
which no recipe function is registered verbatim, as a list of its lines.
The loop of the master function has already read the first line of the
section to determine its MAT/MF/MT numbers, so the stream must be set
back before the lines of the section are collected; without that, the
first line of every such section was missing, and a section of a single
line gave an empty list, which writing rejects. The sections below use
an MF without a recipe (MF39) and an MT without a recipe of an MF whose
recipes are registered per MT (MF1), so that both reach the fallback.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


MAT = 2625


def _line(content, mat, mf, mt):
    assert len(content) <= 66
    return f"{content:<66}{mat:>4}{mf:>2}{mt:>3}"


def _send(mf):
    return _line("", MAT, mf, 0)


def _make_tape():
    lines = [_line("test tape for sections without a recipe", 1, 0, 0)]
    # an MT without a recipe of an MF with per-MT recipes
    lines.append(_line(" 1.000000+0 2.000000+0          0          1", MAT, 1, 480))
    lines.append(_send(1))
    lines.append(_line("", MAT, 0, 0))  # FEND
    # an MF without a recipe: one section of two lines, one of a single line
    lines.append(_line(" first line of the unknown section", MAT, 39, 1))
    lines.append(_line(" second line of the unknown section", MAT, 39, 1))
    lines.append(_send(39))
    lines.append(_line(" sole line of a one-line section", MAT, 39, 2))
    lines.append(_send(39))
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.append(_line("", 0, 0, 0))  # MEND
    lines.append(_line("", -1, 0, 0))  # TEND
    return "".join(l + "\n" for l in lines), lines


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_sections_without_recipe_contain_all_lines(ParserCls):
    tape, lines = _make_tape()
    result = ParserCls().parse(tape)
    assert result[1][480] == [lines[1] + "\n"]
    assert result[39][1] == [lines[4] + "\n", lines[5] + "\n"]
    assert result[39][2] == [lines[7] + "\n"]


def test_both_parsers_agree_on_sections_without_recipe():
    tape, _ = _make_tape()
    cpp_result = EndfParserCpp().parse(tape)
    py_result = EndfParserPy().parse(tape)
    for mf, mt in ((1, 480), (39, 1), (39, 2)):
        assert cpp_result[mf][mt] == py_result[mf][mt]


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_sections_without_recipe_round_trip(ParserCls):
    # the parsed tape can be written again (a one-line section gave an
    # empty list before, which writing rejects) and the content of the
    # verbatim lines is preserved
    tape, _ = _make_tape()
    parser = ParserCls()
    result = parser.parse(tape)
    output = "\n".join(parser.write(result))
    result2 = parser.parse(output)
    for mf, mt in ((1, 480), (39, 1), (39, 2)):
        first = [l[:66] for l in result[mf][mt]]
        second = [l[:66] for l in result2[mf][mt]]
        assert first == second
