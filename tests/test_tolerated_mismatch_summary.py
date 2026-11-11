############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/11
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The summary of the tolerated mismatches of a parse.

With ``ignore_zero_mismatch``, ``ignore_number_mismatch`` and
``ignore_varspec_mismatch``, both parsers accept certain field values that
differ from the recipe. Each call of ``parse`` or ``parsefile`` reports
them in one ``EndfToleratedMismatchWarning``, whose text and mismatches
(MAT/MF/MT, field, variable, kind, line of the input, expected and found
value) must be the same for EndfParserPy and EndfParserCpp. A mismatch
found in a lookahead is not reported; only the final parse of the record
counts. ``EndfFile`` and the tape functions report the lines of the
file, and ``endf-cli validate`` lists the mismatches tolerated with
relaxed options in its report.

The tapes are synthetic. The values of the bodies of LIST records are
also checked in the bulk form of EndfParserCpp (strided delivery and the
code of the per-field form) and in the per-field form, in subprocesses
(see test_cpp_list_bulk_form.py).
"""

import json
import logging
import os
import pickle
import subprocess
import sys
import warnings

import pytest

from endf_parserpy import (
    EndfFile,
    EndfParserCpp,
    EndfParserPy,
    EndfToleratedMismatchWarning,
    parse_tape_file,
)
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError
from endf_parserpy.utils.tolerated_mismatches import (
    MAX_GROUPS,
    ToleratedMismatch,
    format_tolerated_mismatches,
)


PARSER_CLASSES = [EndfParserPy, EndfParserCpp]
STRICT = {
    "ignore_zero_mismatch": False,
    "ignore_number_mismatch": False,
    "ignore_varspec_mismatch": False,
}


def _field(value):
    if isinstance(value, int):
        return f"{value:11d}"
    if value == 0:
        return " 0.000000+0"
    mantissa, exponent = f"{value:.6e}".split("e")
    exponent = int(exponent)
    sign = "+" if exponent >= 0 else "-"
    return f"{mantissa}{sign}{abs(exponent)}".rjust(11)


def _line(fields, mat, mf, mt):
    text = "".join(_field(v) for v in fields).ljust(66)
    return f"{text}{mat:4d}{mf:2d}{mt:3d}"


ZEROS = [0.0, 0.0, 0, 0, 0, 0]
TPID = " synthetic tape".ljust(66) + "   1 0  0"


def _material(mat, sections):
    """The lines of a material: sections is a list of (MF, MT, records)."""
    lines = []
    prev_mf = None
    for mf, mt, records in sections:
        if prev_mf is not None and mf != prev_mf:
            lines.append(_line(ZEROS, mat, 0, 0))  # FEND
        prev_mf = mf
        lines += [_line(rec, mat, mf, mt) for rec in records]
        lines.append(_line(ZEROS, mat, mf, 0))  # SEND
    lines.append(_line(ZEROS, mat, 0, 0))  # FEND
    lines.append(_line(ZEROS, 0, 0, 0))  # MEND
    return lines


def _tape(*materials):
    lines = [TPID]
    for mat, sections in materials:
        lines += _material(mat, sections)
    lines.append(_line(ZEROS, -1, 0, 0))  # TEND
    return "\n".join(lines) + "\n"


def _mf3(l2=0, n1=0, tab1_l1=0):
    # [MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0]HEAD and
    # [MAT, 3, MT/ QM, QI, 0, LR, NR, NP/ E / xs]TAB1
    return [
        [1001.0, 0.9992, 0, l2, n1, 0],
        [0.0, 0.0, tab1_l1, 0, 1, 2],
        [2, 2],
        [1.0e-5, 1.0, 2.0e7, 2.0],
    ]


def _mf4(awr_cont=0.9992, head_n1=0):
    # MF4/MT2 of the endf6-ext flavor with LTT=0 and LI=1: the HEAD record
    # is read in a lookahead (if LVT > 0) and then in the else branch, the
    # CONT record in the lookahead of LTT==3 and then in the else branch
    # [MAT, 4, MT/ 0.0, AWR?, LI, LCT?, 0, 0]CONT
    return [[1001.0, 0.9992, 0, 0, head_n1, 0], [0.0, awr_cont, 1, 1, 0, 0]]


# MAT 125: MF3/MT1 (HEAD L2, N1 and TAB1 L1), MF3/MT2 (HEAD L2), MF4/MT2
# (HEAD N1 and AWR? in the CONT record, both also read in a lookahead)
TAPE = _tape(
    (
        125,
        [
            (3, 1, _mf3(l2=99, n1=1, tab1_l1=3)),
            (3, 2, _mf3(l2=2)),
            (4, 2, _mf4(awr_cont=0.9991, head_n1=5)),
        ],
    )
)

EXPECTED = [
    ToleratedMismatch(125, 3, 1, "L2", None, "zero", 2, 0, 99),
    ToleratedMismatch(125, 3, 1, "N1", None, "zero", 2, 0, 1),
    ToleratedMismatch(125, 3, 1, "L1", None, "zero", 3, 0, 3),
    ToleratedMismatch(125, 3, 2, "L2", None, "zero", 7, 0, 2),
    ToleratedMismatch(125, 4, 2, "N1", None, "zero", 13, 0, 5),
    ToleratedMismatch(125, 4, 2, "C2", "AWR", "varspec", 14, 0.9992, 0.9991),
]

CLEAN_TAPE = _tape((125, [(3, 1, _mf3()), (4, 2, _mf4())]))


def _tolerated(func, *args, **kwargs):
    """Call func and return its result and the tolerated-mismatch
    warnings it issued."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = func(*args, **kwargs)
    found = [
        w.message
        for w in caught
        if issubclass(w.category, EndfToleratedMismatchWarning)
    ]
    return result, found


