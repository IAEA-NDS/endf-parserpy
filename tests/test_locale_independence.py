############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Reading and writing of numbers in a locale with another decimal point.

The C library functions std::strtod and std::snprintf use the decimal
point of the C locale (LC_NUMERIC), which locale.setlocale changes for
the whole process. ENDF-6 numbers always have a period as decimal point,
so the results must be the same as in the "C" locale. The numbers below
are chosen to reach the general code paths of EndfParserCpp, which call
these functions: decimal exponents above 22, subnormal numbers, D
exponents and a decimal point in front of the digits when reading, and
values close to rounding ties, very large and very small magnitudes and
the comparison of the representations with prefer_noexp when writing.

The tests are skipped if the system has no locale with a decimal point
other than a period (on Linux, such a locale can be created without
root permissions with `localedef -i de_DE -f UTF-8 <dir>/de_DE.UTF-8`
and used with the environment variable LOCPATH=<dir>).
"""

import contextlib
import itertools
import locale
import random
import struct
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


# locales with a comma as decimal point (names on Linux, macOS and Windows)
COMMA_LOCALES = (
    "de_DE.UTF-8",
    "de_DE.utf8",
    "de_DE",
    "de-DE",
    "German_Germany.1252",
    "fr_FR.UTF-8",
    "fr_FR.utf8",
    "fr_FR",
    "fr-FR",
    "nl_NL.UTF-8",
    "es_ES.UTF-8",
    "it_IT.UTF-8",
    "ru_RU.UTF-8",
    "pt_BR.UTF-8",
)
# locales whose decimal point is a character of more than one byte
# (U+066B ARABIC DECIMAL SEPARATOR)
MULTIBYTE_LOCALES = ("ps_AF.UTF-8", "ps_AF.utf8")


@contextlib.contextmanager
def _numeric_locale(name):
    saved = locale.setlocale(locale.LC_ALL)
    try:
        locale.setlocale(locale.LC_ALL, name)
        yield locale.localeconv()["decimal_point"]
    finally:
        locale.setlocale(locale.LC_ALL, saved)


def _find_locale(candidates, multibyte):
    for name in candidates:
        try:
            with _numeric_locale(name) as point:
                if point != "." and (len(point.encode("utf-8")) > 1) == multibyte:
                    return name
        except locale.Error:
            continue
    return None


LOCALES = {
    "comma": _find_locale(COMMA_LOCALES, multibyte=False),
    "multibyte": _find_locale(MULTIBYTE_LOCALES, multibyte=True),
}


@pytest.fixture(params=sorted(LOCALES))
def other_locale(request):
    name = LOCALES[request.param]
    if name is None:
        pytest.skip(f"no locale with a {request.param} decimal point available")
    return name


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


def _mf3_text(fields):
    # MF3 section with the given cross section fields (second, fourth and
    # sixth field of the data lines)
    written = EndfParserPy(ignore_missing_tpid=True).write(
        _mf3_section([1.0] * len(fields))
    )
    lines = _lines(written)
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


# fields converted by the general code path of EndfParserCpp (std::strtod)
# and, for comparison, by its fast paths
READ_FIELDS = [
    "1.234567+25",
    "-9.87654+30",
    "1.5000+300",
    "1.79769+308",
    "1.2345D+25",
    "1.2345d+25",
    "1.2345E25",
    "1.5e+023",
    ".5e+025",
    "-.5+025",
    "+.125+030",
    "4.94066-324",
    "4.3709-320",
    "2.22507-308",
    "1.0D+11",
    "1.234567+0",
    "-0.123456",
    "1.5",
    "1.",
    "12345678901",
]
READ_FIELDS = [f.rjust(11) for f in READ_FIELDS]
# fields that must be rejected as in the "C" locale
INVALID_FIELDS = ["  1,2345+25", "     1,5e25", "  1.2.3e+25"]
assert all(len(f) == 11 for f in READ_FIELDS + INVALID_FIELDS)


def _xs_hex(parser, text):
    return [float(x).hex() for x in parser.parse(text)[3][1]["xstable"]["xs"]]


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_reading_independent_of_locale(ParserCls, other_locale):
    parser = ParserCls(ignore_missing_tpid=True)
    text = _mf3_text(READ_FIELDS)
    expected = _xs_hex(parser, text)
    with _numeric_locale(other_locale):
        result = _xs_hex(parser, text)
    assert result == expected


@pytest.mark.parametrize("field", INVALID_FIELDS)
@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_invalid_fields_rejected_in_any_locale(ParserCls, field, other_locale):
    parser = ParserCls(ignore_missing_tpid=True)
    text = _mf3_text([field])
    with pytest.raises(Exception):
        parser.parse(text)
    with _numeric_locale(other_locale):
        with pytest.raises(Exception):
            parser.parse(text)


def _neighbours(x):
    bits = struct.unpack("<q", struct.pack("<d", x))[0]
    return [struct.unpack("<d", struct.pack("<q", bits + d))[0] for d in (-1, 1)]


def _write_values():
    rng = random.Random(7)
    values = []
    # values close to the rounding ties of 5 to 8 significant digits,
    # which the writer formats with std::snprintf
    for _ in range(100):
        digits = rng.choice([5, 6, 7, 8])
        mantissa = rng.randint(10 ** (digits - 1), 10**digits - 1)
        exponent = rng.randint(-30, 30)
        tie = float(f"{mantissa}5e{exponent - digits}")
        values += [tie] + _neighbours(tie)
    # very large and very small magnitudes (std::snprintf), subnormals
    values += [1.234567e300, 9.87654321e-290, 1.7976931348623157e308]
    values += [2.2250738585072014e-308, 4.9406564584124654e-324, 1.5e-320]
    # values for which prefer_noexp chooses the exponent form, the form
    # without exponent, or which need many digits without exponent
    values += [1.234567e-5, 1.2345678e-3, 0.123456789, 123456.789, 1.0e11]
    values += [3.0e9, 0.5, 2.5e-11, 12345678901.0, 1.0e22, 1.5e25]
    return values + [-v for v in values]


WRITE_VALUES = _write_values()
OPTION_NAMES = ("abuse_signpos", "keep_E", "skip_intzero", "prefer_noexp")
OPTION_COMBINATIONS = [
    dict(zip(OPTION_NAMES, values))
    for values in itertools.product([False, True], repeat=len(OPTION_NAMES))
]


def _option_id(options):
    return "+".join(k for k, v in options.items() if v) or "default"


@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_writing_independent_of_locale(ParserCls, options, other_locale):
    parser = ParserCls(ignore_missing_tpid=True, **options)
    section = _mf3_section(WRITE_VALUES)
    expected = _lines(parser.write(section))
    with _numeric_locale(other_locale):
        written = _lines(parser.write(section))
        # the written text is read back as in the "C" locale
        reread = _xs_hex(parser, "\n".join(written))
    differing = [(a, b) for a, b in zip(expected, written) if a != b]
    assert differing == [] and len(written) == len(expected)
    assert reread == _xs_hex(parser, "\n".join(expected))
