from pathlib import Path
from endf_parserpy.interpreter import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.user_tools import list_parsed_sections


def test_parsefile_include_single_mf_option():
    parser = EndfParser()
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    result1 = parser.parsefile(endf_file, include=[3])
    result2 = parser.parsefile(endf_file, include=3)
    compare_objects(result1, result2)


def test_parsefile_exclude_single_mf_option():
    parser = EndfParser()
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    result1 = parser.parsefile(endf_file, exclude=[3])
    result2 = parser.parsefile(endf_file, exclude=3)
    compare_objects(result1, result2)


def test_parsefile_include_option_with_mf_mt():
    parser = EndfParser()
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    result1 = parser.parsefile(endf_file, include=[1, (3, 1), 6])
    result2 = parser.parsefile(endf_file, include=([3, 1], 1, 6))
    parsed_sections = list_parsed_sections(result1)
    assert all(p[0] in (1, 3, 6) for p in parsed_sections)
    assert all(p[1] == 1 for p in parsed_sections if p[0] == 3)
    compare_objects(result1, result2)


def test_parsefile_exclude_option_with_mf_mt():
    parser = EndfParser()
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    result1 = parser.parsefile(endf_file, exclude=[1, (3, 1), 6])
    result2 = parser.parsefile(endf_file, exclude=([3, 1], 1, 6))
    parsed_sections = list_parsed_sections(result1)
    assert not any(p[0] in (1, 6) for p in parsed_sections)
    assert not any(p[1] == 1 for p in parsed_sections if p[0] == 3)
    compare_objects(result1, result2)
