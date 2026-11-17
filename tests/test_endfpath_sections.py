"""EndfPath with section selectors: MF/MT, MF/MT#k and #k on a material."""

from copy import deepcopy
from pathlib import Path

import pytest

from endf_parserpy import (
    EndfParserPy,
    EndfPath,
    AmbiguousSectionError,
    get_section,
    iter_sections,
)
from endf_parserpy.utils.accessories import EndfDict, EndfList, EndfVariable
from endf_parserpy.utils.sections import is_section_list

TESTDATA = Path(__file__).parent / "testdata"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"


def sec(mf, mt, mat=9543, **fields):
    return {"MAT": mat, "MF": mf, "MT": mt, **fields}


def raw(mf, mt, mat=9543, nlines=2):
    return [f"{'':66}{mat:4d}{mf:2d}{mt:3d}{i + 1:5d}" for i in range(nlines)]


def head():
    return {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "tape"}


def gendf_like():
    return [
        head(),
        sec(1, 451, NZ=1),
        sec(3, 102, IZAM=0, sigma=[1.0, 2.0]),
        sec(3, 102, IZAM=952420, sigma=[3.0, 4.0]),
        sec(3, 102, IZAM=952422, sigma=[5.0, 6.0]),
    ]


def nested():
    return {
        0: {0: head()},
        1: {451: sec(1, 451, NZ=1)},
        3: {1: sec(3, 1, xs={1: 0.5}), 2: sec(3, 2, xs={1: 0.25})},
    }


@pytest.fixture(scope="module")
def am241():
    return EndfParserPy(endf_format="gendf").parsefile(AM241)


# -- the grammar --------------------------------------------------------------


@pytest.mark.parametrize(
    "spec, elements",
    [
        ("3/102#0", "3/102#0"),
        (" 3 / 102#2 /IZAM", "3/102#2/IZAM"),
        ("#0", "#0"),
        ("#3/IZAM", "#3/IZAM"),
        ("#01/a", "#1/a"),
        ("3/102#1/xs/E[3]", "3/102#1/xs/E/3"),
        (("3", "102#1", "IZAM"), "3/102#1/IZAM"),
    ],
)
def test_valid_selectors(spec, elements):
    path = EndfPath(spec)
    assert str(path) == elements
    assert EndfPath(str(path)) == path


@pytest.mark.parametrize(
    "spec, message",
    [
        (
            "a/#1",
            "the section selector '#1' must be the first element of the path 'a/#1'",
        ),
        ("3/#1", "the section selector '#1' must be the first element"),
        ("#1/#2", "the section selector '#2' must be the first element"),
        ("3#1/102", "the occurrence '3#1' must follow the MF at the start of the path"),
        ("a/b/102#1", "the occurrence '102#1' must follow the MF"),
        ("#0/102#1", "the occurrence '102#1' must follow the MF"),
        ("3/102#", "invalid section selector '102#'"),
        ("3/102#-1", "invalid section selector '102#-1'"),
        ("3/102#a", "invalid section selector '102#a'"),
        ("3/102#1#2", "invalid section selector '102#1#2'"),
        ("#1#2", "invalid section selector '#1#2'"),
        ("##1", "invalid section selector '##1'"),
        ("3/102#1[0]", "invalid section selector '102#1\\[0\\]'"),
        ("#1[0]", "invalid section selector '#1\\[0\\]'"),
        ("3/*#1", "invalid section selector '\\*#1'"),
        ("#*", "invalid section selector '#\\*'"),
    ],
)
def test_invalid_selectors(spec, message):
    with pytest.raises(ValueError, match=message):
        EndfPath(spec)


def test_selector_message_wording():
    with pytest.raises(ValueError) as excinfo:
        EndfPath("3/102#a")
    assert str(excinfo.value) == (
        "invalid section selector '102#a'; expected MF/MT, MF/MT#k or #k with "
        "non-negative integers"
    )


def test_path_algebra_with_selectors():
    path = EndfPath("3/102#1/IZAM")
    assert len(path) == 3
    assert path[:2] == EndfPath("3/102#1")
    assert str(path[1]) == "102#1"
    assert [str(el) for el in path] == ["3", "102#1", "IZAM"]
    assert EndfPath("3") + "102#1" == EndfPath("3/102#1")
    assert str(EndfPath("#2") + "IZAM") == "#2/IZAM"
    assert str(EndfPath("3/102#1") + EndfPath("IZAM")) == "3/102#1/IZAM"
    with pytest.raises(ValueError, match="must be the first element"):
        EndfPath("a") + "#1"
    assert len(EndfPath("#2/AWR")) == 2