def _single(found):
    assert len(found) == 1
    return found[0]


def _check_line_contents(text, mismatches):
    # the line of a mismatch of a header field holds the value found
    lines = text.split("\n")
    for m in mismatches:
        line = lines[m.line - 1]
        assert int(line[66:70]) == m.mat and int(line[70:72]) == m.mf
        assert int(line[72:75]) == m.mt
        if m.field != "body":
            col = ("C1", "C2", "L1", "L2", "N1", "N2").index(m.field)
            assert line[11 * col : 11 * col + 11] == _field(m.found)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_one_summary_per_parse(ParserCls):
    _, found = _tolerated(ParserCls().parse, TAPE)
    w = _single(found)
    assert list(w.mismatches) == EXPECTED
    assert w.source is None
    assert str(w) == format_tolerated_mismatches(EXPECTED)
    _check_line_contents(TAPE, w.mismatches)


def test_summary_text():
    text = format_tolerated_mismatches(EXPECTED, source="tape.endf")
    assert text.split("\n") == [
        "6 field mismatches tolerated in tape.endf (zero: 5 "
        "(ignore_zero_mismatch), varspec: 1 (ignore_varspec_mismatch)), "
        "in 6 groups; the values found are not kept, writing the data gives "
        "the expected values:",
        "  MAT 125 MF3/MT1 L2: 1 zero mismatch, e.g. line 2: expected 0, found 99",
        "  MAT 125 MF3/MT1 N1: 1 zero mismatch, e.g. line 2: expected 0, found 1",
        "  MAT 125 MF3/MT1 L1: 1 zero mismatch, e.g. line 3: expected 0, found 3",
        "  MAT 125 MF3/MT2 L2: 1 zero mismatch, e.g. line 7: expected 0, found 2",
        "  MAT 125 MF4/MT2 N1: 1 zero mismatch, e.g. line 13: expected 0, found 5",
        "  MAT 125 MF4/MT2 C2 (AWR): 1 varspec mismatch, e.g. line 14: "
        "expected 0.9992, found 0.9991",
    ]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_parsefile_names_file(ParserCls, tmp_path):
    path = tmp_path / "tape.endf"
    path.write_text(TAPE)
    _, found = _tolerated(ParserCls().parsefile, path)
    w = _single(found)
    assert list(w.mismatches) == EXPECTED
    assert w.source == str(path)
    assert str(w) == format_tolerated_mismatches(EXPECTED, source=str(path))


