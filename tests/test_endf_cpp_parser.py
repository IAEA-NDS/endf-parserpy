import pytest
from endf_parserpy.interpreter.endf_parser import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.cpp_parsers.endf6_ext import parse_endf_file


@pytest.fixture(scope="module")
def myEndfParser():
    return EndfParser(
        endf_format="endf6-ext", ignore_zero_mismatch=True, ignore_varspec_mismatch=True
    )


def test_python_and_cpp_parser_equivalent(endf_file, myEndfParser):
    endf_dict1 = myEndfParser.parsefile(endf_file)
    endf_dict2 = parse_endf_file(str(endf_file))
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_exclude_argument(endf_file, myEndfParser):
    exclude = [0, 6, (3, 2)]
    endf_dict1 = myEndfParser.parsefile(endf_file, exclude=exclude)
    endf_dict2 = parse_endf_file(str(endf_file), exclude=exclude)
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_include_argument(endf_file, myEndfParser):
    include = [0, 6, (3, 2)]
    endf_dict1 = myEndfParser.parsefile(endf_file, include=include)
    endf_dict2 = parse_endf_file(str(endf_file), include=include)
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_include_exclude_argument_mixed(endf_file, myEndfParser):
    include = (0, 6, (3, 2))
    exclude = (4,)
    endf_dict1 = myEndfParser.parsefile(endf_file, exclude=exclude, include=include)
    endf_dict2 = parse_endf_file(str(endf_file), exclude=exclude, include=include)
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)
