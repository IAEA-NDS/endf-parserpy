"""endf-cli replace between materials with different MAT numbers: a clean
error and exit status 1, the target file unchanged."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"
ZN64 = TESTDATA / "n_3025_30-Zn-64.endf"


def run_cli(argv):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("path", ["/1/451", "/2", "/", "3/1"])
@pytest.mark.parametrize("backup", [True, False], ids=["backup", "no-backup"])
def test_replace_between_different_mat_numbers(tmp_path, path, backup):
    target = tmp_path / "zn64.endf"
    shutil.copy(ZN64, target)
    argv = ["replace", path, str(CU63), str(target)]
    if not backup:
        argv.insert(1, "--no-backup")
    result = run_cli(argv)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("replace: the source material has MAT=2925 ")
    assert f"the target material in {target} has MAT=3025" in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1
    # nothing written, no backup or temporary file left
    assert target.read_bytes() == ZN64.read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["zn64.endf"]


def test_replace_field_between_different_mat_numbers(tmp_path):
    """A field is copied into the section of the target, whose records
    keep the MAT number of the target."""
    target = tmp_path / "zn64.endf"
    shutil.copy(ZN64, target)
    result = run_cli(["replace", "--no-backup", "/1/451/AWR", str(CU63), str(target)])
    assert result.returncode == 0, result.stderr
    from endf_parserpy import EndfParserCpp

    parser = EndfParserCpp()
    assert parser.parsefile(target, include=[(1, 451)])[1][451]["AWR"] == (
        parser.parsefile(CU63, include=[(1, 451)])[1][451]["AWR"]
    )
    assert parser.parsefile(target, include=[])[1][451][0][66:70] == "3025"


def test_replace_section_with_same_mat_number(tmp_path):
    """The same MAT number (here the same file) still works."""
    target = tmp_path / "cu63.endf"
    shutil.copy(CU63, target)
    result = run_cli(["replace", "--no-backup", "/1/451", str(CU63), str(target)])
    assert result.returncode == 0, result.stderr
    from endf_parserpy import EndfParserCpp

    parser = EndfParserCpp()
    assert parser.parsefile(target) == parser.parsefile(CU63)
