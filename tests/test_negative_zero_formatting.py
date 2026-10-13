############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/13
# Last modified:   2026/10/13
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for writing negative zero.

Both writers write negative zero (-0.0) as zero. Before, EndfParserCpp
wrote ` -0.00000+0` (a leading space in addition to the minus sign, and
one digit less), and with `prefer_noexp=True` `-0`, whereas EndfParserPy
wrote `-0.000000+0` and `0`, respectively.
"""

import itertools
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


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("options", OPTION_COMBINATIONS, ids=_option_id)
def test_negative_zero_written_as_zero(ParserCls, options):
    parser = ParserCls(**options)
    lines_negzero = _lines(parser.write(_mf3_section([-0.0, 1.0])))
    lines_zero = _lines(parser.write(_mf3_section([0.0, 1.0])))
    assert lines_negzero == lines_zero


def _section_text_with_negative_zero():
    # MF3 section in which the second cross section value is -0.000000+0
    lines = _lines(EndfParserPy().write(_mf3_section([1.0, 0.5])))
    data_line = lines[3]
    assert data_line[33:44] == " 5.000000-1"
    lines[3] = data_line[:33] + "-0.000000+0" + data_line[44:]
    return "\n".join(lines)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_negative_zero_in_file_written_as_zero(ParserCls):
    parser = ParserCls(ignore_missing_tpid=True)
    endf_dict = parser.parse(_section_text_with_negative_zero())
    assert endf_dict[3][1]["xstable"]["xs"][1] == 0.0
    written = _lines(parser.write(endf_dict))
    assert written[3][33:44] == " 0.000000+0"


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_negative_zero_string_preserved(ParserCls):
    text = _section_text_with_negative_zero()
    parser = ParserCls(ignore_missing_tpid=True, preserve_value_strings=True)
    endf_dict = parser.parse(text)
    written = _lines(parser.write(endf_dict))
    assert written[3][33:44] == "-0.000000+0"
