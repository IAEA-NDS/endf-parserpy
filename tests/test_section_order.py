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

"""The order of the sections of a material.

Within a material, the sections are in ascending order of MF, and of MT
within an MF, and an MF ends with its FEND record, so that a section
after it has a greater MF. Both parsers check this, also for the
sections read verbatim (include, exclude), and so does
``check_framing`` (and validate). With ``ignore_send_records``, the
position of the FEND records is not checked, but the order of the
sections is. The damaged files are built in ``tmp_path`` from the
decay file of Pu-244 of ``tests/testdata`` (MF1/MT451, MF1/MT452,
MF8/MT457).
"""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import get_endf_parser
from endf_parserpy.tape import check_framing
from test_validate_framing_records import _args, _lines, _tape, _write

TESTDATA = Path(__file__).resolve().parent / "testdata"
PU = TESTDATA / "dec-094_Pu_244.endf"


def _blocks():
    """The lines of Pu-244: tape head, sections (with their SEND records),
    FEND, MEND and TEND records."""
    L = _lines(PU)
    ctrl = [line[66:75] for line in L]
    sends = [i for i, c in enumerate(ctrl) if c[6:9] == b"  0" and c[4:6] != b" 0"]
    fends = [i for i, c in enumerate(ctrl) if c == b"3564 0  0"]
    s451, s452, s457 = sends
    return {
        "tpid": L[:1],
        "451": L[1 : s451 + 1],
        "452": L[s451 + 1 : s452 + 1],
        "457": L[fends[0] + 1 : s457 + 1],
        "fend1": [L[fends[0]]],
        "fend8": [L[fends[1]]],
        "mend": [L[-2]],
        "tend": [L[-1]],
    }


def _file(*parts):
    b = _blocks()
    return [line for part in parts for line in b[part]]


VALID = ("tpid", "451", "452", "fend1", "457", "fend8", "mend", "tend")

# (parts, C++ message, Python message, check_framing message, whether the
# order is also wrong with ignore_send_records)
CASES = {
    "mt_descending": (
        ("tpid", "452", "451", "fend1", "457", "fend8", "mend", "tend"),
        "MT sections must be in ascending order within an MF, but MF=1/MT=451 "
        "follows MF=1/MT=452",
        "The sections of an MF must be in ascending order of MT, but "
        "encountered MT=451 after MT=452 in MF=1 of MAT=3564",
        "section MF=1/MT=451 of MAT 3564 follows section MF=1/MT=452; the "
        "sections of a material must be in ascending order of MF, and of MT "
        "within an MF",
        True,
    ),
    "mf_descending": (
        ("tpid", "457", "fend8", "451", "452", "fend1", "mend", "tend"),
        "MF sections must be in ascending order, but MF=1 follows MF=8",
        "The sections of a material must be in ascending order of MF, but "
        "encountered MF=1 after MF=8 of MAT=3564",
        "section MF=1/MT=451 of MAT 3564 follows section MF=8/MT=457",
        True,
    ),
    "mf_split_by_fend": (
        ("tpid", "451", "fend1", "452", "fend1", "457", "fend8", "mend", "tend"),
        "MF sections must be in ascending order, but MF=1 follows MF=1 and "
        "its FEND record",
        "The sections of a material must be in ascending order of MF, but "
        "encountered MF=1 after the FEND record of MF=1 of MAT=3564",
        "section MF=1/MT=452 of MAT 3564 follows the FEND record of MF=1; the "
        "FEND record ends the MF, so that the next section must have a "
        "greater MF",
        False,
    ),
    "mt_repeated": (
        ("tpid", "451", "452", "451", "fend1", "457", "fend8", "mend", "tend"),
        "MT sections must be in ascending order within an MF, but MF=1/MT=451 "
        "follows MF=1/MT=452",
        "The sections of an MF must be in ascending order of MT, but "
        "encountered MT=451 after MT=452 in MF=1 of MAT=3564",
        "section MF=1/MT=451 of MAT 3564 occurs a second time in the material",
        True,
    ),
    "mt_repeated_next": (
        ("tpid", "451", "451", "452", "fend1", "457", "fend8", "mend", "tend"),
        "MT sections must be in ascending order within an MF, but MF=1/MT=451 "
        "follows MF=1/MT=451",
        "The sections of an MF must be in ascending order of MT, but "
        "encountered MT=451 after MT=451 in MF=1 of MAT=3564",
        "section MF=1/MT=451 of MAT 3564 occurs a second time in the material",
        True,
    ),
}

# the sections are also read verbatim: those of MF1 with include=[8] and
# exclude=[1], one section of MF1 with exclude=[(1, 451)]
FILTERS = {
    "full": {},
    "include": {"include": [8]},
    "exclude": {"exclude": [1]},
    "exclude_mt": {"exclude": [(1, 451)]},
}

OPTIONS = {
    "strict": {},
    "ignore_send_records": {"ignore_send_records": True},
}


def _parser(cls, option):
    return cls(**OPTIONS[option])


