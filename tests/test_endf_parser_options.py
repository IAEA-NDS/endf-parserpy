from pathlib import Path
from endf_parserpy.interpreter import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.user_tools import list_parsed_sections
from endf_parserpy.interpreter.custom_exceptions import UnexpectedControlRecordError


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


def test_preserve_value_strings_option():
    for flag in (True, False):
        parser = EndfParser(preserve_value_strings=flag)
        endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
        result1 = parser.parsefile(endf_file)
        result2 = parser.parse(parser.write(result1))
        compare_objects(result1, result2)


def test_write_include_linenum_false_option():
    parser = EndfParser(include_linenum=False)
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_file, exclude=[3])
    result = parser.write(endf_dict)
    assert all(len(r) == 75 for r in result)


def test_write_include_linenum_true_option():
    parser = EndfParser(include_linenum=True)
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
    parser = EndfParser(include_linenum=True)
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_file, exclude=[0, 15])
    result = parser.write(endf_dict)
    assert all(len(r) == 80 for r in result)
    assert result[0][75:80] == "0".rjust(5)
    assert result[1][75:80] == "1".rjust(5)
    assert all(
        r[75:80] == "99999" for r in result if int(r[70:72]) != 0 and int(r[72:75]) == 0
    )


def _test_ignore_send_records_false_option(ctrl_start, ctrl_len):
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    with open(endf_file, "r") as f:
        endf_lines = f.readlines()
    parser = EndfParser(ignore_send_records=False)
    # remove SEND
    endf_lines_mod = endf_lines.copy()
    for i in range(len(endf_lines)):
        line = endf_lines[i]
        ctrl = int(line[ctrl_start : ctrl_start + ctrl_len])
        if ctrl == 0 and i > 0:
            endf_lines_mod.pop(i)
            break
    failed = False
    try:
        parser.parse(endf_lines_mod)
    except UnexpectedControlRecordError:
        failed = True
    assert failed


def _test_ignore_send_records_true_option(ctrl_start, ctrl_len):
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    with open(endf_file, "r") as f:
        endf_lines = f.readlines()
    parser1 = EndfParser(ignore_send_records=False)
    parser2 = EndfParser(ignore_send_records=True)
    # remove SEND
    endf_lines_mod = endf_lines.copy()
    for i in range(len(endf_lines)):
        line = endf_lines[i]
        ctrl = int(line[ctrl_start : ctrl_start + ctrl_len])
        if ctrl == 0 and i > 0:
            endf_lines_mod.pop(i)
            break
    endf_dict1 = parser1.parse(endf_lines)
    endf_dict2 = parser2.parse(endf_lines_mod)
    compare_objects(endf_dict1, endf_dict2)


def test_ignore_send_records_false_option_with_missing_send_record():
    _test_ignore_send_records_false_option(72, 3)


def test_ignore_send_records_true_option_with_missing_send_record():
    _test_ignore_send_records_true_option(72, 3)


def test_ignore_send_records_false_option_with_missing_fend_record():
    _test_ignore_send_records_false_option(70, 2)


def test_ignore_send_records_true_option_with_missing_fend_record():
    _test_ignore_send_records_true_option(70, 2)


def test_ignore_send_records_false_option_with_missing_mend_record():
    _test_ignore_send_records_false_option(66, 4)


def test_ignore_send_records_true_option_with_missing_mend_record():
    _test_ignore_send_records_true_option(66, 4)
