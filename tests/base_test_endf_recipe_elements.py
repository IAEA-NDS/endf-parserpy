import pytest
from endf_parserpy import EndfParser


def create_mf1_test_section(mt, inconsistent=False):
    ctrl_record = "1234 1  1"
    head_record = (
        (
            "0.0".rjust(11)
            + "0.0".rjust(11)
            + "9".rjust(11)
            + "2".rjust(11)
            + "2".rjust(11)
            + "4".rjust(11)
        )
        + ctrl_record
        + "\n"
    )
    cont_record1 = (
        (
            "0.0".rjust(11)
            + "0.0".rjust(11)
            + "5".rjust(11)
            + "6".rjust(11)
            + "0".rjust(11)
            + "0".rjust(11)
        )
        + ctrl_record
        + "\n"
    )
    cont_record2 = (
        (
            "0.0".rjust(11)
            + "0.0".rjust(11)
            + "2".rjust(11)
            + ("6" if not inconsistent else "7").rjust(11)
            + "0".rjust(11)
            + "0".rjust(11)
        )
        + ctrl_record
        + "\n"
    )
    send_record = "".join(["0".rjust(11)] * 6) + "1234 1  0"
    endf_sec = head_record + cont_record1 + cont_record2 + send_record
    return endf_sec


@pytest.fixture(scope="function")
def mf1_mt1_test_section():
    return create_mf1_test_section(mt=1, inconsistent=False)


@pytest.fixture(scope="function")
def inconsistent_mf1_mt1_test_section():
    return create_mf1_test_section(mt=1, inconsistent=True)


@pytest.fixture(scope="function")
def mf1_mt2_test_section():
    return create_mf1_test_section(mt=2, inconsistent=False)


@pytest.fixture(scope="function")
def mf1_mt3_test_section():
    return create_mf1_test_section(mt=3, inconsistent=False)


def mf1_test_section_assertions(endf_dict):
    assert endf_dict[1][1]["A"][1] == 9
    assert endf_dict[1][1]["A"][2] == 2
    assert endf_dict[1][1]["B"][1] == 2
    assert endf_dict[1][1]["B"][2] == 4
    assert endf_dict[1][1]["C"][1] == 5
    assert endf_dict[1][1]["C"][2] == 6


def test_nested_indices_in_record_fields(mf1_mt1_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt1_test_section)
    mf1_test_section_assertions(endf_dict)


def test_nested_indices_in_if_head(mf1_mt2_test_section, endf_parser):
    parser = EndfParser(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )
    endf_dict = parser.parse(mf1_mt2_test_section)
    mf1_test_section_assertions(endf_dict)


def test_nested_indices_in_for_head(mf1_mt3_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt3_test_section)
    mf1_test_section_assertions(endf_dict)
