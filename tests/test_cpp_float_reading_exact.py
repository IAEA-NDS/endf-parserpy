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

"""Exactness of the conversion of number fields to floats by EndfParserCpp.

EndfParserCpp converts most number fields with a fast path and falls back
to std::strtod for the others. The result must always be the correctly
rounded double, i.e. identical to the value obtained by EndfParserPy (Python
float conversion). The fields cover the notations found in ENDF-6 files,
numbers near the limits of the fast path (many digits, large and small
exponents, subnormal numbers) and decimal numbers close to a rounding tie.
"""

import random
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


def _field_strings():
    rng = random.Random(1)
    fields = [
        " 1.000000+0",
        "-1.000000+0",
        " 1.234567+5",
        "-1.23456-12",
        " 1.23456+12",
        "1.000000E+0",
        " 1.00000e-5",
        "1.000000-10",
        " 2.5000+300",
        " 4.3709-320",
        " 1.7976+308",
        " 2.2251-308",
        "      12345",
        "     -12345",
        "        0.0",
        "       -0.0",
        "         .5",
        "        -.5",
        "  123456.75",
        " 0.10000000",
        " 9.999999+9",
        "9.9999995+9",
        "9.9999999-9",
        "+1.234567+2",
        "     1.0D-3",
        "5.438673D-4",
        " 0.30000000",
        "90071992547",
        "  1.2345678",
        " 1.00000000",
        "2.000000+38",
        "3.402823+38",
        "1.175494-38",
    ]
    assert all(len(f) <= 11 for f in fields)
    fields = [f.rjust(11) for f in fields]
    for _ in range(3000):
        digits = rng.randint(1, 9)
        mantissa = f"{rng.uniform(1, 10):.{digits}f}"
        sign = rng.choice(["", "-"])
        exponent = rng.randint(-99, 99)
        exp_str = f"{exponent:+d}"
        if rng.random() < 0.3:
            exp_str = "E" + exp_str
        field = sign + mantissa + exp_str
        if len(field) > 11:
            field = field[: 11 - len(exp_str)] + exp_str
        fields.append(field.rjust(11))
    for _ in range(1000):
        # plain decimal numbers with up to ten significant digits
        value = rng.uniform(-1e5, 1e5)
        field = f"{value:.{rng.randint(0, 5)}f}"[:11]
        fields.append(field.rjust(11))
    # decimal numbers close to a rounding tie of the double conversion
    for _ in range(500):
        mantissa = str(rng.randint(1000000, 9999999))
        fields.append(
            (mantissa[0] + "." + mantissa[1:] + "5" + f"{rng.randint(-9, 9):+d}").rjust(
                11
            )[:11]
        )
    return fields


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


def _mf3_text(fields):
    # MF3 section written by EndfParserPy, with the cross section fields
    # (second, fourth and sixth field of the data lines) replaced
    written = EndfParserPy().write(_mf3_section([1.0] * len(fields)))
    lines = written.splitlines() if isinstance(written, str) else list(written)
    remaining = list(fields)
    for i in range(3, len(lines)):
        line = lines[i]
        for start in (11, 33, 55):
            if remaining and line[start : start + 11] == " 1.000000+0":
                line = line[:start] + remaining.pop(0) + line[start + 11 :]
        lines[i] = line
        if not remaining:
            break
    assert not remaining
    return "\n".join(lines)


def _expected_value(field):
    # Python float conversion of the field in Fortran notation
    s = field.strip().replace("D", "e").replace("d", "e")
    for i in range(1, len(s)):
        if s[i] in "+-" and s[i - 1] not in "eE":
            s = s[:i] + "e" + s[i:]
            break
    return float(s)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_float_fields_correctly_rounded(ParserCls):
    fields = _field_strings()
    parser = ParserCls(ignore_missing_tpid=True)
    xs = parser.parse(_mf3_text(fields))[3][1]["xstable"]["xs"]
    assert len(xs) == len(fields)
    mismatches = [
        (f, float(x).hex(), _expected_value(f).hex())
        for f, x in zip(fields, xs)
        if float(x).hex() != _expected_value(f).hex()
    ]
    assert mismatches == []


def test_cpp_and_python_reading_agree():
    text = _mf3_text(_field_strings())
    xs_cpp = EndfParserCpp(ignore_missing_tpid=True).parse(text)[3][1]["xstable"]["xs"]
    xs_py = EndfParserPy(ignore_missing_tpid=True).parse(text)[3][1]["xstable"]["xs"]
    assert [float(x).hex() for x in xs_cpp] == [float(x).hex() for x in xs_py]