def test_parsefile_cpp_without_loading_into_memory(tmp_path):
    path = tmp_path / "tape.endf"
    path.write_text(TAPE)
    parser = EndfParserCpp(load_file_into_memory=False)
    _, found = _tolerated(parser.parsefile, path)
    assert list(_single(found).mismatches) == EXPECTED


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_parse_list_of_lines(ParserCls):
    _, found = _tolerated(ParserCls().parse, TAPE.split("\n"))
    assert list(_single(found).mismatches) == EXPECTED


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_crlf_line_endings(ParserCls):
    _, found = _tolerated(ParserCls().parse, TAPE.replace("\n", "\r\n"))
    assert list(_single(found).mismatches) == EXPECTED


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_blank_lines_are_counted(ParserCls):
    # a blank line before MF3/MT2 (skipped with ignore_blank_lines) moves
    # the following lines
    lines = TAPE.split("\n")
    lines.insert(6, "")
    _, found = _tolerated(ParserCls(ignore_blank_lines=True).parse, "\n".join(lines))
    shifted = [m._replace(line=m.line + (m.line > 6)) for m in EXPECTED]
    assert list(_single(found).mismatches) == shifted


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_clean_tape_gives_no_warning(ParserCls):
    _, found = _tolerated(ParserCls().parse, CLEAN_TAPE)
    assert found == []


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_array_types(ParserCls, atype):
    _, found = _tolerated(ParserCls(array_type=atype).parse, TAPE)
    assert list(_single(found).mismatches) == EXPECTED


