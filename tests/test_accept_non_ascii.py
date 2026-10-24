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

"""The option accept_non_ascii (issue #77).

The ENDF-6 format restricts the content of lines to printable ASCII
characters (codes 32 to 126). With accept_non_ascii=False, both parsers
reject any other character in the lines they read, including control
characters such as TAB, with the same message, and text values to be
written that contain such characters. With the default True, such
characters are read and written unchanged (see test_text_encoding.py).

The tests use the default format flavor of EndfParserCpp only (see
test_text_encoding.py).
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfParserFactory
from endf_parserpy.interpreter.custom_exceptions import InvalidCharacterError
from endf_parserpy.cli.actions.validate import STRICT_DEFAULT_ARGS
from test_text_encoding import (
    TEXT_LINE,
    TEXT_COL,
    _base_bytes,
    _modify_line,
    _parser,
    _write_file,
    cp1252_bytes,
    utf8_same_length_bytes,
)


PARSERS = [EndfParserCpp, EndfParserPy]


def _parse_errors(tmp_path, data):
    """The message of the error raised by both parsers for data."""
    path = _write_file(tmp_path, data)
    messages = []
    for ParserCls in PARSERS:
        parser = _parser(ParserCls, accept_non_ascii=False)
        with pytest.raises(InvalidCharacterError) as excinfo:
            parser.parsefile(path)
        messages.append(str(excinfo.value))
    assert messages[0] == messages[1]
    return messages[0]


def _parse_both(tmp_path, data, **kwargs):
    path = _write_file(tmp_path, data)
    return [_parser(ParserCls, **kwargs).parsefile(path) for ParserCls in PARSERS]


@pytest.mark.parametrize("exclude", [None, [1]])
def test_cp1252_byte_rejected(tmp_path, exclude):
    path = _write_file(tmp_path, cp1252_bytes())
    messages = []
    for ParserCls in PARSERS:
        parser = _parser(ParserCls, accept_non_ascii=False)
        with pytest.raises(InvalidCharacterError) as excinfo:
            parser.parsefile(path, exclude=exclude)
        messages.append(str(excinfo.value))
    assert messages[0] == messages[1]
    assert messages[0].startswith(
        "line 6, column 21 (MAT/MF/MT 3564/1/451) contains byte 0x92 "
        "(likely a Windows-1252 character), which is not a printable "
        "ASCII character"
    )
    assert "accept_non_ascii=True" in messages[0]


def test_utf8_bytes_rejected(tmp_path):
    msg = _parse_errors(tmp_path, utf8_same_length_bytes())
    assert msg.startswith(
        "line 6, column 61 (MAT/MF/MT 3564/1/451) contains byte 0xe2 "
        "(non-ASCII, e.g. Latin-1 or part of a UTF-8 multi-byte character)"
    )


def test_tab_in_text_line_rejected(tmp_path):
    data = _modify_line(_base_bytes(), TEXT_LINE, TEXT_COL, b"\t")
    msg = _parse_errors(tmp_path, data)
    assert msg.startswith(
        "line 6, column 21 (MAT/MF/MT 3564/1/451) contains byte 0x09 (TAB)"
    )
    # accepted by default
    res_cpp, res_py = _parse_both(tmp_path, data)
    assert res_cpp[1][451]["ALAB"] == res_py[1][451]["ALAB"] == " BNL     \t "


def test_control_character_in_numeric_record_rejected(tmp_path):
    # the line number columns of a HEAD record of MF8/MT457 (line 50)
    lines = _base_bytes().split(b"\n")
    lineidx = next(i for i, l in enumerate(lines) if l[70:75] == b" 8457")
    data = _modify_line(_base_bytes(), lineidx, 77, b"\x01")
    msg = _parse_errors(tmp_path, data)
    assert msg.startswith(
        f"line {lineidx + 1}, column 78 (MAT/MF/MT 3564/8/457) contains "
        "byte 0x01 (control character)"
    )


def test_character_beyond_column_80_rejected(tmp_path):
    lines = _base_bytes().split(b"\n")
    lines[2] = lines[2] + b" \xa0"
    msg = _parse_errors(tmp_path, b"\n".join(lines))
    assert msg.startswith("line 3, column 82 (MAT/MF/MT 3564/1/451) contains byte 0xa0")


def test_tpid_and_end_records_checked(tmp_path):
    data = _modify_line(_base_bytes(), 0, 50, b"\x7f")
    msg = _parse_errors(tmp_path, data)
    assert msg.startswith("line 1, column 51 (MAT/MF/MT 1/0/0) contains byte 0x7f")
    lines = _base_bytes().split(b"\n")
    lines[-1] = lines[-1][:10] + b"\xff" + lines[-1][11:]
    msg = _parse_errors(tmp_path, b"\n".join(lines))
    assert msg.startswith(f"line {len(lines)}, column 11 (MAT/MF/MT -1/0/0)")


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_ascii_file_unaffected(tmp_path, ParserCls):
    data = _base_bytes()
    path = _write_file(tmp_path, data)
    strict = _parser(ParserCls, accept_non_ascii=False)
    lenient = _parser(ParserCls)
    d = strict.parsefile(path)
    assert d == lenient.parsefile(path)
    assert strict.write(d) == lenient.write(d)
    assert "\n".join(strict.write(d)).encode("ascii") == data
    d = strict.parsefile(path, exclude=[1])
    assert strict.write(d) == lenient.write(d)


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_crlf_line_endings_accepted(tmp_path, ParserCls):
    data = _base_bytes().replace(b"\n", b"\r\n")
    path = _write_file(tmp_path, data)
    d = _parser(ParserCls, accept_non_ascii=False).parsefile(path)
    assert d == _parser(ParserCls).parse(_base_bytes().decode("ascii"))


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("blank", [b"", b"  \t  ", b"\t"])
def test_skipped_blank_lines_not_rejected(tmp_path, ParserCls, blank):
    data = _base_bytes()
    lines = data.split(b"\n")
    lines.insert(20, blank)
    path = _write_file(tmp_path, b"\n".join(lines) + b"\n" + blank)
    parser = _parser(ParserCls, accept_non_ascii=False, ignore_blank_lines=True)
    d = parser.parsefile(path)
    assert "\n".join(parser.write(d)).encode("ascii") == data


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_blank_line_after_tend_not_rejected(tmp_path, ParserCls):
    path = _write_file(tmp_path, _base_bytes() + b"\n \t \n")
    d = _parser(ParserCls, accept_non_ascii=False).parsefile(path)
    assert d == _parser(ParserCls).parse(_base_bytes().decode("ascii"))


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("value", ["\x92", "\t", "\xe9"])
def test_writing_rejects_text_value(ParserCls, value):
    parser = _parser(ParserCls, accept_non_ascii=False)
    d = parser.parse(_base_bytes().decode("ascii"))
    auth = d[1][451]["AUTH"]
    d[1][451]["AUTH"] = auth[:4] + value + auth[5:]
    with pytest.raises(InvalidCharacterError) as excinfo:
        parser.write(d)
    msg = str(excinfo.value)
    assert "the string in variable AUTH contains the character" in msg
    assert "at position 5, which is not a printable ASCII character" in msg
    assert f"(U+{ord(value):04X}" in msg
    # accepted by default
    lines = _parser(ParserCls).write(d)
    assert lines[5][33:66] == d[1][451]["AUTH"]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_writing_rejects_verbatim_line(ParserCls):
    parser = _parser(ParserCls, accept_non_ascii=False)
    d = parser.parse(_base_bytes().decode("ascii"), exclude=[1])
    line = d[1][451][4]
    # beyond column 75, the line is not written and not checked
    d[1][451][4] = line[:76] + "\x92" + line[77:]
    parser.write(d)
    d[1][451][4] = line[:20] + "\x92" + line[21:]
    with pytest.raises(InvalidCharacterError) as excinfo:
        parser.write(d)
    msg = str(excinfo.value)
    assert "line 5 of the section MF=1/MT=451 given as a list of strings" in msg
    assert "the character \\x92 (U+0092) at position 21" in msg
    lines = _parser(ParserCls).write(d)
    assert lines[5][:22] == line[:20] + "\x92" + line[21]


@pytest.mark.parametrize("select", ["cpp", "python"])
def test_factory_passes_option(tmp_path, select):
    path = _write_file(tmp_path, cp1252_bytes())
    kwargs = {"print_cache_info": False} if select == "python" else {}
    parser = EndfParserFactory.create(select=select, accept_non_ascii=False, **kwargs)
    with pytest.raises(InvalidCharacterError):
        parser.parsefile(path)
    parser = EndfParserFactory.create(select=select, **kwargs)
    assert parser.parsefile(path)[1][451]["ALAB"] == " BNL     \x92 "


def test_validate_rejects_non_ascii_by_default():
    assert STRICT_DEFAULT_ARGS["accept_non_ascii"] is False
