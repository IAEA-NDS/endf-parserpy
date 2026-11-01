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

"""Context in the error messages of EndfParserCpp.

A message ends with the template of the record being read (if any), the
number and the content of the last line read (or that the end of the
data was reached) and, for a line longer than 80 columns, a hint. An
invalid number field and a value mismatch name the field (number and
columns) and, for the first line of a record, the variable of the
template; for a line of the body of a TAB1 or LIST record, the record
type. The template and the line are given once, also for value
mismatches, whose messages contained them before.

The tests use the default format flavor of EndfParserCpp only (see
test_text_encoding.py).
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp


TESTDATA = Path(__file__).parent / "testdata"
NEUTRON = TESTDATA / "n_2925_29-Cu-63.endf"
DECAY = TESTDATA / "dec-094_Pu_244.endf"

# line numbers (counting from 1) in the neutron file: the FEND record
# of MF2, the HEAD and TAB1 records of MF3/MT1 and a line of the body
# of the TAB1 record
MF2_FEND = 865
MF3_HEAD = 866
MF3_TAB1 = 867
MF3_BODY = 870
HEAD_TEMPLATE = "[ MAT , 3 , MT / ZA , AWR , 0 , 0 , 0 , 0 ] HEAD"
TAB1_TEMPLATE = (
    "[ MAT , 3 , MT / QM , QI , 0 , LR , NR , NP / E / xs ] TAB1 ( xstable )"
)
# a LIST record of MF8/MT457 in the decay file (header and first body line)
LIST_HEAD = 48
LIST_BODY = 49


def _lines(path):
    return path.read_bytes().decode("latin-1").split("\n")[:-1]


def _set_field(lines, lineno, fieldnum, text):
    # field fieldnum (counting from 0) of line lineno (counting from 1)
    lines = list(lines)
    line = lines[lineno - 1]
    start = 11 * fieldnum
    lines[lineno - 1] = line[:start] + text.rjust(11) + line[start + 11 :]
    return lines


def _error(lines, **kwargs):
    with pytest.raises(RuntimeError) as excinfo:
        EndfParserCpp(**kwargs).parse("\n".join(lines) + "\n")
    msg = str(excinfo.value)
    assert msg.isascii()
    assert "unknown exception" not in msg
    # the marker of the body of a record is never shown
    assert "\\x01" not in msg
    assert msg.count("Template: ") <= 1
    assert msg.count("\nLine ") <= 1
    return msg


def _line_part(lines, lineno):
    return f'\nLine {lineno}: "{lines[lineno - 1]}"'


def test_malformed_number_in_header_record():
    lines = _set_field(_lines(NEUTRON), MF3_HEAD, 1, "1.0x")
    msg = _error(lines)
    assert msg.startswith(
        'malformed number field: "       1.0x" '
        "(field 2, columns 12-22, variable AWR)\n"
    )
    assert f"\nTemplate: {HEAD_TEMPLATE}\n" in msg
    assert msg.endswith(_line_part(lines, MF3_HEAD))


def test_invalid_integer_in_first_line_of_tab1():
    lines = _set_field(_lines(NEUTRON), MF3_TAB1, 4, "1.5")
    msg = _error(lines)
    assert msg.startswith(
        'invalid integer in field: "        1.5" '
        "(field 5, columns 45-55, variable NR).\n"
    )
    assert f"\nTemplate: {TAB1_TEMPLATE}\n" in msg
    assert msg.endswith(_line_part(lines, MF3_TAB1))


@pytest.mark.parametrize("load_file_into_memory", [True, False])
def test_malformed_number_in_body_of_tab1(tmp_path, load_file_into_memory):
    lines = _set_field(_lines(NEUTRON), MF3_BODY, 1, "1.2x34E+0")
    expected_start = (
        'malformed number field: "  1.2x34E+0" '
        "(field 2, columns 12-22, in the body of the TAB1 record)\n"
    )
    msg = _error(lines)
    assert msg.startswith(expected_start)
    assert f"\nTemplate: {TAB1_TEMPLATE}\n" in msg
    assert msg.endswith(_line_part(lines, MF3_BODY))
    # the same message when the file is parsed
    path = tmp_path / "data.endf"
    path.write_bytes(("\n".join(lines) + "\n").encode("latin-1"))
    parser = EndfParserCpp(load_file_into_memory=load_file_into_memory)
    with pytest.raises(RuntimeError) as excinfo:
        parser.parsefile(str(path))
    assert str(excinfo.value) == msg


def test_number_with_spaces_and_non_finite_value():
    lines = _set_field(_lines(NEUTRON), MF3_BODY, 2, "1.0 0")
    msg = _error(lines, accept_spaces=False)
    assert msg.startswith(
        'encountered number with spaces: "      1.0 0" '
        "(field 3, columns 23-33, in the body of the TAB1 record)\n"
    )
    lines = _set_field(_lines(NEUTRON), MF3_HEAD, 0, "1.0+400")
    msg = _error(lines, accept_nan_inf=False)
    assert msg.startswith(
        'non-finite value (overflow / inf / NaN) in field: "    1.0+400" '
        "(field 1, columns 1-11, variable ZA). "
        "Set `accept_nan_inf=true` to allow non-finite values.\n"
    )


def test_malformed_number_in_body_of_list():
    lines = _set_field(_lines(DECAY), LIST_BODY, 2, "x")
    msg = _error(lines)
    assert msg.startswith(
        'malformed number field: "          x" '
        "(field 3, columns 23-33, in the body of the LIST record)\n"
    )
    assert "\nTemplate: [ MAT , 8 , 457 / " in msg
    assert msg.endswith(_line_part(lines, LIST_BODY))


def test_number_mismatch_names_field():
    lines = _set_field(_lines(NEUTRON), MF3_HEAD, 2, "1")
    msg = _error(lines, ignore_zero_mismatch=False)
    assert msg == (
        "Expected a field to contain the value 0 but found instead the value 1 "
        "(field 3, columns 23-33).\n"
        f"Template: {HEAD_TEMPLATE}" + _line_part(lines, MF3_HEAD)
    )


def test_control_record_mismatch():
    lines = _lines(NEUTRON)
    line = lines[MF3_BODY - 1]
    lines[MF3_BODY - 1] = line[:66] + "2926" + line[70:]
    msg = _error(lines, validate_control_records=True)
    assert msg == (
        "Invalid MAT encountered! Expected MAT=2925 but found MAT=2926\n"
        f"Template: {TAB1_TEMPLATE}" + _line_part(lines, MF3_BODY)
    )


def test_send_record_expected():
    # with NP reduced, the TAB1 record ends before the SEND record
    lines = _set_field(_lines(NEUTRON), MF3_TAB1, 5, "99")
    msg = _error(lines)
    assert msg.startswith("Expected SEND record does not contain one!\n")
    assert "\nTemplate: SEND\n" in msg
    assert msg.endswith(_line_part(lines, MF3_TAB1 + 1 + 1 + 33))


def test_end_of_data():
    # the data ends in the body of the TAB1 record
    lines = _lines(NEUTRON)[:880]
    msg = _error(lines)
    assert msg.startswith("Blank line detected")
    assert f"\nTemplate: {TAB1_TEMPLATE}\n" in msg
    assert msg.endswith("\nEnd of the data reached after line 880")


def test_no_template_outside_sections():
    # a record with MF=0 and MT=1 after the FEND record of MF2
    lines = _lines(NEUTRON)
    assert lines[MF2_FEND - 1][66:75] == "2925 0  0"
    lines.insert(MF2_FEND, lines[MF2_FEND - 1][:66] + "2925 0  1")
    msg = _error(lines)
    assert msg.startswith("Invalid line encountered!")
    assert "Template" not in msg
    assert msg.endswith(_line_part(lines, MF2_FEND + 1))
