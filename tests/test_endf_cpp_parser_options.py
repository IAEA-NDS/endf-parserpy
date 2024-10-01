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
