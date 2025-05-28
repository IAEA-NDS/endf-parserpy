import pytest
from endf_parserpy import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects


def create_mf1_test_section(mt, inconsistent=False):
    ctrl_record = "1234 1" + str(mt).rjust(3)
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
def mf1_mt_test_section(request):
    mt = request.param
    return create_mf1_test_section(mt, inconsistent=False)


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


def mf1_test_section_assertions(endf_dict, mt):
    assert endf_dict[1][mt]["A"][1] == 9
    assert endf_dict[1][mt]["A"][2] == 2
    assert endf_dict[1][mt]["B"][1] == 2
    assert endf_dict[1][mt]["B"][2] == 4
    assert endf_dict[1][mt]["C"][1] == 5
    assert endf_dict[1][mt]["C"][2] == 6


def test_nested_indices_in_record_fields(mf1_mt1_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt1_test_section)
    mf1_test_section_assertions(endf_dict, mt=1)


def test_nested_indices_in_if_head(mf1_mt2_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt2_test_section)
    mf1_test_section_assertions(endf_dict, mt=2)


def test_nested_indices_in_for_head(mf1_mt3_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt3_test_section)
    mf1_test_section_assertions(endf_dict, mt=3)


@pytest.mark.parametrize("mf1_mt_test_section", [1, 2, 3], indirect=True)
def test_endf_roundtrip(mf1_mt_test_section, endf_parser):
    endf_dict = endf_parser.parse(mf1_mt_test_section)
    sec_out = endf_parser.write(endf_dict)
    endf_dict2 = endf_parser.parse(sec_out)
    compare_objects(endf_dict, endf_dict2)
