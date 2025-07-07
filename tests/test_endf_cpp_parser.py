import pytest
import os
import tempfile
from pathlib import Path
from endf_parserpy.interpreter.endf_parser import EndfParserPy
from endf_parserpy.cpp_parsers.endf_parser_cpp import EndfParserCpp
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.cpp_parsers.endf6_ext import parse_endf_file, write_endf_file
from endf_parserpy.utils.accessories import EndfDict


@pytest.fixture(scope="module")
def myEndfParserPy(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    accept_spaces,
    array_type,
    endf_format,
    prefer_noexp,
    skip_intzero,
    abuse_signpos,
    keep_E,
    preserve_value_strings,
):
    return EndfParserPy(
        ignore_zero_mismatch=ignore_zero_mismatch,
        ignore_number_mismatch=ignore_number_mismatch,
        ignore_varspec_mismatch=ignore_varspec_mismatch,
        accept_spaces=accept_spaces,
        array_type=array_type,
        endf_format=endf_format,
        prefer_noexp=prefer_noexp,
        skip_intzero=skip_intzero,
        abuse_signpos=abuse_signpos,
        keep_E=keep_E,
        preserve_value_strings=preserve_value_strings,
    )


@pytest.fixture(scope="module")
def myEndfParserCpp(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    accept_spaces,
    array_type,
    endf_format,
    prefer_noexp,
    skip_intzero,
    abuse_signpos,
    keep_E,
    preserve_value_strings,
):
    return EndfParserCpp(
        ignore_zero_mismatch=ignore_zero_mismatch,
        ignore_number_mismatch=ignore_number_mismatch,
        ignore_varspec_mismatch=ignore_varspec_mismatch,
        accept_spaces=accept_spaces,
        array_type=array_type,
        endf_format=endf_format,
        prefer_noexp=prefer_noexp,
        skip_intzero=skip_intzero,
        abuse_signpos=abuse_signpos,
        keep_E=keep_E,
        preserve_value_strings=preserve_value_strings,
    )


@pytest.fixture(scope="module")
def cpp_parse_opts(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    accept_spaces,
    array_type,
    prefer_noexp,
    skip_intzero,
    abuse_signpos,
    keep_E,
    preserve_value_strings,
):
    parse_opts = {
        "ignore_zero_mismatch": ignore_zero_mismatch,
        "ignore_number_mismatch": ignore_number_mismatch,
        "ignore_varspec_mismatch": ignore_varspec_mismatch,
        "accept_spaces": accept_spaces,
        "array_type": array_type,
        "preserve_value_strings": preserve_value_strings,
    }
    return parse_opts


@pytest.fixture(scope="module")
def cpp_write_opts(array_type):
    write_opts = {
        "array_type": array_type,
        "prefer_noexp": prefer_noexp,
        "skip_intzero": skip_intzero,
        "abuse_signpos": abuse_signpos,
        "keep_E": keep_E,
    }
    return write_opts


def test_python_and_cpp_parser_equivalent(
    endf_file, myEndfParserPy, myEndfParserCpp, mf_sel
):
    endf_dict1 = myEndfParserPy.parsefile(endf_file, include=mf_sel)
    endf_dict2 = myEndfParserCpp.parsefile(endf_file, include=mf_sel)
    compare_objects(endf_dict1, endf_dict2, atol=1e-12, rtol=1e-12)


def test_python_and_cpp_parser_write_equivalent(
    endf_file, myEndfParserPy, myEndfParserCpp, mf_sel
):
    endf_dict = myEndfParserCpp.parsefile(endf_file, mf_sel)
    endfout_py = myEndfParserPy.write(endf_dict)
    endfout_cpp = myEndfParserCpp.write(endf_dict)
    assert endfout_py == endfout_cpp


def test_python_and_cpp_parser_writefile_equivalent(
    endf_file, myEndfParserPy, myEndfParserCpp, mf_sel
):
    endf_dict = myEndfParserCpp.parsefile(endf_file, mf_sel)
    with tempfile.TemporaryDirectory() as tmpdirname:
        outfile_py = Path(tmpdirname) / "outfile_py.endf"
        outfile_cpp = Path(tmpdirname) / "outfile_cpp.endf"
        myEndfParserPy.writefile(outfile_py, endf_dict)
        myEndfParserCpp.writefile(outfile_cpp, endf_dict)
        with open(outfile_py, "r") as f:
            endftext_py = f.read()
        with open(outfile_cpp, "r") as f:
            endftext_cpp = f.read()
    assert endftext_py == endftext_cpp


def test_endf_cpp_read_write_read_roundtrip(
    endf_file, tmp_path, myEndfParserCpp, mf_sel
):
    endf_dict1 = myEndfParserCpp.parsefile(endf_file, include=mf_sel)
    outfile = tmp_path / os.path.basename(endf_file)
    myEndfParserCpp.writefile(outfile, endf_dict1)
    endf_dict2 = myEndfParserCpp.parsefile(outfile, include=mf_sel)
    compare_objects(endf_dict1, endf_dict2, atol=1e-12, rtol=1e-12)


def test_cpp_parser_exclude_argument(endf_file, myEndfParserPy, myEndfParserCpp):
    exclude = [0, 6, (3, 2)]
    endf_dict1 = myEndfParserPy.parsefile(endf_file, exclude=exclude)
    endf_dict2 = myEndfParserCpp.parsefile(endf_file, exclude=exclude)
    compare_objects(endf_dict1, endf_dict2, atol=1e-12, rtol=1e-12)


def test_cpp_parser_include_argument(endf_file, myEndfParserPy, myEndfParserCpp):
    include = [0, 6, (3, 2)]
    endf_dict1 = myEndfParserPy.parsefile(endf_file, include=include)
    endf_dict2 = myEndfParserCpp.parsefile(endf_file, include=include)
    compare_objects(endf_dict1, endf_dict2, atol=1e-12, rtol=1e-12)


def test_cpp_parser_include_exclude_argument_mixed(
    endf_file, myEndfParserPy, myEndfParserCpp
):
    include = (0, 6, (3, 2))
    exclude = (4,)
    endf_dict1 = myEndfParserPy.parsefile(endf_file, exclude=exclude, include=include)
    endf_dict2 = myEndfParserCpp.parsefile(endf_file, exclude=exclude, include=include)
    compare_objects(endf_dict1, endf_dict2, atol=1e-12, rtol=1e-12)


def test_linenum_wraparound():
    linenum_width = 5
    linenum_max = 10**linenum_width - 1
    numels = linenum_max * 3
    parser = EndfParserCpp()
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
