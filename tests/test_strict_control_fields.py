############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Non-numeric MAT/MF/MT fields are rejected by both parsers.

EndfParserCpp read the MAT, MF and MT numbers with std::atoi, which reads
non-numeric text as zero ("ab") and stops at the first non-digit ("8x"
reads as 8), so that it accepted lines that EndfParserPy, which reads
these fields with int(), rejects. A field must now be blank (zero) or
hold an integer with an optional sign, preceded and followed by blanks
only, and the MAT/MF/MT fields of every line are checked, also if the
numbers are not compared (validate_control_records=False). The fields of
INTG records are read in the same way, and so is the first line of a
section given as a list of lines when it is written.

EndfParserPy reads these fields and the other integer fields with the same
grammar: int() also accepts other whitespace than blanks (e.g. a tab)
around the number, underscores between digits and digits outside ASCII.
Neither parser accepts tabs, other whitespace than blanks and underscores
in float fields either (float() of Python accepts them; std::strtod skips
whitespace before the number).
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import (
    InvalidFloatError,
    InvalidIntegerError,
)
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.text_encoding import escape_text


TESTDATA = Path(__file__).parent / "testdata"
TESTFILE = TESTDATA / "dec-094_Pu_244.endf"

# the (75-column) lines of the file, read into memory once
LINES = TESTFILE.read_text().splitlines()

# TAB1 form of MF1/MT452 (LNU=2) in place of the LIST form (lines 42 to
# 44), so that the file also has a TAB1 record whose body has two lines
_TAB1_MF1_MT452 = [
    " 9.424400+4 2.419676+2          0          2          0          03564 1452",
    " 0.000000+0 0.000000+0          0          0          1          43564 1452",
    "          4          2                                            3564 1452",
    " 1.000000-5 2.290000+0 1.000000+6 2.300000+0 1.000000+7 2.400000+03564 1452",
    " 2.000000+7 2.500000+0                                            3564 1452",
]
BASE_LINES = LINES[:41] + _TAB1_MF1_MT452 + LINES[44:]


def _find(prefix, ctrl=None):
    """The first line starting with prefix (and with the control columns
    ctrl, if given)."""
    for i, line in enumerate(BASE_LINES):
        if line.startswith(prefix) and (ctrl is None or line[66:75] == ctrl):
            return i
    raise LookupError(prefix)


# line indices (counting from 0) of the records whose fields are damaged
IDX = {
    "tape_head": 0,
    "head": _find(" 9.424400+4 2.419676+2          0          0"),
    "cont": _find(" 2.55932+15"),
    "tab1_body": _find(" 1.000000-5 2.290000+0"),
    # the first of the two body lines of a LIST record (NPL=12): the
    # bulk form reads such a body as one byte range if the MAT/MF/MT
    # columns of its lines are those of the section
    "list_body": _find(" 6.000000+0 0.000000+0 1.842000+8"),
    "send": _find("", "3564 1  0"),
    "fend": _find("", "3564 0  0"),
    "mend": _find("", "   0 0  0"),
    "tend": _find("", "  -1 0  0"),
}

COLUMNS = {"MAT": (66, 4), "MF": (70, 2), "MT": (72, 3)}


def _replace(line, field, text):
    start, length = COLUMNS[field]
    assert len(text) == length
    line = line.ljust(75)
    return line[:start] + text + line[start + length :]


def _text(lines):
    return "\n".join(lines) + "\n"


def _damaged(record, field, text):
    lines = list(BASE_LINES)
    i = IDX[record]
    lines[i] = _replace(lines[i], field, text)
    return _text(lines)


FILTERS = [
    {},
    {"include": [(8, 457)]},
    {"include": [1]},
    {"exclude": [(1, 452)]},
    {"exclude": [8]},
]
FILTER_IDS = ["full", "include_mfmt", "include_mf", "exclude_mfmt", "exclude_mf"]


def _parsers(array_type="dict"):
    return (
        EndfParserCpp(array_type=array_type),
        EndfParserPy(array_type=array_type),
    )