@pytest.mark.parametrize(
    "kwargs, sections",
    [
        ({"include": (4,)}, {(4, 2)}),
        ({"include": ((3, 2),)}, {(3, 2)}),
        ({"exclude": (3,)}, {(4, 2)}),
        ({"exclude": ((3, 1),)}, {(3, 2), (4, 2)}),
    ],
)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_include_and_exclude(ParserCls, kwargs, sections):
    _, found = _tolerated(ParserCls().parse, TAPE, **kwargs)
    expected = [m for m in EXPECTED if (m.mf, m.mt) in sections]
    assert list(_single(found).mismatches) == expected


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_excluded_mismatches_give_no_warning(ParserCls):
    _, found = _tolerated(ParserCls().parse, TAPE, include=((1, 451),))
    assert found == []


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_lookahead_mismatch_reported_once(ParserCls):
    # both records of MF4/MT2 are read in a lookahead first; with LVT=0
    # and LTT=0, the else branches read them again
    tape = _tape((125, [(4, 2, _mf4(awr_cont=0.9991, head_n1=5))]))
    _, found = _tolerated(ParserCls().parse, tape)
    assert list(_single(found).mismatches) == [
        m._replace(line=m.line - 11) for m in EXPECTED if m.mf == 4
    ]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_lookahead_record_of_other_branch(ParserCls):
    # MF2/MT9 of the test flavor: the CONT record is read in the lookahead
    # of L==1 with NP in N2; for L=2, the else branch has 0 in N2
    tape = "\n".join(
        [
            _line(ZEROS, 1, 2, 9),
            _line([1.5, 0.0, 2, 0, 3, 7], 1, 2, 9),
        ]
        + [_line(ZEROS, 1, 2, 0), _line(ZEROS, 1, 0, 0)]
        + [_line(ZEROS, 0, 0, 0), _line(ZEROS, -1, 0, 0)]
    )
    parser = ParserCls(endf_format="test", ignore_missing_tpid=True)
    _, found = _tolerated(parser.parse, tape)
    assert list(_single(found).mismatches) == [
        ToleratedMismatch(1, 2, 9, "C1", None, "zero", 2, 0.0, 1.5),
        ToleratedMismatch(1, 2, 9, "N2", None, "zero", 2, 0, 7),
    ]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_number_mismatch(ParserCls):
    # [MAT, 3, MT/ ZA, 0.0?, 0, 0, NG, 0 / SIG]LIST of the errorr flavor:
    # 0.0? is a zero and a desired number
    tape = _tape((125, [(3, 1, [[1001.0, 2.0, 0, 0, 2, 0], [1.5, 2.5]])]))
    parser = ParserCls(
        endf_format="errorr", ignore_zero_mismatch=False, ignore_number_mismatch=True
    )
    _, found = _tolerated(parser.parse, tape)
    assert list(_single(found).mismatches) == [
        ToleratedMismatch(125, 3, 1, "C2", None, "number", 2, 0.0, 2.0)
    ]
    # with ignore_zero_mismatch, it is a zero mismatch
    _, found = _tolerated(ParserCls(endf_format="errorr").parse, tape)
    assert [m.kind for m in _single(found).mismatches] == ["zero"]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_strict_options_raise(ParserCls):
    exc_type = NumberMismatchError if ParserCls is EndfParserPy else RuntimeError
    with warnings.catch_warnings():
        warnings.simplefilter("error", EndfToleratedMismatchWarning)
        with pytest.raises(exc_type):
            ParserCls(**STRICT).parse(TAPE)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_failed_parse_gives_no_warning(ParserCls):
    # MF3/MT2 is damaged after the tolerated mismatches of MF3/MT1
    lines = TAPE.split("\n")
    lines[7] = lines[7][:22] + "        abc" + lines[7][33:]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(Exception):
            ParserCls().parse("\n".join(lines))
    assert not [w for w in caught if w.category is EndfToleratedMismatchWarning]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_category_can_be_turned_into_error(ParserCls):
    with warnings.catch_warnings():
        warnings.simplefilter("error", EndfToleratedMismatchWarning)
        with pytest.raises(EndfToleratedMismatchWarning) as excinfo:
            ParserCls().parse(TAPE)
    assert list(excinfo.value.mismatches) == EXPECTED
    with warnings.catch_warnings():
        # (a filter added later takes precedence)
        warnings.simplefilter("error")
        warnings.simplefilter("ignore", EndfToleratedMismatchWarning)
        ParserCls().parse(TAPE)


def test_warning_is_attributed_to_caller():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        EndfParserCpp().parse(TAPE)
    assert [w.filename for w in caught] == [__file__]


def test_warning_pickles():
    w = EndfToleratedMismatchWarning("text", EXPECTED, "tape.endf")
    w2 = pickle.loads(pickle.dumps(w))
    assert str(w2) == "text"
    assert w2.mismatches == tuple(EXPECTED) and w2.source == "tape.endf"