def test_sliced_path_reports_a_misplaced_occurrence_when_applied():
    rest = EndfPath("3/102#1/IZAM")[1:]
    with pytest.raises(ValueError, match="must follow the MF"):
        rest.get(gendf_like())


# -- the list form --------------------------------------------------------------


def test_get_by_label_occurrence_position_and_head(am241):
    assert EndfPath("1/451/MT").get(am241) == 451
    assert EndfPath("3/102#2/IZAM").get(am241) == 952422
    assert EndfPath("#3/IZAM").get(am241) == 952422
    assert EndfPath("#0").get(am241) is am241[1]
    assert EndfPath("0/0").get(am241) is am241[0]
    assert EndfPath("").get(am241) is am241


def test_position_k_is_list_element_k_plus_one(am241):
    for entry in iter_sections(am241):
        assert EndfPath(f"#{entry.position}").get(am241) is am241[entry.position + 1]


def test_ambiguous_label_on_the_list_form(am241):
    with pytest.raises(AmbiguousSectionError) as excinfo:
        EndfPath("3/102/IZAM").get(am241)
    assert str(excinfo.value) == (
        "MF=3/MT=102 matches 3 sections at positions [1, 2, 3]; use 3/102#k to "
        "select one"
    )


def test_out_of_range_and_missing(am241):
    with pytest.raises(IndexError, match="occurrence 3 out of range; MF=3/MT=102"):
        EndfPath("3/102#3").get(am241)
    with pytest.raises(IndexError, match="section position 4 out of range"):
        EndfPath("#4").get(am241)
    with pytest.raises(KeyError, match="no section MF=3/MT=1 in the material"):
        EndfPath("3/1").get(am241)


@pytest.mark.parametrize(
    "spec, message",
    [
        (
            "3",
            "the path '3' stops at MF=3, which addresses no section of a material in the list form",
        ),
        ("3/MT", "the path '3/MT' does not address a section"),
        ("AWR", "the path 'AWR' does not address a section"),
        (
            "3/*",
            "the wildcard '\\*' in the section selector of '3/\\*' is not supported",
        ),
        ("*/102/IZAM", "the wildcard"),
    ],
)
def test_paths_that_select_no_section_of_a_list(am241, spec, message):
    with pytest.raises(ValueError, match=message):
        EndfPath(spec).get(am241)


def test_exists_on_the_list_form(am241):
    assert EndfPath("3/102#2/IZAM").exists(am241)
    assert EndfPath("#3").exists(am241)
    assert not EndfPath("3/102#3").exists(am241)
    assert not EndfPath("#4").exists(am241)
    assert not EndfPath("3/1").exists(am241)
    assert not EndfPath("3/102#0/nokey").exists(am241)
    with pytest.raises(AmbiguousSectionError):
        EndfPath("3/102").exists(am241)


def test_set_whole_sections_on_the_list_form():
    m = gendf_like()
    new = sec(3, 102, IZAM=1)
    EndfPath("3/102#1").set(m, new)
    assert m[3] is new and len(m) == 5
    other = sec(3, 18)
    EndfPath("#1").set(m, other)
    assert m[2] is other
    new451 = {"MAT": 9543, "NZ": 2}
    EndfPath("1/451").set(m, new451)
    assert m[1] is new451 and new451["MF"] == 1 and new451["MT"] == 451


def test_set_inserts_a_new_label_after_the_last_smaller_label():
    m = gendf_like()
    EndfPath("2/151").set(m, sec(2, 151))
    EndfPath("6/18").set(m, sec(6, 18))
    EndfPath("1/1").set(m, sec(1, 1))
    assert [(s["MF"], s["MT"]) for s in m] == [
        (0, 0),
        (1, 1),
        (1, 451),
        (2, 151),
        (3, 102),
        (3, 102),
        (3, 102),
        (6, 18),
    ]


def test_set_errors_on_the_list_form():
    m = gendf_like()
    with pytest.raises(AmbiguousSectionError):
        EndfPath("3/102").set(m, sec(3, 102))
    with pytest.raises(IndexError, match="occurrence 3 out of range"):
        EndfPath("3/102#3").set(m, sec(3, 102))
    with pytest.raises(KeyError):
        EndfPath("3/1#0").set(m, sec(3, 1))
    with pytest.raises(ValueError) as excinfo:
        EndfPath("3/102#0").set(m, sec(3, 1))
    assert str(excinfo.value) == (
        "the section has MF=3/MT=1, but the path '3/102#0' addresses MF=3/MT=102"
    )
    with pytest.raises(TypeError):
        EndfPath("3/1").set(m, 5.0)


