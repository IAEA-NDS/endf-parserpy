############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/23
# Last modified:   2026/11/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The parse of the whole file of ``endf-cli validate``.

With the C++ parser and the strict defaults of the framing options,
validate first parses a file once as a whole (see
``validate._passes_in_one_parse``); a file of one material that parses
without a tolerated mismatch passes without the scan of the framing
records, the ``EndfFile`` and the parses of its MFs. These tests check
over all inputs of the tests of validate and of the framing records
(valid files, damaged files and tapes) that

- a file that passes this way also passes the framing check and the
  validation without this step, so that the step cannot pass a file
  that the full validation rejects, and
- the output and the return code of validate are the same with and
  without this step (``validate.WHOLE_FILE_PARSE``), also with options
  that tolerate mismatches or disable the step.
"""

import argparse
from pathlib import Path

import pytest

from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import add_common_cmd_parser_args, get_endf_parser
from endf_parserpy.tape import check_framing
from test_cli_validate_fast_path import _corrupt_first
from test_section_order import CASES as ORDER_CASES, _file as _order_file
from test_tape_structure_conformance import CASES as CONFORMANCE_CASES
from test_tape_structure_conformance import GENDF_CASES
from test_validate_framing_records import (
    BLANK,
    CU,
    CU_CASES,
    PU,
    PU_CASES,
    STRICT,
    TAPE_CASES,
    TESTDATA,
    ZN,
    _ctrl,
    _edit,
    _field,
    _index,
    _lines,
    _tape,
    _write,
)


def _args(*argv):
    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap, defaults=validate.STRICT_DEFAULT_ARGS)
    args = vars(ap.parse_args(list(argv)))
    args["subcommand"] = validate.COMMAND_NAME
    return args


def _zero_mismatch(lines):
    """Cu-63 with 99 in the field L2 of the HEAD record of MF3/MT1, which
    the recipe gives as 0."""
    i = next(k for k, line in enumerate(lines) if line[70:75] == b" 3  1")
    return _edit(lines, i, _field(lines[i], 3, b"99"))


def _variants():
    """The valid variants of Cu-63 of test_valid_variants and others."""
    lines = _lines(CU)
    S, F, M = (_index(lines, k) for k in ("SEND", "FEND", "MEND"))
    variant = _edit(lines, S, b" " * 66 + lines[S][66:])
    variant = _edit(variant, F, _ctrl(variant[F], mf=b"-0", mt=b" +0"))
    variant = _edit(variant, M, _ctrl(b" " * 66, mat=b"   0", mf=b" 0", mt=b"  0"))
    S2 = _index(variant, "SEND", 1)
    variant = _edit(variant, S2, _field(variant[S2], 0, b"0.0 "))
    variant = _edit(variant, S2, _field(variant[S2], 2, b"-0"))
    i = next(k for k, line in enumerate(lines) if k > 0 and line[66:75] == b"2925 0  0")
    return {
        "crlf": b"".join(line + b"\r\n" for line in lines),
        "no_newline_at_end": b"\n".join(lines),
        "blank_after_tend": lines + [b"", BLANK, b" \t "],
        "sequence_numbers_some_lines": [
            line[:75] if k % 3 else line for k, line in enumerate(lines)
        ],
        "framing_variant": variant,
        "send_d_exponent": _edit(lines, S, _field(lines[S], 0, b" 0.00000D+0")),
        "send_spaces": _edit(lines, S, _field(lines[S], 1, b"  0. 0000+0")),
        "fend_field_nonzero": _edit(lines, i, b"%11d" % 7 + lines[i][11:]),
        "truncated": lines[:1000],
        "corrupt_mf3": _corrupt_first(lines, 2925, 3),
        "corrupt_mf4": _corrupt_first(lines, 2925, 4),
        "zero_mismatch": _zero_mismatch(lines),
    }


def _inputs():
    """All inputs, by name: (lines or bytes, flavor or None)."""
    inputs = {}
    for path in sorted(TESTDATA.rglob("*")):
        if path.is_file() and path.suffix != ".json":
            flavor = "gendf" if path.parent.name == "gendf" else None
            inputs[f"testdata:{path.name}"] = (path.read_bytes(), flavor)
    for name, lines in _variants().items():
        inputs[f"cu:{name}"] = (lines, None)
    for name, (lines, *_) in CU_CASES.items():
        inputs[f"cu_damaged:{name}"] = (lines, None)
    for name, (lines, *_) in TAPE_CASES.items():
        inputs[f"tape_damaged:{name}"] = (lines, None)
    for name, lines in PU_CASES.items():
        inputs[f"pu_damaged:{name}"] = (lines, None)
    for name, (parts, *_) in ORDER_CASES.items():
        inputs[f"order:{name}"] = (_order_file(*parts), None)
    for name, lines in CONFORMANCE_CASES.items():
        inputs[f"conformance:{name}"] = (lines, None)
    for name, lines in GENDF_CASES.items():
        inputs[f"gendf:{name}"] = (lines, "gendf")
    tapes = {
        "cu_zn": [CU, ZN],
        "cu_zn_pu_cu": [CU, ZN, PU, CU],
        "pu_pu": [PU, PU],
    }
    for name, files in tapes.items():
        inputs[f"tape:{name}"] = (_tape(files), None)
    two = _tape([CU, ZN])
    inputs["tape:cu_zn_corrupt_second"] = (_corrupt_first(two, 3025, 3), None)
    return inputs


INPUTS = _inputs()


def _write_input(path, data):
    if isinstance(data, bytes):
        path.write_bytes(data)
        return path
    return _write(path, data)


@pytest.fixture(scope="module")
def input_files(tmp_path_factory):
    """The inputs as files, by flavor: lists of (name, path)."""
    folder = tmp_path_factory.mktemp("inputs")
    files = {}
    for k, (name, (data, flavor)) in enumerate(sorted(INPUTS.items())):
        path = _write_input(folder / f"input_{k:03d}.endf", data)
        files.setdefault(flavor, []).append((name, path))
    return files


# the options of validate with which the step is taken, and others
STEP_OPTIONS = {"strict": (), "ignore_zero_mismatch": ("--ignore_zero_mismatch",)}
OTHER_OPTIONS = {
    "ignore_send_records": ("--ignore_send_records",),
    "accept_spaces": ("--accept_spaces",),
    "endf6": ("--endf_format", "endf6"),
}


def _parsers(argv, flavor):
    if flavor is not None:
        argv = argv + ("--endf_format", flavor)
    args = _args(*argv)
    return get_endf_parser(args), validate.get_fast_parser(args)


def _full_validation(parser, path, fast, monkeypatch):
    monkeypatch.setattr(validate, "WHOLE_FILE_PARSE", False)
    try:
        return validate._validate_file(parser, str(path), fast)
    finally:
        monkeypatch.setattr(validate, "WHOLE_FILE_PARSE", True)


@pytest.mark.parametrize("option", sorted(STEP_OPTIONS))
def test_passing_in_one_parse_implies_clean_framing(option, input_files, monkeypatch):
    """A file that passes by the parse of the whole file has no problem
    with its framing records and passes the full validation."""
    passed = []
    for flavor, files in input_files.items():
        parser, fast = _parsers(STEP_OPTIONS[option], flavor)
        for name, path in files:
            if not validate._passes_in_one_parse(parser, str(path), fast):
                continue
            passed.append(name)
            # the framing check of validate (with the options of its parser)
            assert check_framing(path, **STRICT) == [], name
            assert validate._framing_detail(parser, str(path))[0] is None, name
            full = _full_validation(parser, path, fast, monkeypatch)
            assert full == (True, None), name
    # the step is taken for valid files of one material, not for gendf
    # (whose tape structure is not that of ENDF-6) or tapes
    assert "testdata:n_2925_29-Cu-63.endf" in passed
    assert "cu:crlf" in passed
    assert "conformance:pu:valid" in passed
    assert all(INPUTS[name][1] is None for name in passed)
    assert not any(name.startswith("tape:") for name in passed)


def test_damaged_framing_never_passes_in_one_parse(input_files):
    """No input with a problem of the framing records passes by the
    parse of the whole file (the converse of the test above, over the
    inputs whose framing check fails)."""
    rejected = 0
    for flavor, files in input_files.items():
        parser, fast = _parsers((), flavor)
        for name, path in files:
            if validate._framing_detail(parser, str(path))[0] is None:
                continue
            rejected += 1
            assert not validate._passes_in_one_parse(parser, str(path), fast), name
    # all framing damage cases of test_validate_framing_records
    assert rejected >= len(CU_CASES) + len(TAPE_CASES)


@pytest.mark.parametrize("flavor", [None, "gendf"])
def test_no_step_without_its_conditions(flavor, tmp_path):
    """The step is not taken with the Python parser, with options that
    relax the framing check, for a tape structure other than ENDF-6, or
    for a file of several materials."""
    path = _write(tmp_path / "cu.endf", _lines(CU))
    parser, fast = _parsers((), flavor)
    assert validate._passes_in_one_parse(parser, str(path), fast) is (flavor is None)
    for argv in (("--no-cpp",), ("--ignore_blank_lines",), ("--accept_non_ascii",)):
        parser, fast = _parsers(argv, flavor)
        assert not validate._passes_in_one_parse(parser, str(path), fast), argv
    parser, fast = _parsers((), None)
    tape = _write(tmp_path / "tape.endf", _tape([CU, ZN]))
    assert not validate._passes_in_one_parse(parser, str(tape), fast)
    # a tape of two materials without the MEND record between them, which
    # a parse of the whole file may read as one (single-MAT guard)
    lines = TAPE_CASES["mend_missing"][0]
    bad = _write(tmp_path / "mend_missing.endf", lines)
    assert not validate._passes_in_one_parse(parser, str(bad), fast)
    assert validate._validate_file(parser, str(bad), fast)[0] is False


def test_step_skips_scan(tmp_path, monkeypatch):
    """A valid file of one material passes without the framing scan."""

    def fail(*args, **kwargs):
        raise AssertionError("scan")

    parser, fast = _parsers((), None)
    monkeypatch.setattr(validate, "_check_framing_and_index", fail)
    for path in (CU, PU):
        assert validate._validate_file(parser, str(path), fast) == (True, None)
    # a tape of two materials is scanned
    tape = _write(tmp_path / "tape.endf", _tape([CU, ZN]))
    with pytest.raises(AssertionError, match="scan"):
        validate._validate_file(parser, str(tape), fast)


def _run_validate(capsys, parser, fast, paths, whole_file, monkeypatch):
    monkeypatch.setattr(validate, "WHOLE_FILE_PARSE", whole_file)
    capsys.readouterr()
    code = validate._validate_endf_files(parser, [str(p) for p in paths], fast)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.parametrize("option", sorted({**STEP_OPTIONS, **OTHER_OPTIONS}))
def test_output_identical(option, input_files, capsys, monkeypatch):
    """The output and the return code of validate over all inputs are
    the same with and without the parse of the whole file."""
    argv = {**STEP_OPTIONS, **OTHER_OPTIONS}[option]
    for flavor, files in input_files.items():
        parser, fast = _parsers(argv, flavor)
        paths = [path for _, path in files]
        new = _run_validate(capsys, parser, fast, paths, True, monkeypatch)
        old = _run_validate(capsys, parser, fast, paths, False, monkeypatch)
        assert new == old, (option, flavor)
        if flavor is None and option in STEP_OPTIONS:
            assert new[0] == 1 and "ok - " in new[1] and "failed - " in new[1]


def test_tolerated_mismatch_report(tmp_path, capsys, monkeypatch):
    """A file with a tolerated mismatch is validated by the full path,
    which reports it with the line of the file."""
    lines = _zero_mismatch(_lines(CU))
    path = _write(tmp_path / "zero.endf", lines)
    line = next(k for k, x in enumerate(lines) if x[70:75] == b" 3  1") + 1
    parser, fast = _parsers(STEP_OPTIONS["ignore_zero_mismatch"], None)
    assert not validate._passes_in_one_parse(parser, str(path), fast)
    code, out, _ = _run_validate(capsys, parser, fast, [path], True, monkeypatch)
    assert code == 0
    assert f"MAT 2925 MF3/MT1 L2: 1 zero mismatch, e.g. line {line}: " in out
    assert f"ok (1 tolerated mismatch) - {path}" in out
