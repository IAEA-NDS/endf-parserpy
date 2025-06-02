from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfDict
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.user_tools import list_parsed_sections
from endf_parserpy.utils.math_utils import EndfFloat
from endf_parserpy.utils.debugging_utils import compare_objects


@pytest.fixture(scope="function")
def mf3_section():
    d = EndfDict()
    d["3/1"] = {}
    dd = d["3/1"]
    dd["MAT"] = 2625
    dd["MF"] = 3
    dd["MT"] = 1
    dd["ZA"] = 26054.0
    dd["AWR"] = 53.47
    dd["QM"] = 0.0
    dd["QI"] = 0.0
    dd["LR"] = 0
    dd["xstable/E"] = [0.0, 5.0, 10.0, 15.0, 20.0]
    dd["xstable/xs"] = [14.0, 19.0, 22.0, 31.0, 12.0]
    dd["xstable/NBT"] = [len(dd["xstable/E"])]
    dd["xstable/INT"] = [2]
    return d.unwrap()


def test_write_include_linenum_false_option():
    parser = EndfParserCpp(include_linenum=False)
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_file, exclude=[3])
    result = parser.write(endf_dict)
    assert all(len(r) == 75 for r in result)


def test_write_include_linenum_true_option():
    parser = EndfParserCpp(include_linenum=True)
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_file, exclude=[3])
    result = parser.write(endf_dict)
    assert all(len(r) == 80 for r in result)
    assert result[0][75:80] == "0".rjust(5)
    assert result[1][75:80] == "1".rjust(5)
    assert all(
        r[75:80] == "99999" for r in result if int(r[70:72]) != 0 and int(r[72:75]) == 0
    )


def test_write_linenum_true_with_verbatim_tapehead():
    parser = EndfParserCpp(include_linenum=True)
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_file, exclude=[0, 15])
    result = parser.write(endf_dict)
    assert all(len(r) == 80 for r in result)
    assert result[0][75:80] == "0".rjust(5)
    assert result[1][75:80] == "1".rjust(5)
    assert all(
        r[75:80] == "99999" for r in result if int(r[70:72]) != 0 and int(r[72:75]) == 0
    )


def test_missing_tpid_option_true_with_missing_tpid():
    parser = EndfParserCpp(ignore_missing_tpid=True)
    endf_file = Path(__file__).parent.joinpath(
        "testdata", "malformed_endf", "jeff33_13-Al-27g_mf4_mt2.endf"
    )
    endf_dict = parser.parsefile(endf_file)


def test_missing_tpid_option_false_with_missing_tpid():
    parser = EndfParserCpp(ignore_missing_tpid=False)
    endf_file = Path(__file__).parent.joinpath(
        "testdata", "malformed_endf", "jeff33_13-Al-27g_mf4_mt2.endf"
    )
    with pytest.raises(Exception):
        endf_dict = parser.parsefile(endf_file)


def test_preserve_value_strings_option_false(mf3_section):
    parser = EndfParserCpp(ignore_missing_tpid=True, preserve_value_strings=False)
    mf3_section[3][1]["ZA"] = EndfFloat(0.1234567895, ".1234567895")
    mf3_section[3][1]["xstable"]["E"][0] = EndfFloat(0.1234567895, ".1234567895")
    cont = parser.write(mf3_section)
    endf_dict = parser.parse(cont)
    with pytest.raises(ValueError):
        compare_objects(mf3_section, endf_dict, rtol=1e-20, atol=1e-20)
    compare_objects(mf3_section, endf_dict, rtol=1e-6, atol=1e-6)
    assert type(endf_dict[3][1]["ZA"]) == float
    assert type(endf_dict[3][1]["xstable"]["E"][0]) == float


def test_preserve_value_strings_option_true(mf3_section):
    parser = EndfParserCpp(ignore_missing_tpid=True, preserve_value_strings=True)
    mf3_section[3][1]["ZA"] = EndfFloat(0.1234567895, ".1234567895")
    mf3_section[3][1]["xstable"]["E"][0] = EndfFloat(0.1234567895, ".1234567895")
    cont = parser.write(mf3_section)
    endf_dict = parser.parse(cont)
    compare_objects(mf3_section, endf_dict, rtol=1e-20, atol=1e-20)
    assert type(endf_dict[3][1]["ZA"]) == EndfFloat
    assert type(endf_dict[3][1]["xstable"]["E"][0]) == EndfFloat


def test_list_mode_writing(mf3_section):
    parser_py_dict = EndfParserPy(array_type="dict")
    parser_py = EndfParserPy(array_type="list")
    parser_cpp = EndfParserCpp(array_type="list")
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser_py.parsefile(endf_file)
    output_py = parser_py.write(endf_dict)
    output_cpp = parser_cpp.write(endf_dict)
    endf_dict1 = parser_py_dict.parse(output_py)
    endf_dict2 = parser_py_dict.parse(output_cpp)
    compare_objects(endf_dict1, endf_dict2)


def test_list_mode_reading():
    parser_py_dict = EndfParserPy(array_type="dict")
    parser_py = EndfParserPy(array_type="list")
    parser_cpp = EndfParserCpp(array_type="list")
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict1 = parser_py.parsefile(endf_file)
    endf_dict2 = parser_cpp.parsefile(endf_file)
    compare_objects(endf_dict1, endf_dict2)
