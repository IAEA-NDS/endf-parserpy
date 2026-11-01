"""A failed lookahead must not change later parses of the same EndfParserPy.

The recipe of MF8/MT457 reads the HEAD record of the section in a
lookahead (``if NST==0 [lookahead=1]``) with less strict parsing
options. If an error other than a control record mismatch ends the
lookahead (here a malformed number in the HEAD record), the parser
state, including these parsing options, must be restored, so that the
parser instance behaves as a fresh one afterwards, and the error
message must show the record log of the lookahead.
"""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import InvalidFloatError

TESTDATA = Path(__file__).resolve().parent / "testdata"
PU = TESTDATA / "dec-094_Pu_244.endf"


def _lines_with_bad_mf8_head():
    lines = PU.read_text().split("\n")
    for i, line in enumerate(lines):
        if line[70:75] == " 8457":
            lines[i] = "BADBADBAD!!" + line[11:]
            return lines
    raise AssertionError("no MF8/MT457 section")


def _parse_error(parser, lines, **kwargs):
    with pytest.raises(Exception) as excinfo:
        parser.parse(lines, **kwargs)
    return excinfo.value


@pytest.mark.parametrize("mode", ["dict", "list", "numpy"])
def test_parser_usable_after_failed_lookahead(mode):
    if mode == "numpy":
        pytest.importorskip("numpy")
    good = PU.read_text()
    bad = _lines_with_bad_mf8_head()
    parser = EndfParserPy(array_type=mode)
    orig_parse_opts = parser.parse_opts
    _parse_error(parser, bad)
    assert parser.parse_opts is orig_parse_opts
    assert "ignore_all_mismatches" not in parser.parse_opts
    result = parser.parse(good)
    fresh = EndfParserPy(array_type=mode).parse(good)
    assert str(result) == str(fresh)


def test_error_message_of_failed_lookahead():
    """The message shows the record log of the failed lookahead and the
    error that ended it, and is the same for a reused parser."""
    bad = _lines_with_bad_mf8_head()
    parser = EndfParserPy()
    first = _parse_error(parser, bad)
    second = _parse_error(parser, bad)
    assert isinstance(first, InvalidFloatError)
    assert "Here is the parser record log until failure" in str(first)
    assert "BADBADBAD!!" in str(first)
    assert type(first) is type(second)
    assert str(first) == str(second)


def test_strict_options_apply_after_failed_lookahead():
    """A section with a mismatch still fails after a failed lookahead."""
    lines = PU.read_text().split("\n")
    i = next(k for k, line in enumerate(lines) if line[70:75] == " 1451")
    # a nonzero value in a field that must be zero
    mismatch = list(lines)
    mismatch[i + 1] = mismatch[i + 1][:44] + "%11d" % 7 + mismatch[i + 1][55:]
    fresh_error = _parse_error(EndfParserPy(ignore_zero_mismatch=False), mismatch)
    parser = EndfParserPy(ignore_zero_mismatch=False)
    _parse_error(parser, _lines_with_bad_mf8_head())
    error = _parse_error(parser, mismatch)
    assert type(error) is type(fresh_error)
    assert str(error) == str(fresh_error)


def test_nofail_later_sections_not_affected():
    """With ``nofail=True``, the sections after a failed lookahead are
    parsed with the options of the parser."""
    bad = _lines_with_bad_mf8_head()
    parser = EndfParserPy()
    parser.parse(bad, nofail=True)
    assert "ignore_all_mismatches" not in parser.parse_opts
    good = PU.read_text()
    assert str(parser.parse(good)) == str(EndfParserPy().parse(good))
