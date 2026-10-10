############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/10
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests for the `accept_d_exponent` parsing flag.

Some evaluated data files contain numbers with a Fortran double-precision
exponent, e.g. ``5.438673D-4`` in the MF1/MT451 records of the
ENDF/B-VIII.0 electro-atomic sublibrary. Such numbers do not conform to the
ENDF-6 format. Both backends accept them by default and reject them with
`accept_d_exponent=False`. On output, the numbers are written in the
usual ENDF-6 notation unless the original strings are preserved.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, TapeIndex
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# MF3/MT2 section with Fortran double-precision exponents in various forms
# (upper and lower case, with and without sign, mixed with other notations);
# the second section contains the same numbers in the usual ENDF-6 notation
MF3_WITH_D_EXPONENTS = (
    " 2.60540D+45.347000D+1          0          0          0          02625 3  2    1\n"
    "        0.0    -2.5d+6          0          0          1          32625 3  2    2\n"
    "          3          2                                            2625 3  2    3\n"
    " 1.00000D-5     1.0D+3      1.0e3      4.0D5 2.000000+7     1.5d-32625 3  2    4\n"
    "        0.0        0.0          0          0          0          02625 3  099999"
)
MF3_WITH_E_EXPONENTS = (
    " 2.605400+4 5.347000+1          0          0          0          02625 3  2    1\n"
    " 0.000000+0-2.500000+6          0          0          1          32625 3  2    2\n"
    "          3          2                                            2625 3  2    3\n"
    " 1.000000-5 1.000000+3 1.000000+3 4.000000+5 2.000000+7 1.500000-32625 3  2    4\n"
    "        0.0        0.0          0          0          0          02625 3  099999"
)


def _make_parser(ParserCls, **kwargs):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True, **kwargs)


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_d_exponent_accepted_by_default(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF3_WITH_D_EXPONENTS)[3][2]
    assert sec["ZA"] == 26054.0
    assert sec["AWR"] == 53.47
    assert sec["QI"] == -2.5e6
    assert list(sec["xstable"]["E"]) == [1.0e-5, 1.0e3, 2.0e7]
    assert list(sec["xstable"]["xs"]) == [1.0e3, 4.0e5, 1.5e-3]
    compare_objects(sec, parser.parse(MF3_WITH_E_EXPONENTS)[3][2])


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_d_exponent_written_in_endf_notation(ParserCls):
    parser = _make_parser(ParserCls)
    lines = _lines(parser.write(parser.parse(MF3_WITH_D_EXPONENTS)))
    data_lines = MF3_WITH_E_EXPONENTS.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_d_exponent_rejected_if_disabled(ParserCls):
    parser = _make_parser(ParserCls, accept_d_exponent=False)
    # numbers in the usual notation are still read
    parser.parse(MF3_WITH_E_EXPONENTS)
    with pytest.raises(Exception):
        parser.parse(MF3_WITH_D_EXPONENTS)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_d_exponent_preserved_with_value_strings(ParserCls):
    parser = _make_parser(ParserCls, preserve_value_strings=True)
    lines = _lines(parser.write(parser.parse(MF3_WITH_D_EXPONENTS)))
    data_lines = MF3_WITH_D_EXPONENTS.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_d_exponent_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF3_WITH_D_EXPONENTS)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF3_WITH_D_EXPONENTS)
    compare_objects(dict_py, dict_cpp)


def test_tape_index_reads_d_exponent_in_head_record():
    tpid = " " * 66 + "   1 0  0    0"
    fend = "".ljust(66) + "2625 0  0    0"
    mend = "".ljust(66) + "   0 0  0    0"
    tend = "".ljust(66) + "  -1 0  0    0"
    lines = [tpid] + MF3_WITH_D_EXPONENTS.splitlines() + [fend, mend, tend]
    index = TapeIndex.from_lines(lines)
    (material,) = list(index)
    assert material.za == 26054
    assert material.awr == 53.47
