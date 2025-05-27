import pytest
from endf_parserpy import EndfParser
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError


def test_nested_indices():
    head_recdef = "[MAT,MF,MT/ A[1], A[2], B[1], B[2], C[1], C[2]] HEAD\n"
    cont_recdef = "[MAT,MF,MT/ B[A[1]-8], C[B[A[1]-8]+0], 0, 0, 0, 0] CONT\n"
    send_recdef = "SEND\n"
    recipe = head_recdef + cont_recdef + send_recdef
    recipes = {1: {23: recipe}}
    ctrl_record = "1234 123"
    head_record = (
        (
            "9".rjust(11)
            + "4".rjust(11)
            + "2".rjust(11)
            + "3".rjust(11)
            + "4".rjust(11)
            + "5".rjust(11)
        )
        + ctrl_record
        + "\n"
    )
    cont_record = (
        "2".rjust(11)
        + "5".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
    ) + ctrl_record
    endf_sec = head_record + cont_record
    parser = EndfParser(
        recipes=recipes, ignore_send_records=True, ignore_missing_tpid=True, loglevel=10
    )
    endf_dict = parser.parse(endf_sec)
    assert endf_dict[1][23]["A"][1] == 9
    assert endf_dict[1][23]["A"][2] == 4
    assert endf_dict[1][23]["B"][1] == 2
    assert endf_dict[1][23]["B"][2] == 3
    assert endf_dict[1][23]["C"][1] == 4
    assert endf_dict[1][23]["C"][2] == 5


def test_nested_indices_with_inconsistent_assignment():
    head_recdef = "[MAT,MF,MT/ A[1], A[2], B[1], B[2], C[1], C[2]] HEAD\n"
    cont_recdef = "[MAT,MF,MT/ B[A[1]-8], C[B[A[1]-8]+0], 0, 0, 0, 0] CONT\n"
    send_recdef = "SEND\n"
    recipe = head_recdef + cont_recdef + send_recdef
    recipes = {1: {23: recipe}}
    ctrl_record = "1234 123"
    head_record = (
        (
            "9".rjust(11)
            + "4".rjust(11)
            + "2".rjust(11)
            + "3".rjust(11)
            + "4".rjust(11)
            + "5".rjust(11)
        )
        + ctrl_record
        + "\n"
    )
    cont_record = (
        "2".rjust(11)
        + "7".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
        + "0".rjust(11)
    ) + ctrl_record
    endf_sec = head_record + cont_record
    parser = EndfParser(
        recipes=recipes, ignore_send_records=True, ignore_missing_tpid=True
    )
    with pytest.raises(NumberMismatchError):
        endf_dict = parser.parse(endf_sec)
