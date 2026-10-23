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

"""Blank lines in files with CRLF line endings (issue #77, problem 1).

EndfParserCpp kept the carriage return of a line of a file with CRLF line
endings, so that an empty line was read as "\\r", which is not blank: it was
taken for a record and gave "malformed number field", also with
ignore_blank_lines=True. EndfParserPy reads files in text mode and never
sees the carriage return. EndfParserCpp now removes it after reading a
line, and a line of blanks and tabs is blank in both parsers.

With ignore_blank_lines=True, EndfParserCpp also took the MAT number of a
section after a blank line from the blank line (MAT=0), also for LF line
endings: the position of the next section was not advanced past a
skipped blank line.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"
PARSERS = [EndfParserCpp, EndfParserPy]


def _lf_bytes():
    data = TESTFILE.read_bytes().replace(b"\r\n", b"\n")
    return data if data.endswith(b"\n") else data + b"\n"


def _cases():
    lf = _lf_bytes()
    crlf = lf.replace(b"\n", b"\r\n")
    return {
        "crlf": (crlf, False),
        "crlf_blank_after_tend": (crlf + b"\r\n", False),
        "crlf_blank_in_middle": (crlf.replace(b"\r\n", b"\r\n\r\n", 1), True),
        "crlf_blanks_and_tab_line": (crlf.replace(b"\r\n", b"\r\n  \t \r\n", 1), True),
        "lf_blank_in_middle": (lf.replace(b"\n", b"\n\n", 1), True),
        "lf_blank_after_tend": (lf + b"\n", False),
        "lf_tab_line_after_tend": (lf + b"\t\n", False),
    }


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


@pytest.fixture(scope="module")
def reference():
    # results of the file with LF line endings and without blank lines
    return {
        ParserCls: _parser(ParserCls).parse(_lf_bytes().decode())
        for ParserCls in PARSERS
    }


@pytest.mark.parametrize("case", list(_cases()))
@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("exclude", [None, [8]], ids=["parse", "verbatim"])
def test_blank_lines_with_crlf(case, ParserCls, exclude, reference, tmp_path):
    data, needs_option = _cases()[case]
    path = tmp_path / "case.endf"
    path.write_bytes(data)
    parser = _parser(ParserCls, ignore_blank_lines=needs_option)
    res = parser.parsefile(str(path), exclude=exclude)
    if exclude is None:
        assert res == reference[ParserCls]
    else:
        lines = [line.rstrip("\n") for line in res[8][457]]
        expected = [
            line for line in _lf_bytes().decode().splitlines() if line[70:75] == " 8457"
        ]
        assert lines == expected


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_blank_line_in_middle_rejected_without_option(ParserCls, tmp_path):
    data, _ = _cases()["crlf_blank_in_middle"]
    path = tmp_path / "case.endf"
    path.write_bytes(data)
    with pytest.raises(Exception, match="[Bb]lank line"):
        _parser(ParserCls).parsefile(str(path))
