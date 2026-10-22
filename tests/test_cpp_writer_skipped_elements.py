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

"""Writing nested arrays with skipped elements with EndfParserCpp.

The writer of EndfParserCpp keeps index bookkeeping for each level of a
nested array, stored by the position relative to the first element
accessed. An element that is not accessed, e.g. al[i] of an MF4 incident
energy with NL[i]=0, left a gap, and the bookkeeping of the following
element was read and written outside of its memory. This corrupted the
heap (crashes, possibly later and elsewhere).

With array_type="list", the start index of each level must be the first
index of the loop that creates the elements, not the first index accessed,
so that an empty first inner array (al[0] for NL[1]=0) does not shift the
other elements. The output of EndfParserCpp must be identical to that of
EndfParserPy.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTDATA = Path(__file__).parent / "testdata"


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _mf4_section(empty):
    # MF4/MT2 of Cu-63 with NL[i]=0 and no Legendre coefficients al[i] for
    # the incident energies i in `empty` ("last" for the last one)
    parser = EndfParserCpp(array_type="dict")
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    section = parser.parsefile(path, include=[(4, 2)])[4][2]
    last = max(section["al"])
    for i in empty:
        i = last if i == "last" else i
        del section["al"][i]
        section["NL"][i] = 0
    return {4: {2: section}}


EMPTY_CASES = [(2,), (1,), ("last",), (2, "last"), (1, 2, "last")]


@pytest.mark.parametrize("empty", EMPTY_CASES, ids=str)
def test_mf4_dict_written_as_by_python_writer(empty):
    endf_dict = _mf4_section(empty)
    written = _lines(EndfParserCpp(array_type="dict").write(endf_dict))
    expected = _lines(EndfParserPy(print_cache_info=False).write(endf_dict))
    assert written == expected


@pytest.mark.parametrize("empty", EMPTY_CASES, ids=str)
def test_mf4_dict_roundtrip(empty):
    text = _lines(EndfParserPy(print_cache_info=False).write(_mf4_section(empty)))
    parser = EndfParserCpp(array_type="dict", ignore_missing_tpid=True)
    assert _lines(parser.write(parser.parse("\n".join(text)))) == text


@pytest.mark.parametrize("mode", ["list", "numpy"])
@pytest.mark.parametrize("empty", EMPTY_CASES, ids=str)
def test_mf4_roundtrip_list_modes(empty, mode):
    if mode == "numpy":
        pytest.importorskip("numpy")
    text = _lines(EndfParserPy(print_cache_info=False).write(_mf4_section(empty)))
    parser = EndfParserCpp(array_type=mode, ignore_missing_tpid=True)
    assert _lines(parser.write(parser.parse("\n".join(text)))) == text
