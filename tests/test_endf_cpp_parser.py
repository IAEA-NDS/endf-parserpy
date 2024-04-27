import pytest
from endf_parserpy.interpreter.endf_parser import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.cpp_parsers.endf6_ext import parse_endf_file


@pytest.fixture(scope="module")
def myEndfParser():
    return EndfParser(endf_format="endf6-ext")


def test_python_and_cpp_parser_equivalent(endf_file, myEndfParser):
    endf_dict1 = myEndfParser.parsefile(endf_file)
    endf_dict2 = parse_endf_file(str(endf_file))
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)
