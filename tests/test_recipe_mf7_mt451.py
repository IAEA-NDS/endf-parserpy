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

"""Regression tests for the MF7/MT451 recipe (generalized information file).

The LIST record describing the isotopic composition of an element is
repeated NA times, once for each element in the scattering system, and
each of these records carries its own number of atoms NAS (ENDF-102,
Section 7.6.1). The recipe stored NAS in a scalar variable, so a material
with several elements of different multiplicity, such as SiO2, failed
with a ``NumberMismatchError`` on the second LIST record.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# SiO2: silicon (NAS=1, three isotopes) and oxygen (NAS=2, one isotope)
MF7_MT451_SIO2 = (
    " 1.400000+4 2.784400+1          2          0          0          01408 7451    1\n"
    " 0.000000+0 0.000000+0          1          0         18          31408 7451    2\n"
    " 1.402800+4 0.000000+0 9.222300-1 2.773700+1 2.120000+0 0.000000+01408 7451    3\n"
    " 1.402900+4 0.000000+0 4.685000-2 2.872800+1 2.780000+0 0.000000+01408 7451    4\n"
    " 1.403000+4 0.000000+0 3.092000-2 2.971800+1 2.640000+0 0.000000+01408 7451    5\n"
    " 0.000000+0 0.000000+0          2          0          6          11408 7451    6\n"
    " 8.016000+3 0.000000+0 1.000000+0 1.585800+1 3.761000+0 0.000000+01408 7451    7\n"
    " 0.000000+0 0.000000+0          0          0          0          01408 7  099999"
)


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf7_mt451_elements_with_different_multiplicity(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF7_MT451_SIO2)[7][451]
    assert sec["NA"] == 2
    assert sec["NAS"][1] == 1
    assert sec["NAS"][2] == 2
    assert sec["NI"][1] == 3
    assert sec["NI"][2] == 1
    assert sec["ZAI"][1][3] == 14030.0
    assert sec["ZAI"][2][1] == 8016.0
    assert sec["AFI"][1][2] == 4.685e-2
    assert sec["SFI"][2][1] == 3.761


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf7_mt451_roundtrip(ParserCls):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(MF7_MT451_SIO2)
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = MF7_MT451_SIO2.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


def test_mf7_mt451_python_and_cpp_parser_agree():
    dict_py = _make_parser(EndfParserPy).parse(MF7_MT451_SIO2)
    dict_cpp = _make_parser(EndfParserCpp).parse(MF7_MT451_SIO2)
    compare_objects(dict_py, dict_cpp)
