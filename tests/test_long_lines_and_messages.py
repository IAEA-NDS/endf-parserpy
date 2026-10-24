############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lines longer than 80 columns and line content in error messages (issue #77).

A multi-byte character (e.g. UTF-8 U+2019, three bytes) in a TEXT record
makes the line longer than 80 columns and shifts its MAT/MF/MT columns.
EndfParserPy divides a file into sections by these columns and rejects
the line; EndfParserCpp now checks the MAT/MF/MT numbers of a line
longer than 80 columns as well (without validate_control_records). The
messages of both parsers end with a hint that the line is too long.
Lines longer than 80 columns with the correct MAT/MF/MT numbers, e.g.
with text beyond column 80, are still accepted.

Characters outside printable ASCII in error messages, e.g. of the
content of a line, are escaped (\\x92, \\t, \\r) in both parsers. In
EndfParserCpp, pybind11 decodes the message as UTF-8, which failed for
such bytes, so that the message was lost.

The tests use the default format flavor of EndfParserCpp only (see
test_text_encoding.py).
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import (
    UnexpectedControlRecordError,
    InvalidFloatError,
)
from test_text_encoding import (
    TEXT_LINE,
    _base_bytes,
    _modify_line,
    _parser,
    _write_file,
    utf8_inserted_bytes,
)


CPP_HINT = (
    "Hint: line 6 is longer than 80 columns (82 columns; non-ASCII "
    "multi-byte characters or text beyond column 80?)"
)
PY_HINT = (
    "Hint: the line is longer than 80 columns (82 columns; non-ASCII "
    "multi-byte characters or text beyond column 80?)"
)


def _error(tmp_path, ParserCls, data, exc_type, **kwargs):
    path = _write_file(tmp_path, data)
    with pytest.raises(exc_type) as excinfo:
        _parser(ParserCls).parsefile(path, **kwargs)
    msg = str(excinfo.value)
    assert msg.isascii()
    assert "unknown exception" not in msg
    return msg


@pytest.mark.parametrize("exclude", [None, [1]])
def test_shifted_columns_rejected_with_hint(tmp_path, exclude):
    data = utf8_inserted_bytes()
    msg = _error(tmp_path, EndfParserCpp, data, RuntimeError, exclude=exclude)
    if exclude is None:
        # the MAT number is read from the shifted columns
        assert msg.startswith(
            "Invalid MAT encountered! Expected MAT=3564 but found MAT=35\n"
        )
        assert "\\xe2\\x80\\x99" in msg
    else:
        assert msg.startswith("expected SEND of MF/MT 1/451\n")
    assert msg.endswith(CPP_HINT)
    msg = _error(
        tmp_path, EndfParserPy, data, UnexpectedControlRecordError, exclude=exclude
    )
    assert msg.startswith(
        "Currently in MT=451 section but encountered MT=14 in control record"
    )
    assert msg.endswith(PY_HINT)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("exclude", [None, [1]])
def test_text_beyond_column_80_accepted(tmp_path, ParserCls, exclude):
    lines = _base_bytes().split(b"\n")
    for i in (2, TEXT_LINE, len(lines) - 5):
        lines[i] += b"  beyond column 80"
    path = _write_file(tmp_path, b"\n".join(lines))
    parser = _parser(ParserCls)
    d = parser.parsefile(path, exclude=exclude)
    ref = parser.parse(_base_bytes().decode("ascii"), exclude=exclude)
    if exclude is None:
        assert d == ref
    else:
        assert d[1][451][1].rstrip("\n").endswith("  beyond column 80")
        assert d[8] == ref[8]
    assert parser.write(d) == parser.write(ref)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_hint_only_for_long_lines(tmp_path, ParserCls):
    # a malformed number in a line of 80 columns
    data = _modify_line(_base_bytes(), 2, 5, b"x")
    exc_type = RuntimeError if ParserCls is EndfParserCpp else InvalidFloatError
    msg = _error(tmp_path, ParserCls, data, exc_type)
    assert "Hint" not in msg


@pytest.mark.parametrize(
    "new, escaped",
    [(b"\x92", "\\x92"), ("\u2019".encode("utf-8"), "\\xe2\\x80\\x99"), (b"\t", "\\t")],
)
def test_number_field_content_escaped(tmp_path, new, escaped):
    # characters in a number field of a HEAD record (line 3)
    data = _modify_line(_base_bytes(), 2, 4, new)
    msg = _error(tmp_path, EndfParserCpp, data, RuntimeError)
    assert msg.startswith("malformed number field: ")
    assert escaped in msg
    msg = _error(tmp_path, EndfParserPy, data, InvalidFloatError)
    assert escaped in msg
    # the line in the record log of EndfParserPy
    line = data.split(b"\n")[2].decode("latin-1").rstrip()
    expected = line.replace("\t", "\\t")
    for c in set(expected):
        if ord(c) > 126:
            expected = expected.replace(c, f"\\x{ord(c):02x}")
    assert f'Line:     "{expected}"' in msg


def test_carriage_return_escaped(tmp_path):
    # a carriage return inside a line (not at its end) is part of the line
    data = _modify_line(_base_bytes(), 2, 4, b"\r")
    msg = _error(tmp_path, EndfParserCpp, data, RuntimeError)
    assert msg.startswith('malformed number field: " 0.0\\r0000+0"')
    with pytest.raises(InvalidFloatError) as excinfo:
        _parser(EndfParserPy).parse(data.decode("latin-1"))
    msg = str(excinfo.value)
    assert msg.isascii()
    assert "\\r" in msg
