############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The lengths of the text fields of TEXT records.

The text fields of a TEXT record fill its 66 text columns: a single field
without a length spans all of them, otherwise every field has a length and
the lengths add up to 66. Both parsers reject other recipes (EndfParserPy
accepted a last field without a length after fields with one, e.g.
A{12}, B, and fields not filling the 66 columns).

- Reading: columns missing from a short line are blanks, so that every
  text field has its length (EndfParserPy returned shorter strings, e.g.
  for a short tape ID line).
- Writing: the value of a field with a length must have that length; the
  value of a field without one may be shorter and is padded with blanks.
  EndfParserCpp wrote values of other lengths as they were, which shifted
  the following columns (e.g. a short tape description moved MAT/MF/MT).
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.compiler.endf2cpp import generate_cpp_module_code


PARSERS = [EndfParserCpp, EndfParserPy]


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs.setdefault("print_cache_info", False)
    return ParserCls(**kwargs)


def _mf3_dict():
    xstable = {"NBT": [3], "INT": [2], "E": [1.0, 2.0, 3.0], "xs": [4.0, 5.0, 6.0]}
    section = {
        "MAT": 125,
        "MF": 3,
        "MT": 1,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "QM": 0.0,
        "QI": 0.0,
        "LR": 0,
        "xstable": xstable,
    }
    return {3: {1: section}}


def _mf3_lines():
    return _lines(_parser(EndfParserPy).write(_mf3_dict()))


def _with_line(lines, index, line):
    lines = list(lines)
    lines[index] = line
    return "\n".join(lines)


def _tpid_text(cut):
    tape = {0: {0: {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "tape id"}}}
    lines = _lines(_parser(EndfParserPy).write({**tape, **_mf3_dict()}))
    return "\n".join([lines[0][:cut]] + lines[1:])


@pytest.mark.parametrize("cut", [7, 20, 66, 70, 75])
def test_short_tape_id_line(cut):
    results = [_parser(P).parse(_tpid_text(cut))[0][0] for P in PARSERS]
    for res in results:
        assert res["TAPEDESCR"] == "tape id".ljust(66)
        assert res["MAT"] == (1 if cut >= 70 else 0)
    assert results[0] == results[1]