def test_set_fields_on_the_list_form():
    m = gendf_like()
    EndfPath("3/102#1/IZAM").set(m, 7)
    assert m[3]["IZAM"] == 7
    EndfPath("#0/new/1").set(m, 2.5)
    assert m[1]["new"] == {1: 2.5}
    # no section is invented for a field
    with pytest.raises(KeyError, match="no section MF=3/MT=1"):
        EndfPath("3/1/AWR").set(m, 1.0)
    assert len(m) == 5


def test_set_fields_in_list_mode_arrays_of_a_section():
    m = gendf_like()
    path = EndfPath("3/102#2/sigma/2", array_type="list")
    path.set(m, 7.0)
    assert m[4]["sigma"] == [5.0, 6.0, 7.0]
    EndfPath("3/102#2/sigma/0", array_type="list").set(m, 0.0)
    assert m[4]["sigma"] == [0.0, 6.0, 7.0]


def test_remove_on_the_list_form():
    m = gendf_like()
    EndfPath("3/102#1").remove(m)
    assert [s.get("IZAM") for s in m] == [None, None, 0, 952422]
    EndfPath("#0/NZ").remove(m)
    assert "NZ" not in m[1]
    EndfPath("#0").remove(m)
    assert [(s["MF"], s["MT"]) for s in m] == [(0, 0), (3, 102), (3, 102)]
    with pytest.raises(AmbiguousSectionError):
        EndfPath("3/102").remove(m)
    EndfPath("0/0").remove(m)
    assert len(m) == 2


def test_unparsed_sections_in_a_list():
    m = [raw(0, 0, 1, 1), raw(1, 451), raw(3, 102), raw(3, 102, nlines=3)]
    assert len(EndfPath("3/102#1").get(m)) == 3
    assert EndfPath("#1/0").get(m) == m[2][0]
    with pytest.raises(AmbiguousSectionError):
        EndfPath("3/102").get(m)


def test_list_without_tape_head():
    m = gendf_like()[1:]
    assert EndfPath("#0").get(m) is m[0]
    with pytest.raises(KeyError, match="MF=0/MT=0"):
        EndfPath("0/0").get(m)


# -- the nested form ---------------------------------------------------------------


def test_plain_paths_on_the_nested_form_are_unchanged():
    m = nested()
    assert EndfPath("3/1/xs/1").get(m) == 0.5
    assert EndfPath("3").get(m) is m[3]
    EndfPath("3/2").remove(m)
    assert m[3].keys() == {1}
    EndfPath("4/2/a").set(m, 1)
    assert m[4] == {2: {"a": 1}}


def test_selectors_on_the_nested_form():
    m = nested()
    assert EndfPath("3/1#0/xs/1").get(m) == 0.5
    assert EndfPath("#0").get(m) is m[1][451]
    assert EndfPath("#2/xs/1").get(m) == 0.25
    with pytest.raises(IndexError) as excinfo:
        EndfPath("3/1#1").get(m)
    assert (
        str(excinfo.value) == "occurrence 1 out of range; MF=3/MT=1 matches 1 section"
    )
    with pytest.raises(IndexError, match="section position 3 out of range"):
        EndfPath("#3").get(m)
    assert not EndfPath("3/1#1").exists(m)
    assert EndfPath("#2").exists(m)


def test_set_and_remove_with_selectors_on_the_nested_form():
    m = nested()
    EndfPath("#1/xs/1").set(m, 9.0)
    assert m[3][1]["xs"][1] == 9.0
    new = sec(3, 2)
    EndfPath("3/2#0").set(m, new)
    assert m[3][2] is new
    with pytest.raises(ValueError, match="keeps its label: position 2 holds MF=3/MT=2"):
        EndfPath("#2").set(m, sec(3, 1))
    with pytest.raises(KeyError):
        EndfPath("4/2#0").set(m, sec(4, 2))
    with pytest.raises(KeyError):
        EndfPath("4/2#0/a").set(m, 1)
    EndfPath("#0").remove(m)
    assert m[1] == {}


def test_selector_on_an_object_that_is_not_a_material():
    with pytest.raises(ValueError) as excinfo:
        EndfPath("#2/AWR").get({"AWR": 1.0})
    assert str(excinfo.value) == (
        "the path '#2/AWR' starts with a section selector, but the object is not a "
        "material (a list of sections or a dict {MF: {MT: section}})"
    )
    with pytest.raises(ValueError, match="not a material"):
        EndfPath("3/102#0").get([1.0, 2.0])
    with pytest.raises(ValueError, match="not a material"):
        EndfPath("#0").get([])


