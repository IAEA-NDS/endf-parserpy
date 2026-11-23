############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/23
# Last modified:   2026/11/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Float fields without a decimal point are read as ENDF-6 prescribes.

The ENDF-6 formats manual gives the Fortran edit descriptor F11.0 (and the
read formats 2E11.0 and 6E11.0) for float fields: a number without a
decimal point is an integer, not a number with implied decimal digits,
space characters within a number are ignored, and an exponent may follow
the digits without a decimal point. Both parsers must read such fields
with these values, which the lossless writing options rely on when they
write a number as an integer (e.g. ``218588031``).
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy

CU63 = Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf"

# field (11 columns) -> value as read with the edit descriptor F11.0
FIELDS = [
    ("  218588031", 218588031.0),
    ("12345678901", 12345678901.0),
    ("         62", 62.0),
    ("-1234567890", -1234567890.0),
    ("      +1234", 1234.0),
    ("1234       ", 1234.0),
    ("  0001234  ", 1234.0),
    ("  12 34    ", 1234.0),
    ("  1234-2   ", 12.34),
    ("  1234+5   ", 123400000.0),
    ("    1234E-2", 12.34),
    ("          0", 0.0),
]


def _lines_with_awr_field(field):
    """The lines of Cu-63 with the AWR field (columns 12-22) of the HEAD
    record of MF3/MT1 replaced by ``field``."""
    lines = CU63.read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l[70:72] == " 3" and l[72:75] == "  1")
    lines[i] = lines[i][:11] + field + lines[i][22:]
    return lines


@pytest.mark.parametrize("parser_cls", [EndfParserPy, EndfParserCpp])
@pytest.mark.parametrize("field, expected", FIELDS)
def test_float_field_without_decimal_point(parser_cls, field, expected):
    assert len(field) == 11
    if parser_cls is EndfParserCpp:
        pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    lines = _lines_with_awr_field(field)
    endf_dict = parser_cls().parse(lines, include=[(3, 1)])
    value = endf_dict[3][1]["AWR"]
    assert isinstance(value, float)
    assert value == expected


@pytest.mark.parametrize("value", [218588031.0, 26229.0, 12345678901.0])
def test_integer_form_round_trip(value):
    """A float written as an integer with the lossless options is read back
    as the same value by both parsers."""
    pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    opts = dict(
        prefer_noexp=True,
        abuse_signpos=True,
        skip_intzero=True,
        standard_form_on_tie=True,
    )
    endf_dict = EndfParserPy().parse(CU63.read_text().splitlines(), include=[(3, 1)])
    endf_dict[3][1]["AWR"] = value
    for writer_cls in (EndfParserPy, EndfParserCpp):
        lines = writer_cls(**opts).write(endf_dict)
        for reader_cls in (EndfParserPy, EndfParserCpp):
            back = reader_cls().parse(lines, include=[(3, 1)])
            assert back[3][1]["AWR"] == value
