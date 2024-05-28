import pytest
import os
from endf_parserpy.interpreter.endf_parser import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.cpp_parsers.endf6_ext import parse_endf_file, write_endf_file


@pytest.fixture(scope="module")
def myEndfParser(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    accept_spaces,
):
    return EndfParser(
        ignore_zero_mismatch=ignore_zero_mismatch,
        ignore_number_mismatch=ignore_number_mismatch,
        ignore_varspec_mismatch=ignore_varspec_mismatch,
        accept_spaces=accept_spaces,
    )


@pytest.fixture(scope="module")
def cpp_parse_opts(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    accept_spaces,
):
    parse_opts = {
        "ignore_zero_mismatch": ignore_zero_mismatch,
        "ignore_number_mismatch": ignore_number_mismatch,
        "ignore_varspec_mismatch": ignore_varspec_mismatch,
        "accept_spaces": accept_spaces,
    }
    return parse_opts


def test_python_and_cpp_parser_equivalent(endf_file, myEndfParser, cpp_parse_opts):
    endf_dict1 = myEndfParser.parsefile(endf_file)
    endf_dict2 = parse_endf_file(str(endf_file), parse_opts=cpp_parse_opts)
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_endf_cpp_read_write_read_roundtrip(endf_file, tmp_path, cpp_parse_opts):
    endf_dict1 = parse_endf_file(str(endf_file), parse_opts=cpp_parse_opts)
    outfile = tmp_path / os.path.basename(endf_file)
    write_endf_file(str(outfile), endf_dict1)
    endf_dict2 = parse_endf_file(str(endf_file), parse_opts=cpp_parse_opts)
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_exclude_argument(endf_file, myEndfParser, cpp_parse_opts):
    exclude = [0, 6, (3, 2)]
    endf_dict1 = myEndfParser.parsefile(endf_file, exclude=exclude)
    endf_dict2 = parse_endf_file(
        str(endf_file), exclude=exclude, parse_opts=cpp_parse_opts
    )
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_include_argument(endf_file, myEndfParser, cpp_parse_opts):
    include = [0, 6, (3, 2)]
    endf_dict1 = myEndfParser.parsefile(endf_file, include=include)
    endf_dict2 = parse_endf_file(
        str(endf_file), include=include, parse_opts=cpp_parse_opts
    )
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)


def test_cpp_parser_include_exclude_argument_mixed(
    endf_file, myEndfParser, cpp_parse_opts
):
    include = (0, 6, (3, 2))
    exclude = (4,)
    endf_dict1 = myEndfParser.parsefile(endf_file, exclude=exclude, include=include)
    endf_dict2 = parse_endf_file(
        str(endf_file), exclude=exclude, include=include, parse_opts=cpp_parse_opts
    )
    compare_objects(endf_dict1, endf_dict2, atol=1e-10, rtol=1e-10)
