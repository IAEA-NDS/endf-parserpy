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

"""Writing LIST records without elements (NPL=0) with EndfParserCpp.

The writer of EndfParserCpp wrote the header line of an empty LIST record
twice. Its output must be identical to that of EndfParserPy.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _mt455_section():
    # MF1/MT455 with energy-dependent decay constants (LDG=1) and no
    # precursor families (NNF=0): one LIST record without elements for
    # each incident energy
    section = {
        "MAT": 9437,
        "ZA": 94239.0,
        "AWR": 236.9986,
        "LDG": 1,
        "LNU": 2,
        "NNF": 0,
        "NE": 2,
        "E_interpol": {"NBT": [2], "INT": [2]},
        "E": [1e-5, 2e7],
        "Eint": [1e-5, 2e7],
        "nubar_d": [0.0165, 0.009],
        "NBT": [2],
        "INT": [2],
    }
    return {1: {455: section}}


def test_written_as_by_python_writer():
    endf_dict = _mt455_section()
    expected = _lines(
        EndfParserPy(print_cache_info=False, array_type="list").write(endf_dict)
    )
    written = _lines(EndfParserCpp(array_type="list").write(endf_dict))
    assert written == expected


@pytest.mark.parametrize("mode", ["dict", "list"])
def test_roundtrip(mode):
    text = _lines(
        EndfParserPy(print_cache_info=False, array_type="list").write(_mt455_section())
    )
    parser = EndfParserCpp(array_type=mode, ignore_missing_tpid=True)
    assert _lines(parser.write(parser.parse("\n".join(text)))) == text
