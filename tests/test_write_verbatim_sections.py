############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Writing of sections kept verbatim: MAT of the framing records.

The master write function keeps the MAT number of the section written
last for the FEND records and for deciding whether a FEND record is due
before the next MF. For a section written verbatim because no writing
function is available for its MF/MT numbers, the MAT number (from the
control columns of its lines) was not kept and the section did not
count as encountered, so that a dictionary whose first sections are
such verbatim sections gave FEND records with an arbitrary MAT number
(an indeterminate value if the dictionary held only such sections), and
the FEND record between such an MF and the next one was missing.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


MAT = 2625


def _line(content, mat, mf, mt):
    assert len(content) <= 66
    return f"{content:<66}{mat:>4}{mf:>2}{mt:>3}"


def _ctrl(line):
    # (mat, mf, mt) of a written line
    return int(line[66:70]), int(line[70:72]), int(line[72:75])


MF1_LINES = [_line(" 1.000000+0 2.000000+0          0          1", MAT, 1, 480)]
MF39_LINES = [
    _line(" first line of the unknown section", MAT, 39, 1),
    _line(" second line of the unknown section", MAT, 39, 1),
]
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


def _make_tape():
    lines = [_line("test tape for writing verbatim sections", 1, 0, 0)]
    lines.extend(MF1_LINES)
    lines.append(_line("", MAT, 1, 0))  # SEND
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.extend(MF3_LINES)
    lines.append(_line("", MAT, 3, 0))  # SEND
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.extend(MF39_LINES)
    lines.append(_line("", MAT, 39, 0))  # SEND
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.append(_line("", 0, 0, 0))  # MEND
    lines.append(_line("", -1, 0, 0))  # TEND
    return "".join(l + "\n" for l in lines)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_verbatim_only_dict_writes_correct_framing(ParserCls):
    endf_dict = {
        1: {480: [l + "\n" for l in MF1_LINES]},
        39: {1: [l + "\n" for l in MF39_LINES]},
    }
    out = ParserCls().write(endf_dict)
    ctrls = [_ctrl(l) for l in out]
    # the content lines and the SEND records carry the MAT of the sections
    assert all(mat == MAT for mat, mf, mt in ctrls[:3])
    # every FEND record carries the MAT of the material, none an
    # arbitrary number
    fends = [(mat, mf, mt) for mat, mf, mt in ctrls if mf == 0 and mt == 0 and mat > 0]
    assert fends and all(mat == MAT for mat, mf, mt in fends)
    # a FEND record separates the two MFs
    mf1_end = max(i for i, c in enumerate(ctrls) if c[1] == 1)
    mf39_start = min(i for i, c in enumerate(ctrls) if c[1] == 39)
    between = ctrls[mf1_end + 1 : mf39_start]
    assert (MAT, 0, 0) in between
    # the tape ends with MEND and TEND records
    assert ctrls[-2] == (0, 0, 0)
    assert ctrls[-1] == (-1, 0, 0)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_mixed_dict_fend_records_carry_material_mat(ParserCls):
    # the TPID record has MAT=1; a FEND record written with the MAT of
    # the TPID instead of the MAT of the material is the symptom of the
    # MAT of a verbatim section not being kept
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    assert isinstance(endf_dict[1][480], list)
    assert isinstance(endf_dict[3][1], dict)
    out = parser.write(endf_dict)
    ctrls = [_ctrl(l) for l in out]
    assert ctrls[0] == (1, 0, 0)  # the TPID record
    assert all(mat != 1 for mat, mf, mt in ctrls[1:])
    fends = [
        (mat, mf, mt) for mat, mf, mt in ctrls[1:] if mf == 0 and mt == 0 and mat > 0
    ]
    assert len(fends) == 3 and all(mat == MAT for mat, mf, mt in fends)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_mixed_dict_round_trip(ParserCls):
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    out = parser.write(endf_dict)
    endf_dict2 = parser.parse("\n".join(out) + "\n")

    def strip(section):
        # the written lines carry the sequence number columns in addition
        return [line[:75] for line in section]

    assert strip(endf_dict2[1][480]) == strip(endf_dict[1][480])
    assert strip(endf_dict2[39][1]) == strip(endf_dict[39][1])
    assert endf_dict2[3][1]["xstable"] == endf_dict[3][1]["xstable"]
