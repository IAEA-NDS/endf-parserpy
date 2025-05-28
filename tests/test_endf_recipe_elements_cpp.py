import pytest
from endf_parserpy import EndfParserCpp
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError
from test_endf_recipe_elements import (
    mf1_mt1_test_section,
    inconsistent_mf1_mt1_test_section,
    mf1_mt1_test_section_assertions,
)


def test_nested_indices(mf1_mt1_test_section):
    parser = EndfParserCpp(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )
    endf_dict = parser.parse(mf1_mt1_test_section)
    mf1_mt1_test_section_assertions(endf_dict)


def test_nested_indices_with_inconsistent_assignment(inconsistent_mf1_mt1_test_section):
    parser = EndfParserCpp(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )
    with pytest.raises(RuntimeError):
        endf_dict = parser.parse(inconsistent_mf1_mt1_test_section)
