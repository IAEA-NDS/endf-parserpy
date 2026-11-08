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
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


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
    "MAT": ["ab  ", "35x4", "3 64", "-   ", "+-1 ", "35\t4", "1_00"],
    "MF": ["8x", "x8", "- ", "1.", "++", "\t\t"],
    "MT": ["ab ", " x ", "4 7", "45-", "- 1", "4\t5", "1e2", "4_5"],
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


@pytest.mark.parametrize(
    "record,field,text",
    [
        ("list_body", "MF", "\t8"),
        ("list_body", "MF", "8\t"),
        ("tape_head", "MAT", "\t  1"),
        ("tape_head", "MAT", "1 \t "),
    ],
)
def test_tab_around_number(record, field, text):
    # int() of EndfParserPy accepts whitespace other than blanks (e.g. a
    # tab) around the number, EndfParserCpp only blanks (see
    # cpp_int_columns_to_int); a tab is not printable ASCII and rejected
    # by both parsers with accept_non_ascii=False (e.g. by endf-cli
    # validate)
    damaged = _damaged(record, field, text)
    cpp, py = _parsers()
    msg = _cpp_parse_error(cpp, damaged)
    assert f"invalid {field} number field: " in msg
    py.parse(damaged)
    for parser in (
        EndfParserCpp(accept_non_ascii=False),
        EndfParserPy(accept_non_ascii=False),
    ):
        with pytest.raises(Exception, match="not a printable ASCII character"):
            parser.parse(damaged)


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
