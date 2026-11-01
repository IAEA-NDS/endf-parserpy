"""Tests for the fast path of ``endf-cli validate``.

``validate`` first parses all sections of an MF of a material in a
single call (numpy or list mode) and only if that fails falls back to
parsing the sections of this MF one by one in dict mode, which then
decides the verdict and describes the failure. These tests check that the fast path is used for
valid data and that verdicts and failure reports are those of the
per-section validation.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import add_common_cmd_parser_args, get_endf_parser
from endf_parserpy.tape.endf_file import EndfFile

REPO = Path(__file__).resolve().parent.parent
TESTDATA = REPO / "tests" / "testdata"
CU = TESTDATA / "n_2925_29-Cu-63.endf"
ZN = TESTDATA / "n_3025_30-Zn-64.endf"
PU = TESTDATA / "dec-094_Pu_244.endf"


def _args(*argv):
    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap, defaults=validate.STRICT_DEFAULT_ARGS)
    args = vars(ap.parse_args(list(argv)))
    args["subcommand"] = validate.COMMAND_NAME
    return args


@pytest.fixture(scope="module")
def parsers():
    args = _args()
    return get_endf_parser(args), validate.get_fast_parser(args)


def _lines(path):
    return Path(path).read_bytes().split(b"\n")[:-1]


def _write(path, lines):
    Path(path).write_bytes(b"\n".join(lines) + b"\n")
    return path


def _tape(path, files):
    """A multi-material tape of the materials of single-material files."""
    bodies = [_lines(f) for f in files]
    out = [bodies[0][0]]
    for body in bodies:
        out += body[1:-1]
    out.append(bodies[0][-1])
    return _write(path, out)


def _corrupt_first(lines, mat, mf):
    """Corrupt the first data field of the first line of MAT/MF."""
    out = list(lines)
    for i, line in enumerate(out):
        if line[66:70] == b"%4d" % mat and line[70:72] == b"%2d" % mf:
            out[i] = b"BADBADBAD!!" + line[11:]
            return out
    raise AssertionError(f"no line of MAT {mat} MF {mf}")


@pytest.fixture
def no_per_section_parsing(monkeypatch):
    """Make the per-section validation fail loudly if it is reached."""

    def fail(*args, **kwargs):
        raise AssertionError("per-section parsing was used")

    monkeypatch.setattr(EndfFile, "_parse_section", fail)


@pytest.fixture
def per_section_parsing(monkeypatch):
    """Record the ``(MF, MT)`` of every per-section parse."""
    seen = []
    orig = EndfFile._parse_section

    def spy(self, entry, mf, mt, raw):
        seen.append((mf, mt))
        return orig(self, entry, mf, mt, raw)

    monkeypatch.setattr(EndfFile, "_parse_section", spy)
    return seen


class _FailingParser:
    """Stands in for a fast-path parser that rejects everything."""

    def parse(self, text):
        raise RuntimeError("rejected by the fast path")


def test_fast_parser_mode(parsers):
    _, fast = parsers
    try:
        import numpy  # noqa: F401

        expected = "numpy"
    except ImportError:
        expected = "list"
    assert fast.read_opts["array_type"] == expected
    assert fast.read_opts["validate_control_records"] is True


def test_fast_parser_explicit_array_type():
    fast = validate.get_fast_parser(_args("--array_type", "dict"))
    assert fast.read_opts["array_type"] == "dict"


@pytest.mark.parametrize("path", [CU, PU])
def test_valid_file_passes_without_per_section_parsing(
    parsers, path, no_per_section_parsing
):
    parser, fast = parsers
    assert validate._validate_file(parser, str(path), fast) == (True, None)


def test_valid_tape_passes_without_per_section_parsing(
    parsers, tmp_path, no_per_section_parsing
):
    parser, fast = parsers
    tape = _tape(tmp_path / "tape.endf", [CU, ZN, CU])
    assert validate._validate_file(parser, str(tape), fast) == (True, None)


def test_failure_report_identical(parsers, tmp_path):
    parser, fast = parsers
    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(CU), 2925, 3))
    old = validate._validate_file(parser, str(bad))
    new = validate._validate_file(parser, str(bad), fast)
    assert new == old
    assert new[0] is False
    assert new[1].startswith("section MF=3/MT=1:\nfailed to parse MF=3/MT=1 ")


@pytest.mark.parametrize("bad_position", [0, 1])
def test_tape_failure_report_identical(parsers, tmp_path, bad_position):
    parser, fast = parsers
    tape = _tape(tmp_path / "tape.endf", [CU, ZN])
    mat = (2925, 3025)[bad_position]
    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(tape), mat, 3))
    old = validate._validate_file(parser, str(bad))
    new = validate._validate_file(parser, str(bad), fast)
    assert new == old
    assert new[1].startswith(f"material #{bad_position} (MAT {mat}), section MF=3/")


def test_structural_failure_identical(parsers, tmp_path):
    parser, fast = parsers
    truncated = _write(tmp_path / "trunc.endf", _lines(CU)[:1000])
    old = validate._validate_file(parser, str(truncated))
    assert validate._validate_file(parser, str(truncated), fast) == old
    assert old[0] is False


def test_fallback_decides_when_fast_path_fails(parsers, tmp_path):
    """A material rejected by the fast path is validated per section."""
    parser, _ = parsers
    tape = _tape(tmp_path / "tape.endf", [CU, ZN])
    assert validate._validate_file(parser, str(tape), _FailingParser()) == (
        True,
        None,
    )
    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(tape), 3025, 3))
    assert validate._validate_file(
        parser, str(bad), _FailingParser()
    ) == validate._validate_file(parser, str(bad))


def test_failing_mf_falls_back_alone(parsers, tmp_path, per_section_parsing):
    """Only the sections of the MF rejected by the fast path are parsed
    one by one; the report is that of the per-section validation."""
    parser, fast = parsers
    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(CU), 2925, 4))
    old = validate._validate_file(parser, str(bad))
    assert old[0] is False
    assert old[1].startswith("section MF=4/MT=2:\nfailed to parse MF=4/MT=2 ")
    per_section_parsing.clear()
    assert validate._validate_file(parser, str(bad), fast) == old
    # the per-section validation stops at the first failing section
    assert per_section_parsing == [(4, 2)]


def test_rejected_mf_falls_back_alone(parsers, tmp_path, per_section_parsing):
    """An MF rejected by the fast path although all of its sections
    parse alone is validated per section; the other MFs of the
    material (and of the other materials of a tape) are not."""
    parser, fast = parsers

    class RejectMF3:
        def parse(self, text):
            if any(line[70:72] == " 3" for line in text.split("\n")):
                raise RuntimeError("rejected by the fast path")
            return fast.parse(text)

    tape = _tape(tmp_path / "tape.endf", [CU, ZN])
    assert validate._validate_file(parser, str(tape), RejectMF3()) == (True, None)
    endf_file = EndfFile(tape, parser=parser)
    expected = [
        key
        for entry in endf_file.index
        for key in sorted(entry.sections)
        if key[0] == 3
    ]
    assert per_section_parsing == expected

    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(tape), 3025, 6))
    per_section_parsing.clear()
    old = validate._validate_file(parser, str(bad))
    assert old[1].startswith("material #1 (MAT 3025), section MF=6/")
    per_section_parsing.clear()
    assert validate._validate_file(parser, str(bad), RejectMF3()) == old
    assert {mf for mf, _ in per_section_parsing} == {3, 6}


def test_file_framing_not_checked(parsers, tmp_path, no_per_section_parsing):
    """As the per-section validation, the fast path ignores the framing
    records of the file, here a FEND record with a nonzero field."""
    parser, fast = parsers
    lines = _lines(CU)
    i = next(k for k, line in enumerate(lines) if k > 0 and line[66:75] == b"2925 0  0")
    lines[i] = b"%11d" % 7 + lines[i][11:]
    path = _write(tmp_path / "fend.endf", lines)
    assert validate._validate_file(parser, str(path), fast) == (True, None)


def test_sections_tape_matches_mini_tapes(parsers, tmp_path):
    """Each section has the text of its mini tape, also for CRLF files."""
    parser, _ = parsers
    crlf = tmp_path / "crlf.endf"
    crlf.write_bytes(b"\r\n".join(_lines(PU)) + b"\r\n")
    for path in (PU, crlf):
        endf_file = EndfFile(path, parser=parser)
        entry = endf_file.index[0]
        keys = sorted(entry.sections)
        text = endf_file._sections_tape(0, keys)
        assert "\r" not in text
        for mf, mt in keys:
            sec = entry.sections[(mf, mt)]
            raw = endf_file._read_span(sec.offset, sec.length)
            mini = endf_file._mini_tape(entry, raw)
            body = mini.split("\n")[1:-3]
            assert "\n".join(body) + "\n" in text
        assert text.split("\n")[0] == endf_file.index.tpid_line


def test_validate_without_numpy_uses_list_mode(tmp_path):
    """Without numpy the fast path parses in list mode."""
    bad = _write(tmp_path / "bad.endf", _corrupt_first(_lines(PU), 3564, 8))
    code = (
        "import sys\n"
        "sys.modules['numpy'] = None\n"
        "from endf_parserpy.cli.actions import validate\n"
        "from endf_parserpy.cli.cmd import cli_interface\n"
        "orig = validate.get_fast_parser\n"
        "def spy(args):\n"
        "    p = orig(args)\n"
        "    print('FAST MODE', p.read_opts['array_type'])\n"
        "    return p\n"
        "validate.get_fast_parser = spy\n"
        "sys.argv = ['endf-cli', 'validate'] + sys.argv[1:]\n"
        "cli_interface()\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    result = subprocess.run(
        [sys.executable, "-c", code, str(PU), str(bad)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert "FAST MODE list" in result.stdout, result.stderr
    assert result.returncode == 1
    assert f"ok - {PU}" in result.stdout
    assert f"failed - {bad}" in result.stdout
    assert "section MF=8/MT=457:\nfailed to parse MF=8/MT=457" in result.stdout


def test_no_fast_path_with_python_parser():
    """With the Python parser, validate parses section by section only."""
    assert validate.get_fast_parser(_args("--no-cpp")) is None
    assert validate.get_fast_parser(_args("--loglevel", "30")) is None
