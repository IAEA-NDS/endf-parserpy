############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Original strings of float fields: blank fields and empty strings.

- A completely blank float field is read as zero. With
  `preserve_value_strings=True`, EndfParserCpp kept the blank string (an
  EndfFloat), so the field was written as it was read, whereas EndfParserPy
  returned a plain float and wrote ` 0.000000+0`. Both now keep the blank
  string.
- An EndfFloat with an empty original string has no original string: in
  EndfParserCpp, an empty string is the marker for values without one.
  EndfParserCpp formatted the number, EndfParserPy rejected the value. Both
  now format the number. Strings of other lengths than the field width are
  still rejected by both.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.math_utils import EndfFloat


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(ignore_missing_tpid=True, **kwargs)


def _mf3_section(qi=0.0):
    return {
        3: {
            1: {
                "MAT": 125,
                "MF": 3,
                "MT": 1,
                "ZA": 1001.0,
                "AWR": 0.9991673,
                "QM": 0.0,
                "QI": qi,
                "LR": 0,
                "xstable": {
                    "NBT": [2],
                    "INT": [2],
                    "E": [1.0, 2.0],
                    "xs": [3.0, 4.0],
                },
            }
        }
    }


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _text_with_blank_field():
    # MF3 section whose QI field (second field of the TAB1 header record)
    # is blank
    lines = _lines(EndfParserPy(print_cache_info=False).write(_mf3_section()))
    lines[1] = lines[1][:11] + " " * 11 + lines[1][22:]
    return "\n".join(lines), lines


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_blank_field_kept_with_preserve(ParserCls):
    text, lines = _text_with_blank_field()
    parser = _parser(ParserCls, preserve_value_strings=True)
    d = parser.parse(text)
    qi = d[3][1]["QI"]
    assert isinstance(qi, EndfFloat)
    assert float(qi) == 0.0
    assert qi.get_original_string() == " " * 11
    written = _lines(parser.write(d))
    assert written[1] == lines[1]


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_blank_field_is_float_without_preserve(ParserCls):
    text, _ = _text_with_blank_field()
    d = _parser(ParserCls).parse(text)
    qi = d[3][1]["QI"]
    assert type(qi) is float and qi == 0.0


def test_blank_field_same_in_both_parsers():
    text, _ = _text_with_blank_field()
    d_cpp = _parser(EndfParserCpp, preserve_value_strings=True).parse(text)
    d_py = _parser(EndfParserPy, preserve_value_strings=True).parse(text)
    qi_cpp, qi_py = d_cpp[3][1]["QI"], d_py[3][1]["QI"]
    assert list(vars(qi_cpp).items()) == list(vars(qi_py).items())


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_empty_string_written_as_number(ParserCls):
    parser = _parser(ParserCls)
    with_empty = _lines(parser.write(_mf3_section(qi=EndfFloat(2.5, ""))))
    with_float = _lines(parser.write(_mf3_section(qi=2.5)))
    assert with_empty == with_float


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_string_of_other_length_rejected(ParserCls):
    parser = _parser(ParserCls)
    with pytest.raises(Exception):
        parser.write(_mf3_section(qi=EndfFloat(2.5, "2.5")))
