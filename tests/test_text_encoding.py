############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Bytes outside ASCII in ENDF-6 files (issue #77, problems 2 and 3).

Both parsers map every byte of a file to the character with the same
code and back (Latin-1), on every platform: a byte that is not valid
UTF-8, e.g. the Windows-1252 apostrophe 0x92, no longer raises a
UnicodeDecodeError, the columns of a line are byte positions in both
parsers, and reading and writing a file reproduces its bytes. Strings
with characters above U+00FF cannot correspond to bytes; parsing or
writing them raises an InvalidCharacterError.

The tests use the default format flavor of EndfParserCpp only: with
several C++ modules loaded in one process, an exception raised in the
second module may arrive as "Caught an unknown exception!" with the
toolchain used for some builds.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import InvalidCharacterError
from endf_parserpy.tape import parse_tape_file, write_tape_file


TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"
PARSERS = [EndfParserCpp, EndfParserPy]
ARRAY_TYPES = ["dict", "list", "numpy"]

# line 6 (index 5) of the test file is the first line of the MF1/MT451
# description: ZSYMAM (columns 1-11), ALAB (12-22), EDATE (23-32), AUTH
# (34-66); column 21 (index 20) is the last but one column of ALAB
TEXT_LINE = 5
TEXT_COL = 20


_BASE = []


def _base_bytes():
    # the test file with line numbers in columns 76-80, i.e. with lines of
    # 80 columns, as written by the parsers (without a line ending after
    # the TEND record); the file is pure ASCII
    if not _BASE:
        parser = _parser(EndfParserPy)
        lines = parser.write(parser.parsefile(TESTFILE))
        _BASE.append("\n".join(lines).encode("ascii"))
    return _BASE[0]


def _modify_line(data, lineidx, col, new, num_replaced=None):
    lines = data.split(b"\n")
    if num_replaced is None:
        num_replaced = len(new)
    line = lines[lineidx]
    lines[lineidx] = line[:col] + new + line[col + num_replaced :]
    return b"\n".join(lines)


def cp1252_bytes():
    # Windows-1252 apostrophe in place of a blank (the line keeps 75 bytes)
    return _modify_line(_base_bytes(), TEXT_LINE, TEXT_COL, b"\x92")


def utf8_same_length_bytes():
    # UTF-8 encoded U+2019 (three bytes) in place of three blanks of AUTH
    return _modify_line(_base_bytes(), TEXT_LINE, 60, "\u2019".encode("utf-8"))


def utf8_inserted_bytes():
    # UTF-8 encoded U+2019 in place of one blank: the line has 82 bytes and
    # its MAT/MF/MT columns are shifted by two columns
    return _modify_line(_base_bytes(), TEXT_LINE, TEXT_COL, "\u2019".encode("utf-8"), 1)


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


