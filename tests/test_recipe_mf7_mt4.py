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

"""Tests for the MF7/MT4 recipe (incoherent inelastic thermal scattering).

If B(1)=0.0, there is no principal scattering atom and the scattering law
is completely described by the analytic functions of the non-principal
atoms; the tabulated S(alpha,beta), i.e., the TAB2 record and the
TAB1/LIST records that follow it, is then omitted (ENDF-102, Section
7.5.1). The recipe always expected the tabulated S(alpha,beta).
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# No principal scattering atom (B(1)=0.0) and one non-principal atom
# (NS=1) treated in the short-collision-time approximation (B(7)=a1=0.0),
# so that the effective temperature tables Teff0 and Teff1 are given.
MF7_MT4_ANALYTIC_ONLY = (
    " 8.016000+3 1.585800+1          0          0          0          01099 7  4    1\n"
    " 0.000000+0 0.000000+0          0          0         12          11099 7  4    2\n"
    " 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+01099 7  4    3\n"
    " 0.000000+0 3.761000+0 1.585800+1 0.000000+0 0.000000+0 1.000000+01099 7  4    4\n"
    " 0.000000+0 0.000000+0          0          0          1          21099 7  4    5\n"
    "          2          2                                            1099 7  4    6\n"
    " 2.936000+2 3.000000+2 6.000000+2 6.100000+2                      1099 7  4    7\n"
    " 0.000000+0 0.000000+0          0          0          1          21099 7  4    8\n"
    "          2          2                                            1099 7  4    9\n"
    " 2.936000+2 3.200000+2 6.000000+2 6.200000+2                      1099 7  4   10\n"
    " 0.000000+0 0.000000+0          0          0          0          01099 7  099999"
)


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf7_mt4_without_principal_scattering_atom(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF7_MT4_ANALYTIC_ONLY)[7][4]
    assert sec["NS"] == 1
    assert sec["NI"] == 12
    assert sec["B"][1] == 0.0
    assert sec["B"][8] == 3.761
    assert "beta_interp" not in sec
    assert "S_table" not in sec
    assert list(sec["teff0_table"]["Teff0"]) == [300.0, 610.0]
    assert list(sec["teff1_table"]["Teff1"]) == [320.0, 620.0]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf7_mt4_without_principal_scattering_atom_roundtrip(ParserCls):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(MF7_MT4_ANALYTIC_ONLY)
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = MF7_MT4_ANALYTIC_ONLY.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_mf7_mt4_without_principal_scattering_atom_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF7_MT4_ANALYTIC_ONLY)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF7_MT4_ANALYTIC_ONLY)
    compare_objects(dict_py, dict_cpp)