def test_base_file_parses_identically():
    cpp, py = _parsers()
    text = _text(BASE_LINES)
    res_cpp = cpp.parse(text)
    res_py = py.parse(text)
    assert compare_objects(res_cpp, res_py, fail_on_diff=False)
    assert res_cpp[1][452]["LNU"] == 2
    assert len(res_cpp[1][452]["nu"]) == 4


# fields that are neither blank nor an integer between blanks
INVALID = {
    "MAT": ["ab  ", "35x4", "3 64", "-   ", "+-1 ", "35\t4"],
    "MF": ["8x", "x8", "- ", "1.", "++", "\t\t"],
    "MT": ["ab ", " x ", "4 7", "45-", "- 1", "4\t5", "1e2"],
}

# the cases tested for all records and filters (one per field and kind)
INVALID_SHORT = {
    "MAT": ["ab  ", "3 64", "3\t64"],
    "MF": ["8x", "x ", "--"],
    "MT": ["ab ", " x ", "4 7"],
}

# the value of the field of each record as written in the file
VALUES = {}
for _rec, _i in IDX.items():
    _line = BASE_LINES[_i].ljust(75)
    VALUES[_rec] = {f: _line[s : s + n].strip() or "0" for f, (s, n) in COLUMNS.items()}


def _valid_forms(field, value):
    """Forms of an integer accepted by both parsers: blanks before and
    after it and a sign."""
    length = COLUMNS[field][1]
    value = int(value)
    forms = [str(value).rjust(length), str(value).ljust(length)]
    if value >= 0 and len(str(value)) < length:
        forms.append(("+" + str(value)).rjust(length))
        forms.append(("+" + str(value)).ljust(length))
        if len(str(value)) < length - 1:
            forms.append((" +" + str(value)).ljust(length))
    if value == 0:
        forms.append(" " * length)
        forms.append("-0".rjust(length))
        forms.append("0".zfill(length))
    elif len(str(value)) < length:
        forms.append(str(value).zfill(length))
    return sorted(set(f for f in forms if len(f) == length))


def _cpp_parse_error(cpp, text, **kwargs):
    with pytest.raises(RuntimeError) as excinfo:
        cpp.parse(text, **kwargs)
    return str(excinfo.value)


@pytest.mark.parametrize("kwargs", FILTERS, ids=FILTER_IDS)
@pytest.mark.parametrize("record", sorted(IDX))
@pytest.mark.parametrize(
    "field,text",
    [(f, t) for f in sorted(INVALID_SHORT) for t in INVALID_SHORT[f]],
)
def test_invalid_field_rejected_by_both(record, field, text, kwargs):
    damaged = _damaged(record, field, text)
    cpp, py = _parsers()
    msg = _cpp_parse_error(cpp, damaged, **kwargs)
    with pytest.raises(Exception):
        py.parse(damaged, **kwargs)
    start, length = COLUMNS[field]
    columns = f"(columns {start + 1}-{start + length})"
    # the error names the field; the line follows the message
    expected = f'invalid {field} number field: "{text}" {columns}'
    expected = expected.replace("\t", "\\t")
    assert expected in msg
    assert f"Line {IDX[record] + 1}: " in msg


@pytest.mark.parametrize(
    "field,text", [(f, t) for f in sorted(INVALID) for t in INVALID[f]]
)
@pytest.mark.parametrize("record", ["head", "list_body", "tab1_body"])
def test_more_invalid_forms_rejected_by_both(record, field, text):
    damaged = _damaged(record, field, text)
    cpp, py = _parsers()
    _cpp_parse_error(cpp, damaged)
    with pytest.raises(Exception):
        py.parse(damaged)