def test_long_summary_is_truncated():
    sections = [(3, mt, _mf3(l2=mt)) for mt in range(1, MAX_GROUPS + 4)]
    tape = _tape((125, sections))
    texts = []
    for ParserCls in PARSER_CLASSES:
        _, found = _tolerated(ParserCls().parse, tape)
        texts.append(str(_single(found)))
    assert texts[0] == texts[1]
    lines = texts[0].split("\n")
    assert len(lines) == 1 + MAX_GROUPS + 1
    assert lines[-1] == "  ... and 3 more groups"
    assert lines[0].startswith("13 field mismatches tolerated (zero: 13")


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_groups_count_repeated_mismatches(ParserCls):
    # MF10/MT4 of the test flavor: NI LIST records with 0 in L1 and a
    # value 0.0 checked at the end of each body
    nk = 7
    records = [[0.0, 0.0, 3, nk, 0, 0]]
    for i in range(1, 4):
        records.append([0.0, 0.0, i, 0, nk + 1, 0])
        values = [1000.0 * i + k for k in range(1, nk + 1)] + [0.5 * i]
        records += [values[j : j + 6] for j in range(0, len(values), 6)]
    lines = [_line(rec, 1, 10, 4) for rec in records]
    tape = "\n".join(
        lines
        + [_line(ZEROS, 1, 10, 0), _line(ZEROS, 1, 0, 0)]
        + [_line(ZEROS, 0, 0, 0), _line(ZEROS, -1, 0, 0)]
    )
    parser = ParserCls(endf_format="test", ignore_missing_tpid=True)
    _, found = _tolerated(parser.parse, tape)
    w = _single(found)
    # the LIST records of i = 1, 2, 3 start at lines 2, 5 and 8
    expected = []
    for i, head in ((1, 2), (2, 5), (3, 8)):
        expected.append(ToleratedMismatch(1, 10, 4, "L1", None, "zero", head, 0, i))
        expected.append(
            ToleratedMismatch(1, 10, 4, "body", None, "zero", head + 2, 0.0, 0.5 * i)
        )
    assert list(w.mismatches) == expected
    assert "MAT 1 MF10/MT4 L1: 3 zero mismatches, e.g. line 2: " in str(w)
    assert "MAT 1 MF10/MT4 body: 3 zero mismatches, e.g. line 4: " in str(w)


# the Python parser logs the details at DEBUG only


def _logger_records(caplog, level):
    return [
        r
        for r in caplog.records
        if r.name.startswith("EndfParserPyInstance") and r.levelno == level
    ]


def test_python_parser_logs_details_at_debug_only(caplog):
    caplog.set_level(logging.WARNING)
    _tolerated(EndfParserPy().parse, TAPE)
    assert _logger_records(caplog, logging.WARNING) == []
    caplog.clear()
    parser = EndfParserPy(loglevel=logging.DEBUG)
    caplog.set_level(logging.DEBUG)
    _tolerated(parser.parse, TAPE)
    messages = [r.getMessage() for r in _logger_records(caplog, logging.DEBUG)]
    assert sum("in the ENDF file but got" in m for m in messages) == 6
    assert sum("This is not the case for AWR" in m for m in messages) == 1
    assert sum(m.startswith("Offending line: ") for m in messages) == 6


# EndfFile and the tape functions report the lines of the file


def _multi_material_tape():
    return _tape(
        (125, [(3, 1, _mf3(l2=99)), (4, 2, _mf4(awr_cont=0.9991))]),
        (126, [(3, 1, _mf3(n1=4)), (3, 2, _mf3(tab1_l1=2))]),
    )


MULTI_EXPECTED = [
    ToleratedMismatch(125, 3, 1, "L2", None, "zero", 2, 0, 99),
    ToleratedMismatch(125, 4, 2, "C2", "AWR", "varspec", 9, 0.9992, 0.9991),
    ToleratedMismatch(126, 3, 1, "N1", None, "zero", 13, 0, 4),
    ToleratedMismatch(126, 3, 2, "L1", None, "zero", 19, 0, 2),
]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_endf_file_reports_file_lines(ParserCls, tmp_path):
    path = tmp_path / "tape.endf"
    text = _multi_material_tape()
    path.write_text(text)
    endf_file = EndfFile(path, parser=ParserCls())
    found = []
    for material in endf_file:
        for key in material.sections():
            _, ws = _tolerated(material.__getitem__, key)
            found += ws
    # one warning per section with mismatches, for the file
    assert [w.source for w in found] == [str(path)] * 4
    mismatches = [m for w in found for m in w.mismatches]
    assert mismatches == MULTI_EXPECTED
    _check_line_contents(text, mismatches)
    # a section is parsed once (cached)
    _, again = _tolerated(endf_file[0].__getitem__, (3, 1))
    assert again == []


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_parse_tape_file_reports_file_lines(ParserCls, tmp_path):
    path = tmp_path / "tape.endf"
    text = _multi_material_tape()
    # a blank line between the materials is not part of the materials
    lines = text.split("\n")
    lines.insert(12, "")
    text = "\n".join(lines)
    path.write_text(text)
    _, found = _tolerated(parse_tape_file, path, parser=ParserCls())
    assert [w.source for w in found] == [str(path)] * 2
    mismatches = [m for w in found for m in w.mismatches]
    assert mismatches == [
        m._replace(line=m.line + (m.mat == 126)) for m in MULTI_EXPECTED
    ]
    _check_line_contents(text, mismatches)


