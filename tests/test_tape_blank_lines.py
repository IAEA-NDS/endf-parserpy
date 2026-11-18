"""parse_tape, parse_tape_file and iter_parse_tape respect the option
ignore_blank_lines of their parser: a blank line before the tape end is
rejected with ignore_blank_lines=False, with the error and the line number
of the parser, and accepted with True."""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.tape import split_materials
from endf_parserpy.tape.operations import (
    FailedMaterial,
    iter_parse_tape,
    parse_tape,
    parse_tape_file,
)

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"
ZN64 = TESTDATA / "n_3025_30-Zn-64.endf"
INCLUDE = [(1, 451), (3, 1)]
PARSERS = (EndfParserPy, EndfParserCpp)


def _lines(path):
    return path.read_text(encoding="latin-1").rstrip("\n").split("\n")


CU = _lines(CU63)

# a blank line at each place before the TEND record (Cu-63: MF3/MT1 starts
# at line 866, the MEND record is line 25120, the TEND record line 25121)
BLANK_CASES = {
    "before_tpid": [""] + CU,
    "after_tpid": CU[:1] + [""] + CU[1:],
    "within_section": CU[:870] + [""] + CU[870:],
    "between_sections": CU[:865] + [""] + CU[865:],
    "before_mend": CU[:-2] + [""] + CU[-2:],
    "before_tend": CU[:-1] + [""] + CU[-1:],
    "blanks_and_tabs": CU[:870] + [" \t  "] + CU[870:],
}

# accepted with both settings: line endings and lines after TEND
ACCEPTED_CASES = {
    "final_newline": "\n".join(CU) + "\n",
    "no_final_newline": "\n".join(CU),
    "crlf": "\r\n".join(CU) + "\r\n",
    "empty_line_after_tend": "\n".join(CU) + "\n\n",
    "two_lines_after_tend": "\n".join(CU) + "\n\n   \n",
}


def _error(func):
    with pytest.raises(Exception) as err:
        func()
    return type(err.value), str(err.value)


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("case", BLANK_CASES)
def test_blank_line_rejected_as_by_the_parser(cls, case, tmp_path):
    parser = cls(ignore_blank_lines=False)
    text = "\n".join(BLANK_CASES[case]) + "\n"
    expected = _error(lambda: parser.parse(text, include=INCLUDE))
    assert "blank line" in expected[1].lower()
    path = tmp_path / "tape.endf"
    path.write_text(text, encoding="latin-1")
    for func in (
        lambda: parse_tape(text, parser=parser, include=INCLUDE, on_error="raise"),
        lambda: parse_tape_file(path, parser=parser, include=INCLUDE, on_error="raise"),
        lambda: list(
            iter_parse_tape(text, parser=parser, include=INCLUDE, on_error="raise")
        ),
    ):
        assert _error(func) == expected
    marked = parse_tape(text, parser=parser, include=INCLUDE)
    assert len(marked) == 1 and isinstance(marked[0], FailedMaterial)


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("case", BLANK_CASES)
def test_blank_line_accepted_with_ignore_blank_lines(cls, case):
    parser = cls(ignore_blank_lines=True)
    text = "\n".join(BLANK_CASES[case]) + "\n"
    expected = parser.parse(text, include=INCLUDE)
    materials = parse_tape(text, parser=parser, include=INCLUDE, on_error="raise")
    assert len(materials) == 1
    if case == "before_tpid" and cls is EndfParserPy:
        # EndfParserPy takes the blank line before the TPID record for the
        # tape head (not changed here); the tape of parse_tape starts with
        # the TPID record, as EndfParserCpp reads it
        assert expected[0][0] == ["\n"]
        expected[0][0] = [CU[0] + "\n"]
    assert materials == [expected]


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("case", ACCEPTED_CASES)
@pytest.mark.parametrize("ignore", (False, True))
def test_line_endings_and_lines_after_tend_accepted(cls, case, ignore):
    parser = cls(ignore_blank_lines=ignore)
    text = ACCEPTED_CASES[case]
    expected = parser.parse(text, include=INCLUDE)
    assert parse_tape(text, parser=parser, include=INCLUDE, on_error="raise") == [
        expected
    ]


def _two_material_tape(padding):
    zn = _lines(ZN64)
    # Cu-63 without its TEND record, Zn-64 without its TPID record
    return "\n".join(CU[:-1] + padding + zn[1:]) + "\n"


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
def test_blank_line_between_materials(cls):
    text = _two_material_tape([""])
    strict = cls(ignore_blank_lines=False)
    # the blank line after the MEND record of Cu-63 belongs to its tape
    materials = parse_tape(text, parser=strict, include=INCLUDE)
    assert isinstance(materials[0], FailedMaterial)
    assert not isinstance(materials[1], FailedMaterial)
    assert materials[1][1][451]["ZA"] == 30064
    lenient = cls(ignore_blank_lines=True)
    materials = parse_tape(text, parser=lenient, include=INCLUDE, on_error="raise")
    assert [m[1][451]["ZA"] for m in materials] == [29063, 30064]
    assert (
        parse_tape(
            _two_material_tape([]), parser=strict, include=INCLUDE, on_error="raise"
        )
        == materials
    )


def test_split_materials_keep_blank_lines():
    text = _two_material_tape(["", ""]).replace(CU[900] + "\n", CU[900] + "\n\n")
    dropped = list(split_materials(text.splitlines()))
    kept = list(split_materials(text.splitlines(), keep_blank_lines=True))
    assert len(dropped) == len(kept) == 2
    assert all(line.strip() for chunk in dropped for line in chunk)
    assert [line for line in kept[0] if not line.strip()] == ["", "", ""]
    assert all(line.strip() for line in kept[1])
    assert [[line for line in c if line.strip()] for c in kept] == dropped
