############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/11/08
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
formatting options. The same holds for the decimal form of prefer_noexp
for values that round to an integer (with skip_intzero, a value below 1
in magnitude may round to 1) and for random values.
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
    # magnitudes around the range of a 32-bit integer and around 1, where
    # skip_intzero decides whether the integer part is zero
    values += [2.0**31 - 0.5, 2.0**31, 2.0**31 + 1, 3.0e9, 1.0e11, 1.0e15]
    values += [0.9999999, 0.999999999, 1.0, 1.0000001]
    # values whose decimal form (prefer_noexp) has no decimals and rounds
    # up to an integer with one more digit: 1000000000 for a magnitude in
    # [999999999.5, 1e9) (negative values, and non-negative ones without
    # abuse_signpos), 10000000000 for [9999999999.5, 1e10) (non-negative
    # ones with abuse_signpos); and the integers around them
    for n in (1e8, 1e9, 1e10):
        for d in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5):
            values += [n + d] + _neighbours(n + d)
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
    lines_py = _lines(
        EndfParserPy(**{"ignore_missing_tpid": True, **options}).write(section)
    )
    lines_cpp = _lines(
        EndfParserCpp(**{"ignore_missing_tpid": True, **options}).write(section)
    )
    assert len(lines_py) == len(lines_cpp)
    differing = [(a, b) for a, b in zip(lines_py, lines_cpp) if a != b]
    assert differing == []


def _rounding_to_integer_values():
    # values whose decimal form (prefer_noexp) rounds up to an integer: the
    # decimal form of a value below 1 in magnitude has 9 decimals, or 10
    # for a non-negative value with abuse_signpos and skip_intzero, so that
    # values within 5e-10 or 5e-11 of 1 round to 1; with skip_intzero, the
    # integer part 1 that the rounding produced must be kept
    values = []
    for one_minus in (5e-10, 5e-11):
        tie = 1 - one_minus
        values += [tie] + _neighbours(tie)
    values += [1 - k * 1e-12 for k in (1, 3, 10, 30, 49, 51, 100, 499, 501)]
    values += _neighbours(1.0)[:1] + [1 - 2.0**-30, 1 - 2.0**-33, 1 - 2.0**-36]
    # the same for larger integers, where fewer decimals are available
    for n in (2, 3, 9, 10, 99, 100, 12345, 99999999, 999999999, 1000000000):
        for d in (1e-9, 1e-10, 1e-11, 1e-12):
            values += [n - n * d, n + n * d]
    # values that round to 0 in the decimal form
    values += [4e-10, 6e-10, 4e-11, 6e-11, 1e-12]
    return values + [-v for v in values]


def _random_values(n, seed):
    rng = random.Random(seed)
    values = []
    for _ in range(n):
        kind = rng.randrange(4)
        if kind == 0:  # magnitudes where both forms compete
            values.append(rng.uniform(1, 10) * 10.0 ** rng.randint(-12, 11))
        elif kind == 1:  # below 1 in magnitude, the case of skip_intzero
            values.append(rng.random())
        elif kind == 2:  # close to an integer
            k = rng.randint(0, 1000)
            values.append(k + rng.choice([-1, 1]) * 10.0 ** rng.uniform(-13, -7))
        else:  # few significant digits
            values.append(round(rng.uniform(0, 100), rng.randint(0, 9)))
    values = [v for v in values if v != 0]
    return values + [-v for v in values]


@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
@pytest.mark.parametrize("kind", ["rounding_to_integer", "random"])
def test_cpp_writer_agrees_with_python_writer_noexp(options, kind):
    if kind == "random":
        values = _random_values(1500, seed=11)
    else:
        values = _rounding_to_integer_values()
    section = _mf3_section(values)
    lines_py = _lines(
        EndfParserPy(**{"ignore_missing_tpid": True, **options}).write(section)
    )
    lines_cpp = _lines(
        EndfParserCpp(**{"ignore_missing_tpid": True, **options}).write(section)
    )
    assert len(lines_py) == len(lines_cpp)
    differing = [(a, b) for a, b in zip(lines_py, lines_cpp) if a != b]
    assert differing == []


@pytest.mark.parametrize(
    "options",
    [o for o in OPTION_COMBINATIONS if o["prefer_noexp"] and o["skip_intzero"]],
    ids=_option_id,
)
@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_skip_intzero_keeps_carried_one(ParserCls, options):
    # 0.99999999999 rounds to 1 in the decimal form; the 1 is no integer
    # zero to be skipped
    values = [0.99999999999, -0.99999999999, 0.9999999996, -0.9999999996]
    lines = _lines(
        ParserCls(**{"ignore_missing_tpid": True, **options}).write(
            _mf3_section(values)
        )
    )
    # the third line holds the pairs (1, x1), (2, x2), (3, x3)
    fields = [lines[3][11 * i : 11 * (i + 1)] for i in range(6)]
    # 0.9999999996 has a tenth decimal only with abuse_signpos
    expected_third = ".9999999996" if options["abuse_signpos"] else "1".rjust(11)
    assert fields[1] == "1".rjust(11)
    assert fields[3] == "-1".rjust(11)
    assert fields[5] == expected_third
