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

"""The data model of the tape structure and the forms of a material."""

import pickle

import pytest

from endf_parserpy import TapeStructure, section_label, to_dict_form, to_list_form
from endf_parserpy.endf_recipes import (
    get_recipe_dict,
    get_tape_structure,
    list_endf_flavors,
)
from endf_parserpy.interpreter.custom_exceptions import UnexpectedControlRecordError
from endf_parserpy.tape import TapeStructureError
from endf_parserpy.utils.tape_structure import (
    ENDF6,
    check_recipes,
    recipe_ends_with_send,
)

GENDF = {
    "mf_order": "free",
    "mt_order": "free",
    "repeat": True,
    "fend": False,
    "mf": {1: {"fend": True}},
    "section": {(1, 451): {"send": False}},
    "material_form": "list",
    "end_record_fill": "blank",
}

TPID = " " * 66 + "   1 0  0    0\n"


def test_endf6_is_the_default():
    assert TapeStructure.from_spec(None) is ENDF6
    assert TapeStructure.from_spec({}) == ENDF6
    assert ENDF6.is_endf6
    assert ENDF6.to_spec() == {}
    assert TapeStructure.from_spec(ENDF6) is ENDF6
    for mf, mt in ((1, 451), (3, 1), (40, 5)):
        assert ENDF6.send(mf, mt) and ENDF6.fend(mf)
        assert not ENDF6.repeat(mf, mt)
        assert ENDF6.mt_ascending(mf)
    assert ENDF6.mf_ascending
    assert ENDF6.material_form == "dict"
    assert ENDF6.end_record_fill == "zero"


def test_resolution_order():
    ts = TapeStructure.from_spec(GENDF)
    assert not ts.is_endf6
    # the section before the MF before the top level
    assert not ts.send(1, 451)
    assert ts.send(1, 452) and ts.send(3, 102)
    assert ts.fend(1) and not ts.fend(3)
    assert ts.repeat(3, 102) and ts.repeat(1, 451)
    assert not ts.mt_ascending(3) and not ts.mf_ascending
    ts = TapeStructure.from_spec(
        {
            "repeat": True,
            "mf": {3: {"repeat": False}},
            "section": {(3, 1): {"repeat": True}},
        }
    )
    assert ts.repeat(1, 451) and not ts.repeat(3, 2) and ts.repeat(3, 1)


def test_round_trip_of_the_spec_and_pickle():
    ts = TapeStructure.from_spec(GENDF)
    assert ts.to_spec() == GENDF
    assert TapeStructure.from_spec(ts.to_spec()) == ts
    copy = pickle.loads(pickle.dumps(ts))
    assert copy == ts and hash(copy) == hash(ts)
    assert not copy.send(1, 451)
    assert "TapeStructure.from_spec(" in repr(ts)


def test_cpp_options():
    flags, sections, mf_ascending, blank = TapeStructure.from_spec(GENDF).cpp_options()
    assert len(flags) == 100
    assert sections == ((1451, 4),)  # REPEAT, no SEND
    assert (mf_ascending, blank) == (False, True)
    flags, sections, mf_ascending, blank = ENDF6.cpp_options()
    assert set(flags) == {1 | 2 | 8} and sections == () and mf_ascending and not blank


@pytest.mark.parametrize(
    "spec, error, message",
    [
        ([], TypeError, "must be a dict"),
        ({"fends": True}, ValueError, "unknown rule 'fends' at the top level"),
        ({"send": 1}, ValueError, "'send' must be True or False, not 1"),
        ({"mt_order": "sorted"}, ValueError, '"ascending" or "free", not \'sorted\''),
        ({"mf": {3: {"mf_order": "free"}}}, ValueError, "can only be given globally"),
        ({"section": {(3, 1): {"fend": False}}}, ValueError, "globally and per MF"),
        ({"mf": {0: {}}}, ValueError, "MF number 0 is the tape head"),
        ({"mf": {100: {}}}, ValueError, "not between 1 and 99"),
        ({"section": {(3, 1000): {}}}, ValueError, "not between 1 and 999"),
        ({"section": {3: {}}}, TypeError, "tuple (MF, MT) of two ints"),
        ({"mf": {3: []}}, TypeError, "must be a dict"),
    ],
)
def test_validation(spec, error, message):
    with pytest.raises(error) as exc:
        TapeStructure.from_spec(spec)
    assert message in str(exc.value)