def _mf1_lines():
    # MF1/MT451 contains the text record with the fields ZSYMAM{11},
    # ALAB{11}, EDATE{10}, {1}, AUTH{33}
    path = Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf"
    return path.read_text().splitlines()


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("descr", ["", "tape", "x" * 66])
def test_write_text_shorter_than_field(ParserCls, descr):
    tape = {0: {0: {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": descr}}}
    line = _lines(_parser(ParserCls).write(tape))[0]
    assert line == descr.ljust(66) + "   1 0  0    0"


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_write_text_longer_than_field_rejected(ParserCls):
    tape = {0: {0: {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "y" * 67}}}
    with pytest.raises(Exception, match="length"):
        _parser(ParserCls).write(tape)


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("zsymam", ["29-Cu- 63", "29-Cu- 63    "])
def test_write_text_field_with_other_length_rejected(ParserCls, zsymam):
    parser = _parser(ParserCls, ignore_missing_tpid=True)
    endf_dict = parser.parse("\n".join(_mf1_lines()), include=[(1, 451)])
    assert len(endf_dict[1][451]["ZSYMAM"]) == 11
    endf_dict[1][451]["ZSYMAM"] = zsymam
    with pytest.raises(Exception, match="length"):
        parser.write(endf_dict)


TEXT_RECIPE = """
[MAT, 1, 451/ {text} ]TEXT
SEND
"""


def _text_recipe(fields):
    return TEXT_RECIPE.replace("{text}", fields)


INVALID_TEXT_FIELDS = ["HL{12}", "A{12}, B", "A, B{12}", "A{33}, B{34}"]


@pytest.mark.parametrize("fields", INVALID_TEXT_FIELDS)
def test_codegen_rejects_text_fields_not_filling_66_columns(fields):
    with pytest.raises(TypeError):
        generate_cpp_module_code({1: {451: _text_recipe(fields)}}, "codegen_test")


def _text_section():
    zeros = " 0.000000+0 0.000000+0          0          0          0          0"
    return "\n".join(
        [
            "some text".ljust(66) + " 125 1451    1",
            zeros + " 125 1  099999",
            zeros + " 125 0  0    0",
            zeros + "   0 0  0    0",
            zeros + "  -1 0  0    0",
        ]
    )


@pytest.mark.parametrize("fields", INVALID_TEXT_FIELDS)
def test_python_rejects_text_fields_not_filling_66_columns(fields):
    parser = EndfParserPy(
        recipes={1: {451: _text_recipe(fields)}},
        cache_dir=False,
        print_cache_info=False,
        ignore_missing_tpid=True,
    )
    with pytest.raises(Exception, match="TEXT record"):
        parser.parse(_text_section())


# text recipes of the test flavor (endf_recipes/test/endf_recipe_mf6.py):
# MT1 A{33}, B{33}; MT2 {10}, A{56}; MT3 HL (66 columns)
TEXT_LINE = "".join(chr(ord("a") + i % 26) for i in range(66))
EXPECTED = {
    1: {"A": TEXT_LINE[:33], "B": TEXT_LINE[33:]},
    2: {"A": TEXT_LINE[10:]},
    3: {"HL": TEXT_LINE},
}
# columns of a text field without a variable are written as blanks
WRITTEN = {1: TEXT_LINE, 2: " " * 10 + TEXT_LINE[10:], 3: TEXT_LINE}


def _text_line(mt, text):
    return text.ljust(66) + f" 125 6{mt:3d}    1"


def _test_section(mt, first_line):
    send = " 0.000000+0 0.000000+0          0          0          0          0"
    return "\n".join([first_line, send + " 125 6  099999"])


def _test_parser(ParserCls):
    return _parser(
        ParserCls,
        endf_format="test",
        ignore_missing_tpid=True,
        ignore_send_records=True,
    )


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("mt", [1, 2, 3])
def test_text_fields_read_and_written(ParserCls, mt):
    parser = _test_parser(ParserCls)
    line = _text_line(mt, TEXT_LINE)
    res = parser.parse(_test_section(mt, line))[6][mt]
    assert {k: res[k] for k in EXPECTED[mt]} == EXPECTED[mt]
    assert _lines(parser.write({6: {mt: res}}))[0] == _text_line(mt, WRITTEN[mt])


@pytest.mark.parametrize("cut", [5, 15, 30, 50])
def test_cpp_text_fields_of_short_line(cut):
    # the text record ZSYMAM{11}, ALAB{11}, EDATE{10}, {1}, AUTH{33} of
    # MF1/MT451 cut after `cut` columns, without MAT/MF/MT: EndfParserCpp
    # reads it (without validate_control_records); EndfParserPy rejects it,
    # as it divides the file into sections by MAT/MF/MT
    lines = _mf1_lines()
    parser = EndfParserCpp(ignore_missing_tpid=True)
    full = parser.parse("\n".join(lines), include=[(1, 451)])[1][451]
    index = next(i for i, line in enumerate(lines) if line.startswith(full["ZSYMAM"]))
    short = lines[index][:cut].ljust(66)
    lines[index] = lines[index][:cut]
    res = parser.parse("\n".join(lines), include=[(1, 451)])[1][451]
    expected = {
        "ZSYMAM": short[0:11],
        "ALAB": short[11:22],
        "EDATE": short[22:32],
        "AUTH": short[33:66],
    }
    assert {k: res[k] for k in expected} == expected


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize(
    "mt, key, value",
    [(1, "A", "x" * 32), (1, "B", "x" * 34), (2, "A", "x" * 55), (3, "HL", "x" * 67)],
)
def test_text_value_of_wrong_length_rejected(ParserCls, mt, key, value):
    parser = _test_parser(ParserCls)
    res = parser.parse(_test_section(mt, _text_line(mt, TEXT_LINE)))[6][mt]
    res[key] = value
    # the message is checked in test_write_text_longer_than_field_rejected;
    # with several C++ modules in one process, the message of an error of
    # the second module may get lost in some builds
    with pytest.raises(Exception):
        parser.write({6: {mt: res}})


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_shorter_value_of_field_without_length_padded(ParserCls):
    parser = _test_parser(ParserCls)
    res = parser.parse(_test_section(3, _text_line(3, TEXT_LINE)))[6][3]
    res["HL"] = "short"
    assert _lines(parser.write({6: {3: res}}))[0] == _text_line(3, "short")
