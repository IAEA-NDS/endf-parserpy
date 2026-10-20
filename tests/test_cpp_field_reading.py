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

"""Reading of integer and float fields by EndfParserCpp.

EndfParserCpp converts the common shapes of number fields in a single pass
and falls back to the general conversion for all other fields. For valid
fields, the values must agree with EndfParserPy; invalid fields must be
rejected in the same cases, depending on accept_spaces and
accept_d_exponent.
"""

import random
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


def _mf3_section():
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
                "xstable": {"NBT": [2], "INT": [2], "E": [1.0, 2.0], "xs": [3.0, 4.0]},
            }
        }
    }


BASE_LINES = None


def _text(qm, qi, lr):
    # MF3 section in which the fields QM, QI (float) and LR (integer) of the
    # TAB1 header record are replaced by the given 11-character strings
    global BASE_LINES
    if BASE_LINES is None:
        written = EndfParserPy(print_cache_info=False).write(_mf3_section())
        BASE_LINES = written.splitlines() if isinstance(written, str) else list(written)
    lines = list(BASE_LINES)
    line = lines[1]
    lines[1] = qm + qi + line[22:33] + lr + line[44:]
    return "\n".join(lines)


def _outcome(parser, qm, qi, lr):
    try:
        sec = parser.parse(_text(qm, qi, lr))[3][1]
    except Exception:
        return "error"
    return [float(sec["QM"]).hex(), float(sec["QI"]).hex(), sec["LR"]]


FLOAT_FIELDS = [
    " 1.234567+5",
    "-1.23456-12",
    "1.000000E+0",
    " 1.00000e-5",
    "       -0.0",
    "         .5",
    "        -.5",
    "  123456.75",
    " 9.999999+9",
    "+1.234567+2",
    "     1.0D-3",
    "5.438673D-4",
    " 2.5000+300",
    " 4.3709-320",
    "        0.0",
    "           ",
    "1.5        ",
    "      1.5  ",
    "  1.5 E+2  ",
    "    1.5e 2 ",
    "    1.5e+  ",
    "   1.5.2   ",
    "   abc     ",
    "  1.5+3+2  ",
    " 1.0d+3    ",
]
INT_FIELDS = [
    "          0",
    "         12",
    "        -12",
    "         +7",
    "           ",
    "12         ",
    "      12   ",
    "  1 2      ",
    "        1.0",
    "  123456789",
    " 1234567890",
    "         1e",
    "        - 1",
]


def _random_float_fields(rng, n):
    fields = []
    for _ in range(n):
        digits = rng.randint(0, 8)
        value = rng.uniform(-10, 10) * 10.0 ** rng.randint(-30, 30)
        s = f"{value:.{digits}e}"
        s = s.replace("e", rng.choice(["e", "E", ""]))
        if rng.random() < 0.5:
            s = s.replace("+0", "+").replace("-0", "-")
        if len(s) <= 11:
            fields.append(s.rjust(11) if rng.random() < 0.7 else s.ljust(11))
    return fields


@pytest.mark.parametrize("spaces", [True, False])
@pytest.mark.parametrize("d_exponent", [True, False])
def test_float_fields_agree_with_python(spaces, d_exponent):
    opts = {"accept_spaces": spaces, "accept_d_exponent": d_exponent}
    cpp = EndfParserCpp(**opts)
    py = EndfParserPy(**opts, print_cache_info=False)
    fields = FLOAT_FIELDS + _random_float_fields(random.Random(3), 300)
    differing = []
    for f in fields:
        a = _outcome(cpp, f, " 1.000000+0", "          0")
        b = _outcome(py, f, " 1.000000+0", "          0")
        if a != b:
            differing.append((f, a, b))
    assert differing == []


@pytest.mark.parametrize("spaces", [True, False])
def test_integer_fields_agree_with_python(spaces):
    cpp = EndfParserCpp(accept_spaces=spaces)
    py = EndfParserPy(accept_spaces=spaces, print_cache_info=False)
    differing = []
    for f in INT_FIELDS:
        a = _outcome(cpp, " 0.000000+0", " 0.000000+0", f)
        b = _outcome(py, " 0.000000+0", " 0.000000+0", f)
        if a != b:
            differing.append((f, a, b))
    assert differing == []
