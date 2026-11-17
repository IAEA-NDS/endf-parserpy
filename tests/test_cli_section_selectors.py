"""Section selectors (MF/MT#k, #k) in the paths of endf-cli."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy.cli.cmd_utils import (
    is_material_qualified,
    open_endf_file,
    resolve_material_path,
    section_label_of,
    section_names,
)
from endf_parserpy import EndfParserPy

TESTDATA = Path(__file__).resolve().parent / "testdata"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"
HE4 = TESTDATA / "gendf" / "he4_two_temperatures.gendf"
CU = TESTDATA / "n_2925_29-Cu-63.endf"


def run_cli(argv):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "path, qualified",
    [
        ("#0", True),
        ("#1/3/2", True),
        ("#0/#2", True),
        ("#0/#2/IZAM", True),
        ("9543#0", True),
        ("9543#0/3/102#1/IZAM", True),
        ("/#0/3/", True),
        ("#2/IZAM", False),
        ("3/102#1/IZAM", False),
        ("3/2", False),
        ("1/451/AWR", False),
    ],
)
def test_is_material_qualified(path, qualified):
    assert is_material_qualified(path) is qualified


def test_resolve_on_a_single_material():
    parser = EndfParserPy(endf_format="gendf")
    endf_file = open_endf_file(AM241, parser)
    assert resolve_material_path(endf_file, "3/102#1/IZAM") == "#0/3/102#1/IZAM"
    assert resolve_material_path(endf_file, "#2/IZAM") == "#0/#2/IZAM"
    assert resolve_material_path(endf_file, "#0") == "#0"
    assert section_label_of(endf_file, "#0/#2/IZAM") == (3, 102)
    assert section_label_of(endf_file, "#0/3/102#1") == (3, 102)
    with pytest.raises(IndexError, match="section position 9 out of range"):
        section_label_of(endf_file, "#0/#9")


def test_section_names():
    keys = [(1, 451), (3, 102), (3, 1), (3, 102)]
    assert section_names(keys) == ["1/451", "3/102#0", "3/1", "3/102#1"]


GENDF = ["--endf_format", "gendf"]


def test_show_field_by_occurrence():
    result = run_cli(["show", *GENDF, "3/102#2/IZAM", str(AM241)])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "952422.0"


def test_show_field_by_position_on_a_single_material():
    result = run_cli(["show", *GENDF, "#2/IZAM", str(AM241)])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "952420.0"


def test_show_section_with_material_selector():
    result = run_cli(["show", *GENDF, "9543#0/3/102#1", str(AM241)])
    assert result.returncode == 0, result.stderr
    assert "/IZAM:" in result.stdout and "952420.0" in result.stdout


def test_show_material_lists_the_occurrences():
    result = run_cli(["show", *GENDF, "#0", str(AM241)])
    assert result.returncode == 0, result.stderr
    names = [line.strip() for line in result.stdout.splitlines()[2:]]
    assert names == ["1/451", "3/102#0", "3/102#1", "3/102#2"]


def test_show_mf_lists_the_occurrences():
    result = run_cli(["show", *GENDF, "#0/3", str(AM241)])
    assert result.returncode == 0, result.stderr
    assert "MF=3 sections (MT): 102#0, 102#1, 102#2" in result.stdout


def test_show_ambiguous_label_fails_cleanly():
    result = run_cli(["show", *GENDF, "3/102/IZAM", str(AM241)])
    assert result.returncode == 1
    assert "matches 3 sections at positions [1, 2, 3]" in result.stderr


def test_show_section_path_on_a_multi_material_tape_needs_a_material():
    result = run_cli(["show", *GENDF, "#1/TEMPIN", str(HE4)])
    assert result.returncode == 1
    assert "2 materials" in result.stderr
    result = run_cli(["show", *GENDF, "#1/#0/TEMPIN", str(HE4)])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "600.0"


def test_show_endf6_output_is_unchanged():
    result = run_cli(["show", "#0", str(CU)])
    assert result.returncode == 0
    assert "    3/2\n" in result.stdout and "#" not in result.stdout.split("\n", 2)[2]


def test_explain_by_occurrence_and_position():
    for path in ("3/102#2/IZAM", "#3/IZAM", "#0/3/102#0/IZAM"):
        result = run_cli(["explain", *GENDF, path, str(AM241)])
        assert result.returncode == 0, (path, result.stderr)
        assert result.stdout.strip()


def test_explain_by_position_on_endf6():
    by_label = run_cli(["explain", "1/451/AWR", str(CU)])
    by_position = run_cli(["explain", "#0/AWR", str(CU)])
    assert by_position.returncode == 0, by_position.stderr
    assert by_position.stdout == by_label.stdout


def test_material_commands_reject_a_section_by_position(tmp_path):
    target = tmp_path / "copy.endf"
    target.write_bytes(CU.read_bytes())
    result = run_cli(["remove-material", "#0/#1", str(target)])
    assert result.returncode != 0
    assert target.read_bytes() == CU.read_bytes()
