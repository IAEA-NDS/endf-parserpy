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

"""Regression tests for the optional background R-matrix extension of the
R-Matrix Limited format (LRU=1, LRF=7) in the MF2/MT151 recipe.

For KBK>0, KBK channels of a spin group carry a background R-matrix, each
introduced by a CONT record with the channel index LCH and the background
option LBK, followed by LBK-dependent data (ENDF-102, Section 2.2.1.6).
The recipe had two defects:

* For LBK=1 the CONT record was read a second time before the two TAB1
  records with the real and imaginary parts, so that the first TAB1
  record was mistaken for a CONT record.
* LCH, LBK and the LBK-dependent quantities were not indexed by channel,
  so a spin group with background R-matrices in two channels failed with
  a ``NumberMismatchError`` on the second channel.

The data of each channel is now kept in its own ``background[n]`` section.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# Two particle pairs (gamma, n) and one spin group with two channels and a
# single resonance; the background R-matrix of channel 2 is tabulated
# (LBK=1).
MF2_RML_KBK1_LBK1 = (
    " 2.605600+4 5.545400+1          0          0          1          02631 2151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          02631 2151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          02631 2151    3\n"
    " 0.000000+0 0.000000+0          0          3          1          02631 2151    4\n"
    " 0.000000+0 0.000000+0          2          0         24          42631 2151    5\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+02631 2151    6\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+02631 2151    7\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+02631 2151    8\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+02631 2151    9\n"
    " 5.000000-1 1.000000+0          1          0         12          22631 2151   10\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+02631 2151   11\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-12631 2151   12\n"
    " 0.000000+0 0.000000+0          0          1          6          12631 2151   13\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+02631 2151   14\n"
    " 0.000000+0 0.000000+0          2          1          0          02631 2151   15\n"
    " 0.000000+0 0.000000+0          0          0          1          22631 2151   16\n"
    "          2          2                                            2631 2151   17\n"
    " 1.000000-5 1.000000-1 1.000000+6 2.000000-1                      2631 2151   18\n"
    " 0.000000+0 0.000000+0          0          0          1          22631 2151   19\n"
    "          2          2                                            2631 2151   20\n"
    " 1.000000-5 1.000000-2 1.000000+6 2.000000-2                      2631 2151   21\n"
    " 0.000000+0 0.000000+0          0          0          0          02631 2  099999"
)

# Same spin group with background R-matrices in both channels:
# Froehner's parameterization (LBK=3) for channel 1 and SAMMY's logarithmic
# parameterization (LBK=2) for channel 2.
MF2_RML_KBK2_LBK3_LBK2 = (
    " 2.605600+4 5.545400+1          0          0          1          02631 2151    1\n"
    " 2.605600+4 1.000000+0          0          0          1          02631 2151    2\n"
    " 1.000000-5 1.000000+6          1          7          0          02631 2151    3\n"
    " 0.000000+0 0.000000+0          0          3          1          02631 2151    4\n"
    " 0.000000+0 0.000000+0          2          0         24          42631 2151    5\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+02631 2151    6\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+02631 2151    7\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+02631 2151    8\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+02631 2151    9\n"
    " 5.000000-1 1.000000+0          2          0         12          22631 2151   10\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+02631 2151   11\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-12631 2151   12\n"
    " 0.000000+0 0.000000+0          0          1          6          12631 2151   13\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+02631 2151   14\n"
    " 0.000000+0 0.000000+0          1          3          0          02631 2151   15\n"
    " 1.000000-5 1.000000+6          0          0          3          02631 2151   16\n"
    " 1.000000-1 2.000000-1 3.000000-1                                 2631 2151   17\n"
    " 0.000000+0 0.000000+0          2          2          0          02631 2151   18\n"
    " 1.000000-5 1.000000+6          0          0          5          02631 2151   19\n"
    " 1.000000-1 2.000000-1 3.000000-1 4.000000-1 5.000000-1           2631 2151   20\n"
    " 0.000000+0 0.000000+0          0          0          0          02631 2  099999"
)

SECTIONS = {
    "KBK1_LBK1": MF2_RML_KBK1_LBK1,
    "KBK2_LBK3_LBK2": MF2_RML_KBK2_LBK3_LBK2,
}


def _make_parser(ParserCls):
    return ParserCls(ignore_send_records=True, ignore_missing_tpid=True)


def _spin_group(endf_dict):
    return endf_dict[2][151]["isotope"][1]["range"][1]["j_group"][1]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_rml_tabulated_background_rmatrix(ParserCls):
    parser = _make_parser(ParserCls)
    jgroup = _spin_group(parser.parse(MF2_RML_KBK1_LBK1))
    assert jgroup["KBK"] == 1
    bkg = jgroup["background"][1]
    assert bkg["LCH"] == 2
    assert bkg["LBK"] == 1
    assert list(bkg["real_part"]["E"]) == [1.0e-5, 1.0e6]
    assert list(bkg["real_part"]["RBR"]) == [0.1, 0.2]
    assert list(bkg["imag_part"]["RBI"]) == [0.01, 0.02]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_rml_background_rmatrix_in_several_channels(ParserCls):
    parser = _make_parser(ParserCls)
    jgroup = _spin_group(parser.parse(MF2_RML_KBK2_LBK3_LBK2))
    assert jgroup["KBK"] == 2
    bkg1 = jgroup["background"][1]
    bkg2 = jgroup["background"][2]
    assert (bkg1["LCH"], bkg1["LBK"]) == (1, 3)
    assert (bkg1["R0"], bkg1["S0"], bkg1["GA"]) == (0.1, 0.2, 0.3)
    assert (bkg2["LCH"], bkg2["LBK"]) == (2, 2)
    assert (bkg2["ED"], bkg2["EU"]) == (1.0e-5, 1.0e6)
    assert (bkg2["R0"], bkg2["R1"], bkg2["R2"]) == (0.1, 0.2, 0.3)
    assert (bkg2["S0"], bkg2["S1"]) == (0.4, 0.5)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", SECTIONS.keys())
def test_rml_background_rmatrix_roundtrip(ParserCls, case):
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(SECTIONS[case])
    written = parser.write(endf_dict)
    lines = written.splitlines() if isinstance(written, str) else list(written)
    compare_objects(endf_dict, parser.parse("\n".join(lines)))
    # the data records (all but the SEND record) are reproduced verbatim
    data_lines = SECTIONS[case].splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("case", SECTIONS.keys())
def test_rml_background_rmatrix_python_and_cpp_parser_agree(case):
    dict_py = _make_parser(EndfParserPy).parse(SECTIONS[case])
    dict_cpp = _make_parser(EndfParserCpp).parse(SECTIONS[case])
    compare_objects(dict_py, dict_cpp)
