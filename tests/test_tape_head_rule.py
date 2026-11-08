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

"""Which first line is a tape head (TPID), the same in both parsers.

The first non-blank line is the tape head if its MF and MT numbers are 0
(blank reads as 0) and its MAT number (the tape number) is not negative.
The tape number and the text of the line are not checked otherwise. A
first line with MAT=-1, MF=0 and MT=0 is a TEND record, not a tape head:
an error by default (missing tape head), and with ``ignore_missing_tpid``
handled as any other first line that is not a tape head, i.e. as a TEND
record. The tape index (``TapeIndex``) applies the same rule. A
non-numeric MAT number of the tape head is an error, as in any other
line.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.tape import TapeIndex
from endf_parserpy.utils.debugging_utils import compare_objects


TESTDATA = Path(__file__).parent / "testdata"
TESTFILE = TESTDATA / "dec-094_Pu_244.endf"
LINES = TESTFILE.read_text().splitlines()

TEXT = "Pu-244 decay data".ljust(66)
TEND = " " * 66 + "  -1 0  0"

VARIANTS = {
    # tape heads: any MAT number that is not negative, MF and MT 0 or blank
    "regular": [LINES[0]] + LINES[1:],
    "mat_blank": [TEXT + "         "] + LINES[1:],
    "mat_0": [TEXT + "   0 0  0"] + LINES[1:],
    "mat_7777": [TEXT + "7777 0  0"] + LINES[1:],
    "mfmt_blank": [TEXT + "  30     "] + LINES[1:],
    # not tape heads
    "mat_negative_text": [TEXT + "  -1 0  0"] + LINES[1:],
    "mat_negative_2": [TEXT + "  -2 0  0"] + LINES[1:],
    "tend_first": [TEND] + LINES[1:],
    "tend_only": [TEND],
    "tend_then_blank": [TEND, ""],
    "no_tpid": LINES[1:],
}
IS_TAPE_HEAD = {"regular", "mat_blank", "mat_0", "mat_7777", "mfmt_blank"}

OPTIONS = {
    "default": {},
    "ignore_tpid": {"ignore_missing_tpid": True},
    "ignore_tpid_send": {
        "ignore_missing_tpid": True,
        "ignore_send_records": True,
        "ignore_blank_lines": True,
    },
    "ignore_send": {"ignore_send_records": True, "ignore_blank_lines": True},
}

FILTERS = {
    "full": {},
    "include": {"include": [8]},
    "exclude": {"exclude": [(1, 451)]},
}


def _text(lines):
    return "\n".join(lines) + "\n"


def _outcome(parser, text, kwargs):
    try:
        return "ok", parser.parse(text, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return "error", exc


# A first line with MF=0, MT=0 and a negative MAT number but text in its
# fields: with ignore_send_records, EndfParserPy does not look at end
# records, while EndfParserCpp reads the fields of a line with MF=0 and
# MT=0 as numbers to determine whether it is an end record, as for any
# line with these numbers.
_CPP_READS_TEND_FIELDS = {
    ("mat_negative_text", "ignore_tpid_send"),
    ("mat_negative_2", "ignore_tpid_send"),
}


@pytest.mark.parametrize("filt", sorted(FILTERS))
@pytest.mark.parametrize("opts", sorted(OPTIONS))
@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_both_parsers_agree(variant, opts, filt):
    if (variant, opts) in _CPP_READS_TEND_FIELDS:
        pytest.skip("EndfParserPy does not read end records here")
    text = _text(VARIANTS[variant])
    kwargs = FILTERS[filt]
    res_cpp = _outcome(EndfParserCpp(**OPTIONS[opts]), text, kwargs)
    res_py = _outcome(EndfParserPy(**OPTIONS[opts]), text, kwargs)
    assert res_cpp[0] == res_py[0], (res_cpp, res_py)
    if res_cpp[0] == "ok":
        assert compare_objects(res_cpp[1], res_py[1], fail_on_diff=False)
        has_head = 0 in res_cpp[1]
        assert has_head == (variant in IS_TAPE_HEAD)


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_tape_head_required_by_default(variant):
    text = _text(VARIANTS[variant])
    for parser in (EndfParserCpp(), EndfParserPy()):
        if variant in IS_TAPE_HEAD:
            assert 0 in parser.parse(text)
        else:
            with pytest.raises(Exception, match="(TPID)"):
                parser.parse(text)


@pytest.mark.parametrize("variant", ["tend_only", "tend_then_blank"])
def test_tend_as_first_line_with_ignore_missing_tpid(variant):
    # the TEND record ends the (empty) tape
    text = _text(VARIANTS[variant])
    for parser in (
        EndfParserCpp(ignore_missing_tpid=True),
        EndfParserPy(ignore_missing_tpid=True),
    ):
        assert parser.parse(text) == {}


def test_section_after_tend_as_first_line():
    text = _text(VARIANTS["tend_first"])
    with pytest.raises(RuntimeError, match="after MEND/TEND record"):
        EndfParserCpp(ignore_missing_tpid=True).parse(text)
    with pytest.raises(Exception, match="Tape End \\(TEND\\) record"):
        EndfParserPy(ignore_missing_tpid=True).parse(text)


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_tape_index_same_rule(variant):
    lines = VARIANTS[variant]
    if len(lines) < 3:
        pytest.skip("no material")
    if variant in IS_TAPE_HEAD:
        index = TapeIndex.from_lines(lines)
        assert index.tpid_line is not None
    else:
        with pytest.raises(Exception, match="tape head"):
            TapeIndex.from_lines(lines)


@pytest.mark.parametrize("filt", sorted(FILTERS))
@pytest.mark.parametrize("opts", ["default", "ignore_tpid"])
@pytest.mark.parametrize("mat", ["ab  ", "1x  ", " 1 1", "-   "])
def test_non_numeric_tape_number_rejected(mat, opts, filt):
    # parsed with the recipe of MF0/MT0 (full, exclude) and read verbatim
    # (include)
    text = _text([TEXT + mat + " 0  0"] + LINES[1:])
    kwargs = FILTERS[filt]
    with pytest.raises(RuntimeError, match=f'invalid MAT number field: "{mat}"'):
        EndfParserCpp(**OPTIONS[opts]).parse(text, **kwargs)
    with pytest.raises(ValueError):
        EndfParserPy(**OPTIONS[opts]).parse(text, **kwargs)