def test_error_message_names_template_and_line():
    damaged = _damaged("list_body", "MF", "8x")
    cpp, _ = _parsers()
    msg = _cpp_parse_error(cpp, damaged)
    line = BASE_LINES[IDX["list_body"]]
    assert msg.startswith('invalid MF number field: "8x" (columns 71-72)')
    assert "\nTemplate: " in msg
    assert "LIST" in msg
    assert f'Line {IDX["list_body"] + 1}: "{_replace(line, "MF", "8x")}"' in msg


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
@pytest.mark.parametrize("kwargs", FILTERS, ids=FILTER_IDS)
@pytest.mark.parametrize("record", sorted(IDX))
@pytest.mark.parametrize("field", sorted(COLUMNS))
def test_valid_forms_accepted_by_both(record, field, kwargs, atype):
    cpp, py = _parsers(atype)
    reference = cpp.parse(_text(BASE_LINES), **kwargs)
    value = VALUES[record][field]
    for form in _valid_forms(field, value):
        text = _damaged(record, field, form)
        res_cpp = cpp.parse(text, **kwargs)
        res_py = py.parse(text, **kwargs)
        assert compare_objects(res_cpp, res_py, fail_on_diff=False), form
        # the same data as without the change of the field, except for
        # the sections kept as lines (e.g. the tape head)
        for mf in reference:
            for mt in reference[mf]:
                if not isinstance(reference[mf][mt], list):
                    assert compare_objects(
                        res_cpp[mf][mt], reference[mf][mt], fail_on_diff=False
                    ), form


def test_valid_forms_cover_signs_and_blanks():
    assert _valid_forms("MF", "8") == sorted({" 8", "8 ", "+8", "08"})
    assert "  +1" in _valid_forms("MAT", "1")
    assert " -1 " not in _valid_forms("MAT", "-1")
    assert "  -1" in _valid_forms("MAT", "-1")
    assert "-1  " in _valid_forms("MAT", "-1")


@pytest.mark.parametrize("field,text", [("MAT", " -1 "), ("MT", " +1"), ("MT", "+1 ")])
def test_signed_number_between_blanks(field, text):
    # a sign directly before the digits, blanks before and after
    lines = list(BASE_LINES)
    i = IDX["tend"] if field == "MAT" else IDX["tape_head"]
    if field == "MT":
        # the MT number of the tape head must be 0; use MAT instead
        field, text = "MAT", text + " "
    lines[i] = _replace(lines[i], field, text)
    cpp, py = _parsers()
    res_cpp = cpp.parse(_text(lines))
    res_py = py.parse(_text(lines))
    assert compare_objects(res_cpp, res_py, fail_on_diff=False)


def test_validate_control_records_option():
    damaged = _damaged("list_body", "MT", "4 7")
    cpp = EndfParserCpp(validate_control_records=True)
    msg = _cpp_parse_error(cpp, damaged)
    assert 'invalid MT number field: "4 7" (columns 73-75)' in msg


# the characters of Latin-1 (a byte of a file is read as the character
# with its code) that int() and float() of Python accept around a number
# (whitespace other than blanks: tab, vertical tab, form feed, carriage
# return, next line 0x85 and the no-break space 0xa0); they are not part
# of a number for either parser
OTHER_WHITESPACE = ["\t", "\x0b", "\x0c", "\r", "\x85", "\xa0"]


def _other_forms(value, length):
    """Forms of value that int() accepts but that are not an integer
    between blanks: other whitespace before or after the number, an
    underscore between digits and a field of only tabs for zero."""
    forms = []
    for ws in OTHER_WHITESPACE:
        forms.append((ws + value).rjust(length))
        forms.append((value + ws).ljust(length))
    sign = value[:1] if value[:1] in "+-" else ""
    digits = value[len(sign) :]
    forms.append((sign + "0_" + digits).rjust(length))
    if len(digits) >= 2:
        forms.append((sign + digits[0] + "_" + digits[1:]).rjust(length))
    if int(value) == 0:
        forms.append("\t" * length)
        forms.append(" \t".rjust(length))
    # (a carriage return at the end of the MT field is the line ending of
    # a line of 75 columns)
    forms = [f for f in forms if len(f) == length and f[-1] != "\r"]
    for form in forms:
        assert int(form if form.strip() else "0") == int(value)
    if not forms:
        # a value of the width of the field: the forms of a shorter one
        # (int() accepts them, the value differs)
        return _other_forms(value[:-1], length)
    return sorted(set(forms))


