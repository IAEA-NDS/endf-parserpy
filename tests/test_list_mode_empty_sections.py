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

"""Empty subsections with array_type="list" in EndfParserPy.

EndfParserPy builds index-keyed dicts while parsing and converts the dicts
whose keys are all integers to lists afterwards. An empty dict, e.g. the
subsection `discrete` of a decay spectrum without discrete lines (NER=0),
was taken for an array and failed with `ValueError: min() arg is an empty
sequence` (24 of the 3821 decay files of ENDF/B-VIII.0). Empty subsections
stay empty dicts, as with EndfParserCpp.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.helpers import array_dict_to_list
from endf_parserpy.utils.math_utils import EndfFloat


# ENDF/B-VIII.0 decay data of Pu-244; spectra 3 and 4 of MF8/MT457 have no
# discrete lines
TESTFILE = str(Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf")


def _norm(x):
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_norm(v) for v in x]
    if isinstance(x, (float, EndfFloat)):
        return float(x).hex()
    return x


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.fixture(scope="module")
def parsed_list():
    return EndfParserPy(array_type="list", print_cache_info=False).parsefile(TESTFILE)


def test_parse_in_list_mode(parsed_list):
    spectra = parsed_list[8][457]["spectrum"]
    assert isinstance(spectra, list)
    empty = [sp["discrete"] for sp in spectra if sp["NER"] == 0]
    assert empty and all(d == {} for d in empty)


def test_same_result_as_cpp_parser(parsed_list):
    cpp = EndfParserCpp(array_type="list").parsefile(TESTFILE)
    assert _norm(parsed_list) == _norm(cpp)


def test_written_output_independent_of_array_type(parsed_list):
    parser_dict = EndfParserPy(print_cache_info=False)
    parser_list = EndfParserPy(array_type="list", print_cache_info=False)
    written_dict = _lines(parser_dict.write(parser_dict.parsefile(TESTFILE)))
    written_list = _lines(parser_list.write(parsed_list))
    assert written_list == written_dict


def test_array_dict_to_list_keeps_empty_dicts():
    d = {
        "arr": {1: 1.0, 2: 2.0},
        "sec": {},
        "nested": {3: {"sub": {}}, 4: {"sub": {1: 5}}},
    }
    array_dict_to_list(d)
    assert d == {"arr": [1.0, 2.0], "sec": {}, "nested": [{"sub": {}}, {"sub": [5]}]}
