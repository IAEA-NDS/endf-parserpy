# The functions of the generated C++ modules have working defaults for all
# arguments after the data: parse_endf and write_endf (as parse_endf_file and
# write_endf_file) can be called without options.
from pathlib import Path
import pytest

endf6 = pytest.importorskip("endf_parserpy.cpp_parsers.endf6")

TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"


def test_parse_endf_without_options():
    text = TESTFILE.read_text()
    result = endf6.parse_endf(text)
    assert result == endf6.parse_endf(text, None, None, {})
    assert result == endf6.parse_endf(text, parse_opts={})
    assert result == endf6.parse_endf_file(str(TESTFILE))


def test_write_endf_without_options(tmp_path):
    endf_dict = endf6.parse_endf_file(str(TESTFILE))
    output = endf6.write_endf(endf_dict)
    assert output == endf6.write_endf(endf_dict, None, None, {})
    assert output == endf6.write_endf(endf_dict, write_opts={})
    outfile = tmp_path / "out.endf"
    endf6.write_endf_file(str(outfile), endf_dict)
    assert outfile.read_text() == output
