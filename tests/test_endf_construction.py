import pytest
from endf_parserpy.endf_parser import EndfParser
from endf_parserpy.accessories import EndfDict
from endf_parserpy.custom_exceptions import (
    InvalidIntegerError,
    VariableNotFoundError,
    UnavailableIndexError,
)


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
    dd["NWD"] = 5
    dd["NXC"] = 0
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


def test_creation_of_mf3(mf3_section):
    parser = EndfParser()
    try:
        parser.write(mf3_section)
    except Exception:
        pytest.fail("Failed to generate a MF3 section from scratch")


def test_creation_of_mf1_mt451(mf1_mt451_section):
    parser = EndfParser()
    try:
        parser.write(mf1_mt451_section)
    except Exception:
        pytest.fail("Failed to generate a MF1/MT451 section from scratch")


def test_creation_of_mf3_without_strict_datatypes(mf3_section):
    parser = EndfParser(strict_datatypes=False)
    mf3_section["3/1/LR"] = 0.0
    parser.write(mf3_section)
    mf3_section["3/1/LR"] = 0.5
    try:
        parser.write(mf3_section)
        raise Exception("InvalidIntegerError was not raised")
    except InvalidIntegerError:
        pass


def test_creation_of_mf3_with_strict_datatypes(mf3_section):
    parser = EndfParser(strict_datatypes=True)
    mf3_section["3/1/LR"] = 0
    parser.write(mf3_section)
    mf3_section["3/1/LR"] = 0.0
    try:
        parser.write(mf3_section)
        raise Exception("InvalidIntegerError was not raised")
    except InvalidIntegerError:
        pass


def test_creation_of_mf1_mt451_with_check_arrays(mf1_mt451_section):
    d = mf1_mt451_section
    parser = EndfParser(check_arrays=True)
    parser.write(d)
    d["1/451/DESCRIPTION/50"] = "should not be here according to NWD"
    d["1/451/IgnoredVar1"] = 23
    d["1/451/IgnoredVar2"] = {1: "a", 2: "b"}
    try:
        parser.write(d)
        raise Exception("IndexError was not raised")
    except IndexError:
        pass


def test_creation_of_mf1_mt451_without_check_arrays(mf1_mt451_section):
    d = mf1_mt451_section
    parser = EndfParser(check_arrays=False)
    d["1/451/DESCRIPTION/50"] = "should not be here according to NWD"
    d["1/451/IgnoredVar1"] = 23
    d["1/451/IgnoredVar2"] = {1: "a", 2: "b"}
    parser.write(d)


def test_creation_of_mf1_mt451_with_dictionary(mf1_mt451_section):
    parser = EndfParser(check_arrays=False)
    d = mf1_mt451_section
    d["1/451/NXC"] = 1
    d["1/451/MFx[1]"] = 3
    d["1/451/MTx[1]"] = 1
    d["1/451/NCx[1]"] = 10
    d["1/451/MOD[1]"] = 0
    parser.write(d)


def test_creation_of_mf1_mt451_fails_if_variable_missing(mf1_mt451_section):
    parser = EndfParser(check_arrays=False)
    d = mf1_mt451_section
    del d["1/451/LRP"]
    try:
        parser.write(d)
    except VariableNotFoundError:
        pass


def test_creation_of_mf1_mt451_fails_if_counter_larger_than_array(mf1_mt451_section):
    parser = EndfParser(check_arrays=False)
    d = mf1_mt451_section
    d["1/451/NWD"] = len(d["1/451/DESCRIPTION"]) + 1
    try:
        parser.write(d)
    except UnavailableIndexError:
        pass


def test_creation_of_mf1_mt451_fails_if_counter_smaller_than_array(mf1_mt451_section):
    parser = EndfParser()
    d = mf1_mt451_section
    d["1/451/NWD"] = len(d["1/451/DESCRIPTION"]) - 1
    try:
        parser.write(d)
    except IndexError:
        pass