def test_other_forms_accepted_by_int():
    assert "0_0" in _other_forms("0", 3)
    assert "\t8" in _other_forms("8", 2)
    assert "3_56" in _other_forms("3564", 4)
    assert "\t356" in _other_forms("3564", 4)
    assert "\t\t" in _other_forms("0", 2)
    assert "-0_1" in _other_forms("-1", 4)


@pytest.mark.parametrize("kwargs", FILTERS[:2], ids=FILTER_IDS[:2])
@pytest.mark.parametrize("record", sorted(IDX))
@pytest.mark.parametrize("field", sorted(COLUMNS))
def test_other_characters_rejected_by_both(record, field, kwargs):
    # the same error from both parsers: the field and its columns
    start, length = COLUMNS[field]
    columns = f"(columns {start + 1}-{start + length})"
    cpp, py = _parsers()
    forms = _other_forms(VALUES[record][field], length)
    assert len(forms) >= 3
    for text in forms:
        damaged = _damaged(record, field, text)
        expected = f'invalid {field} number field: "{escape_text(text)}" {columns}'
        msg = _cpp_parse_error(cpp, damaged, **kwargs)
        assert expected in msg, repr(text)
        with pytest.raises(ValueError) as excinfo:
            py.parse(damaged, **kwargs)
        assert expected in str(excinfo.value), repr(text)


@pytest.mark.parametrize(
    "record,field,text",
    [
        ("list_body", "MF", "\u0668"),
        ("tape_head", "MT", "\u0660"),
        ("head", "MAT", "\u0663564"),
    ],
)
def test_non_ascii_digits_rejected_by_both(record, field, text):
    # int() accepts digits outside ASCII (here Arabic-Indic digits); a
    # character above U+00FF cannot be a byte of a file and is rejected
    # with the input of either parser
    text = text.rjust(COLUMNS[field][1])
    assert int(text) == int(VALUES[record][field])
    damaged = _damaged(record, field, text)
    for parser in _parsers():
        with pytest.raises(Exception, match="U\\+066"):
            parser.parse(damaged)


@pytest.mark.parametrize(
    "record,field,text",
    [
        ("list_body", "MF", "\t8"),
        ("list_body", "MF", "8\t"),
        ("tape_head", "MAT", "\t  1"),
        ("tape_head", "MAT", "1 \t "),
    ],
)
def test_tab_with_accept_non_ascii_false(record, field, text):
    # a tab is not printable ASCII: with accept_non_ascii=False (e.g. in
    # endf-cli validate), this is the error of both parsers
    damaged = _damaged(record, field, text)
    for parser in (
        EndfParserCpp(accept_non_ascii=False),
        EndfParserPy(accept_non_ascii=False),
    ):
        with pytest.raises(Exception, match="not a printable ASCII character"):
            parser.parse(damaged)


def test_line_endings_of_short_lines():
    # the line ending of a line that ends within the control fields is
    # not part of a field (EndfParserCpp pads such a line with blanks)
    lines = list(BASE_LINES)
    i = IDX["mend"]
    assert lines[i][66:75] == "   0 0  0"
    lines[i] = lines[i][:70]
    cpp, py = _parsers()
    reference = cpp.parse(_text(BASE_LINES))
    for ending in ("\n", "\r\n"):
        text = ending.join(lines) + ending
        res_cpp = cpp.parse(text)
        assert compare_objects(res_cpp, reference, fail_on_diff=False)
        assert compare_objects(py.parse(text), res_cpp, fail_on_diff=False)
        # as read from a file (with the line endings)
        res_py = py.parse([line + ending for line in lines])
        assert compare_objects(res_py, res_cpp, fail_on_diff=False)


# the integer fields L1, L2, N1 and N2 (counting from 0: fields 2 to 5) of
# records, and the NBT/INT values of a TAB1 record; (record, line index,
# field) with the value of the field
INT_FIELDS = {
    "head_L1": (IDX["head"], 2),
    "head_N2": (IDX["head"], 5),
    "cont_L2": (IDX["cont"], 3),
    "cont_N1": (IDX["cont"], 4),
    "tab1_NR": (IDX["tab1_body"] - 2, 4),
    "tab1_NP": (IDX["tab1_body"] - 2, 5),
    "tab1_NBT": (IDX["tab1_body"] - 1, 0),
    "tab1_INT": (IDX["tab1_body"] - 1, 1),
    "list_NPL": (IDX["list_body"] - 1, 4),
    "list_N2": (IDX["list_body"] - 1, 5),
}