# -- other lists are walked as before ---------------------------------------------------


def test_list_mode_arrays_as_roots_are_unchanged():
    arr2d = [[1.0, 2.0], [3.0, 4.0]]
    assert EndfPath("1/0").get(arr2d) == 3.0
    dicts = [{"a": 1}, {"a": 2}]
    assert EndfPath("1/a").get(dicts) == 2
    lines = ["first", "second"]
    assert EndfPath("1").get(lines) == "second"
    empty = []
    EndfPath("0/0", array_type="list", leading="list").set(empty, 5)
    assert empty == [[5]]
    tape = [nested(), nested()]
    assert EndfPath("1/3/1/xs/1").get(tape) == 0.5


def test_empty_list_is_not_a_material():
    # walked as a list-mode array, as before
    with pytest.raises(IndexError):
        EndfPath("3/102", array_type="list", leading="list").set([], sec(3, 102))


# -- EndfDict, EndfList and EndfVariable --------------------------------------------------


def test_endflist_on_a_material_in_the_list_form():
    m = gendf_like()
    view = EndfList(m)
    # an int is positional, the tape head counted
    assert view[0]["MF"] == 0
    assert view[2]["IZAM"] == 0
    assert view[-1]["IZAM"] == 952422
    # a string is a path
    assert view["3/102#1/IZAM"] == 952420
    assert view["#1/IZAM"] == 0
    with pytest.raises(ValueError, match="stops at MF=2"):
        view["2"]
    view["3/102#2/IZAM"] = 1
    assert m[4]["IZAM"] == 1
    view.append(sec(6, 18))
    assert m[-1]["MF"] == 6
    del view[-1]
    assert len(m) == 5
    assert view.pop()["IZAM"] == 1
    assert isinstance(view["#0"], EndfDict)


def test_copying_a_section_between_materials():
    m1 = gendf_like()
    m2 = gendf_like()
    m2[3]["IZAM"] = -1
    EndfList(m2)["3/102#1"] = deepcopy(EndfList(m1)["3/102#1"])
    assert m2[3]["IZAM"] == 952420
    assert m2[3] is not m1[3]


def test_endfdict_on_the_nested_form():
    m = nested()
    view = EndfDict(m)
    assert view["3/2#0/xs/1"] == 0.25
    assert view[3, "1#0", "xs", 1] == 0.5
    assert view[3][1]["MT"] == 1


def test_endfvariable_with_a_selector():
    m = gendf_like()
    var = EndfVariable("3/102#1/IZAM", m)
    assert var.value == 952420
    var.value = 5
    assert m[3]["IZAM"] == 5
    with pytest.raises(ValueError) as excinfo:
        EndfVariable("3/102#1", m)
    assert str(excinfo.value) == (
        "EndfVariable needs a field path in a material in the list form or with a "
        "section selector, not the section path '3/102#1'"
    )
    with pytest.raises(ValueError, match="not the section path '#0'"):
        EndfVariable("#0", nested())


# -- no list within a section looks like a material ---------------------------------------


def _inner_lists(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _inner_lists(value, path + (key,))
    elif isinstance(obj, list):
        yield path, obj
        for i, value in enumerate(obj):
            yield from _inner_lists(value, path + (i,))


@pytest.mark.parametrize(
    "flavor, filename",
    [
        ("endf6-ext", "n_2925_29-Cu-63.endf"),
        ("endf6-ext", "dec-094_Pu_244.endf"),
        ("endf6-ext", "tsl_Al.endf"),
        ("gendf", "gendf/am241_nuclide_production.gendf"),
        ("gendf", "gendf/o16_photon_particle_production.gendf"),
        ("gendf", "gendf/h1_gaminr.gam"),
    ],
)
def test_no_array_in_list_mode_is_taken_for_a_material(flavor, filename):
    parser = EndfParserPy(endf_format=flavor, array_type="list", material_form="list")
    material = parser.parsefile(TESTDATA / filename)
    assert is_section_list(material)
    for entry in iter_sections(material):
        if isinstance(entry.section, dict):
            for path, lst in _inner_lists(entry.section):
                assert not is_section_list(lst), (entry.mf, entry.mt) + path


def test_list_form_and_nested_form_give_the_same_sections(am241):
    for entry in iter_sections(am241):
        key = f"{entry.mf}/{entry.mt}#{entry.occurrence}"
        assert EndfPath(key).get(am241) is entry.section
        assert get_section(am241, position=entry.position) is entry.section
