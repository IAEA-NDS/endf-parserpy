import pytest
from endf_parserpy.interpreter.endf_parser import EndfParserPy
from endf_parserpy.interpreter.helpers import array_dict_to_list
from endf_parserpy.utils.accessories import EndfDict
from endf_parserpy.interpreter.custom_exceptions import (
    InvalidIntegerError,
    VariableNotFoundError,
    UnavailableIndexError,
    BlankLineError,
    UnexpectedEndOfInputError,
    UnexpectedControlRecordError,
)
from endf_parserpy.utils.debugging_utils import compare_objects
from copy import deepcopy


@pytest.fixture(scope="function")
def mf1_mt451_section():
    d = EndfDict()
    d["1/451"] = {}
    dd = d["1/451"]
    dd["MAT"] = 2625
    dd["MF"] = 1
    dd["MT"] = 451
    dd["ZA"] = 26054
    dd["AWR"] = 53.47
    dd["LRP"] = 0
    dd["LFI"] = 0
    dd["NLIB"] = 0
    dd["NMOD"] = 0
    dd["ELIS"] = 0.0
    dd["STA"] = 0
    dd["LIS"] = 0
    dd["LISO"] = 0
    dd["NFOR"] = 6
    dd["AWI"] = 0
    dd["EMAX"] = 200
    dd["LREL"] = 2
    dd["NSUB"] = 10
    dd["NVER"] = 7
    dd["TEMP"] = 0.0
    dd["LDRV"] = 0
    dd["NWD"] = 10
    dd["NXC"] = 0
    dd["ZSYMAM"] = " 26-Fe- 54 "
    dd["ALAB"] = "IAEA".ljust(11)
    dd["EDATE"] = "EVAL-JUL23"
    dd["AUTH"] = "John Doe".ljust(33)
    dd["REF"] = "Unpbulished".ljust(21)
    dd["DDATE"] = "DIST-OCT23"
    dd["RDATE"] = "REV2-JAN24"
    dd["ENDATE"] = "20240315"
    dd["HSUB"] = {1: " " * 66, 2: " " * 66, 3: " " * 66}
    dd["DESCRIPTION"] = {}
    descr = dd["DESCRIPTION"]
    descr[1] = "dummy extra info"
    descr[2] = "dummy extra info"
    descr[3] = "dummy extra info"
    descr[4] = "This is my awesome evaluation"
    descr[5] = "Feedback is welcome!"
    return d


@pytest.fixture(scope="function")
def mf3_section():
    d = EndfDict()
    d["3/1"] = {}
    dd = d["3/1"]
    dd["MAT"] = 2625
    dd["MF"] = 3
    dd["MT"] = 1
    dd["ZA"] = 26054
    dd["AWR"] = 53.47
    dd["QM"] = 0.0
    dd["QI"] = 0.0
    dd["LR"] = 0
    dd["xstable/E"] = [0, 5, 10, 15, 20]
    dd["xstable/xs"] = [14, 19, 22, 31, 12]
    dd["xstable/NBT"] = [len(dd["xstable/E"])]
    dd["xstable/INT"] = [2]
    return d


def test_creation_of_mf3_in_dict_mode(mf3_section):
    parser = EndfParserPy()
    parser.write(mf3_section)


def test_creation_of_mf3_in_list_mode(mf3_section):
    parser = EndfParserPy(array_type="list")
    sec = deepcopy(mf3_section)
    array_dict_to_list(sec[3][1])
    parser.write(sec)


def test_creation_of_mf3_in_list_and_dict_mode_equivalent(mf3_section):
    parser1 = EndfParserPy(array_type="dict")
    parser2 = EndfParserPy(array_type="list")
    sec1 = mf3_section
    sec2 = deepcopy(mf3_section)
    array_dict_to_list(sec2[3][1])
    res1 = parser1.write(sec1)
    res2 = parser2.write(sec2)
    assert res1 == res2


def test_linenum_wraparound(mf3_section):
    parser = EndfParserPy()
    endf_dict = deepcopy(mf3_section)
    linenum_width = 5
    linenum_max = 10**linenum_width - 1
    numels = linenum_max * 3
    dd = endf_dict["3/1"]
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


