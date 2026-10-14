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

"""Regression tests for the MF8/MT457 recipe (radioactive decay data).

The covariance matrix of the discrete radiation intensities (LCOV=2,3) is
given in a LB=5 LIST record with NERP=NER+1 energies followed by the upper
triangle of a symmetric NER x NER matrix, i.e., NE=NERP*(NERP+1)/2 values
in total (ENDF-102, Section 8.4.1). The recipe iterated the matrix indices
only up to NERP-2, so that one row and column of the matrix were missing
and parsing failed with an ``UnconsumedListElementsError``. The JENDL
flavor carries its own copy of the recipe and was affected in the same way.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]
FLAVORS = ["endf6", "jendl"]


# One gamma spectrum with two discrete lines, LCON=0 (discrete only),
# LCOV=2 (covariance of the discrete spectrum)
MF8_MT457_LCON0_LCOV2 = (
    " 2.706000+4 5.940000+1          0          0          0          12725 8457    1\n"
    " 1.663000+8 2.000000+4          0          0          6          02725 8457    2\n"
    " 9.600000+4 1.000000+2 2.500000+6 1.000000+3 0.000000+0 0.000000+02725 8457    3\n"
    " 5.000000+0 1.000000+0          0          0          6          12725 8457    4\n"
    " 1.000000+0 0.000000+0 2.823800+6 2.100000+1 1.000000+0 0.000000+02725 8457    5\n"
    " 0.000000+0 0.000000+0          0          2          6          22725 8457    6\n"
    " 1.000000+0 0.000000+0 2.500000+6 1.000000+3 1.000000+0 0.000000+02725 8457    7\n"
    " 1.173228+6 3.000000+0          0          0          6          02725 8457    8\n"
    " 1.000000+0 0.000000+0 9.985000-1 2.000000-4 0.000000+0 0.000000+02725 8457    9\n"
    " 1.332492+6 4.000000+0          0          0          6          02725 8457   10\n"
    " 1.000000+0 0.000000+0 9.998000-1 6.000000-5 0.000000+0 0.000000+02725 8457   11\n"
    " 0.000000+0 0.000000+0          1          5          6          32725 8457   12\n"
    " 1.173228+6 1.332492+6 1.000000+0 4.000000-8 1.000000-8 3.600000-92725 8457   13\n"
    " 0.000000+0 0.000000+0          0          0          0          02725 8  099999"
)

# Same spectrum with an additional continuous component, LCON=2, and both
# covariance matrices, LCOV=3: the continuous covariance (LB=2) precedes
# the discrete covariance (LB=5).
MF8_MT457_LCON2_LCOV3 = (
    " 2.706000+4 5.940000+1          0          0          0          12725 8457    1\n"
    " 1.663000+8 2.000000+4          0          0          6          02725 8457    2\n"
    " 9.600000+4 1.000000+2 2.500000+6 1.000000+3 0.000000+0 0.000000+02725 8457    3\n"
    " 5.000000+0 1.000000+0          0          0          6          12725 8457    4\n"
    " 1.000000+0 0.000000+0 2.823800+6 2.100000+1 1.000000+0 0.000000+02725 8457    5\n"
    " 0.000000+0 0.000000+0          2          3          6          22725 8457    6\n"
    " 1.000000+0 0.000000+0 2.500000+6 1.000000+3 1.000000+0 0.000000+02725 8457    7\n"
    " 1.173228+6 3.000000+0          0          0          6          02725 8457    8\n"
    " 1.000000+0 0.000000+0 9.985000-1 2.000000-4 0.000000+0 0.000000+02725 8457    9\n"
    " 1.332492+6 4.000000+0          0          0          6          02725 8457   10\n"
    " 1.000000+0 0.000000+0 9.998000-1 6.000000-5 0.000000+0 0.000000+02725 8457   11\n"
    " 1.000000+0 0.000000+0          0          0          1          22725 8457   12\n"
    "          2          2                                            2725 8457   13\n"
    " 1.000000+3 5.000000-7 2.000000+6 1.000000-7                      2725 8457   14\n"
    " 0.000000+0 0.000000+0          0          2          4          22725 8457   15\n"
    " 1.000000+3 1.000000-2 2.000000+6 4.000000-2                      2725 8457   16\n"
    " 0.000000+0 0.000000+0          1          5          6          32725 8457   17\n"
    " 1.173228+6 1.332492+6 1.000000+0 4.000000-8 1.000000-8 3.600000-92725 8457   18\n"
    " 0.000000+0 0.000000+0          0          0          0          02725 8  099999"
)

SECTIONS = {
    "LCON0_LCOV2": MF8_MT457_LCON0_LCOV2,
    "LCON2_LCOV3": MF8_MT457_LCON2_LCOV3,
}


def _make_parser(ParserCls, flavor):
    return ParserCls(
        endf_format=flavor, ignore_send_records=True, ignore_missing_tpid=True
    )


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("flavor", FLAVORS)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf8_mt457_discrete_spectrum_covariance(ParserCls, flavor, case):
    parser = _make_parser(ParserCls, flavor)
    spec = parser.parse(SECTIONS[case])[8][457]["spectrum"][1]
    assert spec["NER"] == 2
    cov = spec["discrete"]["cov"]
    assert cov["LS"] == 1
    assert cov["NERP"] == 3
    assert cov["NE"] == 6
    assert cov["E"][2] == 1.332492e6
    # upper triangle of the 2x2 relative covariance matrix
    assert cov["F"][1][1] == 4.0e-8
    assert cov["F"][1][2] == 1.0e-8
    assert cov["F"][2][2] == 3.6e-9


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("flavor", FLAVORS)
def test_mf8_mt457_continuous_and_discrete_covariance(ParserCls, flavor):
    parser = _make_parser(ParserCls, flavor)
    spec = parser.parse(MF8_MT457_LCON2_LCOV3)[8][457]["spectrum"][1]
    assert spec["LCON"] == 2
    assert spec["LCOV"] == 3
    assert list(spec["continuous"]["RP"]) == [5.0e-7, 1.0e-7]
    assert spec["continuous"]["NPP"] == 2
    assert spec["continuous"]["F"][2] == 4.0e-2


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("flavor", FLAVORS)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf8_mt457_roundtrip(ParserCls, flavor, case):
    parser = _make_parser(ParserCls, flavor)
    endf_dict = parser.parse(SECTIONS[case])
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = SECTIONS[case].splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("flavor", FLAVORS)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf8_mt457_python_and_cpp_parser_agree(flavor, case):
    dict_py = _make_parser(EndfParserPy, flavor).parse(SECTIONS[case])
    dict_cpp = _make_parser(EndfParserCpp, flavor).parse(SECTIONS[case])
    compare_objects(dict_py, dict_cpp)
