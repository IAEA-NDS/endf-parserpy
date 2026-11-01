############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/13
# Last modified:   2026/11/02
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for the formatting of floats by the two writers.

Both writers use the largest precision for which a number fits into the
11-character field. A carry in the rounding changes the length of the
exponent, which the writers handled differently:

- 9.99999949e-10 with keep_E=True: EndfParserPy wrote `1.0000e-9`
  (one digit less than possible), EndfParserCpp `1.00000e-9`.
- 9.9999995e-10 with abuse_signpos=True: EndfParserCpp produced a field of
  10 characters and failed ("wrong size10").
- 9999999500 with abuse_signpos=True: the exact `9.9999995+9` fits, both
  writers wrote `1.000000+10`.

In addition, the module checks that both writers produce identical output
for a set of values and all combinations of the formatting options.
"""

import itertools
import random
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]

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


def _written_xs_field(parser, value):
    # field of the cross section in the first line of the TAB1 body
    return _lines(parser.write(_mf3_section([value])))[3][11:22]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "value, options, expected",
    [
        (9.99999949e-10, {"keep_E": True}, " 1.00000e-9"),
        (-9.99999949e-10, {"keep_E": True, "abuse_signpos": True}, "-1.00000e-9"),
        (9.9999995e-10, {"abuse_signpos": True}, " 1.000000-9"),
        (9999999500.0, {"abuse_signpos": True}, "9.9999995+9"),
        (9.99999949e-10, {}, "  1.00000-9"),
        (1.2345678e-5, {}, " 1.234568-5"),
        (-1.2345678e-15, {}, "-1.23457-15"),
    ],
    ids=[
        "carry_shorter_exponent_keep_E",
        "carry_negative_abuse_signpos_keep_E",
        "carry_abuse_signpos_width",
        "carry_longer_exponent",
        "carry_no_extra_digit",
        "regular",
        "regular_negative",
    ],
)
def test_carry_in_rounding(ParserCls, value, options, expected):
    assert _written_xs_field(ParserCls(**options), value) == expected


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "value, options, expected",
    [
        # 4 to 8 significant digits, with exponents of 1, 2 and 3 digits
        (1.23456789, {}, " 1.234568+0"),
        (-0.987654321, {}, "-9.876543-1"),
        (3.0102999e-10, {}, " 3.01030-10"),
        (-4.5678901e-99, {}, "-4.56789-99"),
        (5.6789012e100, {}, " 5.6789+100"),
        (-6.7890123e-280, {}, "-6.7890-280"),
        (7.8901234e279, {}, " 7.8901+279"),
        (1.23456789, {"abuse_signpos": True}, "1.2345679+0"),
        (9.0123456e-10, {"abuse_signpos": True}, "9.012346-10"),
        (2.3456789e-123, {"abuse_signpos": True}, "2.34568-123"),
        (1.23456789, {"keep_E": True}, " 1.23457e+0"),
        (-8.9012345e10, {"keep_E": True}, "-8.9012e+10"),
        (6.5432109e-200, {"keep_E": True}, " 6.543e-200"),
        (4.3210987e200, {"keep_E": True, "abuse_signpos": True}, "4.3211e+200"),
        (-4.3210987e200, {"keep_E": True, "abuse_signpos": True}, "-4.321e+200"),
        # zero and negative zero
        (0.0, {}, " 0.000000+0"),
        (-0.0, {}, " 0.000000+0"),
        (0.0, {"abuse_signpos": True}, "0.0000000+0"),
        (-0.0, {"keep_E": True}, " 0.00000e+0"),
        (0.0, {"keep_E": True, "abuse_signpos": True}, "0.000000e+0"),
        # subnormal, smallest normal and largest double
        (5e-324, {}, " 4.9407-324"),
        (2.2250738585072014e-308, {}, " 2.2251-308"),
        (-1.7976931348623157e308, {}, "-1.7977+308"),
    ],
)
def test_digits_and_exponent_lengths(ParserCls, value, options, expected):
    # every number of digits of the mantissa and of the exponent that a
    # field can have; EndfParserCpp writes the values with decimal
    # exponents up to about 44 in magnitude in its fast path, the others
    # with the general procedure (std::snprintf)
    assert _written_xs_field(ParserCls(**options), value) == expected


def _test_values():
    rng = random.Random(1)
    values = []
    for _ in range(3000):
        mantissa = rng.uniform(1, 10) * rng.choice([1, -1])
        values.append(mantissa * 10.0 ** rng.randint(-40, 40))
    for k in range(-12, 13):
        for m in (1.0, 9.9999995, 9.99999949, 1.0000005, 1.23456785, 2.5, 0.5, 9.5):
            values += [m * 10.0**k, -m * 10.0**k]
    for _ in range(600):
        values.append(round(rng.uniform(0, 1e6), rng.randint(0, 9)))
    values += [0.0, 1e-300, 1e300, 123456789.0, 1e10, 9999999.5, 0.1, 1 / 3]
    return values


TEST_VALUES = _test_values()


@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
def test_python_and_cpp_writer_agree(options):
    section = _mf3_section(TEST_VALUES)
    lines_py = _lines(EndfParserPy(**options).write(section))
    lines_cpp = _lines(EndfParserCpp(**options).write(section))
    assert len(lines_py) == len(lines_cpp)
    differing = [(a, b) for a, b in zip(lines_py, lines_cpp) if a != b]
    assert differing == []