def test_creation_of_mf1_mt451_in_dict_mode(mf1_mt451_section):
    parser = EndfParserPy()
    parser.write(mf1_mt451_section)


def test_creation_of_mf1_mt451_in_list_mode(mf1_mt451_section):
    parser = EndfParserPy(array_type="list")
    sec = deepcopy(mf1_mt451_section)
    array_dict_to_list(sec[1][451])
    parser.write(sec)


def test_creation_of_mf1_mt451_in_list_and_dict_mode_equivalent(mf1_mt451_section):
    parser1 = EndfParserPy(array_type="dict")
    parser2 = EndfParserPy(array_type="list")
    sec1 = mf1_mt451_section
    sec2 = deepcopy(mf1_mt451_section)
    array_dict_to_list(sec2[1][451])
    res1 = parser1.write(sec1)
    res2 = parser2.write(sec2)
    assert res1 == res2


def test_creation_of_mf3_without_strict_datatypes(mf3_section):
    parser = EndfParserPy(strict_datatypes=False)
    mf3_section["3/1/LR"] = 0.0
    parser.write(mf3_section)
    mf3_section["3/1/LR"] = 0.5
    with pytest.raises(InvalidIntegerError):
        parser.write(mf3_section)


def test_creation_of_mf3_with_strict_datatypes(mf3_section):
    parser = EndfParserPy(strict_datatypes=True)
    mf3_section["3/1/LR"] = 0
    parser.write(mf3_section)
    mf3_section["3/1/LR"] = 0.0
    with pytest.raises(InvalidIntegerError):
        parser.write(mf3_section)


def test_creation_of_mf1_mt451_with_check_arrays(mf1_mt451_section):
    d = mf1_mt451_section
    parser = EndfParserPy(check_arrays=True)
    parser.write(d)
    d["1/451/DESCRIPTION/50"] = "should not be here according to NWD"
    d["1/451/IgnoredVar1"] = 23
    d["1/451/IgnoredVar2"] = {1: "a", 2: "b"}
    with pytest.raises(IndexError):
        parser.write(d)


def test_creation_of_mf1_mt451_without_check_arrays(mf1_mt451_section):
    d = mf1_mt451_section
    parser = EndfParserPy(check_arrays=False)
    d["1/451/DESCRIPTION/50"] = "should not be here according to NWD"
    d["1/451/IgnoredVar1"] = 23
    d["1/451/IgnoredVar2"] = {1: "a", 2: "b"}
    parser.write(d)


def test_creation_of_mf1_mt451_with_dictionary(mf1_mt451_section):
    parser = EndfParserPy(check_arrays=False)
    d = mf1_mt451_section
    d["1/451/NXC"] = 1
    d["1/451/MFx[1]"] = 3
    d["1/451/MTx[1]"] = 1
    d["1/451/NCx[1]"] = 10
    d["1/451/MOD[1]"] = 0
    parser.write(d)


def test_creation_of_mf1_mt451_fails_if_variable_missing(mf1_mt451_section):
    parser = EndfParserPy(check_arrays=False)
    d = mf1_mt451_section
    del d["1/451/LRP"]
    with pytest.raises(VariableNotFoundError):
        parser.write(d)


def test_creation_of_mf1_mt451_fails_if_counter_larger_than_array_in_dict_mode(
    mf1_mt451_section,
):
    parser = EndfParserPy(check_arrays=False)
    d = mf1_mt451_section
    d["1/451/NWD"] = 5 + len(d["1/451/DESCRIPTION"]) + 1
    with pytest.raises(UnavailableIndexError):
        parser.write(d)


def test_creation_of_mf1_mt451_fails_if_counter_larger_than_array_in_list_mode(
    mf1_mt451_section,
):
    parser = EndfParserPy(check_arrays=False, array_type="list")
    d = mf1_mt451_section
    d["1/451/NWD"] = 5 + len(d["1/451/DESCRIPTION"]) + 1
    sec = deepcopy(mf1_mt451_section)
    array_dict_to_list(sec[1][451])
    with pytest.raises(UnavailableIndexError):
        parser.write(sec)