# float fields: C1 and C2 of records, a value of a TAB1 body and two values
# of a LIST body (read in its bulk form if the line is valid)
FLOAT_FIELDS = {
    "head_C1": (IDX["head"], 0),
    "head_C2": (IDX["head"], 1),
    "cont_C1": (IDX["cont"], 0),
    "tab1_x": (IDX["tab1_body"], 2),
    "tab1_y": (IDX["tab1_body"], 5),
    "list_first": (IDX["list_body"], 0),
    "list_last": (IDX["list_body"], 5),
}


def _field_text(line_index, fieldnum):
    line = BASE_LINES[line_index].ljust(75)
    return line[11 * fieldnum : 11 * fieldnum + 11]


def _with_field(line_index, fieldnum, text):
    assert len(text) == 11
    lines = list(BASE_LINES)
    line = lines[line_index].ljust(75)
    lines[line_index] = line[: 11 * fieldnum] + text + line[11 * fieldnum + 11 :]
    return _text(lines)


def _float_forms(value):
    """Forms of value (an 11-character float field) that float() accepts
    after the steps of EndfParserPy (e.g. the 'E' inserted before the
    sign of the exponent) but that are not a number of an ENDF-6 field."""
    number = value.strip(" ")
    assert len(number) < 11
    forms = []
    for ws in OTHER_WHITESPACE:
        forms.append((ws + number).rjust(11))
        if ws != "\r":
            # (a carriage return at the end of a field may be the line
            # ending of a short line for EndfParserPy, see the PR notes)
            forms.append((number + ws).rjust(11))
    # an underscore between two digits of the mantissa
    k = next(i for i in range(1, len(number)) if number[i - 1 : i + 1].isdigit())
    forms.append((number[:k] + "_" + number[k:]).rjust(11))
    return forms


def _float_value_of(form):
    # the value of a form for float(), as EndfParserPy read it before
    s = form.strip()
    s = s[0] + s[1:].replace("+", "E+").replace("-", "E-")
    return float(s)


def test_int_and_float_field_values():
    assert _field_text(*INT_FIELDS["tab1_NP"]).strip() == "4"
    assert _field_text(*INT_FIELDS["tab1_NBT"]).strip() == "4"
    assert _field_text(*INT_FIELDS["tab1_INT"]).strip() == "2"
    assert _field_text(*INT_FIELDS["list_NPL"]).strip() == "12"
    for key in FLOAT_FIELDS:
        value = _field_text(*FLOAT_FIELDS[key])
        for form in _float_forms(value):
            assert _float_value_of(form) == _float_value_of(value)


@pytest.mark.parametrize("key", sorted(INT_FIELDS))
def test_int_field_other_characters_rejected_by_both(key):
    i, fieldnum = INT_FIELDS[key]
    value = _field_text(i, fieldnum).strip() or "0"
    cpp, py = _parsers()
    for text in _other_forms(value, 11):
        damaged = _with_field(i, fieldnum, text)
        msg = _cpp_parse_error(cpp, damaged)
        assert msg.startswith(
            ("invalid integer in field: ", "malformed number field: ")
        )
        with pytest.raises((InvalidIntegerError, InvalidFloatError)):
            py.parse(damaged)


