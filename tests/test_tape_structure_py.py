############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Reading and writing with a tape structure other than that of ENDF-6.

The material is built from the decay file of Pu-244 (MF1/MT451,
MF1/MT452, MF8/MT457) with the recipes of ``endf6``; the structures free
the order, allow repeated sections, leave out FEND records or the SEND
record after MF1/MT451 (with a recipe of MF1/MT451 without SEND).
"""

import copy

import pytest

from endf_parserpy import EndfParserPy, section_label, to_dict_form
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.interpreter.custom_exceptions import UnexpectedControlRecordError
from endf_parserpy.tape import TapeStructureError
from test_section_order import PU, _blocks

FREE = {"mf_order": "free", "mt_order": "free", "repeat": True, "fend": False}
NO_SEND = {
    "fend": False,
    "mf": {1: {"fend": True}},
    "section": {(1, 451): {"send": False}},
}


def _text(*parts):
    b = _blocks()
    lines = [line for part in parts for line in b[part]]
    return "\n".join(line.decode("latin-1") for line in lines) + "\n"


def _labels(material):
    return [section_label(s)[1:] for s in material]


def _recipes_without_send_after_451():
    recipes = copy.deepcopy(get_recipe_dict("endf6"))
    text = recipes[1][451].rstrip()
    assert text.endswith("SEND")
    recipes[1][451] = text[: -len("SEND")]
    return recipes


def _no_send_parser(**kwargs):
    return EndfParserPy(
        recipes=_recipes_without_send_after_451(), tape_structure=NO_SEND, **kwargs
    )


def _no_send_text(*parts):
    # the section MF1/MT451 without its SEND record
    b = _blocks()
    b["451"] = b["451"][:-1]
    lines = [line for part in parts for line in b[part]]
    return "\n".join(line.decode("latin-1") for line in lines) + "\n"


def test_list_form_of_endf6():
    as_dict = EndfParserPy().parsefile(str(PU))
    as_list = EndfParserPy(material_form="list").parsefile(str(PU))
    assert isinstance(as_list, list)
    assert _labels(as_list) == [(0, 0), (1, 451), (1, 452), (8, 457)]
    assert to_dict_form(as_list) == as_dict


def test_invalid_material_form():
    with pytest.raises(ValueError, match="material_form must be"):
        EndfParserPy(material_form="nested")


def test_recipes_must_agree_with_the_tape_structure():
    with pytest.raises(ValueError, match="ends with a SEND record"):
        EndfParserPy(tape_structure=NO_SEND)


def test_free_order_and_repeats():
    text = _text("tpid", "457", "452", "451", "457", "mend", "tend")
    parser = EndfParserPy(tape_structure=FREE, material_form="list")
    material = parser.parse(text)
    assert _labels(material) == [(0, 0), (8, 457), (1, 452), (1, 451), (8, 457)]
    assert material[1] == material[4]
    # the nested form cannot hold the repeated section
    with pytest.raises(TapeStructureError, match="2 sections MF=8/MT=457"):
        EndfParserPy(tape_structure=FREE).parse(text)
    # verbatim sections in the same order
    material = parser.parse(text, exclude=[1, 8])
    assert _labels(material) == [(0, 0), (8, 457), (1, 452), (1, 451), (8, 457)]
    assert all(isinstance(s, list) for s in material[1:])


def test_free_order_without_repeats():
    text = _text("tpid", "457", "452", "451", "457", "mend", "tend")
    parser = EndfParserPy(tape_structure=dict(FREE, repeat=False))
    with pytest.raises(UnexpectedControlRecordError) as exc:
        parser.parse(text)
    assert str(exc.value).startswith(
        "The section MF=8/MT=457 of MAT=3564 occurs a second time in the "
        "material, which the tape structure does not allow, in control record "
        "of line "
    )


def test_fend_not_expected():
    parser = EndfParserPy(tape_structure=FREE)
    with pytest.raises(UnexpectedControlRecordError) as exc:
        parser.parse(_text("tpid", "451", "452", "fend1", "457", "mend", "tend"))
    assert str(exc.value).startswith(
        "Unexpected FEND record after MF=1 of MAT=3564: the tape structure has "
        "no FEND record after the sections of this MF, in control record of line "
    )


@pytest.mark.parametrize("filt", [{}, {"exclude": [1]}, {"include": [8]}])
def test_no_send_after_451(filt):
    text = _no_send_text("tpid", "451", "452", "fend1", "457", "mend", "tend")
    result = _no_send_parser().parse(text, **filt)
    expected = EndfParserPy().parsefile(str(PU), **filt)
    if "exclude" in filt:
        # the verbatim section has no SEND record, as in the file
        assert result[1][451] == expected[1][451]
    assert sorted(result) == sorted(expected)
    assert result == expected


def test_extra_send():
    text = _text("tpid", "451", "452", "fend1", "457", "mend", "tend")
    with pytest.raises(UnexpectedControlRecordError) as exc:
        _no_send_parser().parse(text)
    assert str(exc.value).startswith(
        "Unexpected SEND record after section MF=1/MT=451 of MAT=3564: the tape "
        "structure has no SEND record after this section, in control record of "
        "line "
    )


def test_missing_send_and_fend_give_the_rule():
    # a missing SEND record after MF1/MT451, a missing FEND record after MF1
    b = _blocks()
    b["451"] = b["451"][:-1]
    lines = [
        line for p in ("tpid", "451", "452", "457", "mend", "tend") for line in b[p]
    ]
    text = "\n".join(line.decode("latin-1") for line in lines) + "\n"
    with pytest.raises(UnexpectedControlRecordError) as exc:
        EndfParserPy(tape_structure=FREE).parse(text)
    assert str(exc.value).startswith(
        "Currently in MT=451 section but encountered MT=452 in control record of "
        "line "
    )
    assert str(exc.value).endswith(
        " The tape structure requires a SEND record after MF=1/MT=451."
    )
    nofend = _no_send_text("tpid", "451", "452", "457", "mend", "tend")
    with pytest.raises(UnexpectedControlRecordError) as exc:
        _no_send_parser().parse(nofend)
    assert str(exc.value).startswith(
        "Currently in MF=1 section but encountered MF=8 in control record of line"
    )
    assert str(exc.value).endswith(
        " The tape structure requires a FEND record after MF=1."
    )


def test_second_material_rejected():
    text = _text("tpid", "451", "452", "fend1", "457", "fend8", "mend")
    text += _text("451", "452", "fend1", "457", "fend8", "mend", "tend")
    with pytest.raises(UnexpectedControlRecordError) as exc:
        EndfParserPy().parse(text)
    assert str(exc.value).startswith(
        "No MF/MT section allowed after the MEND record: parse reads one "
        "material; use parse_tape for a tape of several materials"
    )
