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

"""Formatting of floats by EndfParserCpp in the cases where its fast path
needs care, compared with EndfParserPy.

EndfParserCpp computes the decimal digits of a float with exact double
arithmetic and falls back to std::snprintf for values close to a rounding
tie and for very large or very small magnitudes. The values below
concentrate on these cases and on the transitions between them; the output
must be identical to that of EndfParserPy for all combinations of the
formatting options.
"""

import itertools
import random
import struct
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


OPTION_NAMES = ("abuse_signpos", "keep_E", "skip_intzero", "prefer_noexp")
OPTION_COMBINATIONS = [
    dict(zip(OPTION_NAMES, values))
    for values in itertools.product([False, True], repeat=len(OPTION_NAMES))
]


def _option_id(options):
    return "+".join(k for k, v in options.items() if v) or "default"


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


def _neighbours(x):
    # the two adjacent doubles of a positive double (math.nextafter needs 3.9)
    bits = struct.unpack("<q", struct.pack("<d", x))[0]
    return [struct.unpack("<d", struct.pack("<q", bits + d))[0] for d in (-1, 1)]


def _test_values():
    rng = random.Random(5)
    values = []
    # decimal numbers exactly halfway between two candidates of the rounding
    # to 5, 6, 7 and 8 significant digits, and their neighbouring doubles
    for _ in range(400):
        digits = rng.choice([5, 6, 7, 8])
        mantissa = rng.randint(10 ** (digits - 1), 10**digits - 1)
        exponent = rng.randint(-30, 30)
        tie = float(f"{mantissa}5e{exponent - digits}")
        values += [tie] + _neighbours(tie)
    # very large and very small magnitudes, including subnormal numbers
    for exponent in list(range(270, 309)) + list(range(-323, -270)):
        mantissa = rng.uniform(1, 10)
        if exponent < 308 or mantissa < 1.7:
            values.append(mantissa * 10.0**exponent)
    values += [5e-324, 2.2250738585072014e-308, 1.7976931348623157e308]
    # values whose rounding carries into the next power of ten
    for exponent in range(-25, 25):
        for m in (9.9999995, 9.99999949, 9.999995, 9.9999949, 9.99999995):
            values.append(m * 10.0**exponent)
    values = [v for v in values if v != 0]
    return values + [-v for v in values]


TEST_VALUES = _test_values()


@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
def test_cpp_writer_agrees_with_python_writer(options):
    if options["prefer_noexp"]:
        # The prefer_noexp path uses the general formatting function, not
        # the fast path; it converts the candidate representations back with
        # std::stod, which fails if the rounded number is subnormal.
        values = [v for v in TEST_VALUES if abs(v) >= 1e-307]
    else:
        values = TEST_VALUES
    section = _mf3_section(values)
    lines_py = _lines(EndfParserPy(**options).write(section))
    lines_cpp = _lines(EndfParserCpp(**options).write(section))
    assert len(lines_py) == len(lines_cpp)
    differing = [(a, b) for a, b in zip(lines_py, lines_cpp) if a != b]
    assert differing == []
