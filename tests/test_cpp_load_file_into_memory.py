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

"""Tests for the `load_file_into_memory` option of EndfParserCpp.

By default, EndfParserCpp.parsefile reads the complete file into memory
and parses it from there; with load_file_into_memory=False, the file is
read through a file stream while it is parsed. Strings passed to parse
are parsed in place. All three ways must give the same result.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserFactory


TESTDATA = Path(__file__).parent / "testdata"
FILES = ["n_2925_29-Cu-63.endf", "tsl_Al.endf"]


@pytest.mark.parametrize("filename", FILES)
@pytest.mark.parametrize(
    "selection",
    [{}, {"exclude": (3,)}, {"include": ((1, 451), 4)}],
    ids=["all", "exclude", "include"],
)
def test_parse_results_independent_of_reading_mode(filename, selection):
    path = str(TESTDATA / filename)
    in_memory = EndfParserCpp().parsefile(path, **selection)
    streamed = EndfParserCpp(load_file_into_memory=False).parsefile(path, **selection)
    from_string = EndfParserCpp().parse(Path(path).read_text(), **selection)
    assert streamed == in_memory
    assert from_string == in_memory


def test_option_in_read_opts():
    assert EndfParserCpp().read_opts["load_file_into_memory"] is True
    parser = EndfParserCpp(load_file_into_memory=False)
    assert parser.read_opts["load_file_into_memory"] is False


def test_missing_file_raises_in_both_modes(tmp_path):
    missing = str(tmp_path / "missing.endf")
    for load in (True, False):
        with pytest.raises(Exception):
            EndfParserCpp(load_file_into_memory=load).parsefile(missing)


@pytest.mark.parametrize("load", [True, False])
def test_option_accepted_by_parser_factory(load):
    path = str(TESTDATA / "tsl_Al.endf")
    cpp_parser = EndfParserFactory.create(select="cpp", load_file_into_memory=load)
    py_parser = EndfParserFactory.create(
        select="python", load_file_into_memory=load, print_cache_info=False
    )
    assert isinstance(cpp_parser, EndfParserCpp)
    assert cpp_parser.read_opts["load_file_into_memory"] is load
    assert (
        py_parser.parsefile(path)[7][4]["AWR"]
        == cpp_parser.parsefile(path)[7][4]["AWR"]
    )
