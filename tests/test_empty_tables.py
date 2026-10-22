############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/22
# Last modified:   2026/10/22
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""TAB1/TAB2 records with empty interpolation tables or no points.

Both parsers read ceil(2*NR/6) lines of interpolation ranges and
ceil(2*NP/6) lines of points, i.e. no line for NR=0 or NP=0, as for a
LIST record with NPL=0. EndfParserCpp wrote a blank line for each empty
part, which neither parser reads back, and EndfParserPy failed with an
IndexError. Both now write no line for an empty part.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTDATA = Path(__file__).parent / "testdata"


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _mf3_section(NBT, INT, E, xs):
    xstable = {"NBT": list(NBT), "INT": list(INT), "E": list(E), "xs": list(xs)}
    section = {
        "MAT": 125,
        "MF": 3,
        "MT": 1,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "QM": 0.0,
        "QI": 0.0,
        "LR": 0,
        "xstable": xstable,
    }
    return {3: {1: section}}


def _mf4_section_without_tab2_ranges():
    # MF4/MT2 of Cu-63 with an empty interpolation table (NR=0) of the TAB2
    # record `leg_int` over the incident energies
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    section = EndfParserCpp(array_type="list").parsefile(path, include=[(4, 2)])
    section = section[4][2]
    section["leg_int"] = {"NBT": [], "INT": []}
    return {4: {2: section}}


CASES = {
    "TAB1 NR=NP=0": lambda: _mf3_section([], [], [], []),
    "TAB1 NR=0": lambda: _mf3_section([], [], [1.0, 2.0], [3.0, 4.0]),
    "TAB2 NR=0": _mf4_section_without_tab2_ranges,
}


@pytest.mark.parametrize("case", list(CASES))
def test_same_output_of_both_writers(case):
    endf_dict = CASES[case]()
    expected = _lines(
        EndfParserPy(print_cache_info=False, array_type="list").write(endf_dict)
    )
    assert _lines(EndfParserCpp(array_type="list").write(endf_dict)) == expected
    assert not any(line[:66].strip() == "" for line in expected)


def test_tab1_without_points_is_header_line_only():
    lines = _lines(EndfParserCpp().write(_mf3_section([], [], [], [])))
    # HEAD record, TAB1 header with NR=NP=0, then directly the SEND record
    assert lines[1][44:66] == "0".rjust(11) + "0".rjust(11)
    assert lines[2][70:75] == " 3  0"


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_roundtrip(case, ParserCls):
    kwargs = {"print_cache_info": False} if ParserCls is EndfParserPy else {}
    text = _lines(
        EndfParserPy(print_cache_info=False, array_type="list").write(CASES[case]())
    )
    parser = ParserCls(ignore_missing_tpid=True, array_type="list", **kwargs)
    assert _lines(parser.write(parser.parse("\n".join(text)))) == text