# the values of the bodies of LIST records in the forms of EndfParserCpp

BULK_WORKER = r"""
import json, sys, warnings
from endf_parserpy import EndfParserCpp
import importlib
tape = open(sys.argv[1]).read()
out = []
for array_type in ("dict", "list", "numpy"):
    parser = EndfParserCpp(
        endf_format="test", ignore_missing_tpid=True, array_type=array_type
    )
    module = importlib.import_module(parser._parse_endf.__module__)
    _, mismatches = parser._parse_and_collect(tape)
    out.append(
        {
            "mismatches": [list(m) for m in mismatches],
            "counts": module._bulk_body_info()["bulk_list_bodies"],
        }
    )
print(json.dumps(out))
"""


def _body_tape():
    # MF10/MT1: A, B, {X[k], 0.0, {Y[k,m]}{m=1 to M}}{k=1 to N} (strided
    # delivery); MF10/MT8: {{F[k,l]}{l=k to N}, 0.0}{k=1 to N} (one copy
    # per row)
    n, m = 3, 4
    values = [1.5, -2.25]
    for k in range(1, n + 1):
        values += [k + 0.125, 0.25 * k if k != 2 else 0.0]
        values += [100.0 * k + mm + 0.5 for mm in range(1, m + 1)]
    mt1 = [[0.0, 0.0, n, m, len(values), 0]]
    mt1 += [values[i : i + 6] for i in range(0, len(values), 6)]
    rows = []
    for k in range(1, n + 1):
        rows += [10.0 * k + l for l in range(k, n + 1)] + [7.5 if k == 2 else 0.0]
    mt8 = [[0.0, 0.0, n, 0, len(rows), 0]]
    mt8 += [rows[i : i + 6] for i in range(0, len(rows), 6)]
    lines = []
    for mt, records in ((1, mt1), (8, mt8)):
        lines += [_line(rec, 1, 10, mt) for rec in records]
        lines.append(_line(ZEROS, 1, 10, 0))
    lines += [_line(ZEROS, 1, 0, 0), _line(ZEROS, 0, 0, 0), _line(ZEROS, -1, 0, 0)]
    return "\n".join(lines) + "\n"


BODY_EXPECTED = [
    ToleratedMismatch(1, 10, 1, "body", None, "zero", 2, 0.0, 0.25),
    ToleratedMismatch(1, 10, 1, "body", None, "zero", 4, 0.0, 0.75),
    ToleratedMismatch(1, 10, 8, "body", None, "zero", 9, 0.0, 7.5),
]


def test_list_body_python_parser():
    parser = EndfParserPy(endf_format="test", ignore_missing_tpid=True)
    _, found = _tolerated(parser.parse, _body_tape())
    assert list(_single(found).mismatches) == BODY_EXPECTED
    _check_line_contents(_body_tape(), BODY_EXPECTED)


