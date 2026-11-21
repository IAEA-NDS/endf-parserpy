"""update_directory, get_description, set_description and
insert_description with array_type "dict", "list" and "numpy", and the
subcommands update-directory and insert-text with --array_type: the
written result is the same in all three."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy, update_directory
from endf_parserpy.utils.endf6_plumbing import (
    get_description,
    insert_description,
    set_description,
)

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"
ZN64 = TESTDATA / "n_3025_30-Zn-64.endf"
ARRAY_TYPES = ("dict", "list", "numpy")


def _cpp_available():
    try:
        EndfParserCpp()
    except Exception:  # noqa: BLE001
        return False
    return True


def _parsers(atype):
    yield EndfParserPy(array_type=atype)
    if _cpp_available():
        yield EndfParserCpp(array_type=atype)


@pytest.fixture(scope="module", autouse=True)
def numpy_available():
    pytest.importorskip("numpy")


def _edit(parser, filename):
    # remove a section, change the MOD of the first one and the
    # description, and update the directory
    mat = parser.parsefile(filename, include=[(1, 451)])
    del mat[3][2]
    mt451 = mat[1][451]
    if isinstance(mt451["MOD"], dict):
        mt451["MOD"][1] = 7
    else:
        mt451["MOD"][0] = 7
    text = get_description(mat)
    insert_description(mat, "first inserted line\nsecond inserted line", 3)
    assert get_description(mat).splitlines()[3] == "first inserted line".ljust(66)
    assert len(get_description(mat).splitlines()) == len(text.splitlines()) + 2
    update_directory(mat, parser)
    return mat, parser.write(mat)


@pytest.mark.parametrize("filename", [CU63, ZN64])
def test_functions_same_result_in_all_array_types(filename):
    results = {}
    for atype in ARRAY_TYPES:
        for parser in _parsers(atype):
            mat, lines = _edit(parser, filename)
            results[(type(parser).__name__, atype)] = lines
    reference = results[("EndfParserPy", "dict")]
    for key, lines in results.items():
        assert lines == reference, key
    # the directory lists the removed section no more, the MOD is kept
    mt451 = EndfParserPy().parse(reference, include=[(1, 451)])[1][451]
    listed = list(zip(mt451["MFx"].values(), mt451["MTx"].values()))
    assert (3, 2) not in listed
    assert mt451["MOD"][1] == 7
    assert mt451["NXC"] == len(listed)


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_arrays_keep_their_form(atype):
    import numpy as np

    parser = EndfParserPy(array_type=atype)
    mat = parser.parsefile(ZN64, include=[(1, 451)])
    update_directory(mat, parser)
    set_description(mat, "one line")
    mt451 = mat[1][451]
    expected = {"dict": dict, "list": list, "numpy": np.ndarray}[atype]
    for name in ("MFx", "MTx", "NCx", "MOD"):
        assert isinstance(mt451[name], expected)
    if atype == "numpy":
        assert mt451["MFx"].dtype == np.int64 or mt451["MFx"].dtype.kind == "i"
    descr_type = dict if atype == "dict" else list
    assert isinstance(mt451["DESCRIPTION"], descr_type)
    assert get_description(mat) == "one line".ljust(66)
    assert mt451["NWD"] == 6


@pytest.mark.parametrize("atype", ARRAY_TYPES)
def test_set_description_same_lines(atype):
    parser = EndfParserPy(array_type=atype)
    mat = parser.parsefile(ZN64, include=[(1, 451)])
    set_description(mat, "a\nb\n")
    assert get_description(mat).splitlines() == ["a".ljust(66), "b".ljust(66)]
    update_directory(mat, parser)
    reference = EndfParserPy().parsefile(ZN64, include=[(1, 451)])
    set_description(reference, "a\nb\n")
    update_directory(reference, EndfParserPy())
    assert parser.write(mat) == EndfParserPy().write(reference)


# the subcommands


def run_cli(argv, stdin=None):
    # the environment of the test process (see test_cli_multimaterial)
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        input=stdin,
        env=env,
        capture_output=True,
        text=True,
    )


def _changed_copy(tmp_path, name):
    # Cu-63 with an outdated directory: a wrong number of lines of the
    # first section listed
    parser = EndfParserPy()
    mat = parser.parsefile(CU63, include=[(1, 451)])
    mat[1][451]["NCx"][1] = 999
    work = tmp_path / name
    parser.writefile(work, mat)
    return work


@pytest.mark.parametrize("cpp", [False, True], ids=["python", "cpp"])
def test_cli_update_directory_all_array_types(tmp_path, cpp):
    if cpp and not _cpp_available():
        pytest.skip("C++ parser not available")
    outputs = {}
    for atype in ARRAY_TYPES:
        work = _changed_copy(tmp_path, f"{atype}.endf")
        argv = ["update-directory", "-n", "--array_type", atype]
        if not cpp:
            argv.append("--no-cpp")
        result = run_cli(argv + [str(work)])
        assert result.returncode == 0, result.stderr
        assert "Traceback" not in result.stderr
        outputs[atype] = work.read_bytes()
    assert outputs["list"] == outputs["dict"]
    assert outputs["numpy"] == outputs["dict"]
    assert outputs["dict"] != _changed_copy(tmp_path, "orig.endf").read_bytes()
    assert b"        999" not in outputs["dict"]


@pytest.mark.parametrize("cpp", [False, True], ids=["python", "cpp"])
def test_cli_insert_text_all_array_types(tmp_path, cpp):
    if cpp and not _cpp_available():
        pytest.skip("C++ parser not available")
    outputs = {}
    for atype in ARRAY_TYPES:
        work = _changed_copy(tmp_path, f"{atype}.endf")
        argv = ["insert-text", "-n", "-l", "2", "--array_type", atype]
        if not cpp:
            argv.append("--no-cpp")
        result = run_cli(argv + [str(work)], stdin="inserted line\n")
        assert result.returncode == 0, result.stderr
        assert "Traceback" not in result.stderr
        outputs[atype] = work.read_bytes()
    assert outputs["list"] == outputs["dict"]
    assert outputs["numpy"] == outputs["dict"]
    lines = outputs["dict"].decode().splitlines()
    assert any(line.startswith("inserted line".ljust(66)) for line in lines)
