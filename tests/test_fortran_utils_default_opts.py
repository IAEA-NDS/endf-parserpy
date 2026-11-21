"""The number conversions of fortran_utils without options (None): the
defaults of each option, as with an empty dict."""

import pytest

from endf_parserpy.interpreter.fortran_utils import (
    float2basicnumstr,
    float2expformstr,
    float2fortstr,
    fortstr2float,
    read_fort_floats,
    write_fort_floats,
)

VALUES = [3007.0, -1.5e-7, 0.0, 1.234567e12, -2.0]


@pytest.mark.parametrize("val", VALUES)
def test_float2fortstr_without_options(val):
    assert float2fortstr(val) == float2fortstr(val, write_opts={})
    assert float2fortstr(val, write_opts=None) == float2fortstr(val, {})
    assert len(float2fortstr(val)) == 11


def test_float2fortstr_value():
    assert float2fortstr(3007.0) == " 3.007000+3"


@pytest.mark.parametrize("val", VALUES)
def test_helpers_without_options(val):
    assert float2basicnumstr(val) == float2basicnumstr(val, {})
    assert float2expformstr(val) == float2expformstr(val, {})


def test_write_fort_floats_without_options():
    expected = write_fort_floats(VALUES, write_opts={})
    assert write_fort_floats(VALUES) == expected
    assert write_fort_floats(VALUES, write_opts=None) == expected
    assert len(expected) == 11 * len(VALUES)


def test_read_fort_floats_without_options():
    line = write_fort_floats(VALUES[:3] + [1.0, 2.5, -3.0])
    expected = read_fort_floats(line, read_opts={})
    assert read_fort_floats(line) == expected
    assert read_fort_floats(line, n=6, read_opts=None) == expected
    assert expected == [fortstr2float(line[i : i + 11]) for i in range(0, 66, 11)]
    assert read_fort_floats(" 1.000000+0 2.5", n=2) == [1.0, 2.5]