@pytest.mark.parametrize("bulk", [None, "off", "scalar"])
def test_list_body_cpp_forms(bulk, tmp_path):
    path = tmp_path / "bodies.endf"
    path.write_text(_body_tape())
    env = dict(os.environ)
    env.pop("ENDF_PARSERPY_CPP_BULK_BODIES", None)
    if bulk is not None:
        env["ENDF_PARSERPY_CPP_BULK_BODIES"] = bulk
    res = subprocess.run(
        [sys.executable, "-c", BULK_WORKER, str(path)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    results = json.loads(res.stdout.splitlines()[-1])
    for result in results:
        assert [ToleratedMismatch(*m) for m in result["mismatches"]] == BODY_EXPECTED
    counts = results[-1]["counts"]
    if bulk == "off":
        assert counts["strided"] == 0 and counts["looped"] == 0
    else:
        # strided copies (MT1) and one copy per row (MT8)
        assert counts["strided"] > 0 and counts["row_bodies"] > 0


# endf-cli


def _cli(*argv, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


@pytest.fixture
def tape_file(tmp_path):
    path = tmp_path / "tape.endf"
    path.write_text(TAPE)
    return path


@pytest.mark.parametrize("extra", [[], ["--no-cpp"]], ids=["cpp", "py"])
def test_cli_validate_strict_fails(tape_file, extra):
    res = _cli("validate", *extra, str(tape_file))
    assert res.returncode == 1
    assert f"failed - {tape_file}" in res.stdout
    assert "tolerated" not in res.stdout
    assert "EndfToleratedMismatchWarning" not in res.stderr


@pytest.mark.parametrize("extra", [[], ["--no-cpp"]], ids=["cpp", "py"])
def test_cli_validate_reports_tolerated(tape_file, extra):
    res = _cli(
        "validate",
        *extra,
        "--ignore_zero_mismatch",
        "--ignore_varspec_mismatch",
        str(tape_file),
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Warning" not in res.stderr
    report = format_tolerated_mismatches(EXPECTED)
    assert f"  Validation of {tape_file} passed with mismatches tolerated" in res.stdout
    # each mismatch is counted once
    assert report in res.stdout
    assert res.stdout.count("MAT 125") == len(EXPECTED)
    assert f"ok (6 tolerated mismatches) - {tape_file}" in res.stdout


@pytest.mark.parametrize("extra", [[], ["--no-cpp"]], ids=["cpp", "py"])
def test_cli_validate_only_zero_tolerated(tape_file, extra):
    # the varspec mismatch of MF4 is not tolerated: the file fails
    res = _cli("validate", *extra, "--ignore_zero_mismatch", str(tape_file))
    assert res.returncode == 1
    assert "MF=4/MT=2" in res.stdout
    assert "tolerated" not in res.stdout


def test_cli_validate_fast_path_fallback(tmp_path):
    # MF3/MT2 fails in the parse of MF3 in one call (fast path), so the
    # sections of MF3 are parsed one by one; MF3/MT1 is counted once
    text = _tape(
        (
            125,
            [
                (3, 1, _mf3(l2=99)),
                (3, 2, [[1001.0, 0.9992, 0, 0, 0, 0], [0.0, 0.0, 0, 0, 1, 2]]),
            ],
        )
    )
    path = tmp_path / "tape.endf"
    path.write_text(text)
    res = _cli("validate", "--ignore_zero_mismatch", str(path))
    assert res.returncode == 1
    assert "MF=3/MT=2" in res.stdout


def test_cli_validate_counts_once_per_section(tmp_path):
    # several files: the counts and groups of each file
    paths = []
    for i, text in enumerate((TAPE, CLEAN_TAPE)):
        path = tmp_path / f"tape{i}.endf"
        path.write_text(text)
        paths.append(str(path))
    res = _cli(
        "validate", "--ignore_zero_mismatch", "--ignore_varspec_mismatch", *paths
    )
    assert res.returncode == 0
    assert res.stdout.count("passed with mismatches tolerated") == 1
    assert f"ok - {paths[1]}" in res.stdout
    assert res.stdout.count("MAT 125") == len(EXPECTED)


@pytest.mark.parametrize("extra", [[], ["--no-cpp"]], ids=["cpp", "py"])
def test_cli_show_reports_once_per_file(tape_file, extra):
    res = _cli("show", *extra, "3/1/AWR", str(tape_file))
    assert res.returncode == 0, res.stderr
    assert res.stderr.count("endf-cli: warning:") == 1
    mf3 = [m for m in EXPECTED if (m.mf, m.mt) == (3, 1)]
    assert format_tolerated_mismatches(mf3, str(tape_file)) in res.stderr
