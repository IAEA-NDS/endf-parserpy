############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""A scalar variable read for the first time in a loop is checked in the
following iterations, by both parsers, e.g. NP and LI of the LIST records
of MF7/MT2 (one per temperature), which must agree with the first one.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError


def _create(ParserCls, **kwargs):
    try:
        return ParserCls(**kwargs)
    except Exception:
        pytest.skip(f"{ParserCls.__name__} unavailable")


@pytest.fixture(scope="module")
def mf7mt2_lines():
    sec = {
        "MAT": 1,
        "MF": 7,
        "MT": 2,
        "ZA": 1001.0,
        "AWR": 1.0,
        "LTHR": 1,
        "T0": 296.0,
        "LT": 2,
        "LI": 2,
        "NP": 3,
        "S_T0_table": {
            "NBT": [3],
            "INT": [1],
            "Eint": [1e-3, 2e-3, 3e-3],
            "S": [1.0, 2.0, 3.0],
        },
        "T": {1: 400.0, 2: 500.0},
        "S": {q: {i: float(q + 10 * i) for i in (1, 2)} for q in (1, 2, 3)},
    }
    tpid = {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "tape"}
    return EndfParserPy().write({0: {0: tpid}, 7: {2: sec}})


def _variant(lines, np2=None, li2=None):
    # the LIST record of the second temperature is lines[7] (head) and
    # lines[8] (values)
    lines = list(lines)
    assert lines[7][:11] == " 5.000000+2"
    if np2 is not None:
        lines[7] = lines[7][:44] + f"{np2:11d}" + lines[7][55:]
        lines[8] = lines[8][:22] + " " * 11 + lines[8][33:]
    if li2 is not None:
        lines[7] = lines[7][:22] + f"{li2:11d}" + lines[7][33:]
    return lines


@pytest.mark.parametrize("ParserCls", [EndfParserPy, EndfParserCpp])
@pytest.mark.parametrize("kwargs", [{"np2": 2}, {"li2": 1}])
def test_mf7mt2_list_records_checked(mf7mt2_lines, ParserCls, kwargs):
    parser = _create(ParserCls)
    assert parser.parse(mf7mt2_lines)[7][2]["NP"] == 3
    # EndfParserCpp reports a mismatch as a RuntimeError
    with pytest.raises((NumberMismatchError, RuntimeError), match="NP|LI|Expected"):
        parser.parse(_variant(mf7mt2_lines, **kwargs))


LENIENT = dict(
    ignore_number_mismatch=True,
    ignore_zero_mismatch=True,
    ignore_varspec_mismatch=True,
)


@pytest.mark.parametrize("ParserCls", [EndfParserPy, EndfParserCpp])
@pytest.mark.parametrize("kwargs", [{"np2": 2}, {"li2": 1}])
def test_mf7mt2_mismatch_also_with_lenient_options(mf7mt2_lines, ParserCls, kwargs):
    # ignore_number_mismatch accepts a mismatch only in a field marked
    # with ? in the recipe, which NP and LI of MF7/MT2 are not, so both
    # parsers reject the differing value also with the lenient options
    extra = {"print_cache_info": False} if ParserCls is EndfParserPy else {}
    parser = _create(ParserCls, **LENIENT, **extra)
    assert parser.parse(mf7mt2_lines)[7][2]["NP"] == 3
    with pytest.raises((NumberMismatchError, RuntimeError), match="NP|LI|Expected"):
        parser.parse(_variant(mf7mt2_lines, **kwargs))
