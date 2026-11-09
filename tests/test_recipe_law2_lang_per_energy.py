############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/09
# Last modified:   2026/11/09
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""LANG of the LIST records of MF6 and MF26 LAW=2, one per incident energy.

In LAW=2 (discrete two-body scattering, ENDF-6 manual, section 6.2.4), each
incident energy has its own LIST record, and its L1 field is LANG for that
energy: Legendre coefficients (LANG=0) at one energy may be followed by a
tabulated angular distribution (LANG=11-15) at a higher one, as in MF6
MT50-55 of p-004_Be_009 of the ENDF/B-VIII.1 proton sublibrary (LANG=0 up to
75 MeV, then LANG=12). The recipes declared a single LANG for the whole
subsection, so that EndfParserCpp rejected a later LIST record with another
LANG (``Invalid LANG encountered!``), and EndfParserPy kept the first value
(with a warning if it was 0, otherwise it raised a NumberMismatchError) and
wrote the later records back with it. LANG is now an array indexed like
NLW and NL, ``LANG[j]``, and the check 11 <= LANG <= 15 of MF26 applies to
the LANG of each energy.

The data are minimal tapes, with a tape head and the framing records, with
an MF6 section (LANG 0, 0 and 12) and an MF26 section (LANG 12 and 14), and
an MF6 section with a LAW=1 subsection (one LANG, in the TAB2 record) and
a LAW=2 subsection, in both orders.
"""

import numpy as np
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import StopException
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserPy, EndfParserCpp]
ARRAY_TYPES = ["dict", "list", "numpy"]
# the flavors with the MF6 and MF26 recipes (endf6-ext and jendl inherit
# those of endf6, pendf has its own MF6 recipe)
ENDF_FORMATS = ["endf6-ext", "endf6", "jendl", "pendf"]


# MF6/MT2 with one LAW=2 subsection and three incident energies: Legendre
# coefficients (LANG=0) at 1 and 50 MeV, a tabulated distribution of mu
# and p (LANG=12) at 100 MeV
MF6_TAPE = (
    " synthetic tape                                                      1 0  0    0\n"
    " 4.009000+3 8.934780+0          0          2          1          0 425 6  2    1\n"
    " 1.001000+3 9.986235-1          0          2          1          2 425 6  2    2\n"
    "          2          2                                             425 6  2    3\n"
    " 1.000000+6 1.000000+0 1.000000+8 1.000000+0                       425 6  2    4\n"
    " 0.000000+0 0.000000+0          0          0          1          3 425 6  2    5\n"
    "          3          2                                             425 6  2    6\n"
    " 0.000000+0 1.000000+6          0          0          2          2 425 6  2    7\n"
    " 1.000000-1-5.000000-2                                             425 6  2    8\n"
    " 0.000000+0 5.000000+7          0          0          3          3 425 6  2    9\n"
    " 2.000000-1 5.000000-2 1.000000-2                                  425 6  2   10\n"
    " 0.000000+0 1.000000+8         12          0          6          3 425 6  2   11\n"
    "-1.000000+0 2.500000-1 0.000000+0 5.000000-1 1.000000+0 7.500000-1 425 6  2   12\n"
    " 0.000000+0 0.000000+0          0          0          0          0 425 6  099999\n"
    " 0.000000+0 0.000000+0          0          0          0          0 425 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0   0 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0  -1 0  0    0\n"
)
MF6_E = [1.0e6, 5.0e7, 1.0e8]
MF6_LANG = [0, 0, 12]
MF6_NL = [2, 3, 3]
MF6_A = [
    [0.1, -0.05],
    [0.2, 0.05, 0.01],
    [-1.0, 0.25, 0.0, 0.5, 1.0, 0.75],
]

# MF26/MT525 with one LAW=2 subsection and two incident energies, tabulated
# distributions with LANG=12 and LANG=14
MF26_TAPE = (
    " synthetic tape                                                      1 0  0    0\n"
    " 1.000000+3 9.992414-1          0          0          1          0 10026525    1\n"
    " 1.100000+1 5.438673-4          0          2          1          2 10026525    2\n"
    "          2          2                                             10026525    3\n"
    " 1.000000+1 1.000000+0 1.00000+11 1.000000+0                       10026525    4\n"
    " 0.000000+0 0.000000+0          0          0          1          2 10026525    5\n"
    "          2          2                                             10026525    6\n"
    " 0.000000+0 1.000000+1         12          0          4          2 10026525    7\n"
    "-1.000000+0 1.000000-3 1.000000+0 9.990000-1                       10026525    8\n"
    " 0.000000+0 1.00000+11         14          0          6          3 10026525    9\n"
    "-1.000000+0 0.000000+0 9.000000-1 1.000000-1 1.000000+0 1.000000+8 10026525   10\n"
    " 0.000000+0 0.000000+0          0          0          0          0 10026  099999\n"
    " 0.000000+0 0.000000+0          0          0          0          0 100 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0   0 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0  -1 0  0    0\n"
)
MF26_E = [10.0, 1.0e11]
MF26_LANG = [12, 14]
MF26_NL = [2, 3]
MF26_A = [
    [-1.0, 1.0e-3, 1.0, 0.999],
    [-1.0, 0.0, 0.9, 0.1, 1.0, 1.0e8],
]

CASES = {
    "mf6": (MF6_TAPE, 6, 2, MF6_E, MF6_LANG, MF6_NL, MF6_A),
    "mf26": (MF26_TAPE, 26, 525, MF26_E, MF26_LANG, MF26_NL, MF26_A),
}

STOP_MESSAGE = "Only 11 <= LANG <= 15 is permitted in MF26/LAW2"


def _seq(obj):
    # the elements of a per-energy array, in the order of the energies,
    # for all three array types (dict indexed from 1, list, numpy array)
    if isinstance(obj, dict):
        assert sorted(obj) == list(range(1, len(obj) + 1))
        return [obj[k] for k in sorted(obj)]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return list(obj)


def _first_subsection(sec):
    subs = sec["subsection"]
    return subs[1] if isinstance(subs, dict) else subs[0]


def _text(written):
    if isinstance(written, str):
        return written
    return "".join(line if line.endswith("\n") else line + "\n" for line in written)


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("mode", ARRAY_TYPES)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_lang_per_energy(ParserCls, mode, case):
    tape, mf, mt, E, LANG, NL, A = CASES[case]
    parser = ParserCls(array_type=mode)
    sub = _first_subsection(parser.parse(tape)[mf][mt])
    assert sub["LAW"] == 2
    assert sub["NE"] == len(E)
    lang = sub["LANG"]
    if mode == "dict":
        assert isinstance(lang, dict)
    elif mode == "list":
        assert isinstance(lang, list)
    else:
        assert isinstance(lang, np.ndarray)
        assert np.issubdtype(lang.dtype, np.integer)
    assert _seq(lang) == LANG
    assert _seq(sub["E"]) == E
    assert _seq(sub["NL"]) == NL
    assert _seq(sub["NLW"]) == [len(a) for a in A]
    assert [_seq(a) for a in _seq(sub["A"])] == A


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("flavor", ENDF_FORMATS)
@pytest.mark.parametrize("mode", ARRAY_TYPES)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_write_reproduces_input(ParserCls, mode, flavor, case):
    tape, mf, mt, E, LANG, NL, A = CASES[case]
    parser = ParserCls(array_type=mode, endf_format=flavor)
    endf_dict = parser.parse(tape)
    assert _seq(_first_subsection(endf_dict[mf][mt])["LANG"]) == LANG
    assert _text(parser.write(endf_dict)) == tape


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("mode", ARRAY_TYPES)
def test_python_and_cpp_parser_agree(mode, case):
    tape = CASES[case][0]
    dict_py = EndfParserPy(array_type=mode).parse(tape)
    dict_cpp = EndfParserCpp(array_type=mode).parse(tape)
    compare_objects(dict_py, dict_cpp)


def _mf26_with_lang(lang, energy):
    # MF26_TAPE with LANG of the given energy (1 or 2) replaced
    lines = MF26_TAPE.splitlines(keepends=True)
    lineno = (7, 9)[energy - 1]
    line = lines[lineno]
    assert line[22:33] == str(MF26_LANG[energy - 1]).rjust(11)
    lines[lineno] = line[:22] + str(lang).rjust(11) + line[33:]
    return "".join(lines)


@pytest.mark.parametrize("energy", [1, 2])
@pytest.mark.parametrize("lang", [1, 10, 16])
@pytest.mark.parametrize("mode", ARRAY_TYPES)
def test_mf26_invalid_lang_rejected(mode, lang, energy):
    tape = _mf26_with_lang(lang, energy)
    with pytest.raises(RuntimeError) as excinfo:
        EndfParserCpp(array_type=mode).parse(tape)
    msg = str(excinfo.value)
    assert msg.startswith("Encountered STOP instruction in recipe: " + STOP_MESSAGE)
    # the stop comes right after the LIST record of this energy: the last
    # line read is the last line of its body (lines counted from 1)
    last_body_line = MF26_TAPE.splitlines()[(8, 10)[energy - 1]]
    assert msg.endswith(f'Line {(9, 11)[energy - 1]}: "{last_body_line}"')
    with pytest.raises(StopException) as excinfo:
        EndfParserPy(array_type=mode).parse(tape)
    assert str(excinfo.value).endswith("Error message: " + STOP_MESSAGE)


@pytest.mark.parametrize("lang", [11, 15])
def test_mf26_lang_limits_accepted(lang):
    tape = _mf26_with_lang(lang, 2)
    for ParserCls in PARSER_CLASSES:
        parser = ParserCls()
        endf_dict = parser.parse(tape)
        assert _seq(endf_dict[26][525]["subsection"][1]["LANG"]) == [12, lang]
        assert _text(parser.write(endf_dict)) == tape


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf26_invalid_lang_rejected_when_writing(ParserCls):
    parser = ParserCls()
    endf_dict = parser.parse(MF26_TAPE)
    endf_dict[26][525]["subsection"][1]["LANG"][2] = 1
    with pytest.raises(Exception) as excinfo:
        parser.write(endf_dict)
    assert STOP_MESSAGE in str(excinfo.value)


# An MF6/MT5 section with a LAW=1 subsection, whose LANG is a single value
# (in the TAB2 record), and a LAW=2 subsection, whose LANG is per energy.
# Both use the variable name LANG within their subsection, as a scalar and
# as an array. The lines without the sequence number; the head, the two
# subsections and the end records.
MIXED_HEAD = [
    " 4.009000+3 8.934780+0          0          2          2          0 425 6  5",
]
MIXED_LAW1 = [
    " 1.000000+0 1.000000+0          0          1          1          2 425 6  5",
    "          2          2                                             425 6  5",
    " 1.000000+6 1.000000+0 1.000000+8 1.000000+0                       425 6  5",
    " 0.000000+0 0.000000+0          1          2          1          2 425 6  5",
    "          2          2                                             425 6  5",
    " 0.000000+0 1.000000+6          0          0          4          2 425 6  5",
    " 0.000000+0 1.000000-6 1.000000+6 0.000000+0                       425 6  5",
    " 0.000000+0 1.000000+8          0          0          4          2 425 6  5",
    " 0.000000+0 1.000000-6 1.000000+6 0.000000+0                       425 6  5",
]
MIXED_LAW2 = [
    " 1.001000+3 9.986235-1          0          2          1          2 425 6  5",
    "          2          2                                             425 6  5",
    " 1.000000+6 1.000000+0 1.000000+8 1.000000+0                       425 6  5",
    " 0.000000+0 0.000000+0          0          0          1          3 425 6  5",
    "          3          2                                             425 6  5",
    " 0.000000+0 1.000000+6          0          0          2          2 425 6  5",
    " 1.000000-1-5.000000-2                                             425 6  5",
    " 0.000000+0 5.000000+7          0          0          3          3 425 6  5",
    " 2.000000-1 5.000000-2 1.000000-2                                  425 6  5",
    " 0.000000+0 1.000000+8         12          0          6          3 425 6  5",
    "-1.000000+0 2.500000-1 0.000000+0 5.000000-1 1.000000+0 7.500000-1 425 6  5",
]
MIXED_END = (
    " 0.000000+0 0.000000+0          0          0          0          0 425 6  099999\n"
    " 0.000000+0 0.000000+0          0          0          0          0 425 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0   0 0  0    0\n"
    " 0.000000+0 0.000000+0          0          0          0          0  -1 0  0    0\n"
)


def _mixed_tape(law2_first):
    subsections = [MIXED_LAW1, MIXED_LAW2]
    if law2_first:
        subsections.reverse()
    lines = MIXED_HEAD + subsections[0] + subsections[1]
    tape = MF6_TAPE.splitlines(keepends=True)[0]
    tape += "".join(f"{line}{ns:5d}\n" for ns, line in enumerate(lines, 1))
    return tape + MIXED_END


@pytest.mark.parametrize("law2_first", [False, True])
@pytest.mark.parametrize("mode", ARRAY_TYPES)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf6_law1_and_law2_in_one_section(ParserCls, mode, law2_first):
    tape = _mixed_tape(law2_first)
    parser = ParserCls(array_type=mode)
    endf_dict = parser.parse(tape)
    subs = endf_dict[6][5]["subsection"]
    subs = [subs[k] for k in sorted(subs)] if isinstance(subs, dict) else list(subs)
    if law2_first:
        subs.reverse()
    assert [sub["LAW"] for sub in subs] == [1, 2]
    assert subs[0]["LANG"] == 1
    assert _seq(subs[1]["LANG"]) == MF6_LANG
    assert [_seq(a) for a in _seq(subs[1]["A"])] == MF6_A
    assert _text(parser.write(endf_dict)) == tape
