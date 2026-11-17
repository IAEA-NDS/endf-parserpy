"""The functions that address the sections of a material (utils/sections.py)."""

from pathlib import Path

import pytest

from endf_parserpy import (
    EndfParserPy,
    AmbiguousSectionError,
    TapeStructureError,
    iter_sections,
    section_positions,
    locate_section,
    get_section,
    set_section,
    insert_section,
    remove_section,
)
from endf_parserpy.tape import AmbiguousSectionError as TapeAmbiguousSectionError
from endf_parserpy.utils.accessories import EndfDict, EndfList
from endf_parserpy.utils.sections import (
    insertion_position,
    is_section,
    is_section_list,
)

TESTDATA = Path(__file__).parent / "testdata"


def sec(mf, mt, mat=9543, **fields):
    return {"MAT": mat, "MF": mf, "MT": mt, **fields}


def raw(mf, mt, mat=9543, nlines=2):
    return [f"{'':66}{mat:4d}{mf:2d}{mt:3d}{i + 1:5d}" for i in range(nlines)]


def head():
    return {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "tape"}


def gendf_like():
    # the labels of the Am-241 nuclide production tape, IZAM tells the copies apart
    return [
        head(),
        sec(1, 451),
        sec(3, 102, IZAM=0),
        sec(3, 102, IZAM=952420),
        sec(3, 102, IZAM=952422),
    ]


def nested():
    return {0: {0: head()}, 1: {451: sec(1, 451)}, 3: {2: sec(3, 2), 1: sec(3, 1)}}


# -- the error class --------------------------------------------------------


def test_ambiguous_section_error_is_a_lookup_error_but_not_a_key_error():
    assert AmbiguousSectionError is TapeAmbiguousSectionError
    assert issubclass(AmbiguousSectionError, LookupError)
    assert not issubclass(AmbiguousSectionError, KeyError)


# -- iter_sections and section_positions --------------------------------------


def test_iter_sections_list_form_skips_the_head():
    m = gendf_like()
    entries = list(iter_sections(m))
    assert [(e.position, e.mf, e.mt, e.occurrence) for e in entries] == [
        (0, 1, 451, 0),
        (1, 3, 102, 0),
        (2, 3, 102, 1),
        (3, 3, 102, 2),
    ]
    assert entries[3].section is m[4]


def test_iter_sections_with_head():
    m = gendf_like()
    entries = list(iter_sections(m, head=True))
    assert (entries[0].position, entries[0].mf, entries[0].mt) == (None, 0, 0)
    assert entries[0].section is m[0]
    assert len(entries) == 5


def test_iter_sections_list_without_head():
    m = gendf_like()[1:]
    assert [e.position for e in iter_sections(m)] == [0, 1, 2, 3]
    assert [e.position for e in iter_sections(m, head=True)] == [0, 1, 2, 3]


def test_iter_sections_nested_form_canonical_order():
    m = nested()
    labels = [(e.position, e.mf, e.mt) for e in iter_sections(m)]
    assert labels == [(0, 1, 451), (1, 3, 1), (2, 3, 2)]
    assert [e.mf for e in iter_sections(m, head=True)] == [0, 1, 3, 3]


def test_iter_sections_unparsed_sections():
    m = [raw(0, 0, mat=1, nlines=1), raw(1, 451), raw(3, 102), raw(3, 102)]
    assert [(e.mf, e.mt, e.occurrence) for e in iter_sections(m)] == [
        (1, 451, 0),
        (3, 102, 0),
        (3, 102, 1),
    ]


def test_section_positions():
    m = gendf_like()
    assert section_positions(m, 3, 102) == [1, 2, 3]
    assert section_positions(m, 1, 451) == [0]
    assert section_positions(m, 3, 1) == []
    assert section_positions(nested(), 3, 2) == [2]


def test_wrapped_materials_are_accepted():
    m = gendf_like()
    assert get_section(EndfList(m), 3, 102, 1) is m[3]
    n = nested()
    assert get_section(EndfDict(n), 3, 2) is n[3][2]


def test_is_section_list():
    assert is_section_list(gendf_like())
    assert is_section_list([raw(1, 451)])
    assert not is_section_list([])
    assert not is_section_list([1.0, 2.0])
    assert not is_section_list([{"a": 1}])
    assert not is_section_list(["line"])
    assert not is_section_list([[1.0, 2.0]])
    assert is_section(sec(3, 1)) and not is_section({"MF": 3})


# -- get_section and locate_section -------------------------------------------