def _write_file(tmp_path, data, name="case.endf"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("exclude", [None, [1]])
def test_cp1252_byte_is_parsed(tmp_path, ParserCls, exclude):
    path = _write_file(tmp_path, cp1252_bytes())
    parser = _parser(ParserCls)
    d = parser.parsefile(path, exclude=exclude)
    if exclude is None:
        assert d[1][451]["ALAB"] == " BNL     \x92 "
    else:
        # the first line of the section is its HEAD record
        assert d[1][451][TEXT_LINE - 1][:22] == " 94-Pu-244  BNL     \x92 "
        assert d[1][451][TEXT_LINE - 1].endswith("3564 1451    5\n")


@pytest.mark.parametrize("data_fun", [cp1252_bytes, utf8_same_length_bytes])
@pytest.mark.parametrize("exclude", [None, [1]])
def test_text_identical_in_both_parsers(tmp_path, data_fun, exclude):
    path = _write_file(tmp_path, data_fun())
    res_cpp = _parser(EndfParserCpp).parsefile(path, exclude=exclude)
    res_py = _parser(EndfParserPy).parsefile(path, exclude=exclude)
    assert res_cpp[1][451] == res_py[1][451]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_utf8_bytes_are_latin1_decoded(tmp_path, ParserCls):
    path = _write_file(tmp_path, utf8_same_length_bytes())
    d = _parser(ParserCls).parsefile(path)
    auth = d[1][451]["AUTH"]
    assert len(auth) == 33
    assert "\xe2\x80\x99" in auth


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_utf8_inserted_bytes_fail_with_exclude(tmp_path, ParserCls):
    # the MF/MT columns of the shifted line do not belong to MF1/MT451
    path = _write_file(tmp_path, utf8_inserted_bytes())
    with pytest.raises(Exception):
        _parser(ParserCls).parsefile(path, exclude=[1])


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("arrtype", ARRAY_TYPES)
@pytest.mark.parametrize("exclude", [None, [1]])
@pytest.mark.parametrize("data_fun", [cp1252_bytes, utf8_same_length_bytes])
def test_file_round_trip_is_byte_exact(tmp_path, ParserCls, arrtype, exclude, data_fun):
    data = data_fun()
    path = _write_file(tmp_path, data)
    parser = _parser(ParserCls, array_type=arrtype)
    d = parser.parsefile(path, exclude=exclude)
    outpath = tmp_path / "out.endf"
    parser.writefile(outpath, d, exclude=None)
    assert outpath.read_bytes() == data


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("arrtype", ARRAY_TYPES)
@pytest.mark.parametrize("data_fun", [cp1252_bytes, utf8_same_length_bytes])
def test_string_round_trip(ParserCls, arrtype, data_fun):
    text = data_fun().decode("latin-1")
    parser = _parser(ParserCls, array_type=arrtype)
    for inp in (text, text.split("\n")):
        d = parser.parse(inp)
        assert "\n".join(parser.write(d)) == text


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_tape_file_round_trip(tmp_path, ParserCls):
    data = cp1252_bytes()
    path = _write_file(tmp_path, data)
    parser = _parser(ParserCls)
    materials = parse_tape_file(path, parser=parser, on_error="raise")
    assert materials[0][1][451]["ALAB"] == " BNL     \x92 "
    outpath = tmp_path / "out.endf"
    write_tape_file(materials, outpath, parser=parser)
    # the tape writer ends the last line with a line ending
    assert outpath.read_bytes() == data + b"\n"


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_writing_character_above_ff_names_variable(ParserCls):
    parser = _parser(ParserCls)
    d = parser.parsefile(TESTFILE)
    auth = d[1][451]["AUTH"]
    d[1][451]["AUTH"] = auth[:10] + "\u2019" + auth[11:]
    with pytest.raises(InvalidCharacterError) as excinfo:
        parser.write(d)
    msg = str(excinfo.value)
    assert "the string in variable AUTH contains the character U+2019" in msg
    assert "RIGHT SINGLE QUOTATION MARK" in msg
    assert "at position 11" in msg


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_writing_verbatim_line_above_ff_names_line(ParserCls):
    parser = _parser(ParserCls)
    d = parser.parsefile(TESTFILE, exclude=[1])
    line = d[1][451][2]
    d[1][451][2] = line[:5] + "\u20ac" + line[6:]
    with pytest.raises(InvalidCharacterError) as excinfo:
        parser.write(d)
    msg = str(excinfo.value)
    assert "line 3 of the section MF=1/MT=451 given as a list of strings" in msg
    assert "U+20AC, EURO SIGN at position 6" in msg


@pytest.mark.parametrize("as_list", [False, True])
def test_parsing_character_above_ff_same_error(as_list):
    lines = _base_bytes().decode("latin-1").split("\n")
    line = lines[TEXT_LINE]
    lines[TEXT_LINE] = line[:TEXT_COL] + "\u2019" + line[TEXT_COL + 1 :]
    text = "\n".join(lines)
    inp = text.split("\n") if as_list else text
    messages = []
    for ParserCls in PARSERS:
        with pytest.raises(InvalidCharacterError) as excinfo:
            _parser(ParserCls).parse(inp)
        messages.append(str(excinfo.value))
    assert messages[0] == messages[1]
    assert messages[0].startswith(
        "line 6, column 21 of the input contains the character "
        "U+2019, RIGHT SINGLE QUOTATION MARK"
    )


def test_cpp_module_accepts_bytes_and_str():
    from endf_parserpy.cpp_parsers.endf6_ext import parse_endf

    data = cp1252_bytes()
    res_bytes = parse_endf(data, parse_opts={})
    res_str = parse_endf(data.decode("latin-1"), parse_opts={})
    assert res_bytes[1][451]["ALAB"] == " BNL     \x92 "
    assert res_bytes == res_str
