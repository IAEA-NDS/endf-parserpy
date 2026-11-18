"""A final line ending (LF or CRLF), its absence, or one empty line after
the tape end is not a blank line: accepted with ignore_blank_lines=False,
the default of both parser classes and of EndfParserFactory.create. A blank
line in the middle of a file is still rejected."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import (
    EndfFile,
    EndfParserCpp,
    EndfParserFactory,
    EndfParserPy,
    TapeIndex,
)
from endf_parserpy.tape import SectionParseError
from endf_parserpy.tape.operations import parse_tape_file
from endf_parserpy.utils.user_tools import list_parsed_sections

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"

# parsed in every test (MF3/MT1 contains the blank line of MIDDLE_BLANK);
# the other sections stay unparsed, so that the Python parser is fast
INCLUDE = [(1, 451), (3, 1)]

ENDINGS = ("lf_final", "lf_no_final", "crlf_final", "crlf_no_final", "lf_extra_empty")


def _lines():
    return CU63.read_text(encoding="latin-1").rstrip("\n").split("\n")


def _text(ending):
    lines = _lines()
    return {
        "lf_final": "\n".join(lines) + "\n",
        "lf_no_final": "\n".join(lines),
        "crlf_final": "\r\n".join(lines) + "\r\n",
        "crlf_no_final": "\r\n".join(lines),
        "lf_extra_empty": "\n".join(lines) + "\n\n",
    }[ending]


def _middle_blank_text():
    lines = _lines()
    # within MF3/MT1 (its HEAD record is line 866)
    return "\n".join(lines[:870] + [""] + lines[870:]) + "\n"


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    directory = tmp_path_factory.mktemp("endings")
    paths = {}
    for ending in ENDINGS:
        paths[ending] = directory / f"cu63_{ending}.endf"
        paths[ending].write_bytes(_text(ending).encode("latin-1"))
    paths["middle_blank"] = directory / "cu63_middle_blank.endf"
    paths["middle_blank"].write_bytes(_middle_blank_text().encode("latin-1"))
    return paths


@pytest.fixture(scope="module")
def expected():
    return EndfParserCpp().parsefile(CU63, include=INCLUDE)


def _parsers():
    return {
        "EndfParserPy": lambda: EndfParserPy(ignore_blank_lines=False),
        "EndfParserCpp": lambda: EndfParserCpp(ignore_blank_lines=False),
        "factory-python": lambda: EndfParserFactory.create(select="python"),
        "factory-cpp": lambda: EndfParserFactory.create(select="cpp"),
    }


PARSERS = _parsers()


@pytest.mark.parametrize("select", ("python", "cpp", "fastest"))
def test_factory_rejects_blank_lines_by_default(select):
    parser = EndfParserFactory.create(select=select, warn_slow=False)
    assert parser.read_opts["ignore_blank_lines"] is False


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("ending", ENDINGS)
def test_parsefile_accepts_final_line_ending(files, expected, name, ending):
    parser = PARSERS[name]()
    assert parser.parsefile(files[ending], include=INCLUDE) == expected


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("ending", ENDINGS)
def test_parse_str_accepts_final_line_ending(expected, name, ending):
    parser = PARSERS[name]()
    assert parser.parse(_text(ending), include=INCLUDE) == expected


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("ending", ENDINGS)
def test_parse_list_of_lines_accepts_final_line_ending(expected, name, ending):
    # the lines without their line endings (see the docstring of parse)
    parser = PARSERS[name]()
    lines = _text(ending).splitlines()
    assert parser.parse(lines, include=INCLUDE) == expected


@pytest.mark.parametrize("name", PARSERS)
def test_blank_line_in_the_middle_is_rejected(files, name):
    parser = PARSERS[name]()
    text = _middle_blank_text()
    for parse in (
        lambda: parser.parsefile(files["middle_blank"], include=INCLUDE),
        lambda: parser.parse(text, include=INCLUDE),
        lambda: parser.parse(text.splitlines(), include=INCLUDE),
    ):
        with pytest.raises(Exception, match="(?i)blank line"):
            parse()


@pytest.mark.parametrize("ending", ENDINGS)
def test_tape_index_accepts_final_line_ending(files, ending):
    reference = TapeIndex.from_file(CU63)
    index = TapeIndex.from_file(files[ending])
    assert len(index) == len(reference) == 1
    assert [s[:2] for s in index[0].sections] == [s[:2] for s in reference[0].sections]


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
@pytest.mark.parametrize("ending", ENDINGS)
def test_endf_file_accepts_final_line_ending(files, expected, cls, ending):
    endf_file = EndfFile(files[ending], parser=cls(ignore_blank_lines=False))
    assert len(endf_file) == 1
    material = endf_file[0]
    assert material[1, 451]["DESCRIPTION"] == expected[1][451]["DESCRIPTION"]
    assert material[3, 1]["xstable"] == expected[3][1]["xstable"]


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("ending", ENDINGS)
def test_parse_tape_file_accepts_final_line_ending(files, expected, name, ending):
    parser = PARSERS[name]()
    materials = parse_tape_file(files[ending], parser=parser, include=INCLUDE)
    assert len(materials) == 1
    assert list_parsed_sections(materials[0]) == list_parsed_sections(expected)
    assert materials[0][3][1] == expected[3][1]


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
def test_tape_layer_rejects_blank_line_in_the_middle(files, cls):
    parser = cls(ignore_blank_lines=False)
    with pytest.raises(SectionParseError) as err:
        EndfFile(files["middle_blank"], parser=parser)[0][3, 1]
    assert (err.value.mf, err.value.mt) == (3, 1)
    assert "blank line" in err.value.detail.lower()


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
def test_parse_tape_file_rejects_blank_line_in_the_middle(files, cls):
    parser = cls(ignore_blank_lines=False)
    with pytest.raises(Exception, match="(?i)blank line"):
        parse_tape_file(
            files["middle_blank"], parser=parser, include=INCLUDE, on_error="raise"
        )


def _validate(path):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", "validate", str(path)],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("ending", ENDINGS)
def test_cli_validate_accepts_final_line_ending(files, ending):
    result = _validate(files[ending])
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"ok - {files[ending]}" in result.stdout.splitlines()


def test_cli_validate_rejects_blank_line_in_the_middle(files):
    result = _validate(files["middle_blank"])
    assert result.returncode == 1
    assert f"failed - {files['middle_blank']}" in result.stdout.splitlines()
    assert "line 871: blank line" in result.stdout


# --- a list of lines that keep their line endings, e.g. from readlines() ---


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("ending", ENDINGS)
def test_parse_list_of_lines_with_line_endings(files, expected, name, ending):
    parser = PARSERS[name]()
    # readlines() in text mode (universal newlines: "\r\n" becomes "\n")
    with open(files[ending], encoding="latin-1") as fh:
        assert parser.parse(fh.readlines(), include=INCLUDE) == expected
    # the line endings as they are in the file
    with open(files[ending], encoding="latin-1", newline="") as fh:
        lines = fh.readlines()
    if ending.startswith("crlf"):
        assert lines[0].endswith("\r\n")
    assert parser.parse(lines, include=INCLUDE) == expected


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("end", ("\n", "\r\n", "\r"))
def test_parse_list_last_line_without_ending(expected, name, end):
    parser = PARSERS[name]()
    lines = [line + end for line in _lines()]
    lines[-1] = lines[-1][: -len(end)]
    assert parser.parse(lines, include=INCLUDE) == expected


@pytest.mark.parametrize("name", PARSERS)
@pytest.mark.parametrize("blank", ("\n", "\r\n", "", "   \n"))
def test_parse_list_with_blank_element_is_rejected(name, blank):
    parser = PARSERS[name]()
    lines = [line + "\n" for line in _lines()]
    lines.insert(870, blank)
    with pytest.raises(Exception, match="(?i)blank line"):
        parser.parse(lines, include=INCLUDE)


def test_factory_parse_of_readlines(files, expected):
    with open(files["crlf_final"], encoding="latin-1", newline="") as fh:
        lines = fh.readlines()
    for select in ("python", "cpp", "fastest"):
        parser = EndfParserFactory.create(select=select)
        assert parser.parse(lines, include=INCLUDE) == expected