@pytest.mark.parametrize("option", sorted(OPTIONS))
@pytest.mark.parametrize("filt", sorted(FILTERS))
@pytest.mark.parametrize("name", sorted(CASES))
def test_parsers_reject_wrong_order(name, filt, option, tmp_path):
    parts, cpp_msg, py_msg, _, with_option = CASES[name]
    path = _write(tmp_path / "bad.endf", _file(*parts))
    kwargs = FILTERS[filt]
    if option == "ignore_send_records" and not with_option:
        # the position of the FEND records is not checked
        expected = EndfParserCpp(**OPTIONS[option]).parsefile(str(PU), **kwargs)
        for cls in (EndfParserCpp, EndfParserPy):
            result = _parser(cls, option).parsefile(str(path), **kwargs)
            assert sorted(result) == sorted(expected)
        return
    with pytest.raises(RuntimeError, match=cpp_msg):
        _parser(EndfParserCpp, option).parsefile(str(path), **kwargs)
    with pytest.raises(Exception, match=py_msg):
        _parser(EndfParserPy, option).parsefile(str(path), **kwargs)


@pytest.mark.parametrize("option", sorted(OPTIONS))
@pytest.mark.parametrize("name", sorted(CASES))
def test_check_framing(name, option, tmp_path):
    parts, _, _, message, with_option = CASES[name]
    path = _write(tmp_path / "bad.endf", _file(*parts))
    ignore_send_records = option == "ignore_send_records"
    problems = check_framing(path, ignore_send_records=ignore_send_records)
    if ignore_send_records and not with_option:
        assert problems == []
        return
    lines = _lines(path)
    # the first line of the second of the two sections
    assert [p.message for p in problems if message in p.message], problems
    problem = [p for p in problems if message in p.message][0]
    mf, mt = (int(x) for x in message.split()[1][3:].split("/MT="))
    assert int(lines[problem.line - 1][70:72]) == mf
    assert int(lines[problem.line - 1][72:75]) == mt
    if not ignore_send_records:
        # the order is the only problem
        assert len(problems) == 1


@pytest.mark.parametrize("parser_kind", ["cpp", "python"])
@pytest.mark.parametrize("name", sorted(CASES))
def test_validate(name, parser_kind, tmp_path):
    parts, _, _, message, _ = CASES[name]
    path = _write(tmp_path / "bad.endf", _file(*parts))
    args = _args() if parser_kind == "cpp" else _args("--no-cpp")
    parser, fast_parser = get_endf_parser(args), validate.get_fast_parser(args)
    ok, detail = validate._validate_file(parser, str(path), fast_parser)
    assert not ok
    assert detail.startswith("framing records (SEND/FEND/MEND/TEND):\n")
    assert message in detail.splitlines()[1]


def test_valid_file(tmp_path):
    path = _write(tmp_path / "valid.endf", _file(*VALID))
    assert path.read_bytes() == PU.read_bytes()
    for option in OPTIONS:
        for cls in (EndfParserCpp, EndfParserPy):
            _parser(cls, option).parsefile(str(path))
        assert check_framing(path, **OPTIONS[option]) == []


def test_mf_ends_without_fend_with_ignore_send_records(tmp_path):
    # with ignore_send_records, MF8 may follow MF1 without a FEND record
    parts = ("tpid", "451", "452", "457", "mend", "tend")
    path = _write(tmp_path / "nofend.endf", _file(*parts))
    for cls in (EndfParserCpp, EndfParserPy):
        result = _parser(cls, "ignore_send_records").parsefile(str(path))
        assert sorted(result) == [0, 1, 8]
    assert check_framing(path, ignore_send_records=True) == []


# --- tapes of several materials ----------------------------------------------


def _material(*parts, mat=None):
    lines = _file(*parts)
    if mat is not None:
        lines = [
            line[:66] + mat + line[70:] if line[66:70] == b"3564" else line
            for line in lines
        ]
    return lines


def test_tape_order_per_material(tmp_path):
    """The order applies within each material; the materials may be in any
    order of their MAT numbers, which the format does not require to be
    ascending."""
    body = ("451", "452", "fend1", "457", "fend8", "mend")
    swapped = ("452", "451", "fend1", "457", "fend8", "mend")
    first = _material("tpid", *body)
    # MAT 3564, then MAT 2000: the order of the sections starts anew
    valid = first + _material(*body, mat=b"2000") + _file("tend")
    path = _write(tmp_path / "tape.endf", valid)
    assert check_framing(path) == []
    assert check_framing(path, ignore_send_records=True) == []
    # the sections of the second material in the wrong order
    bad = first + _material(*swapped, mat=b"2000") + _file("tend")
    path = _write(tmp_path / "bad.endf", bad)
    for option in OPTIONS:
        problems = check_framing(path, **OPTIONS[option])
        assert len(problems) == 1
        assert problems[0].line == len(first) + 1 + len(_file("452"))
        assert "section MF=1/MT=451 of MAT 2000 follows section MF=1/MT=452" in (
            problems[0].message
        )
    args = _args()
    ok, detail = validate._validate_file(
        get_endf_parser(args), str(path), validate.get_fast_parser(args)
    )
    assert not ok
    assert "of MAT 2000 follows section MF=1/MT=452" in detail


def test_tape_of_one_mat_number_with_ignore_send_records(tmp_path):
    """With ignore_send_records, the MEND records do not delimit the
    materials, as in the parsers, which merge the sections of a tape: two
    materials with the same MAT number are one material, whose sections
    are then not in ascending order."""
    path = _write(tmp_path / "tape.endf", _tape([PU, PU]))
    assert check_framing(path) == []
    problems = check_framing(path, ignore_send_records=True)
    assert [p.message for p in problems] == [
        f"section MF={mf}/MT={mt} of MAT 3564 occurs a second time in the material"
        for mf, mt in ((1, 451), (1, 452), (8, 457))
    ]
    for cls in (EndfParserCpp, EndfParserPy):
        with pytest.raises(Exception, match="ascending order"):
            _parser(cls, "ignore_send_records").parsefile(str(path))
