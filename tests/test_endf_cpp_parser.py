import pytest
import os
from endf_parserpy.interpreter.endf_parser import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.cpp_parsers.endf6_ext import parse_endf_file, write_endf_file
from endf_parserpy.utils.accessories import EndfDict


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


def test_linenum_wraparound():
    linenum_width = 5
    linenum_max = 10**linenum_width - 1
    numels = linenum_max * 3
    parser = EndfParser()
    endf_dict = EndfDict()
    endf_dict["3/1"] = {}
    dd = endf_dict["3/1"]
    dd["MAT"] = 2625
    dd["MF"] = 3
    dd["MT"] = 1
    dd["ZA"] = 26054
    dd["AWR"] = 53.47
    dd["QM"] = 0.0
    dd["QI"] = 0.0
    dd["LR"] = 0
    dd["xstable/E"] = [i * 0.01 for i in range(numels)]
    dd["xstable/xs"] = [1.0 for i in range(numels)]
    dd["xstable/NBT"] = [numels]
    dd["xstable/INT"] = [2]
    lines = parser.write(endf_dict)
    lines = lines[:-4]  # remove FEND, MEND, TEND
    linenum_strs = [l.rstrip()[75:] for l in lines]
    assert all(len(l) == 5 for l in linenum_strs)
    linenums = [int(l) for l in linenum_strs]
    assert min(linenums) == 1
    assert max(linenums) == linenum_max
    assert len([lnum for lnum in linenums if lnum == 1]) > 1
    assert all(n == (m % linenum_max) + 1 for m, n in enumerate(linenums))
