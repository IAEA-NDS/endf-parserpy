############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Writing EndfFloat values: original strings are always used.

The option `preserve_value_strings` determines whether the original
string representations of float numbers are recorded during parsing (as
EndfFloat objects). When writing, both backends use the original string of
an EndfFloat value verbatim, irrespective of the option, as documented in
the guide on perfect precision control. Before, EndfParserCpp used the
strings only if the option was also set for writing.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.math_utils import EndfFloat


TESTFILE = str(Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf")
SECTIONS = ((1, 451), (3, 1), (3, 2))


def _parser(ParserCls, **kwargs):
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.fixture(scope="module")
def preserved_dict():
    # parse with recorded strings and give some values a non-canonical
    # string representation that differs from the default formatting
    parser = _parser(EndfParserPy, preserve_value_strings=True)
    d = parser.parsefile(TESTFILE, include=SECTIONS)
    d[1][451]["ZA"] = EndfFloat(29063.0, "29063".rjust(11))
    d[3][1]["xstable"]["xs"][0] = EndfFloat(1.5, "1.50000E+00")
    return d


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("preserve", [True, False], ids=["preserve", "no_preserve"])
def test_strings_written_irrespective_of_option(preserved_dict, ParserCls, preserve):
    parser = _parser(ParserCls, preserve_value_strings=preserve)
    lines = _lines(parser.write(preserved_dict, include=SECTIONS))
    reference = _lines(
        _parser(EndfParserPy, preserve_value_strings=True).write(
            preserved_dict, include=SECTIONS
        )
    )
    assert lines == reference
    assert any(line.startswith("29063".rjust(11)) for line in lines)
    assert any("1.50000E+00" in line for line in lines)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_verbatim_round_trip_with_default_writer(ParserCls):
    # strings recorded by one parser are reproduced by a writer created
    # with default options
    text = Path(TESTFILE).read_text().splitlines()
    reader = _parser(ParserCls, preserve_value_strings=True)
    d = reader.parse(text, include=SECTIONS)
    writer = _parser(ParserCls)
    assert _lines(writer.write(d, include=SECTIONS)) == _lines(
        reader.write(d, include=SECTIONS)
    )


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_custom_string_with_default_options(ParserCls):
    # example of the guide on perfect precision control
    parser = _parser(ParserCls)
    d = parser.parsefile(TESTFILE, include=((1, 451),))
    d[1][451]["ZA"] = EndfFloat(26056.0, "26056".rjust(11))
    lines = _lines(parser.write(d, include=((1, 451),)))
    assert lines[0].startswith("26056".rjust(11))


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("preserve", [True, False], ids=["preserve", "no_preserve"])
def test_string_of_wrong_length_rejected(ParserCls, preserve):
    parser = _parser(ParserCls, preserve_value_strings=preserve)
    d = parser.parsefile(TESTFILE, include=((1, 451),))
    d[1][451]["ZA"] = EndfFloat(29063.0, "29063")
    with pytest.raises(Exception):
        parser.write(d, include=((1, 451),))
