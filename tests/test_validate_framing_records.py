############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The check of the framing records (SEND, FEND, MEND, TEND).

``endf-cli validate`` parses the sections of a file one by one through
``EndfFile``, with generated FEND/MEND/TEND records, so that the framing
records of the file are checked separately, once per file, by
``check_framing``. The damaged files are built in ``tmp_path`` from the
files of ``tests/testdata``.
"""

import argparse
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import add_common_cmd_parser_args, get_endf_parser
from endf_parserpy.tape import FramingProblem, check_framing
from endf_parserpy.tape import parse_tape_file, write_tape_file
from endf_parserpy.utils.debugging_utils import compare_objects

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU = TESTDATA / "n_2925_29-Cu-63.endf"
ZN = TESTDATA / "n_3025_30-Zn-64.endf"
PU = TESTDATA / "dec-094_Pu_244.endf"
BLANK = b" " * 80


def _lines(path):
    return Path(path).read_bytes().split(b"\n")[:-1]


def _write(path, lines, ending=b"\n"):
    Path(path).write_bytes(b"".join(line + ending for line in lines))
    return path


def _ci(field):
    field = field.strip()
    return int(field) if field else 0


def _kind(line):
    mat, mf, mt = _ci(line[66:70]), _ci(line[70:72]), _ci(line[72:75])
    if mt != 0:
        return "section"
    if mat == -1:
        return "TEND"
    if mat == 0:
        return "MEND"
    return "FEND" if mf == 0 else "SEND"


def _index(lines, kind, n=0):
    """Index of the ``n``-th record of ``kind`` after the tape head."""
    return [i for i, line in enumerate(lines) if i > 0 and _kind(line) == kind][n]


def _ctrl(line, mat=None, mf=None, mt=None):
    line = bytearray(line.ljust(75))
    for value, cols in ((mat, slice(66, 70)), (mf, slice(70, 72)), (mt, slice(72, 75))):
        if value is not None:
            line[cols] = value
    return bytes(line)


def _field(line, k, text):
    return line[: 11 * k] + text.rjust(11) + line[11 * k + 11 :]


def _edit(lines, i, new):
    lines = list(lines)
    lines[i] = new
    return lines


def _delete(lines, i):
    return lines[:i] + lines[i + 1 :]


def _insert(lines, i, new):
    return lines[:i] + [new] + lines[i:]


def _tape(files):
    """The lines of a tape of the materials of single-material files."""
    bodies = [_lines(f) for f in files]
    out = [bodies[0][0]]
    for body in bodies:
        out += body[1:-1]
    out.append(bodies[0][-1])
    return out


def _sections_of_mf(lines, mf):
    """Start and end (after the SEND) of the sections of an MF."""
    rows = [i for i, line in enumerate(lines) if line[70:72] == b"%2d" % mf]
    sends = [i for i in rows if _kind(lines[i]) == "SEND"]
    starts = [rows[0]] + [i + 1 for i in sends[:-1]]
    return list(zip(starts, [i + 1 for i in sends]))


def _swap_first_sections(lines, mf):
    (a0, a1), (b0, b1) = _sections_of_mf(lines, mf)[:2]
    return lines[:a0] + lines[b0:b1] + lines[a0:a1] + lines[b1:]


def _duplicate_first_section(lines, mf):
    a0, a1 = _sections_of_mf(lines, mf)[0]
    return lines[:a1] + lines[a0:a1] + lines[a1:]


def _cu_cases():
    """Damaged variants of Cu-63: (lines, line of the first problem, text)."""
    L = _lines(CU)
    S, F, M, T = (_index(L, k) for k in ("SEND", "FEND", "MEND", "TEND"))
    S3 = _index(L, "SEND", 2)  # the SEND of MF3/MT1
    n = len(L)
    return {
        "send_wrong_mat": (
            _edit(L, S, _ctrl(L[S], mat=b"2926")),
            S + 1,
            "found a SEND record (MAT/MF/MT 2926/1/0)",
        ),
        "send_mat_zero": (
            _edit(L, S, _ctrl(L[S], mat=b"   0")),
            S + 1,
            "found a SEND record (MAT/MF/MT 0/1/0)",
        ),
        "send_wrong_mf": (
            _edit(L, S, _ctrl(L[S], mf=b" 2")),
            S + 1,
            "expected a record of section MF=1/MT=451 of MAT 2925 or its SEND "
            "record (MAT/MF/MT 2925/1/0), found a SEND record (MAT/MF/MT 2925/2/0)",
        ),
        "send_missing": (
            _delete(L, S3),
            S3 + 1,
            "found a record of section MF=3/MT=2 of MAT 2925; the SEND record "
            "of section MF=3/MT=1 is missing",
        ),
        "send_missing_before_fend": (
            _delete(L, S),
            S + 1,
            "found a FEND record (MAT/MF/MT 2925/0/0); the SEND record of "
            "section MF=1/MT=451 is missing",
        ),
        "send_extra": (
            _insert(L, S + 1, L[S]),
            S + 2,
            "expected a section of MF=1 of MAT 2925 or the FEND record "
            "(MAT/MF/MT 2925/0/0), found a SEND record (MAT/MF/MT 2925/1/0)",
        ),
        "fend_wrong_mat": (
            _edit(L, F, _ctrl(L[F], mat=b"2926")),
            F + 1,
            "found a FEND record (MAT/MF/MT 2926/0/0)",
        ),
        "fend_missing": (
            _delete(L, F),
            F + 1,
            "found a record of section MF=2/MT=151 of MAT 2925; the FEND record "
            "of MF=1 is missing",
        ),
        "fend_extra": (
            _insert(L, F + 1, L[F]),
            F + 2,
            "expected a section of MAT 2925 or the MEND record "
            "(MAT/MF/MT 0/0/0), found a FEND record (MAT/MF/MT 2925/0/0)",
        ),
        "fend_last_missing": (
            _delete(L, M - 1),
            M,
            "found a MEND record (MAT/MF/MT 0/0/0); the FEND record is missing",
        ),
        "mend_mat_nonzero": (
            _edit(L, M, _ctrl(L[M], mat=b"2925")),
            M + 1,
            "expected a section of MAT 2925 or the MEND record "
            "(MAT/MF/MT 0/0/0), found a FEND record (MAT/MF/MT 2925/0/0)",
        ),
        "mend_missing": (
            _delete(L, M),
            M + 1,
            "found a TEND record (MAT/MF/MT -1/0/0); the MEND record is missing",
        ),
        "mend_extra": (
            _insert(L, M + 1, L[M]),
            M + 2,
            "expected a section of a new material or the TEND record "
            "(MAT/MF/MT -1/0/0), found a MEND record (MAT/MF/MT 0/0/0)",
        ),
        "tend_missing": (
            _delete(L, T),
            n - 1,
            "the file ends here, the TEND record is missing",
        ),
        "tend_wrong_mat": (
            _edit(L, T, _ctrl(L[T], mat=b"  -2")),
            n,
            "found a FEND record (MAT/MF/MT -2/0/0)",
        ),
        "tend_wrong_mf": (
            _edit(L, T, _ctrl(L[T], mf=b" 1")),
            n,
            "found a TEND record (MAT/MF/MT -1/1/0)",
        ),
        "tend_twice": (
            L + [L[T]],
            n + 1,
            "only blank lines may follow the TEND record",
        ),
        "text_after_tend": (
            L + [BLANK, b"some text"],
            n + 2,
            "only blank lines may follow the TEND record",
        ),
        "section_after_tend": (
            L + L[1:5],
            n + 1,
            "only blank lines may follow the TEND record",
        ),
        "send_mt_text": (
            _edit(L, S, _ctrl(L[S], mt=b" ab")),
            S + 1,
            'invalid MT field " ab" (columns 73-75)',
        ),
        "send_mat_text": (
            _edit(L, S, _ctrl(L[S], mat=b"29x5")),
            S + 1,
            'invalid MAT field "29x5" (columns 67-70)',
        ),
        "send_mf_text": (
            _edit(L, S, _ctrl(L[S], mf=b"1x")),
            S + 1,
            'invalid MF field "1x" (columns 71-72)',
        ),
        "fend_mat_text": (
            _edit(L, F, _ctrl(L[F], mat=b"ab  ")),
            F + 1,
            'invalid MAT field "ab  " (columns 67-70)',
        ),
        "fend_mt_text": (
            _edit(L, F, _ctrl(L[F], mt=b"  y")),
            F + 1,
            'invalid MT field "  y" (columns 73-75)',
        ),
        "mend_mf_text": (
            _edit(L, M, _ctrl(L[M], mf=b" z")),
            M + 1,
            'invalid MF field " z" (columns 71-72)',
        ),
        "tend_mat_text": (
            _edit(L, T, _ctrl(L[T], mat=b"-1x ")),
            n,
            'invalid MAT field "-1x " (columns 67-70)',
        ),
        "tpid_mt_text": (
            _edit(L, 0, _ctrl(L[0], mt=b" ab")),
            1,
            'invalid MT field " ab" (columns 73-75)',
        ),
        "send_c1": (
            _edit(L, S, _field(L[S], 0, b"1.000000+0")),
            S + 1,
            "the fields 1-6 (columns 1-66) of the SEND record must be zero or "
            "blank, but field 1 is not",
        ),
        "fend_l1_n2": (
            _edit(L, F, _field(_field(L[F], 2, b"3"), 5, b"1")),
            F + 1,
            "of the FEND record must be zero or blank, but fields 3, 6 are not",
        ),
        "mend_text": (
            _edit(L, M, b"abc".ljust(66) + L[M][66:]),
            M + 1,
            'of the MEND record must be zero or blank, but field 1 is not: "abc"',
        ),
        "tend_text": (
            _edit(L, T, b"END OF TAPE".ljust(66) + L[T][66:]),
            n,
            "of the TEND record must be zero or blank",
        ),
        "fend_non_ascii": (
            _edit(L, F, L[F][:77] + b"\xe9" + L[F][78:]),
            F + 1,
            "column 78 of the FEND record contains the byte 0xe9, which is not "
            "a printable ASCII character",
        ),
        "blank_before_tpid": ([b""] + L, 1, "blank line"),
        "blank_after_send": (_insert(L, S + 1, b""), S + 2, "blank line"),
        "blank_after_fend": (_insert(L, F + 1, BLANK), F + 2, "blank line"),
        "blank_before_tend": (_insert(L, T, b""), n, "blank line"),
        "blank_in_section": (_insert(L, 5, b""), 6, "blank line"),
        "section_twice": (
            _duplicate_first_section(L, 3),
            S3 + 2,
            "section MF=3/MT=1 of MAT 2925 occurs a second time in the material",
        ),
        "mat_damaged_in_section": (
            _edit(L, 10, _ctrl(L[10], mat=b"2926")),
            11,
            "expected a record of section MF=1/MT=451 of MAT 2925 or its SEND "
            "record (MAT/MF/MT 2925/1/0), found a record of section "
            "MF=1/MT=451 of MAT 2926",
        ),
    }


CU_CASES = _cu_cases()


@pytest.fixture(scope="module")
def cpp_parser():
    return EndfParserCpp()


def _args(*argv):
    ap = argparse.ArgumentParser()
    add_common_cmd_parser_args(ap, defaults=validate.STRICT_DEFAULT_ARGS)
    args = vars(ap.parse_args(list(argv)))
    args["subcommand"] = validate.COMMAND_NAME
    return args


@pytest.fixture(scope="module")
def cpp_parsers():
    args = _args()
    return get_endf_parser(args), validate.get_fast_parser(args)


@pytest.fixture(scope="module")
def py_parsers():
    args = _args("--no-cpp")
    return get_endf_parser(args), validate.get_fast_parser(args)


@pytest.mark.parametrize("path", [CU, ZN, PU, TESTDATA / "tsl_Al.endf"])
def test_valid_files(path):
    assert check_framing(path) == []


def test_valid_variants(tmp_path):
    lines = _lines(CU)
    # CRLF line endings, no newline after the last line, blank lines after
    # the TEND record, sequence numbers on some lines only, framing records
    # with blank columns 1-66 and with blank or signed zero control fields
    assert check_framing(_write(tmp_path / "crlf.endf", lines, b"\r\n")) == []
    path = tmp_path / "nonl.endf"
    path.write_bytes(b"\n".join(lines))
    assert check_framing(path) == []
    path = _write(tmp_path / "tail.endf", lines + [b"", BLANK, b" \t "])
    assert check_framing(path) == []
    mixed = [line[:75] if i % 3 else line for i, line in enumerate(lines)]
    assert check_framing(_write(tmp_path / "mixed.endf", mixed)) == []
    S, F, M = (_index(lines, k) for k in ("SEND", "FEND", "MEND"))
    variant = _edit(lines, S, b" " * 66 + lines[S][66:])
    variant = _edit(variant, F, _ctrl(variant[F], mf=b"-0", mt=b" +0"))
    variant = _edit(variant, M, _ctrl(b" " * 66, mat=b"   0", mf=b" 0", mt=b"  0"))
    S2 = _index(variant, "SEND", 1)
    variant = _edit(variant, S2, _field(variant[S2], 0, b"0.0 "))
    variant = _edit(variant, S2, _field(variant[S2], 2, b"-0"))
    assert check_framing(_write(tmp_path / "variant.endf", variant)) == []


def test_valid_tapes(tmp_path, cpp_parser):
    path = _write(tmp_path / "tape.endf", _tape([CU, ZN, PU, CU]))
    assert check_framing(path) == []
    materials = parse_tape_file(path, parser=cpp_parser)
    out = tmp_path / "written.endf"
    write_tape_file(materials, out, parser=cpp_parser, overwrite=True)
    assert check_framing(out) == []


@pytest.mark.parametrize("name", sorted(CU_CASES))
def test_damaged(name, tmp_path):
    lines, line, text = CU_CASES[name]
    path = _write(tmp_path / "bad.endf", lines)
    problems = check_framing(path)
    assert problems, name
    assert problems[0].line == line
    assert text in problems[0].message


@pytest.mark.parametrize(
    "name", ["send_wrong_mat", "fend_missing", "tend_missing", "blank_after_fend"]
)
@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
def test_validate_report(name, parser_kind, cpp_parsers, py_parsers, tmp_path):
    parsers = cpp_parsers if parser_kind == "cpp" else py_parsers
    lines, line, text = CU_CASES[name]
    path = _write(tmp_path / "bad.endf", lines)
    ok, detail = validate._validate_file(parsers[0], str(path), parsers[1])
    assert not ok
    problem = check_framing(path)[0]
    assert problem.line == line
    assert detail.startswith(f"framing records (SEND/FEND/MEND/TEND):\n{problem}")
    assert text in detail.splitlines()[1]


def test_validate_report_with_section_failure(cpp_parsers, tmp_path):
    # a damaged FEND record and a damaged section: both are reported
    lines = _lines(CU)
    F = _index(lines, "FEND")
    lines = _edit(lines, F, _ctrl(lines[F], mat=b"2926"))
    lines = _edit(lines, 869, _field(lines[869], 1, b"1.2x34E+0"))
    path = _write(tmp_path / "bad.endf", lines)
    ok, detail = validate._validate_file(cpp_parsers[0], str(path), cpp_parsers[1])
    assert not ok
    framing, section = detail.split("\n\n")
    assert framing == (
        "framing records (SEND/FEND/MEND/TEND):\n"
        f"line {F + 1}: expected a section of MF=1 of MAT 2925 or the FEND "
        "record (MAT/MF/MT 2925/0/0), found a FEND record (MAT/MF/MT 2926/0/0)"
    )
    assert section.startswith("section MF=3/MT=1:\nThe section starts at line 866")


def test_validate_report_limit(cpp_parsers, tmp_path):
    lines = _lines(CU)
    for k in range(15):
        lines = _insert(lines, 1, b"")
    path = _write(tmp_path / "bad.endf", lines)
    ok, detail = validate._validate_file(cpp_parsers[0], str(path), cpp_parsers[1])
    assert not ok
    report = detail.split("\n\n")[0].splitlines()
    assert report[1:] == [f"line {k}: blank line" for k in range(2, 12)] + [
        "... and 5 more"
    ]


@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
def test_validate_valid_files(parser_kind, cpp_parsers, py_parsers, tmp_path):
    parsers = cpp_parsers if parser_kind == "cpp" else py_parsers
    for path in (PU, _write(tmp_path / "tape.endf", _tape([PU, PU]))):
        assert validate._validate_file(parsers[0], str(path), parsers[1]) == (
            True,
            None,
        )


def test_framing_problem():
    problem = FramingProblem(12, "blank line")
    assert str(problem) == "line 12: blank line"
    assert problem == FramingProblem(12, "blank line")


# --- options ---------------------------------------------------------------


BLANK_CASES = [name for name in CU_CASES if name.startswith("blank_")]


@pytest.mark.parametrize("name", BLANK_CASES)
def test_ignore_blank_lines(name, tmp_path):
    path = _write(tmp_path / "bad.endf", CU_CASES[name][0])
    assert check_framing(path, ignore_blank_lines=True) == []


@pytest.mark.parametrize("name", ["blank_after_send", "blank_after_fend"])
def test_validate_ignore_blank_lines(name, tmp_path):
    args = _args("--ignore_blank_lines")
    parser, fast = get_endf_parser(args), validate.get_fast_parser(args)
    path = _write(tmp_path / "bad.endf", CU_CASES[name][0])
    assert validate._validate_file(parser, str(path), fast) == (True, None)


# the damages that remain problems with ignore_send_records: the control
# fields, the columns 1-66 and the characters of the records, and blank
# lines
_KEPT_WITH_IGNORE_SEND = (
    "send_mt_text",
    "send_mat_text",
    "send_mf_text",
    "fend_mat_text",
    "fend_mt_text",
    "mend_mf_text",
    "tend_mat_text",
    "tpid_mt_text",
    "fend_non_ascii",
    "send_c1",
    "fend_l1_n2",
    "mend_text",
    "tend_text",
)


# the damages that are other problems with ignore_send_records: the text
# after the TEND record is a record with non-zero columns 1-66, as the
# parsers read it with this option, and a section occurring twice is
# reported also if a TEND record precedes the second one, which does not
# end the tape with this option
_OTHER_WITH_IGNORE_SEND = {
    "text_after_tend": (
        len(CU_CASES["text_after_tend"][0]),
        "the fields 1-6 (columns 1-66) of the MEND record must be zero or blank, "
        'but field 1 is not: "some text"',
    ),
    "section_after_tend": (
        len(CU_CASES["section_after_tend"][0]) - 3,
        "section MF=1/MT=451 of MAT 2925 occurs a second time in the material",
    ),
}


@pytest.mark.parametrize("name", sorted(CU_CASES))
def test_ignore_send_records(name, tmp_path):
    lines, line, text = CU_CASES[name]
    path = _write(tmp_path / "bad.endf", lines)
    problems = check_framing(path, ignore_send_records=True)
    line, text = _OTHER_WITH_IGNORE_SEND.get(name, (line, text))
    # also blank lines and a section occurring twice (the order of the
    # sections) remain problems
    if (
        name in _KEPT_WITH_IGNORE_SEND
        or name in _OTHER_WITH_IGNORE_SEND
        or name.startswith(("blank_", "section_"))
    ):
        assert [(p.line, text in p.message) for p in problems] == [(line, True)]
    else:
        assert problems == []


def test_accept_non_ascii(tmp_path):
    path = _write(tmp_path / "bad.endf", CU_CASES["fend_non_ascii"][0])
    assert check_framing(path, accept_non_ascii=True) == []


def test_accept_d_exponent_and_spaces(tmp_path):
    lines = _lines(CU)
    S = _index(lines, "SEND")
    path = _write(tmp_path / "d.endf", _edit(lines, S, _field(lines[S], 0, b"0.0D+0")))
    assert len(check_framing(path)) == 1
    assert check_framing(path, accept_d_exponent=True) == []
    path = _write(tmp_path / "s.endf", _edit(lines, S, _field(lines[S], 1, b"0.0 +0")))
    assert len(check_framing(path)) == 1
    assert check_framing(path, accept_spaces=True) == []


def test_missing_tpid(tmp_path):
    path = _write(tmp_path / "notpid.endf", _lines(CU)[1:])
    problems = check_framing(path)
    assert [str(p) for p in problems] == [
        "line 1: the tape does not begin with a tape head (TPID) record "
        "(found MAT/MF/MT 2925/1/451)"
    ]
    assert check_framing(path, ignore_missing_tpid=True) == []
    path = _write(tmp_path / "blank.endf", [b""] + _lines(CU)[1:])
    assert [p.line for p in check_framing(path)] == [1, 2]


# --- multi-material tapes --------------------------------------------------


def _tape_cases():
    T = _tape([CU, ZN])
    mend = _index(T, "MEND")
    fend2 = [i for i in range(mend, len(T)) if _kind(T[i]) == "FEND"][0]
    send2 = [i for i in range(mend, len(T)) if _kind(T[i]) == "SEND"][3]
    return {
        "mend_missing": (
            _delete(T, mend),
            mend + 1,
            "expected a section of MAT 2925 or the MEND record (MAT/MF/MT "
            "0/0/0), found a record of section MF=1/MT=451 of MAT 3025; the "
            "MEND record is missing",
        ),
        "mend_nonzero": (
            _edit(T, mend, _ctrl(T[mend], mat=b"2925")),
            mend + 1,
            "found a FEND record (MAT/MF/MT 2925/0/0)",
        ),
        "fend_of_other_material": (
            _edit(T, fend2, _ctrl(T[fend2], mat=b"2925")),
            fend2 + 1,
            "expected a section of MF=1 of MAT 3025 or the FEND record "
            "(MAT/MF/MT 3025/0/0), found a FEND record (MAT/MF/MT 2925/0/0)",
        ),
        "send_text": (
            _edit(T, send2, _ctrl(T[send2], mt=b"x  ")),
            send2 + 1,
            'invalid MT field "x  " (columns 73-75)',
        ),
        "blank_between": (_insert(T, mend + 1, b""), mend + 2, "blank line"),
        "extra_mend": (
            _insert(T, mend + 1, T[mend]),
            mend + 2,
            "expected a section of a new material or the TEND record",
        ),
        "tend_between": (
            _insert(T, mend + 1, T[-1]),
            mend + 3,
            "only blank lines may follow the TEND record",
        ),
    }


TAPE_CASES = _tape_cases()


@pytest.mark.parametrize("name", sorted(TAPE_CASES))
@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
def test_damaged_tape(name, parser_kind, cpp_parsers, py_parsers, tmp_path):
    lines, line, text = TAPE_CASES[name]
    path = _write(tmp_path / "bad.endf", lines)
    problems = check_framing(path)
    assert problems[0].line == line
    assert text in problems[0].message
    if parser_kind == "python" and name != "blank_between":
        return  # the report is the same; parsing the tape takes long
    parsers = cpp_parsers if parser_kind == "cpp" else py_parsers
    ok, detail = validate._validate_file(parsers[0], str(path), parsers[1])
    assert not ok
    assert detail.startswith(f"framing records (SEND/FEND/MEND/TEND):\n{problems[0]}")


# --- agreement with a full parse -------------------------------------------


def _pu_cases():
    """Damages of the framing records of the decay file of Pu-244."""
    L = _lines(PU)
    S, F, M, T = (_index(L, k) for k in ("SEND", "FEND", "MEND", "TEND"))
    S2 = _index(L, "SEND", 1)
    F2 = _index(L, "FEND", 1)
    cases = {
        "valid": L,
        "send_wrong_mat": _edit(L, S, _ctrl(L[S], mat=b"3565")),
        "send_wrong_mf": _edit(L, S, _ctrl(L[S], mf=b" 2")),
        "send_missing": _delete(L, S),
        "send_extra": _insert(L, S2 + 1, L[S2]),
        "fend_wrong_mat": _edit(L, F, _ctrl(L[F], mat=b"3565")),
        "fend_wrong_mf": _edit(L, F, _ctrl(L[F], mf=b" 1")),
        "fend_missing": _delete(L, F),
        "fend_extra": _insert(L, F + 1, L[F]),
        "fend_last_missing": _delete(L, F2),
        "mend_mat_nonzero": _edit(L, M, _ctrl(L[M], mat=b"3564")),
        "mend_missing": _delete(L, M),
        "mend_extra": _insert(L, M + 1, L[M]),
        "tend_missing": _delete(L, T),
        "tend_wrong_mat": _edit(L, T, _ctrl(L[T], mat=b"  -2")),
        "tend_twice": L + [L[T]],
        "text_after_tend": L + [b"text"],
        "blank_after_tend": L + [b"", BLANK],
        "send_mt_text": _edit(L, S, _ctrl(L[S], mt=b" ab")),
        "fend_mf_text": _edit(L, F, _ctrl(L[F], mf=b" x")),
        "mend_mat_text": _edit(L, M, _ctrl(L[M], mat=b"  ab")),
        "tend_mt_text": _edit(L, T, _ctrl(L[T], mt=b"  q")),
        "fend_mt_blank": _edit(L, F, _ctrl(L[F], mt=b"   ")),
        "mend_ctrl_blank": _edit(L, M, _ctrl(L[M], mat=b"    ", mf=b"  ", mt=b"   ")),
        "send_c2": _edit(L, S, _field(L[S], 1, b"2.5")),
        "send_blank": _edit(L, S, b" " * 66 + L[S][66:]),
        "fend_n1": _edit(L, F, _field(L[F], 4, b"7")),
        "fend_zeros": _edit(
            L, F, (b"%11s" % b"0.0") * 2 + b"%11s" % b"0" * 4 + L[F][66:]
        ),
        "mend_text": _edit(L, M, b"abc".ljust(66) + L[M][66:]),
        "tend_l2": _edit(L, T, _field(L[T], 3, b"1")),
        "tend_neg_zero": _edit(L, T, _field(L[T], 0, b"-0.0")),
        "fend_non_ascii": _edit(L, F, L[F][:5] + b"\x7f" + L[F][6:]),
        "blank_after_send": _insert(L, S + 1, b""),
        "blank_after_fend": _insert(L, F + 1, BLANK),
        "blank_after_mend": _insert(L, M + 1, b""),
        "blank_before_tpid": [b""] + L,
        "section_twice": _duplicate_first_section(L, 1),
        "sections_descending": _swap_first_sections(L, 1),
        # the order of the sections: MF8 before MF1, MF1 divided by a
        # FEND record (MF1 after its FEND record)
        "mf_descending": L[:1] + L[F + 1 : F2 + 1] + L[1 : F + 1] + L[F2 + 1 :],
        "mf_split_by_fend": _insert(L, S + 1, L[F]),
        # the lines after the TEND record: a section in ascending order
        # (MF8 after MF1 of the same material), and MF1/MT451 again
        "section_after_tend": L[: F + 1] + [L[M], L[T]] + L[F + 1 :],
        "section_after_tend_twice": L + L[1 : S + 1] + [L[F], L[M], L[T]],
        # the end of the data: without the MEND and TEND records, without
        # the last SEND, FEND, MEND and TEND records
        "mend_tend_missing": L[:M],
        "end_records_missing": L[: F2 - 1],
        # a record with MF=0 and MT≠0 between the sections
        "record_mf0_mt451": _insert(L, S + 1, _ctrl(L[S], mf=b" 0", mt=b"451")),
    }
    return cases


PU_CASES = _pu_cases()


# the options of validate, and with ignore_send_records
_OPTION_ARGS = {"strict": (), "ignore_send_records": ("--ignore_send_records",)}

# non-numeric control fields, which EndfParserCpp reads as numbers
# (fix/strict-control-fields rejects them)
_CPP_LENIENT_CONTROL_FIELDS = {
    "send_mt_text",
    "fend_mf_text",
    "mend_mat_text",
    "tend_mt_text",
}


@pytest.fixture(scope="module")
def full_parsers():
    """The parsers of a full parse (C++, Python) and of validate (with the
    parser of the fast path) for the options of validate and with
    ignore_send_records."""
    result = {}
    for option, argv in _OPTION_ARGS.items():
        args = _args(*argv)
        py_args = _args("--no-cpp", *argv)
        result[option] = (
            (get_endf_parser(args), get_endf_parser(py_args)),
            (get_endf_parser(args), validate.get_fast_parser(args)),
        )
    return result


def _parses(parser, path, **kwargs):
    try:
        parser.parsefile(str(path), **kwargs)
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.parametrize("option", sorted(_OPTION_ARGS))
@pytest.mark.parametrize("name", sorted(PU_CASES))
def test_agreement_with_full_parse(name, option, full_parsers, tmp_path):
    """The check fails if and only if a full parse fails with one of the
    parsers (with the options of validate, and with ignore_send_records),
    so that it finds everything a full parse finds, and nothing else;
    validate fails if and only if the check fails, as the sections are
    valid. With ignore_send_records, both parsers give the same verdict,
    except for non-numeric control fields."""
    path = _write(tmp_path / "bad.endf", PU_CASES[name])
    parsers, validate_parsers = full_parsers[option]
    verdicts = [_parses(parser, path) for parser in parsers]
    ignore_send_records = option == "ignore_send_records"
    problems = check_framing(path, ignore_send_records=ignore_send_records)
    assert (problems == []) == all(verdicts), (verdicts, problems)
    ok, _ = validate._validate_file(validate_parsers[0], str(path), validate_parsers[1])
    assert ok == all(verdicts)
    if ignore_send_records and name not in _CPP_LENIENT_CONTROL_FIELDS:
        assert verdicts[0] == verdicts[1]


# the damages of the framing records that both parsers accept with
# ignore_send_records, also with include and exclude, which read the
# other sections verbatim
_ACCEPTED_WITH_IGNORE_SEND = (
    "send_missing",
    "send_extra",
    "send_wrong_mf",
    "fend_missing",
    "fend_wrong_mf",
    "mend_extra",
    "mf_split_by_fend",
    "section_after_tend",
    "mend_tend_missing",
    "end_records_missing",
    "blank_after_tend",
)
_FILTERS = {
    "full": {},
    "include": {"include": [8]},
    "exclude": {"exclude": [1]},
    "exclude_mt": {"exclude": [(1, 451)]},
}


@pytest.mark.parametrize("filt", sorted(_FILTERS))
@pytest.mark.parametrize("name", _ACCEPTED_WITH_IGNORE_SEND)
def test_ignore_send_records_parsers_agree(name, filt, full_parsers, tmp_path):
    lines = PU_CASES[name]
    path = _write(tmp_path / "bad.endf", lines)
    cpp, py = full_parsers["ignore_send_records"][0]
    kwargs = _FILTERS[filt]
    res_cpp = cpp.parsefile(str(path), **kwargs)
    res_py = py.parsefile(str(path), **kwargs)
    assert compare_objects(res_cpp, res_py, fail_on_diff=False)
    # the sections are those of the valid file
    expected = cpp.parsefile(str(PU), **kwargs)
    assert compare_objects(res_cpp, expected, fail_on_diff=False)
    assert check_framing(path, ignore_send_records=True) == []


@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
def test_sections_after_tend_with_ignore_send_records(parser_kind, tmp_path):
    """With ignore_send_records, the parsers read the sections after a
    TEND record, and validate validates them: the index does not end at
    the TEND record, and a material without MEND record ends with the
    file."""
    from endf_parserpy.tape.framing import _check_framing_and_index

    lines = PU_CASES["section_after_tend"]
    tend = _index(lines, "TEND")
    head = tend + 1  # the HEAD record of MF8/MT457 after the TEND record
    bad = _edit(lines, head, _field(lines[head], 3, b"x"))
    argv = ("--ignore_send_records",) + (
        ("--no-cpp",) if parser_kind == "python" else ()
    )
    args = _args(*argv)
    parser, fast_parser = get_endf_parser(args), validate.get_fast_parser(args)
    path = _write(tmp_path / "valid.endf", lines)
    assert validate._validate_file(parser, str(path), fast_parser) == (True, None)
    problems, index, error = _check_framing_and_index(path, ignore_send_records=True)
    assert (problems, error) == ([], None)
    assert [sorted(m.sections) for m in index.materials] == [
        [(1, 451), (1, 452)],
        [(8, 457)],
    ]
    path = _write(tmp_path / "bad.endf", bad)
    ok, detail = validate._validate_file(parser, str(path), fast_parser)
    assert not ok
    assert "section MF=8/MT=457:" in detail
    assert not _parses(parser, path)
    # without the MEND and TEND records
    path = _write(tmp_path / "noend.endf", PU_CASES["mend_tend_missing"])
    problems, index, error = _check_framing_and_index(path, ignore_send_records=True)
    assert (problems, error) == ([], None)
    assert index.materials[0].byte_length == path.stat().st_size - len(lines[0]) - 1
    assert validate._validate_file(parser, str(path), fast_parser) == (True, None)


# --- one scan --------------------------------------------------------------


def test_index_of_the_framing_scan(tmp_path):
    from endf_parserpy.tape import TapeIndex
    from endf_parserpy.tape.framing import _check_framing_and_index

    tape = _write(tmp_path / "tape.endf", _tape([CU, ZN, PU]))
    for path in (CU, PU, tape):
        problems, index, error = _check_framing_and_index(path)
        assert (problems, error) == ([], None)
        expected = TapeIndex.from_file(path)
        assert index.materials == expected.materials
        assert (index.tpid_line, index.tpid_offset, index.tpid_length) == (
            expected.tpid_line,
            expected.tpid_offset,
            expected.tpid_length,
        )
        assert (index.source, index.source_size) == (str(path), path.stat().st_size)
    # a tape that the index rejects: the problems and the error
    path = _write(tmp_path / "bad.endf", CU_CASES["mend_missing"][0][:-1])
    problems, index, error = _check_framing_and_index(path)
    assert index is None
    assert "the final MEND or TEND record is missing" in str(error)
    assert [p.line for p in problems] == [len(_lines(path))]


def test_validate_scans_once(cpp_parsers, tmp_path, monkeypatch):
    from endf_parserpy.tape import TapeIndex

    def fail(*args, **kwargs):
        raise AssertionError("second scan")

    path = _write(tmp_path / "tape.endf", _tape([PU, PU]))
    monkeypatch.setattr(TapeIndex, "from_file", fail)
    ok, detail = validate._validate_file(cpp_parsers[0], str(path), cpp_parsers[1])
    assert (ok, detail) == (True, None)
