"""endf-cli replace and compare with several sections with the same label."""

import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import EndfFile, EndfParserPy, compare_objects
from endf_parserpy.cli.cmd_utils import parsed_material_dict

TESTDATA = Path(__file__).resolve().parent / "testdata"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"
H1_GAMINR = TESTDATA / "gendf" / "h1_gaminr.gam"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"
GENDF = ["--endf_format", "gendf"]


def run_cli(argv):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def parser():
    return EndfParserPy(endf_format="gendf")


def write_list(parser, material, path):
    parser.writefile(str(path), material)
    return path


def izam_of(path, parser):
    material = parser.parsefile(str(path))
    return [
        (s["MF"], s["MT"], s.get("IZAM")) for s in material[1:] if isinstance(s, dict)
    ]


@pytest.fixture
def changed_am241(tmp_path, parser):
    """Am-241 with the second MF3/MT102 changed and a fourth one added."""
    material = parser.parsefile(str(AM241))
    material[3]["IZAM"] = 952421.0
    extra = dict(material[4])
    extra["IZAM"] = 952423.0
    material.append(extra)
    return write_list(parser, material, tmp_path / "changed.gendf")


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "target.gendf"
    path.write_bytes(AM241.read_bytes())
    return path


# -- replace ----------------------------------------------------------------------


def test_replace_a_whole_material_copies_the_sequence(changed_am241, target, parser):
    result = run_cli(["replace", *GENDF, "-n", "#0", str(changed_am241), str(target)])
    assert result.returncode == 0, result.stderr
    assert izam_of(target, parser) == izam_of(changed_am241, parser)
    assert [x[2] for x in izam_of(target, parser)][1:] == [
        0.0,
        952421.0,
        952422.0,
        952423.0,
    ]


def test_replace_an_mf_copies_the_sequence(tmp_path, target, parser):
    material = parser.parsefile(str(AM241))
    del material[2]  # the source has two MF3/MT102 sections
    source = write_list(parser, material, tmp_path / "two.gendf")
    result = run_cli(["replace", *GENDF, "-n", "#0/3", str(source), str(target)])
    assert result.returncode == 0, result.stderr
    assert izam_of(target, parser) == [
        (1, 451, None),
        (3, 102, 952420.0),
        (3, 102, 952422.0),
    ]


def test_replace_one_occurrence(changed_am241, target, parser):
    result = run_cli(
        ["replace", *GENDF, "-n", "3/102#1", str(changed_am241), str(target)]
    )
    assert result.returncode == 0, result.stderr
    assert [x[2] for x in izam_of(target, parser)][1:] == [0.0, 952421.0, 952422.0]


def test_replace_another_occurrence_and_by_position(changed_am241, target, parser):
    result = run_cli(
        [
            "replace",
            *GENDF,
            "-n",
            "--source-path",
            "3/102#3",
            "#0/#1",
            str(changed_am241),
            str(target),
        ]
    )
    assert result.returncode == 0, result.stderr
    assert [x[2] for x in izam_of(target, parser)][1:] == [952423.0, 952420.0, 952422.0]


def test_replace_a_field_of_one_occurrence(changed_am241, target, parser):
    result = run_cli(
        ["replace", *GENDF, "-n", "3/102#1/IZAM", str(changed_am241), str(target)]
    )
    assert result.returncode == 0, result.stderr
    assert [x[2] for x in izam_of(target, parser)][1:] == [0.0, 952421.0, 952422.0]


# -- compare ---------------------------------------------------------------------------


def test_compare_pairs_the_occurrences(changed_am241):
    result = run_cli(["compare", *GENDF, str(AM241), str(changed_am241)])
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "Value mismatch at /3/102#1/IZAM (952420.0 vs 952421.0)",
        f"unpaired: section 3/102#3 only in {changed_am241}",
    ]


def test_compare_equal_gendf_files(changed_am241):
    result = run_cli(["compare", *GENDF, str(changed_am241), str(changed_am241)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_compare_reports_a_different_order(tmp_path, parser):
    material = parser.parsefile(str(H1_GAMINR))
    material[2], material[3] = material[3], material[2]
    swapped = write_list(parser, material, tmp_path / "swapped.gam")
    result = run_cli(["compare", *GENDF, str(H1_GAMINR), str(swapped)])
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        f"section order differs: {H1_GAMINR} has 1/451, 23/501, 26/502, 23/504, "
        f"26/504, 23/525; {swapped} has 1/451, 26/502, 23/501, 23/504, 26/504, "
        "23/525"
    ]


def test_compare_reports_the_order_of_occurrences(tmp_path, parser):
    material = parser.parsefile(str(AM241))
    material[1], material[2] = material[2], material[1]
    moved = write_list(parser, material, tmp_path / "moved.gendf")
    result = run_cli(["compare", *GENDF, str(AM241), str(moved)])
    assert result.returncode == 1
    assert result.stdout.splitlines()[-1] == (
        f"section order differs: {AM241} has 1/451, 3/102#0, 3/102#1, 3/102#2; "
        f"{moved} has 3/102#0, 1/451, 3/102#1, 3/102#2"
    )


def test_compare_endf6_output_is_unchanged(tmp_path):
    """The output for ENDF-6 files is that of the comparison of the
    {MF: {MT: section}} dicts, as before the pairing by occurrence."""
    other = tmp_path / "other.endf"
    with EndfFile(CU63, parser=EndfParserPy(), check_edits="deferred") as ef:
        ef["#0/3/2/AWR"] = 1.0
        ef["#0/3/1/xstable/xs/3"] = 0.5
        del ef["#0/3/102"]
        ef.export(other)
    result = run_cli(["compare", "--no-cpp", str(CU63), str(other)])
    assert result.returncode == 1
    parser = EndfParserPy()
    expected = io.StringIO()
    with contextlib.redirect_stdout(expected):
        with EndfFile(CU63, parser=parser) as ef1, EndfFile(
            other, parser=parser
        ) as ef2:
            compare_objects(
                parsed_material_dict(ef1[0]),
                parsed_material_dict(ef2[0]),
                fail_on_diff=False,
            )
    assert result.stdout == expected.getvalue()
    lines = result.stdout.splitlines()
    assert "at path /3: only obj1 contains {102}" in lines
    assert "Value mismatch at /3/2/AWR (62.389 vs 1.0)" in lines
    assert "#" not in result.stdout
