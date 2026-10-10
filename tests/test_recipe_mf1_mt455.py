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

"""Regression tests for the MF1/MT455 recipe (delayed neutron data).

With energy-dependent decay constants (LDG=1), one LIST record with the
decay constants and abundances is given for each of the NE incident
energies E(k) of the preceding TAB2 record (ENDF-102, Section 1.2.2). In
the LDG=1, LNU=1 branch the recipe read the energy into a scalar variable
``E1`` instead of the array element ``E[k]``, so that every section with
NE>1 failed with a ``NumberMismatchError`` on the second energy.

Moreover, in both LDG=1 branches the TAB2 record with the interpolation
scheme for the incident energies was not given a table name, so that its
NBT and INT arrays shared the section-level keys of the TAB1 record of
nubar_d in the LNU=2 branch. Unless both interpolation tables happened to
coincide, the TAB1 record raised a mismatch in the Python parser, and the
C++ parser could not compare the arrays at all. The TAB2 interpolation
table is now stored under ``E_interpol``.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# LDG=1 (energy-dependent decay constants), LNU=1 (constant nubar_d)
MF1_MT455_LDG1_LNU1 = (
    " 9.223500+4 2.330248+2          1          1          0          09228 1455    1\n"
    " 0.000000+0 0.000000+0          0          0          1          29228 1455    2\n"
    "          2          2                                            9228 1455    3\n"
    " 0.000000+0 1.000000-5          0          0          4          09228 1455    4\n"
    " 1.333600-2 3.500000-2 3.273900-2 1.807000-1                      9228 1455    5\n"
    " 0.000000+0 2.000000+7          0          0          4          09228 1455    6\n"
    " 1.333600-2 3.600000-2 3.273900-2 1.900000-1                      9228 1455    7\n"
    " 0.000000+0 0.000000+0          0          0          1          09228 1455    8\n"
    " 1.585000-2                                                       9228 1455    9\n"
    " 0.000000+0 0.000000+0          0          0          0          09228 1  099999"
)

# LDG=1 (energy-dependent decay constants), LNU=2 (tabulated nubar_d);
# the interpolation tables of the TAB2 and the TAB1 record differ
MF1_MT455_LDG1_LNU2 = (
    " 9.223500+4 2.330248+2          1          2          0          09228 1455    1\n"
    " 0.000000+0 0.000000+0          0          0          1          29228 1455    2\n"
    "          2          2                                            9228 1455    3\n"
    " 0.000000+0 1.000000-5          0          0          4          09228 1455    4\n"
    " 1.333600-2 3.500000-2 3.273900-2 1.807000-1                      9228 1455    5\n"
    " 0.000000+0 2.000000+7          0          0          4          09228 1455    6\n"
    " 1.333600-2 3.600000-2 3.273900-2 1.900000-1                      9228 1455    7\n"
    " 0.000000+0 0.000000+0          0          0          1          39228 1455    8\n"
    "          3          2                                            9228 1455    9\n"
    " 1.000000-5 1.585000-2 1.000000+6 1.600000-2 2.000000+7 9.000000-39228 1455   10\n"
    " 0.000000+0 0.000000+0          0          0          0          09228 1  099999"
)

SECTIONS = {
    "LDG1_LNU1": MF1_MT455_LDG1_LNU1,
    "LDG1_LNU2": MF1_MT455_LDG1_LNU2,
}


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf1_mt455_energy_dependent_decay_constants(ParserCls, case):
    parser = _make_parser(ParserCls)
    sec = parser.parse(SECTIONS[case])[1][455]
    assert sec["LDG"] == 1
    assert sec["NE"] == 2
    assert sec["NNF"] == 2
    assert sec["E"][1] == 1e-5
    assert sec["E"][2] == 2e7
    assert "E1" not in sec
    assert sec["lambda"][2][1] == 1.3336e-2
    assert sec["alpha"][2][2] == 1.9e-1
    # interpolation scheme of the TAB2 record for the incident energies
    assert list(sec["E_interpol"]["NBT"]) == [2]
    assert list(sec["E_interpol"]["INT"]) == [2]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mf1_mt455_tabulated_nubar_with_energy_dependent_decay_constants(ParserCls):
    parser = _make_parser(ParserCls)
    sec = parser.parse(MF1_MT455_LDG1_LNU2)[1][455]
    assert list(sec["NBT"]) == [3]
    assert list(sec["INT"]) == [2]
    assert list(sec["Eint"]) == [1e-5, 1e6, 2e7]
    assert list(sec["nubar_d"]) == [1.585e-2, 1.6e-2, 9.0e-3]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf1_mt455_roundtrip(ParserCls, case):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(SECTIONS[case])
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = SECTIONS[case].splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("case", SECTIONS.keys())
def test_mf1_mt455_python_and_cpp_parser_agree(case):
    dict_py = _make_parser(EndfParserPy).parse(SECTIONS[case])
    dict_cpp = _make_parser(EndfParserCpp).parse(SECTIONS[case])
    compare_objects(dict_py, dict_cpp)