def test_dict_form_allowed_with_repeats():
    # the public form is the default of the parsers; "dict" may be chosen
    # for any structure (the conversion raises only at an actual repeat)
    ts = TapeStructure.from_spec(dict(GENDF, material_form="dict"))
    assert ts.material_form == "dict"


def _material():
    return {
        0: {0: [TPID]},
        1: {451: {"MAT": 125, "MF": 1, "MT": 451}},
        3: {2: {"MAT": 125}, 1: [" " * 66 + " 125 3  1    1\n"]},
    }


def test_list_and_dict_forms():
    material = _material()
    sections = to_list_form(material)
    assert [section_label(s) for s in sections] == [
        (1, 0, 0),
        (125, 1, 451),
        (125, 3, 1),
        (125, 3, 2),
    ]
    # only references are moved; missing MF/MT keys are filled in
    assert sections[3] is material[3][2] and sections[3]["MT"] == 2
    assert to_dict_form(sections) == material
    assert to_list_form(sections) is sections
    assert to_dict_form(material) is material


def test_to_list_form_checks_the_keys():
    with pytest.raises(
        UnexpectedControlRecordError, match="expected MF=3 but found MF=4"
    ):
        to_list_form({3: {1: {"MAT": 1, "MF": 4, "MT": 1}}})
    with pytest.raises(
        UnexpectedControlRecordError, match="expected MT=1 but found MT=2"
    ):
        to_list_form({3: {1: {"MAT": 1, "MF": 3, "MT": 2}}})


def test_to_dict_form_repeated_label():
    sections = to_list_form(_material())
    sections.insert(3, {"MAT": 125, "MF": 3, "MT": 2})
    with pytest.raises(TapeStructureError) as exc:
        to_dict_form(sections)
    assert str(exc.value) == (
        "the material has 2 sections MF=3/MT=2 (at positions 3 and 4 of the "
        "list); the nested form {MF: {MT: section}} holds one section per "
        'MF/MT; use material_form="list"'
    )


def test_section_label_errors():
    with pytest.raises(TypeError, match="dict \\(parsed\\) or a list of strings"):
        section_label(3)
    with pytest.raises(ValueError, match="empty list"):
        section_label([])
    with pytest.raises(ValueError, match='invalid MF number field: " x"'):
        section_label([" " * 66 + " 125 x  1"])
    assert section_label([(" " * 66 + " 125 3  1").encode()]) == (125, 3, 1)
    assert section_label([" " * 66]) == (0, 0, 0)


def test_recipe_ends_with_send():
    assert recipe_ends_with_send("[MAT, 3, MT/ 0, 0, 0, 0, 0, 0] HEAD\nSEND\n# end\n")
    assert not recipe_ends_with_send("[MAT, 0, 0/ TAPEDESCR] TEXT\n")


@pytest.mark.parametrize(
    "flavor", ["endf6-ext", "endf6", "jendl", "pendf", "errorr", "test"]
)
def test_recipes_of_the_endf6_flavors_agree(flavor):
    check_recipes(get_recipe_dict(flavor), {})


def test_check_recipes_disagreement():
    with pytest.raises(ValueError) as exc:
        check_recipes(get_recipe_dict("endf6"), {"mf": {3: {"send": False}}})
    assert str(exc.value).startswith(
        "the recipe for MF=3 ends with a SEND record, but the tape structure has "
        "no SEND record after the sections of MF=3 (rule of MF=3)"
    )
    recipes = {3: {1: "[MAT, 3, MT/ 0, 0, 0, 0, 0, 0] HEAD\n"}}
    with pytest.raises(ValueError, match="does not end with a SEND record"):
        check_recipes(recipes, {})
    check_recipes(recipes, {"section": {(3, 1): {"send": False}}})


@pytest.mark.parametrize("flavor", list_endf_flavors())
def test_tape_structure_of_each_flavor_agrees_with_its_recipes(flavor):
    ts = get_tape_structure(flavor)
    assert isinstance(ts, TapeStructure)
    check_recipes(get_recipe_dict(flavor), ts)


def test_tape_structure_of_an_alias():
    assert get_tape_structure("endf6-ext@0.19") is get_tape_structure("endf6-ext")
    with pytest.raises(TypeError):
        get_tape_structure("no-such-flavor")
