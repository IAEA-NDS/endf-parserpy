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

"""Tests for the MF5 recipe (energy distributions of secondary particles).

The energy-dependent Watt spectrum (LF=11) is given by the fractional
probability p(E) followed by two TAB1 records with the energy-dependent
parameters a(E) and b(E) (ENDF-102, Section 5.2.5). The recipe used to
stop with an error for LF=11.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# Prompt fission neutron spectrum (MT=18) represented by a single
# energy-dependent Watt spectrum (LF=11)
MF5_MT18_LF11 = (
    " 9.423900+4 2.369986+2          0          0          1          09437 5 18    1\n"
    "-3.000000+7 0.000000+0          0         11          1          29437 5 18    2\n"
    "          2          2                                            9437 5 18    3\n"
    " 1.000000-5 1.000000+0 3.000000+7 1.000000+0                      9437 5 18    4\n"
    " 0.000000+0 0.000000+0          0          0          1          39437 5 18    5\n"
    "          3          2                                            9437 5 18    6\n"
    " 1.000000-5 9.650000+5 1.000000+6 9.800000+5 3.000000+7 1.100000+69437 5 18    7\n"
    " 0.000000+0 0.000000+0          0          0          1          29437 5 18    8\n"
    "          2          2                                            9437 5 18    9\n"
    " 1.000000-5 2.290000-6 3.000000+7 2.100000-6                      9437 5 18   10\n"
    " 0.000000+0 0.000000+0          0          0          0          09437 5  099999"
)


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf5_energy_dependent_watt_spectrum(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF5_MT18_LF11)[5][18]
    assert sec["NK"] == 1
    contrib = sec["contribution"][1]
    assert contrib["LF"] == 11
    assert contrib["U"] == -3.0e7
    assert list(contrib["p_table"]["p"]) == [1.0, 1.0]
    assert list(contrib["a_table"]["E"]) == [1.0e-5, 1.0e6, 3.0e7]
    assert list(contrib["a_table"]["a"]) == [9.65e5, 9.8e5, 1.1e6]
    assert list(contrib["b_table"]["E"]) == [1.0e-5, 3.0e7]
    assert list(contrib["b_table"]["b"]) == [2.29e-6, 2.1e-6]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf5_energy_dependent_watt_spectrum_roundtrip(ParserCls):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(MF5_MT18_LF11)
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = MF5_MT18_LF11.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_mf5_energy_dependent_watt_spectrum_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF5_MT18_LF11)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF5_MT18_LF11)
    compare_objects(dict_py, dict_cpp)
