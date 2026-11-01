############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/01
# Last modified:   2026/11/01
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The failure report of ``endf-cli validate``.

Under the line naming the section, the report gives the line of the
file at which the section starts and the message of the parser error,
with the line numbers it gives counted in the file. A section is parsed
on its own, as a short tape of the TPID record, the lines of the section
and the end records, so that the parser counts the lines of this tape;
``EndfFile`` translates them (``SectionParseError.line`` and
``SectionParseError.detail``).
"""

import argparse
import pickle
from pathlib import Path

import pytest

from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import add_common_cmd_parser_args, get_endf_parser
from endf_parserpy.tape import EndfFile, SectionParseError
from endf_parserpy.tape.endf_file import _message_in_file_lines

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU = TESTDATA / "n_2925_29-Cu-63.endf"
ZN = TESTDATA / "n_3025_30-Zn-64.endf"

# the HEAD record of MF3/MT1 of the Cu-63 file and a line of the body of
# the TAB1 record that follows (line numbers counting from 1)
CU_MF3_HEAD = 866
CU_MF3_BODY = 870


def _args(*argv):
    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap, defaults=validate.STRICT_DEFAULT_ARGS)
    args = vars(ap.parse_args(list(argv)))
    args["subcommand"] = validate.COMMAND_NAME
    return args


@pytest.fixture(scope="module")
def cpp_parsers():
    args = _args()
    return get_endf_parser(args), validate.get_fast_parser(args)


@pytest.fixture(scope="module")
def py_parsers():
    args = _args("--no-cpp")
    return get_endf_parser(args), validate.get_fast_parser(args)


def _lines(path):
    return Path(path).read_bytes().split(b"\n")[:-1]


def _write(path, lines):
    Path(path).write_bytes(b"\n".join(lines) + b"\n")
    return path


def _tape(files):
    """The lines of a tape of the materials of single-material files."""
    bodies = [_lines(f) for f in files]
    out = [bodies[0][0]]
    for body in bodies:
        out += body[1:-1]
    out.append(bodies[0][-1])
    return out


def _set_field(lines, lineno, fieldnum, text):
    lines = list(lines)
    line = lines[lineno - 1]
    start = 11 * fieldnum
    lines[lineno - 1] = line[:start] + text.rjust(11) + line[start + 11 :]
    return lines


def _first_line(lines, mat, mf, mt):
    ctrl = b"%4d%2d%3d" % (mat, mf, mt)
    return next(i + 1 for i, line in enumerate(lines) if line[66:75] == ctrl)


def test_cpp_report_single_material(cpp_parsers, tmp_path):
    lines = _set_field(_lines(CU), CU_MF3_BODY, 1, b"1.2x34E+0")
    path = _write(tmp_path / "bad.endf", lines)
    ok, detail = validate._validate_file(cpp_parsers[0], str(path), cpp_parsers[1])
    assert not ok
    assert detail == (
        "section MF=3/MT=1:\n"
        f"The section starts at line {CU_MF3_HEAD} of the file.\n"
        'malformed number field: "  1.2x34E+0" '
        "(field 2, columns 12-22, in the body of the TAB1 record)\n"
        "Template: [ MAT , 3 , MT / QM , QI , 0 , LR , NR , NP / E / xs ] "
        "TAB1 ( xstable )\n"
        f'Line {CU_MF3_BODY}: "{lines[CU_MF3_BODY - 1].decode()}"'
    )


def test_python_report_single_material(py_parsers, tmp_path):
    lines = _set_field(_lines(CU), CU_MF3_HEAD + 1, 4, b"1.5")
    path = _write(tmp_path / "bad.endf", lines)
    ok, detail = validate._validate_file(py_parsers[0], str(path), py_parsers[1])
    assert not ok
    assert detail.startswith(
        "section MF=3/MT=1:\n"
        f"The section starts at line {CU_MF3_HEAD} of the file.\n"
        "Here is the parser record log until failure:\n"
    )
    # the record log of EndfParserPy counts the lines of the section
    assert f"\n-------- Line {CU_MF3_HEAD} -----------\n" in detail
    assert f"\n-------- Line {CU_MF3_HEAD + 1} -----------\n" in detail
    assert f'"{lines[CU_MF3_HEAD].decode()}"' in detail
    assert "\nError message: " in detail


@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
def test_report_second_material(cpp_parsers, py_parsers, tmp_path, parser_kind):
    parsers = cpp_parsers if parser_kind == "cpp" else py_parsers
    lines = _tape([CU, ZN])
    # a byte outside ASCII in the fifth line of MF3/MT1 of Zn-64
    head = _first_line(lines, 3025, 3, 1)
    bad = head + 4
    lines[bad - 1] = lines[bad - 1][:3] + b"\xe9" + lines[bad - 1][4:]
    path = _write(tmp_path / "tape.endf", lines)
    ok, detail = validate._validate_file(parsers[0], str(path), parsers[1])
    assert not ok
    assert detail.startswith(
        "material #1 (MAT 3025), section MF=3/MT=1:\n"
        f"The section starts at line {head} of the file.\n"
        f"line {bad}, column 4 (MAT/MF/MT 3025/3/1) contains byte 0xe9 "
    )


def test_cpp_report_second_material_number(cpp_parsers, tmp_path):
    lines = _tape([CU, ZN])
    head = _first_line(lines, 3025, 3, 1)
    lines = _set_field(lines, head + 4, 0, b"x")
    path = _write(tmp_path / "tape.endf", lines)
    ok, detail = validate._validate_file(cpp_parsers[0], str(path), cpp_parsers[1])
    assert not ok
    assert detail.startswith(
        "material #1 (MAT 3025), section MF=3/MT=1:\n"
        f"The section starts at line {head} of the file.\n"
        'malformed number field: "          x" (field 1, columns 1-11, '
    )
    assert detail.endswith(f'\nLine {head + 4}: "{lines[head + 3].decode()}"')


def test_section_parse_error_attributes(cpp_parsers, tmp_path):
    lines = _set_field(_lines(CU), CU_MF3_BODY, 1, b"1.2x34E+0")
    path = _write(tmp_path / "bad.endf", lines)
    for on_error in ("raise", "mark"):
        endf_file = EndfFile(path, parser=cpp_parsers[0], on_error=on_error)
        with pytest.raises(SectionParseError) as excinfo:
            endf_file[0][3, 1]
        exc = excinfo.value
        assert (exc.position, exc.mat, exc.mf, exc.mt) == (0, 2925, 3, 1)
        assert exc.line == CU_MF3_HEAD
        assert isinstance(exc.__cause__, RuntimeError)
        # the parser counts the lines of the tape of the section
        assert "\nLine 6: " in str(exc.__cause__)
        assert exc.detail == str(exc.__cause__).replace(
            "\nLine 6: ", f"\nLine {CU_MF3_BODY}: "
        )
        copy = pickle.loads(pickle.dumps(exc))
        assert (copy.line, copy.detail, copy.mf) == (exc.line, exc.detail, 3)


def test_message_in_file_lines():
    # a section of 4 lines starting at line 100 of the file; the tape of
    # the section handed to the parser has the TPID record as line 1 and
    # the added FEND, MEND and TEND records as lines 6 to 8
    lines = ["head", "", "data", "send"]
    cases = [
        ('Line 4: "x"', 'Line 102: "x"'),
        (
            "Hint: line 3 is longer than 80 columns",
            "Hint: line 101 is longer than 80 columns",
        ),
        (
            "End of the data reached after line 5",
            "End of the data reached after line 103",
        ),
        (
            "line 2, column 4 (MAT/MF/MT 1/3/1) contains",
            "line 100, column 4 (MAT/MF/MT 1/3/1) contains",
        ),
        (
            "line 5, column 1 of the input contains",
            "line 103, column 1 of the input contains",
        ),
        # counting from 0 (EndfParserPy)
        (
            "encountered MT=2 in control record of line 3.",
            "encountered MT=2 in control record of line 102.",
        ),
        ("Line 1 is a blank line.", "Line 100 is a blank line."),
        # the record log of EndfParserPy counts the lines of the section
        # without blank lines from 0
        ("-------- Line 0 -----------", "-------- Line 100 -----------"),
        ("-------- Line 1 -----------", "-------- Line 102 -----------"),
        ("-------- Line 2 -----------", "-------- Line 103 -----------"),
        # the end records added after the section (lines 6 to 8)
        (
            'Line 6: "x"',
            'Line after the section (FEND record added to parse it alone): "x"',
        ),
        (
            "End of the data reached after line 8",
            "End of the data reached after the section and the end records "
            "added to parse it alone",
        ),
        (
            "encountered MAT=0 in control record of line 6.",
            "encountered MAT=0 in control record of the MEND record added "
            "after the section.",
        ),
        # unchanged: the TPID record and other numbers
        ('Line 1: "tpid"', 'Line 1: "tpid"'),
        ('Line:     "line 3"', 'Line:     "line 3"'),
        ("expected 3 values in line 5", "expected 3 values in line 5"),
    ]
    for message, expected in cases:
        assert _message_in_file_lines(message, 100, lines) == expected


def test_builtin_exception_named():
    try:
        try:
            [][0]
        except IndexError as cause:
            raise SectionParseError("failed", line=12, detail=str(cause)) from cause
    except SectionParseError as exc:
        detail = validate._failure_detail(exc)
    assert detail == (
        "The section starts at line 12 of the file.\n"
        "IndexError: list index out of range"
    )
    # errors other than SectionParseError are reported by their message
    assert validate._failure_detail(ValueError("no tape")) == "no tape"
