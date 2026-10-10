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

"""Regression tests for the MF26 recipe (electro-atomic interaction data).

Each of the NK product subsections of an MF26 section starts with its own
yield TAB1 record carrying ZAP, AWI and LAW (ENDF-102, Section 26.2). The
recipe used to read this record outside of the ``subsection[i]`` block, so
that ZAP, AWI, LAW and the yield table of all subsections shared a single
namespace. As soon as two subsections differed in one of these values the
parser failed with a ``NumberMismatchError``. This affected every
bremsstrahlung section (MT=527) of the ENDF/B-VIII.0 electro-atomic
sublibrary, which contains a LAW=1 photon spectrum followed by a LAW=8
energy-loss subsection.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# Bremsstrahlung section (MT=527) modelled after e-001_H_000.endf of
# ENDF/B-VIII.0: subsection 1 with LAW=1 (photon spectrum, LANG=1, NA=0)
# and subsection 2 with LAW=8 (average energy loss).
MF26_MT527 = (
    " 1.000000+3 9.992414-1          0          0          2          0 10026527    1\n"
    " 1.100000+1 5.438673-4          0          1          1          2 10026527    2\n"
    "          2          2                                             10026527    3\n"
    " 1.000000+1 1.000000+0 1.00000+11 1.000000+0                       10026527    4\n"
    " 0.000000+0 0.000000+0          1          2          1          2 10026527    5\n"
    "          2          2                                             10026527    6\n"
    " 0.000000+0 1.000000+1          0          0          4          2 10026527    7\n"
    " 1.000000-1 2.139400+0 1.000000+1 2.130000-2                       10026527    8\n"
    " 0.000000+0 1.00000+11          0          0          4          2 10026527    9\n"
    " 1.000000-1 1.500000+0 1.00000+11 1.000000-2                       10026527   10\n"
    " 1.100000+1 5.438673-4          0          8          1          2 10026527   11\n"
    "          2          2                                             10026527   12\n"
    " 1.000000+1 1.000000+0 1.00000+11 1.000000+0                       10026527   13\n"
    " 0.000000+0 0.000000+0          0          0          1          2 10026527   14\n"
    "          2          2                                             10026527   15\n"
    " 1.000000+1 1.700000-1 1.00000+11 2.40000+10                       10026527   16\n"
    " 0.000000+0 0.000000+0          0          0          0          0 10026  099999"
)


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf26_subsections_with_different_laws(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF26_MT527)[26][527]
    assert sec["NK"] == 2
    sub1 = sec["subsection"][1]
    sub2 = sec["subsection"][2]
    # the yield record belongs to its subsection
    assert sub1["ZAP"] == 11.0
    assert sub1["LAW"] == 1
    assert sub2["ZAP"] == 11.0
    assert sub2["LAW"] == 8
    assert list(sub1["yields"]["Eint"]) == [10.0, 1e11]
    assert "ZAP" not in sec and "LAW" not in sec and "yields" not in sec
    # LAW=1 specific data
    assert sub1["LANG"] == 1
    assert sub1["NE"] == 2
    assert sub1["Ep"][2][2] == 1e11
    assert sub1["b"][1][2][0] == 2.13e-2
    # LAW=8 specific data
    assert list(sub2["ET"]) == [0.17, 2.4e10]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf26_roundtrip(ParserCls):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(MF26_MT527)
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = MF26_MT527.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_mf26_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF26_MT527)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF26_MT527)
    compare_objects(dict_py, dict_cpp)
