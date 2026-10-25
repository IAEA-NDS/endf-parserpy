"""Lines given as bytes in a section written verbatim (a list of lines).

A line of such a section may be given as ``bytes``; it is written as
these bytes, i.e. as the string of the characters with the same codes
(Latin-1), by both parsers. With ``accept_non_ascii=False``, a byte
outside printable ASCII raises the same ``InvalidCharacterError`` as the
corresponding character of a string.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import InvalidCharacterError


TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"
PARSERS = [EndfParserPy, EndfParserCpp]


def _create(ParserCls, **kwargs):
    try:
        return ParserCls(**kwargs)
    except Exception:
        pytest.skip(f"{ParserCls.__name__} unavailable")


def _with_line(endf_dict, index, line):
    """Copy of endf_dict whose verbatim MF1/MT451 has line at index."""
    result = {mf: dict(sections) for mf, sections in endf_dict.items()}
    lines = list(endf_dict[1][451])
    lines[index] = line
    result[1][451] = lines
    return result


@pytest.fixture(scope="module")
def verbatim_dict():
    return EndfParserPy().parsefile(TESTFILE, exclude=[(1, 451)])


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("accept_non_ascii", [True, False])
def test_ascii_bytes_line_written_as_string(verbatim_dict, ParserCls, accept_non_ascii):
    parser = _create(ParserCls, accept_non_ascii=accept_non_ascii)
    line = verbatim_dict[1][451][3]
    expected = parser.write(verbatim_dict)
    as_bytes = _with_line(verbatim_dict, 3, line.encode("latin-1"))
    assert parser.write(as_bytes) == expected
    as_bytes = _with_line(verbatim_dict, 0, verbatim_dict[1][451][0].encode())
    assert parser.write(as_bytes) == expected


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_non_ascii_bytes_line_written_as_its_bytes(verbatim_dict, ParserCls):
    parser = _create(ParserCls)
    line = verbatim_dict[1][451][3]
    line = line[:10] + "\x92" + line[11:]
    expected = parser.write(_with_line(verbatim_dict, 3, line))
    as_bytes = _with_line(verbatim_dict, 3, line.encode("latin-1"))
    assert parser.write(as_bytes) == expected


@pytest.mark.parametrize("char", ["\x92", "\t"])
def test_non_ascii_bytes_line_rejected(verbatim_dict, char):
    line = verbatim_dict[1][451][3]
    line = line[:10] + char + line[11:]
    messages = set()
    for ParserCls in PARSERS:
        parser = _create(ParserCls, accept_non_ascii=False)
        for value in (line, line.encode("latin-1")):
            with pytest.raises(InvalidCharacterError) as exc_info:
                parser.write(_with_line(verbatim_dict, 3, value))
            messages.add(str(exc_info.value))
    assert len(messages) == 1
    assert "line 4 of the section MF=1/MT=451" in messages.pop()