def test_get_section_by_label_occurrence_and_position():
    m = gendf_like()
    assert get_section(m, 1, 451) is m[1]
    assert get_section(m, 3, 102, 0)["IZAM"] == 0
    assert get_section(m, 3, 102, 2)["IZAM"] == 952422
    assert get_section(m, position=0) is m[1]
    assert get_section(m, position=3) is m[4]
    assert get_section(m, 0, 0) is m[0]
    assert locate_section(m, 3, 102, 1) == 2
    assert locate_section(m, position=3) == 3
    assert locate_section(m, 0, 0) is None


def test_get_section_ambiguous_label():
    m = gendf_like()
    with pytest.raises(AmbiguousSectionError) as excinfo:
        get_section(m, 3, 102)
    assert str(excinfo.value) == (
        "MF=3/MT=102 matches 3 sections at positions [1, 2, 3]; "
        "use 3/102#k to select one"
    )
    assert excinfo.value.mf == 3
    assert excinfo.value.mt == 102
    assert excinfo.value.positions == [1, 2, 3]


def test_get_section_out_of_range_and_missing():
    m = gendf_like()
    with pytest.raises(IndexError, match=r"^occurrence 3 out of range; "):
        get_section(m, 3, 102, 3)
    with pytest.raises(IndexError) as excinfo:
        get_section(m, position=4)
    assert str(excinfo.value) == (
        "section position 4 out of range; the material has 4 sections"
    )
    with pytest.raises(KeyError, match="no section MF=3/MT=1 in the material"):
        get_section(m, 3, 1)
    with pytest.raises(KeyError, match="MF=0/MT=0"):
        get_section(m[1:], 0, 0)


def test_get_section_nested_form():
    m = nested()
    assert get_section(m, 3, 1) is m[3][1]
    assert get_section(m, 3, 1, 0) is m[3][1]
    assert get_section(m, position=2) is m[3][2]
    assert get_section(m, 0, 0) is m[0][0]
    with pytest.raises(IndexError) as excinfo:
        get_section(m, 3, 1, 1)
    assert str(excinfo.value) == (
        "occurrence 1 out of range; MF=3/MT=1 matches 1 section"
    )


def test_selector_arguments_are_checked():
    m = gendf_like()
    with pytest.raises(TypeError):
        get_section(m, 3, 102, position=1)
    with pytest.raises(TypeError):
        get_section(m, 3)
    with pytest.raises(ValueError):
        get_section(m, 3, 102, -1)
    with pytest.raises(TypeError):
        get_section(m, "3", 102)
    with pytest.raises(TypeError):
        get_section(42, 3, 102)


# -- insertion ----------------------------------------------------------------


def test_insertion_position():
    m = [head(), sec(1, 451), sec(3, 1), sec(3, 102), sec(6, 18)]
    assert insertion_position(m, 3, 2) == 2
    assert insertion_position(m, 3, 102) == 3
    assert insertion_position(m, 4, 2) == 3
    assert insertion_position(m, 1, 1) == 0
    assert insertion_position(m, 99, 1) == 4


def test_insert_section_keeps_an_ascending_list_ascending():
    m = [head(), sec(1, 451), sec(3, 1), sec(6, 18)]
    assert insert_section(m, sec(3, 2)) == 2
    assert insert_section(m, sec(4, 2)) == 3
    assert insert_section(m, sec(1, 1)) == 0
    assert [(s["MF"], s["MT"]) for s in m] == [
        (0, 0),
        (1, 1),
        (1, 451),
        (3, 1),
        (3, 2),
        (4, 2),
        (6, 18),
    ]


def test_insert_section_adds_a_copy_after_the_copies():
    m = gendf_like()
    new = sec(3, 102, IZAM=952421)
    assert insert_section(m, new) == 4
    assert m[5] is new
    assert section_positions(m, 3, 102) == [1, 2, 3, 4]


def test_insert_section_free_order():
    # gaminr-like order: the rule only looks at the labels before it
    m = [head(), sec(1, 451), sec(23, 501), sec(26, 501), sec(23, 502)]
    assert insert_section(m, sec(23, 501)) == 2
    assert [(s["MF"], s["MT"]) for s in m[1:]] == [
        (1, 451),
        (23, 501),
        (23, 501),
        (26, 501),
        (23, 502),
    ]


def test_insert_section_at_a_position():
    m = gendf_like()
    s = sec(3, 18)
    assert insert_section(m, s, 0) == 0
    assert m[1] is s
    assert insert_section(m, sec(5, 18), 5) == 5
    with pytest.raises(IndexError):
        insert_section(m, sec(5, 18), 7)