@pytest.mark.parametrize("atype", ["dict", "numpy"])
@pytest.mark.parametrize("key", sorted(INT_FIELDS))
def test_int_field_valid_forms_accepted_by_both(key, atype):
    i, fieldnum = INT_FIELDS[key]
    value = _field_text(i, fieldnum).strip() or "0"
    cpp, py = _parsers(atype)
    reference = cpp.parse(_text(BASE_LINES))
    forms = [
        value.rjust(11),
        value.ljust(11),
        value.zfill(11),
        (" +" + value).ljust(11),
    ]
    if int(value) == 0:
        forms += [" " * 11, "-0".rjust(11)]
    for text in forms:
        res_cpp = cpp.parse(_with_field(i, fieldnum, text))
        assert compare_objects(res_cpp, reference, fail_on_diff=False), text
        res_py = py.parse(_with_field(i, fieldnum, text))
        assert compare_objects(res_py, res_cpp, fail_on_diff=False), text


@pytest.mark.parametrize("atype", ["dict", "numpy"])
@pytest.mark.parametrize("key", sorted(FLOAT_FIELDS))
def test_float_field_other_characters_rejected_by_both(key, atype):
    i, fieldnum = FLOAT_FIELDS[key]
    cpp, py = _parsers(atype)
    for text in _float_forms(_field_text(i, fieldnum)):
        damaged = _with_field(i, fieldnum, text)
        msg = _cpp_parse_error(cpp, damaged)
        assert msg.startswith("malformed number field: "), repr(text)
        with pytest.raises(InvalidFloatError, match="malformed number field"):
            py.parse(damaged)


@pytest.mark.parametrize("key", ["head_C1", "list_first"])
@pytest.mark.parametrize("text", ["\t" * 11, " " * 10 + "\t", "\x0b".rjust(11)])
def test_float_field_of_other_whitespace_rejected_by_both(key, text):
    # a field of only blanks is zero; other whitespace is not blank
    i, fieldnum = FLOAT_FIELDS[key]
    cpp, py = _parsers()
    damaged = _with_field(i, fieldnum, text)
    _cpp_parse_error(cpp, damaged)
    with pytest.raises(InvalidFloatError):
        py.parse(damaged)


@pytest.mark.parametrize("key", ["head_C1", "tab1_x", "list_first"])
@pytest.mark.parametrize(
    "text", [" 1.5\x00abcdef", " 1.5\x00      ", "\x00\x00 1.5+2   "]
)
def test_float_field_with_nul_rejected_by_both(key, text):
    # std::strtod stopped at a NUL character, so that EndfParserCpp read
    # " 1.5\x00abcdef" as 1.5
    i, fieldnum = FLOAT_FIELDS[key]
    cpp, py = _parsers()
    damaged = _with_field(i, fieldnum, text)
    assert _cpp_parse_error(cpp, damaged).startswith("malformed number field: ")
    with pytest.raises(InvalidFloatError):
        py.parse(damaged)


@pytest.mark.parametrize("atype", ["dict", "numpy"])
@pytest.mark.parametrize("key", sorted(FLOAT_FIELDS))
def test_float_field_valid_forms_accepted_by_both(key, atype):
    # the forms of a float field kept by the change (exponent with and
    # without 'E', D exponent, blanks inside the number with the default
    # accept_spaces=True, blanks after the number)
    i, fieldnum = FLOAT_FIELDS[key]
    value = _field_text(i, fieldnum)
    number = value.strip()
    k = max(number.rfind("+"), number.rfind("-"))
    assert k > 0
    mant, sign, expo = number[:k], number[k], number[k + 1 :]
    cpp, py = _parsers(atype)
    reference = cpp.parse(_text(BASE_LINES))
    forms = [
        number.ljust(11),
        (mant + "E" + sign + expo).rjust(11),
        (mant + "D" + sign + expo).rjust(11),
        (mant + "e" + sign + "0" + expo).rjust(11),
        (mant + " " + sign + expo).rjust(11),
    ]
    forms = [f for f in forms if len(f) == 11]
    assert len(forms) >= 4
    for text in forms:
        res_cpp = cpp.parse(_with_field(i, fieldnum, text))
        assert compare_objects(res_cpp, reference, fail_on_diff=False), text
        res_py = py.parse(_with_field(i, fieldnum, text))
        assert compare_objects(res_py, res_cpp, fail_on_diff=False), text


