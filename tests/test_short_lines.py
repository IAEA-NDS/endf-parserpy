############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lines shorter than 75 characters in EndfParserCpp.

EndfParserCpp read the fields and the MAT/MF/MT numbers of a line at fixed
columns, also beyond the end of a shorter line, i.e. leftover characters
of an earlier line or unrelated memory, so that the results could vary
from run to run. Columns missing from a short line are now blanks, as for
EndfParserPy, which reads the columns of a line by slicing.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSERS = [EndfParserCpp, EndfParserPy]


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs.setdefault("print_cache_info", False)
    return ParserCls(**kwargs)


def _mf3_dict():
    xstable = {"NBT": [3], "INT": [2], "E": [1.0, 2.0, 3.0], "xs": [4.0, 5.0, 6.0]}
    section = {
        "MAT": 125,
        "MF": 3,
        "MT": 1,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "QM": 0.0,
        "QI": 0.0,
        "LR": 0,
        "xstable": xstable,
    }
    return {3: {1: section}}


def _mf3_lines():
    return _lines(_parser(EndfParserPy).write(_mf3_dict()))


def _with_line(lines, index, line):
    lines = list(lines)
    lines[index] = line
    return "\n".join(lines)


# short lines


def test_cpp_short_data_line_read_as_blanks():
    lines = _mf3_lines()
    # the second line of the TAB1 table, cut after the fourth field: the
    # missing fields and the MAT/MF/MT numbers are blanks
    text = _with_line(lines, 3, lines[3][:44])
    for _ in range(3):
        xstable = EndfParserCpp(ignore_missing_tpid=True).parse(text)[3][1]["xstable"]
        assert list(xstable["E"]) == [1.0, 2.0, 0.0]
        assert list(xstable["xs"]) == [4.0, 5.0, 0.0]


@pytest.mark.parametrize("cut", [0, 44, 66, 70, 74])
def test_cpp_short_line_rejected_with_validated_control_records(cut):
    # the blank MAT/MF/MT of a short line do not match; EndfParserPy always
    # rejects such a line, as it divides the file into sections by them
    lines = _mf3_lines()
    text = _with_line(lines, 3, lines[3][:cut] if cut > 0 else "     ")
    parser = EndfParserCpp(ignore_missing_tpid=True, validate_control_records=True)
    with pytest.raises(Exception):
        parser.parse(text)
    with pytest.raises(Exception):
        _parser(EndfParserPy, ignore_missing_tpid=True).parse(text)


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("cut", [20, 66, 70])
def test_short_first_line_of_section_rejected(ParserCls, cut):
    # the parsers find a section by the MAT/MF/MT numbers of its first line;
    # blank (missing) numbers are not a section, but an invalid line
    lines = _mf3_lines()
    text = _with_line(lines, 0, lines[0][:cut])
    for _ in range(3):
        with pytest.raises(Exception):
            _parser(ParserCls, ignore_missing_tpid=True).parse(text)


def test_cpp_lines_without_line_numbers_unchanged():
    # lines of 75 characters (without the line number) are complete
    lines = [line[:75] for line in _mf3_lines()]
    text = "\n".join(lines)
    for ParserCls in PARSERS:
        res = _parser(ParserCls, ignore_missing_tpid=True).parse(text)
        assert list(res[3][1]["xstable"]["xs"]) == [4.0, 5.0, 6.0]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_verbatim_section_keeps_lines_as_read(ParserCls):
    lines = [line[:75] for line in _mf3_lines()]
    text = "\n".join(lines)
    res = _parser(ParserCls, ignore_missing_tpid=True).parse(text, exclude=[3])
    assert [line.rstrip("\n") for line in res[3][1]] == lines[:-4]
