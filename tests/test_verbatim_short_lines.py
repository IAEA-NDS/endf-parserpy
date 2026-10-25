############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lines of sections written verbatim that are shorter than 75 columns.

A section given as a list of lines is written verbatim. The columns
missing from a short line are written as blanks, as they are read as
blanks. EndfParserCpp padded such a line with NUL characters (with
include_linenum=True) or raised an IndexError (with include_linenum=False);
EndfParserPy wrote it without padding, so that the sequence number did not
start in column 76.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTFILE = Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf"
PARSERS = [EndfParserCpp, EndfParserPy]


def _parser(ParserCls, include_linenum):
    kwargs = {"include_linenum": include_linenum}
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.fixture(scope="module")
def mf3mt1():
    lines = TESTFILE.read_text(encoding="latin-1").splitlines()
    section = [l for l in lines if l[70:75] == " 3  1"][:-1]  # without SEND
    return lines[0], section


VARIANTS = {
    "short": "short line",
    "empty": "",
    "newline": "short line\n",
    "crlf": "short line\r\n",
    "74 columns": "x" * 74,
}


@pytest.mark.parametrize("include_linenum", [True, False])
@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_short_verbatim_line_padded_with_blanks(
    mf3mt1, ParserCls, variant, include_linenum
):
    tpid, section = mf3mt1
    line = VARIANTS[variant]
    lines = section[:3] + [line] + section[3:]
    parser = _parser(ParserCls, include_linenum)
    out = _lines(parser.write({0: {0: [tpid]}, 3: {1: lines}}))
    written = out[4]  # TPID, the three lines before the short line
    width = 80 if include_linenum else 75
    assert "\x00" not in "".join(out)
    assert len(written) == width
    content = line.rstrip("\r\n")
    assert written[:75] == content.ljust(75)
    if include_linenum:
        assert written[75:] == "    4"
    # the other lines are written as before
    assert out[1] == section[0][:width]


@pytest.mark.parametrize("include_linenum", [True, False])
@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_short_verbatim_line_same_in_both_parsers(mf3mt1, variant, include_linenum):
    tpid, section = mf3mt1
    lines = section[:3] + [VARIANTS[variant]] + section[3:]
    data = {0: {0: [tpid]}, 3: {1: lines}}
    out = [_lines(_parser(P, include_linenum).write(data)) for P in PARSERS]
    assert out[0] == out[1]


@pytest.mark.parametrize("include_linenum", [True, False])
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_full_verbatim_lines_unchanged(mf3mt1, ParserCls, include_linenum):
    tpid, section = mf3mt1
    parser = _parser(ParserCls, include_linenum)
    out = _lines(parser.write({0: {0: [tpid]}, 3: {1: section}}))
    width = 80 if include_linenum else 75
    body = [l for l in out if l[70:75] == " 3  1"]
    assert body == [l[:width] for l in section]
