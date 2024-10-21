from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.user_tools import list_parsed_sections


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


# TODO from here

from endf_parserpy import EndfDict, EndfParser


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


def test_endf_parser_endf_float_is_working(mf3_section):
    pyparser = EndfParser(ignore_missing_tpid=True)
    parser = EndfParserCpp(ignore_missing_tpid=True)
    # mf3_section[3][1]['ZA'] = EndfFloat(0.1234567895, ".12345695  ")
    # mf3_section[3][1]['xstable']['E'][0] = EndfFloat(4.57, "4.57       ")
    cont = parser.write(mf3_section)
    print("#### ATTEMPTING PARSING ####")
    dict2 = parser.parse(cont)
    # new_mf3sec = parser.parse(cont)
    # parser.parse(cont)
    # endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    # endf_dict = parser.parsefile(endf_file, include=[1])
    # endf_dict[1][451]['AWR'] = EndfFloat(100, "  100.     ")
    # cont_out = parser.write(endf_dict)
    # endf_dict2 = parser.parse(cont_out)
