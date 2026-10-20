############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/20
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for writing very small numbers with prefer_noexp=True.

With prefer_noexp=True, the writers choose between the representation with
and without exponent the one that reproduces the value more closely.
EndfParserCpp converted the candidates back with std::stod, which throws
std::out_of_range for subnormal numbers (below about 2.2e-308), so writing
such a number, or a slightly larger one that is rounded to a subnormal
number in one of the representations, failed. Both writers must produce
the same output.
"""

import itertools
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


OPTION_NAMES = ("abuse_signpos", "keep_E", "skip_intzero")
OPTION_COMBINATIONS = [
    dict(zip(OPTION_NAMES, values), prefer_noexp=True)
    for values in itertools.product([False, True], repeat=len(OPTION_NAMES))
]


def _option_id(options):
    return "+".join(k for k, v in options.items() if v)


def _mf3_section(xs):
    return {
        3: {
            1: {
                "MAT": 125,
                "MF": 3,
                "MT": 1,
                "ZA": 1001.0,
                "AWR": 0.9991673,
                "QM": 0.0,
                "QI": 0.0,
                "LR": 0,
                "xstable": {
                    "NBT": [len(xs)],
                    "INT": [2],
                    "E": [float(i + 1) for i in range(len(xs))],
                    "xs": xs,
                },
            }
        }
    }


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _small_values():
    values = [5e-324, 1e-320, 4.3709e-320, 1e-310]
    # normal numbers that are rounded to a subnormal number when written,
    # e.g. 2.2250738585072014e-308 as 2.225e-308 with keep_E=True
    values += [2.2250738585072014e-308, 2.22504e-308, 2.225074e-308, 2.2251e-308]
    values += [1e-300, 1.234567e-200, 1e-100, 1e-20, 1.5e-12, 1e-13, 3e-7]
    x = 5e-324
    while x < 1e-290:
        values.append(x)
        x *= 7.3
    return values + [-v for v in values]


@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
def test_small_numbers_written_by_both_parsers(options):
    section = _mf3_section(_small_values())
    lines_py = _lines(EndfParserPy(**options).write(section))
    lines_cpp = _lines(EndfParserCpp(**options).write(section))
    assert lines_cpp == lines_py


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_subnormal_number_round_trip(ParserCls):
    parser = ParserCls(prefer_noexp=True, ignore_missing_tpid=True)
    written = parser.write(_mf3_section([4.3709e-320, 1.0]))
    xs = parser.parse(written)[3][1]["xstable"]["xs"]
    assert xs[0] == pytest.approx(4.3709e-320, rel=1e-4, abs=0)
