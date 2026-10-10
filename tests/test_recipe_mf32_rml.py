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

"""Regression tests for the uncertainties of the scattering radii (ISR>0)
in the covariance formats for the R-Matrix Limited formalism (LRU=1,
LRF=7) of the MF32/MT151 recipe.

For both LCOMP=1 and LCOMP=2, the uncertainties DAP are given in a LIST
record whose sixth field is the number of lines occupied by the values,
1+(NJCH-1)/6 with Fortran integer division (ENDF-102, Sections 32.2.2.4
and 32.2.4.3). The recipe used the expression literally, but integer
division in recipes must be exact, so parsing failed unless NJCH-1 was a
multiple of six. For LCOMP=1 the recipe additionally relied on the number
of channels NCH, which is not available at this point, so that the record
could never be read.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# LCOMP=1: one short-range block with a spin group of two channels and a
# single resonance; four (JCH=4) and eight (JCH=8, two lines) DAP values
MF32_LCOMP1_RML_JCH4 = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151    3\n"
    " 0.000000+0 0.000000+0          0          1          0          1263132151    4\n"
    " 0.000000+0 0.000000+0          0          0          4          1263132151    5\n"
    " 1.000000-2 2.000000-2 3.000000-2 4.000000-2                      263132151    6\n"
    " 5.545400+1 0.000000+0          0          0          1          0263132151    7\n"
    " 0.000000+0 0.000000+0          1          0          0          0263132151    8\n"
    " 0.000000+0 0.000000+0          2          1          6          1263132151    9\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151   10\n"
    " 0.000000+0 0.000000+0          0          0          6          3263132151   11\n"
    " 1.000000+2 0.000000+0 0.000000+0 1.000000-2 0.000000+0 2.500000-3263132151   12\n"
    " 0.000000+0 0.000000+0          0          0          0          0263132  099999"
)

MF32_LCOMP1_RML_JCH8 = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151    3\n"
    " 0.000000+0 0.000000+0          0          1          0          1263132151    4\n"
    " 0.000000+0 0.000000+0          0          0          8          2263132151    5\n"
    " 1.000000-2 2.000000-2 3.000000-2 4.000000-2 5.000000-2 6.000000-2263132151    6\n"
    " 7.000000-2 8.000000-2                                            263132151    7\n"
    " 5.545400+1 0.000000+0          0          0          1          0263132151    8\n"
    " 0.000000+0 0.000000+0          1          0          0          0263132151    9\n"
    " 0.000000+0 0.000000+0          2          1          6          1263132151   10\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151   11\n"
    " 0.000000+0 0.000000+0          0          0          6          3263132151   12\n"
    " 1.000000+2 0.000000+0 0.000000+0 1.000000-2 0.000000+0 2.500000-3263132151   13\n"
    " 0.000000+0 0.000000+0          0          0          0          0263132  099999"
)

# LCOMP=2: one spin group (NJS=1) with two channels, hence NJCH=2 values
MF32_LCOMP2_RML_NJCH2 = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151    3\n"
    " 0.000000+0 0.000000+0          0          2          1          1263132151    4\n"
    " 0.000000+0 0.000000+0          0          0          2          1263132151    5\n"
    " 1.000000-2 2.000000-2                                            263132151    6\n"
    " 0.000000+0 0.000000+0          2          1         24          4263132151    7\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+0263132151    8\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+0263132151    9\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+0263132151   10\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+0263132151   11\n"
    " 5.000000-1 1.000000+0          0          0         12          2263132151   12\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0263132151   13\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-1263132151   14\n"
    " 0.000000+0 0.000000+0          0          1         12          1263132151   15\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151   16\n"
    " 1.000000+1 1.000000-2 5.000000-3 0.000000+0 0.000000+0 0.000000+0263132151   17\n"
    " 0.000000+0 0.000000+0          2          0          0          0263132151   18\n"
    " 0.000000+0 0.000000+0          0          0          0          0263132  099999"
)

SECTIONS = {
    "LCOMP1_JCH4": MF32_LCOMP1_RML_JCH4,
    "LCOMP1_JCH8": MF32_LCOMP1_RML_JCH8,
    "LCOMP2_NJCH2": MF32_LCOMP2_RML_NJCH2,
}


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


def _range(endf_dict):
    return endf_dict[32][151]["isotope"][1]["range"][1]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", ["LCOMP1_JCH4", "LCOMP1_JCH8"])
def test_mf32_lcomp1_rml_scattering_radius_uncertainty(ParserCls, case):
    parser = _make_parser(ParserCls)
    rng = _range(parser.parse(SECTIONS[case]))
    assert (rng["LCOMP"], rng["ISR"]) == (1, 1)
    njch = int(case[-1])
    assert rng["JCH"] == njch
    assert [rng["DAP"][m] for m in range(1, njch + 1)] == [
        round(0.01 * m, 2) for m in range(1, njch + 1)
    ]
    # the short-range covariance block that follows is read as before
    assert rng["NSRS"] == 1
    assert rng["sr_subsec"][1]["j_group"][1]["NCH"] == 2


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf32_lcomp2_rml_scattering_radius_uncertainty(ParserCls):
    parser = _make_parser(ParserCls)
    rng = _range(parser.parse(MF32_LCOMP2_RML_NJCH2))
    assert (rng["LCOMP"], rng["ISR"], rng["NJS"]) == (2, 1, 1)
    assert rng["NJCH"] == 2
    assert (rng["DAP"][1][1], rng["DAP"][1][2]) == (0.01, 0.02)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf32_rml_scattering_radius_uncertainty_roundtrip(ParserCls, case):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(SECTIONS[case])
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = SECTIONS[case].splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf32_rml_scattering_radius_uncertainty_python_and_cpp_parser_agree(case):
    dict_py = _make_parser(EndfParserPy).parse(SECTIONS[case])
    dict_cpp = _make_parser(EndfParserCpp).parse(SECTIONS[case])
    compare_objects(dict_py, dict_cpp)
