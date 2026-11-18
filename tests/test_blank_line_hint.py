"""The error for a blank line says how to parse the file anyway: remove the
line, or create the parser with ignore_blank_lines=True (on the command
line: the option --ignore_blank_lines)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import EndfFile, EndfParserCpp, EndfParserFactory, EndfParserPy
from endf_parserpy.cli.cmd_utils import cli_message
from endf_parserpy.tape import SectionParseError
from endf_parserpy.tape.operations import parse_tape

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"
INCLUDE = [(1, 451), (3, 1)]
HINT_PY = (
    "Line 871 is a blank line. Remove it, or create the parser with "
    "ignore_blank_lines=True to skip blank lines."
)
HINT_CPP = (
    "Blank line detected: remove it, or create the parser with "
    "ignore_blank_lines=True to skip blank lines"
)


def _lines():
    return CU63.read_text(encoding="latin-1").rstrip("\n").split("\n")


# a blank line in MF3/MT1 (whose HEAD record is line 866), line 871
TEXT = "\n".join(_lines()[:870] + [""] + _lines()[870:]) + "\n"

PARSERS = {
    "EndfParserPy": (lambda **kw: EndfParserPy(**kw), HINT_PY),
    "EndfParserCpp": (lambda **kw: EndfParserCpp(**kw), HINT_CPP),
    "create-python": (
        lambda **kw: EndfParserFactory.create(select="python", **kw),
        HINT_PY,
    ),
    "create-cpp": (lambda **kw: EndfParserFactory.create(select="cpp", **kw), HINT_CPP),
}


@pytest.fixture(scope="module")
def blank_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("hint") / "cu63_blank.endf"
    path.write_text(TEXT, encoding="latin-1")
    return path


@pytest.fixture(scope="module")
def expected():
    return EndfParserCpp().parsefile(CU63, include=INCLUDE)


@pytest.mark.parametrize("name", PARSERS)
def test_parser_message_names_the_option(name, blank_file):
    make, hint = PARSERS[name]
    parser = make()
    for parse in (
        lambda: parser.parse(TEXT, include=INCLUDE),
        lambda: parser.parsefile(blank_file, include=INCLUDE),
    ):
        with pytest.raises(Exception) as err:
            parse()
        assert str(err.value).startswith(hint)


@pytest.mark.parametrize("name", PARSERS)
def test_endf_file_and_parse_tape_keep_the_hint(name, blank_file):
    make, hint = PARSERS[name]
    parser = make()
    with pytest.raises(SectionParseError) as err:
        EndfFile(blank_file, parser=parser)[0][3, 1]
    # the line number counted in the file (EndfFile translates it)
    assert err.value.detail.startswith(hint)
    with pytest.raises(Exception) as err:
        parse_tape(TEXT, parser=parser, include=INCLUDE, on_error="raise")
    assert str(err.value).startswith(hint)


@pytest.mark.parametrize("name", PARSERS)
def test_the_option_parses_the_file(name, blank_file, expected):
    make, _ = PARSERS[name]
    parser = make(ignore_blank_lines=True)
    assert parser.parse(TEXT, include=INCLUDE) == expected
    assert parser.parsefile(blank_file, include=INCLUDE) == expected
    assert EndfFile(blank_file, parser=parser)[0][3, 1] == expected[3][1]
    assert parse_tape(TEXT, parser=parser, include=INCLUDE, on_error="raise") == [
        expected
    ]


def test_cli_message():
    assert cli_message(HINT_PY) == (
        "Line 871 is a blank line. Remove it, or use the option "
        "--ignore_blank_lines to skip blank lines."
    )
    assert cli_message(HINT_CPP) == (
        "Blank line detected: remove it, or use the option "
        "--ignore_blank_lines to skip blank lines"
    )
    assert cli_message("other message") == "other message"


def _validate(*argv):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", "validate", *argv],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("no_cpp", (False, True), ids=("cpp", "no-cpp"))
def test_cli_validate_names_the_flag(blank_file, no_cpp):
    extra = ["--no-cpp"] if no_cpp else []
    result = _validate(*extra, str(blank_file))
    assert result.returncode == 1
    hint = cli_message(HINT_PY if no_cpp else HINT_CPP)
    assert hint in result.stdout.splitlines()
    assert "ignore_blank_lines=True" not in result.stdout
    result = _validate(*extra, "--ignore_blank_lines", str(blank_file))
    assert result.returncode == 0, result.stdout
