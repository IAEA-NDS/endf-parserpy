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

"""Integers that do not fit into their field are rejected when writing.

A number wider than its field shifted the following fields of the line
(EndfParserPy: an 11-column integer field, MAT/MF/MT, the fields of INTG
records; EndfParserCpp: MAT/MF/MT and the fields of INTG records, as its
integers of 32 bits fit into 11 columns). Both writers now raise an error.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import InvalidIntegerError


def _mf3_section(MAT=125, LR=0, NBT=2):
    xstable = {"NBT": [NBT], "INT": [2], "E": [1.0, 2.0], "xs": [3.0, 4.0]}
    section = {
        "MAT": MAT,
        "MF": 3,
        "MT": 1,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "QM": 0.0,
        "QI": 0.0,
        "LR": LR,
        "xstable": xstable,
    }
    return {3: {1: section}}


def _py_write(endf_dict):
    return EndfParserPy(print_cache_info=False).write(endf_dict)


@pytest.mark.parametrize(
    "kwargs",
    [{"LR": 10**12}, {"LR": -(10**10)}, {"NBT": 10**11}],
    ids=["L2 too large", "L2 too small", "NBT too large"],
)
def test_python_writer_rejects_wide_integers(kwargs):
    with pytest.raises(InvalidIntegerError, match="does not fit"):
        _py_write(_mf3_section(**kwargs))


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("mat", [10000, -1000])
def test_mat_number_too_wide(ParserCls, mat):
    kwargs = {"print_cache_info": False} if ParserCls is EndfParserPy else {}
    with pytest.raises(Exception, match="does not fit"):
        ParserCls(**kwargs).write(_mf3_section(MAT=mat))


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_largest_integers_written(ParserCls):
    kwargs = {"print_cache_info": False} if ParserCls is EndfParserPy else {}
    lines = ParserCls(**kwargs).write(_mf3_section(MAT=9999, LR=-(10**9)))
    lines = lines.splitlines() if isinstance(lines, str) else list(lines)
    assert lines[1][33:44] == str(-(10**9)).rjust(11)
    assert lines[1][66:70] == "9999"
    assert all(len(line) == 80 for line in lines)
