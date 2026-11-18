"""The commands of endf-cli that parse a file report a failed parse with
the message of the parser, without a traceback: the section, the line of
the file at which it starts, and the reason with its hint, which names
the option of the command line (e.g. --ignore_blank_lines). The exit
status is that of an error of the command (1, or 2 for compare and
match)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import EndfFile, EndfParserCpp, EndfParserPy, parse_tape
from endf_parserpy.cli.cmd_utils import (
    cli_message,
    located_parse_error,
    parse_error_message,
)
from endf_parserpy.tape import SectionParseError

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"


def _cut():
    """MF1/MT451 and MF3/MT1 of Cu-63, with the end records."""
    lines = CU63.read_text(encoding="latin-1").rstrip("\n").split("\n")
    # lines 1-603: TPID, MF1/MT451, SEND, FEND; lines 866-2119: MF3/MT1
    # and its SEND record; then FEND, MEND and TEND
    return lines[:603] + lines[865:2119] + [lines[602], lines[-2], lines[-1]]


GOOD = _cut()
# the HEAD record of MF3/MT1 is line 604; a blank line as line 609
BLANK = GOOD[:608] + [""] + GOOD[608:]
# a malformed number in line 614
BADNUM = list(GOOD)
BADNUM[613] = BADNUM[613][:2] + "x" + BADNUM[613][3:]

SECTION_LINE = "The section starts at line 604 of the file."
BLANK_REASON = {
    "cpp": (
        "Blank line detected: remove it, or use the option "
        "--ignore_blank_lines to skip blank lines"
    ),
    "no-cpp": (
        "Line 609 is a blank line. Remove it, or use the option "
        "--ignore_blank_lines to skip blank lines."
    ),
}
BADNUM_REASON = {
    "cpp": 'malformed number field: " 1x004670+5"',
    "no-cpp": "could not convert string to float: '1x004670E+5'",
}


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")
    return path


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    d = tmp_path_factory.mktemp("cli_parse_errors")
    return {
        "good": _write(d / "good.endf", GOOD),
        "blank": _write(d / "blank.endf", BLANK),
        "badnum": _write(d / "badnum.endf", BADNUM),
    }


def run_cli(argv, cwd):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        cwd=cwd,
        env=env,
        input="",
        capture_output=True,
        text=True,
    )


# the commands that parse the file F (G is a file without errors), with
# the exit status of a failed parse and the start of the message, which
# is on stderr (for validate on stdout, after the summary of the framing
# records)
COMMANDS = {
    "show-section": (["show", "3/1", "F"], 1, "cannot access #0/3/1: "),
    "show-field": (["show", "3/1/AWR", "F"], 1, "cannot access #0/3/1/AWR: "),
    "explain": (["explain", "3/1/AWR", "F"], 1, "cannot access section #0/3/1: "),
    "replace-from": (
        ["replace", "-n", "3/1/AWR", "F", "G"],
        1,
        "replace: cannot read #0/3/1/AWR from F: ",
    ),
    "replace-into": (
        ["replace", "-n", "3/1/AWR", "G", "F"],
        1,
        "replace: cannot write #0/3/1/AWR in F: ",
    ),
    "match": (["match", "--query", "/3/1/AWR > 0", "F"], 2, "parsing failed: F: "),
    "compare": (["compare", "F", "G"], 2, "compare: cannot parse F: "),
    "convert": (
        ["convert", "--to", "json", "F", "out.json"],
        1,
        "convert: cannot parse F: ",
    ),
    "update-directory": (
        ["update-directory", "-n", "F"],
        1,
        "update-directory: cannot parse F: ",
    ),
    "insert-text": (["insert-text", "-n", "F"], 1, "insert-text: cannot parse F: "),
    "validate": (["validate", "F"], 1, None),
}
# update-directory and insert-text parse only MF1/MT451 and split the
# material into its sections, which finds a blank line but not a
# malformed number
SPLIT_ONLY = ("update-directory", "insert-text")
# explain uses the Python parser
PYTHON_ONLY = ("explain",)


def _run(name, kind, sources, tmp_path, options=()):
    argv = COMMANDS[name][0]
    shutil.copy(sources[kind], tmp_path / "F")
    shutil.copy(sources["good"], tmp_path / "G")
    command, *rest = argv
    return run_cli([command, *options, *rest], tmp_path)


def _check_failure(result, name, reason):
    _, status, start = COMMANDS[name]
    output = result.stdout if name == "validate" else result.stderr
    assert result.returncode == status, (result.stdout, result.stderr)
    assert "Traceback" not in result.stdout + result.stderr
    assert reason in output, output
    assert "ignore_blank_lines=True" not in output
    if start is not None:
        assert output.startswith(start), output
        assert "MF=3/MT=1 of the material at position 0" in output
        assert SECTION_LINE in output.splitlines()


@pytest.mark.parametrize("name", COMMANDS)
@pytest.mark.parametrize("parser", ("cpp", "no-cpp"))
def test_blank_line(name, parser, sources, tmp_path):
    options = ["--no-cpp"] if parser == "no-cpp" else []
    used = "no-cpp" if name in PYTHON_ONLY else parser
    result = _run(name, "blank", sources, tmp_path, options)
    _check_failure(result, name, BLANK_REASON[used])


@pytest.mark.parametrize("name", [n for n in COMMANDS if n not in SPLIT_ONLY])
def test_malformed_number(name, sources, tmp_path):
    used = "no-cpp" if name in PYTHON_ONLY else "cpp"
    result = _run(name, "badnum", sources, tmp_path)
    _check_failure(result, name, BADNUM_REASON[used])


@pytest.mark.parametrize("name", COMMANDS)
def test_ignore_blank_lines_parses_the_file(name, sources, tmp_path):
    result = _run(name, "blank", sources, tmp_path, ["--ignore_blank_lines"])
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stderr == ""


def test_compare_names_the_file_that_fails(sources, tmp_path):
    shutil.copy(sources["good"], tmp_path / "F")
    shutil.copy(sources["blank"], tmp_path / "G")
    result = run_cli(["compare", "F", "G"], tmp_path)
    assert result.returncode == 2
    assert result.stderr.startswith("compare: cannot parse G: ")


@pytest.fixture(scope="module")
def two_materials(tmp_path_factory):
    """A tape of two materials, the second with the blank line (line
    609 of its material, line 2467 of the tape)."""
    path = tmp_path_factory.mktemp("cli_parse_errors_two") / "two.endf"
    return _write(path, GOOD[:-1] + BLANK[1:])


def test_lines_of_the_file_for_a_later_material(two_materials):
    # parse_tape gives the line in the material
    parser = EndfParserPy()
    text = two_materials.read_text(encoding="latin-1")
    with pytest.raises(Exception) as err:
        parse_tape(text, parser=parser, on_error="raise")
    assert "Line 609 is a blank line" in str(err.value)
    # the error of the section gives the line in the file
    exc = located_parse_error(err.value, EndfFile(two_materials, parser=parser))
    assert isinstance(exc, SectionParseError)
    assert exc.position == 1 and (exc.mf, exc.mt) == (3, 1)
    message = parse_error_message(exc)
    assert message.splitlines() == [
        "MF=3/MT=1 of the material at position 1 failed to parse",
        "The section starts at line 2462 of the file.",
        "Line 2467 is a blank line. Remove it, or use the option "
        "--ignore_blank_lines to skip blank lines.",
    ]


def test_convert_gives_the_line_of_the_file(two_materials, tmp_path):
    result = run_cli(
        ["convert", "--to", "json", str(two_materials), "x.json"], tmp_path
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "material at position 1" in result.stderr
    assert "The section starts at line 2462 of the file." in result.stderr
    assert 'Line 2467: ""' in result.stderr
    assert not (tmp_path / "x.json").exists()


def test_located_parse_error_keeps_other_errors(sources):
    endf_file = EndfFile(sources["good"], parser=EndfParserCpp())
    exc = ValueError("not a section")
    assert located_parse_error(exc, endf_file) is exc
    assert parse_error_message(exc) == "not a section"


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "non-finite value (overflow / inf / NaN) in field: 'inf'. "
            "Set `accept_nan_inf=True` to allow non-finite values.",
            "non-finite value (overflow / inf / NaN) in field: 'inf'. "
            "Use the option --accept_nan_inf to allow non-finite values.",
        ),
        (
            'non-finite value (overflow / inf / NaN) in field: "inf". '
            "Set `accept_nan_inf=true` to allow non-finite values.",
            'non-finite value (overflow / inf / NaN) in field: "inf". '
            "Use the option --accept_nan_inf to allow non-finite values.",
        ),
        (
            "... as required by the ENDF-6 format; use the option "
            "accept_non_ascii=True to accept it",
            "... as required by the ENDF-6 format; use the option "
            "--accept_non_ascii to accept it",
        ),
    ],
)
def test_cli_message_other_hints(message, expected):
    assert cli_message(message) == expected


TRUNCATED = "the tape ends in the middle of a material"


@pytest.mark.parametrize(
    "argv,status",
    [
        (["show", "3/1/AWR", "F"], 1),
        (["explain", "3/1/AWR", "F"], 1),
        (["list-materials", "F"], 1),
        (["update-directory", "-n", "F"], 1),
        (["insert-text", "-n", "F"], 1),
        (["replace", "-n", "3/1/AWR", "F", "G"], 1),
        (["convert", "--to", "json", "F", "out.json"], 1),
        (["compare", "F", "G"], 2),
        (["match", "--query", "/3/1/AWR > 0", "F"], 2),
    ],
    ids=lambda v: v[0] if isinstance(v, list) else str(v),
)
def test_a_file_that_cannot_be_read(argv, status, sources, tmp_path):
    """A tape that ends in the middle of a material cannot be indexed."""
    _write(tmp_path / "F", GOOD[:1500])
    shutil.copy(sources["good"], tmp_path / "G")
    result = run_cli(argv, tmp_path)
    assert result.returncode == status, result.stderr
    assert "Traceback" not in result.stderr
    assert TRUNCATED in result.stderr
