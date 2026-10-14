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

"""Tests for the MF14 recipe (photon angular distributions).

For anisotropic distributions given in tabular form (LI=0, LTT=2), the
NI isotropic photons are each represented by a CONT record and the
remaining NK-NI anisotropic photons by a TAB2 record followed by one TAB1
record of the probability distribution p(mu,E) for each of the NE incident
energies (ENDF-102, Section 14.2.3). The recipe used to stop with an
error for LTT=2.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# NK=3 photons: one isotropic photon (NI=1), followed by an anisotropic
# discrete photon and the anisotropic continuum (EG=0), each tabulated at
# two incident energies
MF14_LTT2 = (
    " 6.012000+3 1.189690+1          0          2          3          1 62514 51    1\n"
    " 4.438900+6 4.438900+6          0          0          0          0 62514 51    2\n"
    " 3.200000+6 7.650000+6          0          0          1          2 62514 51    3\n"
    "          2          2                                             62514 51    4\n"
    " 0.000000+0 5.000000+6          0          0          1          3 62514 51    5\n"
    "          3          2                                             62514 51    6\n"
    "-1.000000+0 6.000000-1 0.000000+0 4.000000-1 1.000000+0 6.000000-1 62514 51    7\n"
    " 0.000000+0 2.000000+7          0          0          1          3 62514 51    8\n"
    "          3          2                                             62514 51    9\n"
    "-1.000000+0 7.000000-1 0.000000+0 3.000000-1 1.000000+0 7.000000-1 62514 51   10\n"
    " 0.000000+0 0.000000+0          0          0          1          2 62514 51   11\n"
    "          2          2                                             62514 51   12\n"
    " 0.000000+0 5.000000+6          0          0          1          2 62514 51   13\n"
    "          2          2                                             62514 51   14\n"
    "-1.000000+0 5.000000-1 1.000000+0 5.000000-1                       62514 51   15\n"
    " 0.000000+0 2.000000+7          0          0          1          2 62514 51   16\n"
    "          2          2                                             62514 51   17\n"
    "-1.000000+0 4.000000-1 1.000000+0 6.000000-1                       62514 51   18\n"
    " 0.000000+0 0.000000+0          0          0          0          0 62514  099999"
)


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf14_tabulated_angular_distributions(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF14_LTT2)[14][51]
    assert (sec["LI"], sec["LTT"], sec["NK"], sec["NI"]) == (0, 2, 3, 1)
    # isotropic photon
    assert (sec["EG"][1], sec["ES"][1]) == (4.4389e6, 4.4389e6)
    # anisotropic discrete photon
    assert (sec["EG"][2], sec["ES"][2]) == (3.2e6, 7.65e6)
    assert sec["NE"][2] == 2
    assert sec["E"][2][2] == 2.0e7
    assert list(sec["angtable"][2][1]["mu"]) == [-1.0, 0.0, 1.0]
    assert list(sec["angtable"][2][2]["p"]) == [0.7, 0.3, 0.7]
    # anisotropic continuum
    assert sec["EG"][3] == 0.0
    assert sec["E"][3][1] == 5.0e6
    assert list(sec["angtable"][3][2]["p"]) == [0.4, 0.6]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf14_tabulated_angular_distributions_roundtrip(ParserCls):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(MF14_LTT2)
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = MF14_LTT2.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_mf14_tabulated_angular_distributions_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF14_LTT2)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF14_LTT2)
    compare_objects(dict_py, dict_cpp)
