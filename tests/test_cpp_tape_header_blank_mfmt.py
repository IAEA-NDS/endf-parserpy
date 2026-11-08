############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tape header (MF0/MT0) with blank MF/MT columns and a section filter.

With include=, EndfParserCpp reads the tape header verbatim. It read the
MF/MT numbers of its lines with std::stoi, which throws for a blank field
("ValueError: stoi"), e.g. for the FENDL-3.2c files whose header line has
only the MAT number (issue #150). A blank MF/MT field now reads as zero,
as everywhere else in the parser and in EndfParserPy. The cases without a
filter and with exclude= are checked as well.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


TESTDATA = Path(__file__).parent / "testdata"
TESTFILE = TESTDATA / "dec-094_Pu_244.endf"


def _with_header(header):
    lines = TESTFILE.read_text().splitlines()
    return "\n".join([header] + lines[1:]) + "\n"


HEADERS = {
    # MAT number only, MF/MT blank, padded to 80 columns
    "blank_mfmt": "FENDL-3.0".ljust(66) + "   0".ljust(14),
    # MAT number only, line cut after the MAT field
    "cut_after_mat": "FENDL-3.0".ljust(66) + "   0",
    # the line ends before the MAT field
    "cut_before_mat": "FENDL-3.0",
    # the regular form
    "regular": "FENDL-3.0".ljust(66) + "   1 0  0    0",
}


@pytest.mark.parametrize("header", sorted(HEADERS))
@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"include": [(8, 457)]},
        {"include": [8]},
        {"exclude": [(1, 451)]},
        {"exclude": [1]},
    ],
    ids=["full", "include_mfmt", "include_mf", "exclude_mfmt", "exclude_mf"],
)
def test_cpp_parse_with_filter_matches_python(header, kwargs):
    text = _with_header(HEADERS[header])
    res_cpp = EndfParserCpp().parse(text, **kwargs)
    res_py = EndfParserPy().parse(text, **kwargs)
    assert res_cpp.keys() == res_py.keys()
    assert res_cpp[0][0] == res_py[0][0]
    for mf in res_py:
        assert res_cpp[mf].keys() == res_py[mf].keys()
    if "include" in kwargs:
        assert 8 in res_cpp
