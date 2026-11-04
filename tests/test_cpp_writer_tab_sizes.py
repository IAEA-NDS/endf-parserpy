############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/22
# Last modified:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""TAB1/TAB2 tables with arrays of different lengths in EndfParserCpp.

The arrays of a table that are written in pairs (NBT and INT, x and y)
must have the same number of elements. EndfParserCpp only checked this
with assert, which is disabled in release builds: a shorter second array
was read beyond its end, a shorter first array silently truncated the
table. Both cases are now rejected, as by EndfParserPy.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTDATA = Path(__file__).parent / "testdata"


def _mf3_section(E, xs, NBT=(2,), INT=(2,)):
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


def _mf4_section_with_tab2(NBT, INT):
    # MF4/MT2 of Cu-63: the interpolation of the Legendre coefficients over
    # the incident energies is given by the TAB2 record `leg_int`
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    parser = EndfParserCpp(ignore_missing_tpid=True, array_type="list")
    section = parser.parsefile(path, include=[(4, 2)])[4][2]
    section["leg_int"] = {"NBT": list(NBT), "INT": list(INT)}
    return {4: {2: section}}


CASES = {
    "y shorter": _mf3_section([1.0, 2.0, 3.0], [4.0, 5.0]),
    "x shorter": _mf3_section([1.0, 2.0], [4.0, 5.0, 6.0]),
    "INT shorter": _mf3_section([1.0, 2.0], [4.0, 5.0], NBT=(1, 2), INT=(2,)),
    "NBT shorter": _mf3_section([1.0, 2.0], [4.0, 5.0], NBT=(2,), INT=(2, 2)),
    "TAB2 INT shorter": _mf4_section_with_tab2(NBT=(10, 22), INT=(2,)),
    "TAB2 NBT shorter": _mf4_section_with_tab2(NBT=(22,), INT=(2, 2)),
}


@pytest.mark.parametrize("case", list(CASES))
def test_arrays_of_different_lengths_rejected(case):
    with pytest.raises(RuntimeError, match="same number of elements"):
        EndfParserCpp(ignore_missing_tpid=True, array_type="list").write(CASES[case])
    with pytest.raises(Exception):
        EndfParserPy(
            ignore_missing_tpid=True, print_cache_info=False, array_type="list"
        ).write(CASES[case])


@pytest.mark.parametrize(
    "endf_dict",
    [
        _mf3_section([1.0, 2.0], [4.0, 5.0]),
        _mf4_section_with_tab2(NBT=(10, 22), INT=(2, 2)),
    ],
    ids=["TAB1", "TAB2"],
)
def test_arrays_of_same_length_accepted(endf_dict):
    written = EndfParserCpp(ignore_missing_tpid=True, array_type="list").write(
        endf_dict
    )
    expected = EndfParserPy(
        ignore_missing_tpid=True, print_cache_info=False, array_type="list"
    ).write(endf_dict)
    assert list(written) == list(expected)
