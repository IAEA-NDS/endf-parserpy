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

"""Tests for the MF31 recipe (covariances of fission neutron multiplicities).

The subsubsections for spontaneous fission carry no energy dependence
(ENDF-102, Section 31.2). They are special cases of the formats for
particle-induced fission, which MF31 shares with MF33, and are therefore
read by the same recipe:

* NC-type, LTY=0: ``[0.0, 0.0, 0, 0, 2*NCI, NCI/ {CI, XMTI}]LIST`` is the
  LTY=0 record with E1 = E2 = 0.0,
* NC-type, LTY=1,2,3: ``[0.0, 0.0, MATS, MTS, 4, 1/ XMFS, XLFSS, 0.0,
  Weight]LIST`` is the LTY=1,2,3 record with NEI=1, E[1]=0.0 and
  WE[1]=Weight,
* NI-type, LB=0,1: ``[0.0, 0.0, 0, LB, 2, 1/ 0.0, F]LIST`` is the LB=0,1
  record with LT=0, NP=1, Ek[1]=0.0 and Fk[1]=F.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# Section of dec-098_Cf_252.endf (ENDF/B-VIII.0 decay sublibrary):
# variance of the total nubar of spontaneous fission (NI-type, LB=0)
MF31_MT452_CF252_SF = (
    " 9.825200+4 2.499160+2          0          0          0          1364431452    1\n"
    " 1.000000+0 0.000000+0          0        452          0          1364431452    2\n"
    " 0.000000+0 0.000000+0          0          0          2          1364431452    3\n"
    " 0.000000+0 2.209000-5                                            364431452    4\n"
    " 0.000000+0 0.000000+0          0          0          0          0364431  099999"
)

# Spontaneous fission with NC-type subsubsections (LTY=0 and LTY=1) and an
# NI-type subsubsection with LB=1
MF31_MT456_SF_NC_AND_NI = (
    " 9.825200+4 2.499160+2          0          0          0          1364431456    1\n"
    " 1.000000+0 0.000000+0          0        456          2          1364431456    2\n"
    " 0.000000+0 0.000000+0          0          0          0          0364431456    3\n"
    " 0.000000+0 0.000000+0          0          0          4          2364431456    4\n"
    " 1.000000+0 4.520000+2-1.000000+0 4.550000+2                      364431456    5\n"
    " 0.000000+0 0.000000+0          0          1          0          0364431456    6\n"
    " 0.000000+0 0.000000+0       9861        452          4          1364431456    7\n"
    " 3.100000+1 0.000000+0 0.000000+0 1.000000+0                      364431456    8\n"
    " 0.000000+0 0.000000+0          0          1          2          1364431456    9\n"
    " 0.000000+0 4.000000-6                                            364431456   10\n"
    " 0.000000+0 0.000000+0          0          0          0          0364431  099999"
)

SECTIONS = {
    "MT452_CF252": MF31_MT452_CF252_SF,
    "MT456_NC_AND_NI": MF31_MT456_SF_NC_AND_NI,
}


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf31_spontaneous_fission_ni_type(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF31_MT452_CF252_SF)[31][452]
    sub = sec["subsection"][1]
    assert (sub["MT1"], sub["NC"], sub["NI"]) == (452, 0, 1)
    ni = sub["ni_subsection"][1]
    assert (ni["LT"], ni["LB"], ni["NP"]) == (0, 0, 1)
    assert ni["Ek"][1] == 0.0
    assert ni["Fk"][1] == 2.209e-5


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf31_spontaneous_fission_nc_type(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF31_MT456_SF_NC_AND_NI)[31][456]
    sub = sec["subsection"][1]
    assert (sub["NC"], sub["NI"]) == (2, 1)
    # NC-type, LTY=0: derived redundant quantity
    nc1 = sub["nc_subsection"][1]
    assert (nc1["LTY"], nc1["E1"], nc1["E2"], nc1["NCI"]) == (0, 0.0, 0.0, 2)
    assert (nc1["C"][1], nc1["XMT"][1]) == (1.0, 452.0)
    assert (nc1["C"][2], nc1["XMT"][2]) == (-1.0, 455.0)
    # NC-type, LTY=1: ratio to a standard, a single weight
    nc2 = sub["nc_subsection"][2]
    assert (nc2["LTY"], nc2["MATS"], nc2["MTS"], nc2["NEI"]) == (1, 9861, 452, 1)
    assert (nc2["XMFS"], nc2["XLFSS"]) == (31.0, 0.0)
    assert (nc2["E"][1], nc2["WE"][1]) == (0.0, 1.0)
    # NI-type, LB=1: relative variance
    ni = sub["ni_subsection"][1]
    assert (ni["LB"], ni["NP"], ni["Ek"][1], ni["Fk"][1]) == (1, 1, 0.0, 4.0e-6)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf31_spontaneous_fission_roundtrip(ParserCls, case):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(SECTIONS[case])
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = SECTIONS[case].splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf31_spontaneous_fission_python_and_cpp_parser_agree(case):
    dict_py = _make_parser(EndfParserPy).parse(SECTIONS[case])
    dict_cpp = _make_parser(EndfParserCpp).parse(SECTIONS[case])
    compare_objects(dict_py, dict_cpp)