def _floats(obj):
    # the float values of a parse result in a fixed order, as repr
    if isinstance(obj, dict):
        return [r for k in sorted(obj, key=str) for r in _floats(obj[k])]
    if isinstance(obj, list):
        return [r for v in obj for r in _floats(v)]
    return [repr(obj)] if isinstance(obj, float) else []


@pytest.mark.parametrize("token", ["NaN", "nan", "Inf", "-Inf", "inf", "infinity"])
def test_float_field_nan_inf_accepted_by_both(token):
    # non-finite values are written as "NaN", "Inf" and "-Inf" and read
    # back with the default accept_nan_inf=True (unchanged)
    i, fieldnum = FLOAT_FIELDS["list_last"]
    text = _with_field(i, fieldnum, token.rjust(11))
    cpp, py = _parsers("list")
    values = [_floats(parser.parse(text)[8][457]) for parser in (cpp, py)]
    assert values[0] == values[1]
    assert repr(float(token)) in values[0]


# a section given as a list of lines when writing


def _verbatim_dict(parser_class):
    # MF1/MT451 has no recipe used here: it is kept as a list of lines
    return parser_class().parse(_text(LINES), include=[8])


@pytest.mark.parametrize("parser_class", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("which", ["first", "last"])
@pytest.mark.parametrize(
    "field,text", [("MAT", "ab  "), ("MF", "1x"), ("MT", "4 1"), ("MT", " -x")]
)
def test_write_verbatim_section_invalid_field(parser_class, which, field, text):
    data = _verbatim_dict(parser_class)
    lines = list(data[1][451])
    i = 0 if which == "first" else len(lines) - 1
    lines[i] = _replace(lines[i].rstrip("\n"), field, text) + "\n"
    data[1][451] = lines
    with pytest.raises(ValueError) as excinfo:
        parser_class().write(data)
    if parser_class is EndfParserCpp:
        start, length = COLUMNS[field]
        assert str(excinfo.value) == (
            f'invalid {field} number field: "{text}" '
            f"(columns {start + 1}-{start + length}) in line {i + 1} "
            "of the section MF=1/MT=451 given as a list of lines"
        )


@pytest.mark.parametrize("field,text", [("MAT", "3564"), ("MF", " 1"), ("MT", "451")])
def test_write_verbatim_section_valid_fields(field, text):
    # the other lines are written as they are by both parsers, the first
    # and the last line must hold numbers (or blanks)
    outputs = []
    for parser_class in (EndfParserCpp, EndfParserPy):
        data = _verbatim_dict(parser_class)
        lines = list(data[1][451])
        lines[0] = _replace(lines[0].rstrip("\n"), "MAT", "3564".rjust(4)) + "\n"
        lines[3] = _replace(lines[3].rstrip("\n"), field, "x" * len(text)) + "\n"
        data[1][451] = lines
        outputs.append(parser_class().write(data))
    assert outputs[0] == outputs[1]


# endf-cli validate


def _validate(path, *argv):
    import argparse
    from endf_parserpy.cli.actions import validate
    from endf_parserpy.cli.cmd_utils import (
        add_common_cmd_parser_args,
        get_endf_parser,
    )

    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap, defaults=validate.STRICT_DEFAULT_ARGS)
    args = vars(ap.parse_args(list(argv)))
    args["subcommand"] = validate.COMMAND_NAME
    parser = get_endf_parser(args)
    fast_parser = validate.get_fast_parser(args)
    return validate._validate_file(parser, str(path), fast_parser)


@pytest.mark.parametrize(
    "record,field,text",
    [("tape_head", "MT", "ab "), ("tape_head", "MAT", "ab  "), ("send", "MT", " x ")],
)
def test_cli_validate_reports_invalid_field(tmp_path, record, field, text):
    path = tmp_path / "damaged.endf"
    path.write_text(_damaged(record, field, text))
    ok, detail = _validate(path)
    assert not ok
    start, length = COLUMNS[field]
    assert (
        f'invalid {field} number field: "{text}" (columns {start + 1}-{start + length})'
        in detail
    )
    ok_py, _ = _validate(path, "--no-cpp")
    assert not ok_py
    path.write_text(_text(BASE_LINES))
    assert _validate(path) == (True, None)
