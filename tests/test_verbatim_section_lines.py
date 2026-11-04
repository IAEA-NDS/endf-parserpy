############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Representation of the lines of sections kept verbatim.

A section that is not parsed — because no recipe is available for its
MF/MT numbers or because it is excluded with ``exclude``/``include`` —
is kept as a list of its lines. Both parsers represent each line the
same way: the line as read, without its line ending and with a newline
appended. For ``EndfParserPy``, this representation was previously
different between ``parse`` (no newline; a ``\\r`` of a CRLF line ending
remained part of the line) and ``parsefile`` (line ending kept), and
thus also different from ``EndfParserCpp``.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


MAT = 2625


def _line(content, mat, mf, mt):
    assert len(content) <= 66
    return f"{content:<66}{mat:>4}{mf:>2}{mt:>3}"


def _send(mf):
    return _line("", MAT, mf, 0)


# a tape with an MF3/MT1 section (recipe available, so that ``exclude``
# decides whether it is kept verbatim) and an MF39/MT1 section (no
# recipe, always kept verbatim)
MF3_LINES = [
    _line(
        " 2.906300+4 6.238900+1          0          0          0          0", MAT, 3, 1
    ),
    _line(
        " 0.000000+0 0.000000+0          0          0          1          1", MAT, 3, 1
    ),
    _line("          1          2", MAT, 3, 1),
    _line(" 1.000000+0 2.000000+0", MAT, 3, 1),
]
MF39_LINES = [
    _line(" first line of the unknown section", MAT, 39, 1),
    _line(" second line of the unknown section", MAT, 39, 1),
]


def _make_tape():
    lines = [_line("test tape for verbatim line representation", 1, 0, 0)]
    lines.extend(MF3_LINES)
    lines.append(_send(3))
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.extend(MF39_LINES)
    lines.append(_send(39))
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.append(_line("", 0, 0, 0))  # MEND
    lines.append(_line("", -1, 0, 0))  # TEND
    return "".join(l + "\n" for l in lines)


EXPECTED_MF3 = [l + "\n" for l in MF3_LINES]
EXPECTED_MF39 = [l + "\n" for l in MF39_LINES]


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_verbatim_lines_have_normalized_newline(ParserCls):
    parser = ParserCls()
    result = parser.parse(_make_tape(), exclude=(3,))
    assert result[3][1] == EXPECTED_MF3
    assert result[39][1] == EXPECTED_MF39


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_verbatim_lines_same_for_parse_and_parsefile(ParserCls, tmp_path):
    path = tmp_path / "tape.endf"
    path.write_text(_make_tape())
    parser = ParserCls()
    from_str = parser.parse(_make_tape(), exclude=(3,))
    from_file = parser.parsefile(str(path), exclude=(3,))
    for mf, mt in ((3, 1), (39, 1)):
        assert from_str[mf][mt] == from_file[mf][mt]
        assert from_str[mf][mt] == (EXPECTED_MF3 if mf == 3 else EXPECTED_MF39)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_verbatim_lines_of_crlf_input_carry_no_cr(ParserCls):
    tape = _make_tape().replace("\n", "\r\n")
    result = ParserCls().parse(tape, exclude=(3,))
    assert result[3][1] == EXPECTED_MF3
    assert result[39][1] == EXPECTED_MF39


def test_both_parsers_give_identical_verbatim_sections():
    tape = _make_tape()
    cpp_result = EndfParserCpp().parse(tape, exclude=(3,))
    py_result = EndfParserPy().parse(tape, exclude=(3,))
    for mf, mt in ((3, 1), (39, 1)):
        assert cpp_result[mf][mt] == py_result[mf][mt]
