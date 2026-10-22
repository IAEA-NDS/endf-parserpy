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

"""Number of correlation values of INTG records for all NDIGIT.

ENDF-102 (Section 0.6.4.9) specifies 18, 13, 11, 9 and 8 values KIJ per
INTG record for NDIGIT=2, ..., 6. Both parsers read and wrote 14 values
for NDIGIT=3, the last one overlapping the MAT number in columns 67-70.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.endf_utils import (
    INTG_NUM_VALUES,
    intg_field_starts,
    read_intg,
    write_intg,
)


FORMATS = {
    # Fortran formats of the INTG record (without MAT, MF, MT, NS)
    2: (11, 18, 3),  # 2I5,1X,18I3,1X
    3: (11, 13, 4),  # 2I5,1X,13I4,3X
    4: (11, 11, 5),  # 2I5,1X,11I5
    5: (11, 9, 6),  # 2I5,1X,9I6,1X
    6: (10, 8, 7),  # 2I5,8I7
}


@pytest.mark.parametrize("ndigit", sorted(FORMATS))
def test_field_positions(ndigit):
    start, num, width = FORMATS[ndigit]
    assert INTG_NUM_VALUES[ndigit] == num
    assert list(intg_field_starts(ndigit)) == [start + k * width for k in range(num)]
    # all fields end before the MAT number in column 67
    assert start + num * width <= 66


def _intg_line(ndigit, values):
    start, num, width = FORMATS[ndigit]
    line = "    5    1" + " " * (start - 10)
    line += "".join(str(v).rjust(width) for v in values)
    return line.ljust(66) + "9437" + "32" + "151"


@pytest.mark.parametrize("ndigit", sorted(FORMATS))
def test_python_read_and_write(ndigit):
    num = INTG_NUM_VALUES[ndigit]
    values = [(-1) ** k * (k + 1) for k in range(num)]
    line = _intg_line(ndigit, values)
    opts = {"width": 11, "include_linenum": False}
    dic, ofs = read_intg([line], ndigit=ndigit, read_opts=opts)
    assert dic["KIJ"] == values
    assert dic["MAT"] == 9437
    assert write_intg(dic, ndigit=ndigit, write_opts=opts) == [line]