def test_creation_of_mf1_mt451_fails_if_counter_smaller_than_array_in_dict_mode(
    mf1_mt451_section,
):
    parser = EndfParserPy(check_arrays=True, array_type="dict")
    d = mf1_mt451_section
    d["1/451/NWD"] = 5 + len(d["1/451/DESCRIPTION"]) - 1
    with pytest.raises(IndexError):
        parser.write(d)


def test_creation_of_mf1_mt451_fails_if_counter_smaller_than_array_in_list_mode(
    mf1_mt451_section,
):
    parser = EndfParserPy(check_arrays=True, array_type="list")
    d = mf1_mt451_section
    d["1/451/NWD"] = 5 + len(d["1/451/DESCRIPTION"]) - 1
    sec = deepcopy(mf1_mt451_section)
    array_dict_to_list(sec[1][451])
    with pytest.raises(IndexError):
        parser.write(sec)


def test_ignore_blank_lines_option_does_not_impact_result(mf1_mt451_section):
    parser1 = EndfParserPy(ignore_missing_tpid=True, ignore_blank_lines=False)
    parser2 = EndfParserPy(ignore_missing_tpid=True, ignore_blank_lines=True)
    lines = parser1.write(mf1_mt451_section)
    result1 = parser1.parse(lines)
    lines.insert(0, "  ")
    lines.insert(4, "  ")
    result2 = parser2.parse(lines)
    compare_objects(result1, result2)


def test_blank_lines_cause_failure_if_not_ignored(mf1_mt451_section):
    parser = EndfParserPy(ignore_missing_tpid=True, ignore_blank_lines=False)
    lines = parser.write(mf1_mt451_section)
    lines.insert(3, "  ")
    with pytest.raises(BlankLineError):
        parser.parse(lines)


def test_missing_send_record_causes_failure_if_not_ignored(mf1_mt451_section):
    parser = EndfParserPy(ignore_missing_tpid=True, ignore_send_records=False)
    lines = parser.write(mf1_mt451_section)
    lines_list = [lines.copy() for i in range(3)]
    for i in range(0, 3):
        lines = lines_list[i]
        del lines[-(i + 1)]
        if i == 0:
            with pytest.raises(UnexpectedEndOfInputError):
                parser.parse(lines)
        if i in (1, 2):
            with pytest.raises(UnexpectedControlRecordError):
                parser.parse(lines)


def test_missing_send_record_option_does_not_impact_result(mf1_mt451_section):
    parser1 = EndfParserPy(ignore_missing_tpid=True, ignore_send_records=False)
    parser2 = EndfParserPy(ignore_missing_tpid=True, ignore_send_records=True)
    lines = parser1.write(mf1_mt451_section)
    result1 = parser1.parse(lines)
    lines_list = [lines.copy() for i in range(3)]
    for i in range(0, 3):
        lines = lines_list[i]
        del lines[-(i + 1)]
        result2 = parser2.parse(lines)
        compare_objects(result1, result2)


def test_ignore_missing_tpid_prevents_failure(mf1_mt451_section):
    if 0 in mf1_mt451_section:
        del mf1_mt451_section[0]
    parser = EndfParserPy(ignore_missing_tpid=True)
    lines = parser.write(mf1_mt451_section)
    parser.parse(lines)


def test_missing_tpid_does_not_impact_result(mf1_mt451_section):
    parser1 = EndfParserPy(ignore_missing_tpid=True)
    parser2 = EndfParserPy(ignore_missing_tpid=False)
    lines1 = parser1.write(mf1_mt451_section)
    mf1_mt451_section.setdefault(0, {})[0] = {
        "MAT": 1,
        "MF": 0,
        "MT": 0,
        "TAPEDESCR": "dummy taped hea description",
    }
    lines2 = parser1.write(mf1_mt451_section)
    result1 = parser1.parse(lines1)
    result2 = parser2.parse(lines2)
    del result2[0]
    compare_objects(result1, result2)
