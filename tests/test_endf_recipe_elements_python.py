import pytest
from base_test_endf_recipe_elements import *
from endf_parserpy import EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError


@pytest.fixture(scope="function")
def endf_parser():
    return EndfParserPy(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )


def test_nested_indices_in_record_fields_with_inconsistent_assignment(
    inconsistent_mf1_mt1_test_section, endf_parser
):
    with pytest.raises(NumberMismatchError):
        endf_dict = endf_parser.parse(inconsistent_mf1_mt1_test_section)