def test_insert_section_without_head_and_into_an_empty_list():
    m = []
    assert insert_section(m, sec(3, 1)) == 0
    assert insert_section(m, head()) is None
    assert m[0]["MF"] == 0
    with pytest.raises(ValueError, match="already has a tape head"):
        insert_section(m, head())


def test_insert_section_nested_form():
    m = nested()
    assert insert_section(m, sec(2, 151)) == 1
    assert m[2][151]["MT"] == 151
    with pytest.raises(TapeStructureError, match="already has a section MF=3/MT=1"):
        insert_section(m, sec(3, 1))
    with pytest.raises(ValueError):
        insert_section(m, sec(4, 2), 0)


# -- set_section ----------------------------------------------------------------


def test_set_section_replaces_in_place():
    m = gendf_like()
    new = sec(1, 451, NZ=7)
    assert set_section(m, new) == 0
    assert m[1] is new and len(m) == 5
    copy = sec(3, 102, IZAM=1)
    assert set_section(m, copy, 1) == 2
    assert m[3] is copy


def test_set_section_ambiguous_and_out_of_range():
    m = gendf_like()
    with pytest.raises(AmbiguousSectionError):
        set_section(m, sec(3, 102))
    with pytest.raises(IndexError):
        set_section(m, sec(3, 102), 3)
    with pytest.raises(KeyError):
        set_section(m, sec(3, 1), 0)


def test_set_section_inserts_a_new_label():
    m = gendf_like()
    assert set_section(m, sec(2, 151)) == 1
    assert m[2]["MF"] == 2


def test_set_section_by_position():
    m = gendf_like()
    other = sec(3, 18)
    assert set_section(m, other, position=1) == 1
    assert m[2] is other
    with pytest.raises(IndexError):
        set_section(m, other, position=4)
    with pytest.raises(TypeError):
        set_section(m, other, 0, position=1)


def test_set_section_nested_form():
    m = nested()
    new = sec(3, 2, X=1)
    assert set_section(m, new) == 2
    assert m[3][2] is new
    assert set_section(m, sec(3, 2, X=2), position=2) == 2
    with pytest.raises(ValueError) as excinfo:
        set_section(m, sec(3, 1), position=2)
    assert str(excinfo.value) == (
        "in the nested form a section set by position keeps its label: "
        "position 2 holds MF=3/MT=2, the section has MF=3/MT=1"
    )
    assert set_section(m, sec(4, 2)) == 3


def test_set_section_head():
    m = gendf_like()
    h = head()
    assert set_section(m, h) is None
    assert m[0] is h
    m = m[1:]
    assert set_section(m, h) is None
    assert m[0] is h


def test_set_section_unparsed():
    m = [raw(0, 0, 1, 1), raw(1, 451), raw(3, 102), raw(3, 102)]
    new = raw(3, 102, nlines=3)
    assert set_section(m, new, 1) == 2
    assert m[3] is new


def test_parsed_section_without_label_is_an_error():
    with pytest.raises(KeyError, match="MF and MT"):
        set_section(gendf_like(), {"MAT": 1})


# -- remove_section ---------------------------------------------------------------


def test_remove_section():
    m = gendf_like()
    removed = remove_section(m, 3, 102, 1)
    assert removed["IZAM"] == 952420
    assert section_positions(m, 3, 102) == [1, 2]
    assert remove_section(m, position=0)["MT"] == 451
    with pytest.raises(AmbiguousSectionError):
        remove_section(m, 3, 102)
    assert remove_section(m, 0, 0)["MF"] == 0
    assert [e.position for e in iter_sections(m)] == [0, 1]


def test_remove_section_nested_form_keeps_an_empty_mf():
    m = nested()
    remove_section(m, 1, 451)
    assert m[1] == {}
    assert [(e.mf, e.mt) for e in iter_sections(m)] == [(3, 1), (3, 2)]


# -- a parsed gendf tape ----------------------------------------------------------


def test_parsed_gendf_nuclide_production():
    parser = EndfParserPy(endf_format="gendf")
    m = parser.parsefile(TESTDATA / "gendf" / "am241_nuclide_production.gendf")
    assert section_positions(m, 3, 102) == [1, 2, 3]
    izam = [get_section(m, 3, 102, k)["IZAM"] for k in range(3)]
    assert izam == [0, 952420, 952422]
    # the position k is the list element k + 1 (the tape head is element 0)
    for e in iter_sections(m):
        assert m[e.position + 1] is e.section
