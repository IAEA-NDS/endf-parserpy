"""sanitize_fieldname_types (canonical integer strings only, idempotent,
the list form) and list_parsed_sections/list_unparsed_sections of a
MaterialView and of other mappings."""

import json
from pathlib import Path

import pytest

from endf_parserpy import (
    EndfFile,
    EndfParserPy,
    list_parsed_sections,
    list_unparsed_sections,
    sanitize_fieldname_types,
)
from endf_parserpy.utils.accessories import EndfDict

TESTDATA = Path(__file__).resolve().parent / "testdata"
PU244 = TESTDATA / "dec-094_Pu_244.endf"


@pytest.fixture(scope="module")
def pu244():
    return EndfParserPy().parsefile(PU244)


def _json_roundtrip(obj):
    return json.loads(json.dumps(obj))


def test_sanitize_undoes_json(pu244):
    restored = _json_roundtrip(pu244)
    sanitize_fieldname_types(restored)
    assert restored == pu244
    assert EndfParserPy().write(restored) == EndfParserPy().write(pu244)


def test_sanitize_is_idempotent(pu244):
    restored = _json_roundtrip(pu244)
    sanitize_fieldname_types(restored)
    sanitize_fieldname_types(restored)
    assert restored == pu244
    data = {5: {"1": 1.0, 2: 2.0}}
    sanitize_fieldname_types(data)
    assert data == {5: {1: 1.0, 2: 2.0}}


def test_sanitize_keeps_key_order():
    data = {"a": 1, "2": 2, "b": 3, "1": 4}
    sanitize_fieldname_types(data)
    assert list(data) == ["a", 2, "b", 1]


@pytest.mark.parametrize(
    "key", [" 3 ", "03", "+3", "1_0", "3.0", "", "x1", "\u0661"]  # Arabic-Indic one
)
def test_sanitize_keeps_noncanonical_strings(key):
    data = {key: 1}
    sanitize_fieldname_types(data)
    assert data == {key: 1}
    assert type(next(iter(data))) is str


@pytest.mark.parametrize("key, value", [("3", 3), ("-1", -1), ("0", 0)])
def test_sanitize_converts_canonical_strings(key, value):
    data = {key: {"10": 1.0}}
    sanitize_fieldname_types(data)
    assert data == {value: {10: 1.0}}


def test_sanitize_conflicting_keys():
    with pytest.raises(IndexError, match="'3'"):
        sanitize_fieldname_types({3: 1, "3": 2})


def test_sanitize_list_form_material(pu244):
    sections = EndfParserPy(material_form="list").parsefile(PU244)
    assert isinstance(sections, list)
    restored = _json_roundtrip(sections)
    sanitize_fieldname_types(restored)
    assert restored == sections
    parser = EndfParserPy()
    assert parser.write(restored) == parser.write(pu244)


def test_sanitize_list_form_with_raw_sections():
    sections = EndfParserPy(material_form="list").parsefile(PU244, include=[(1, 451)])
    restored = _json_roundtrip(sections)
    sanitize_fieldname_types(restored)
    assert restored == sections


def test_sanitize_list_of_materials(pu244):
    restored = _json_roundtrip([pu244, pu244])
    sanitize_fieldname_types(restored)
    assert restored == [pu244, pu244]


def test_sanitize_nested_lists():
    data = {"x": [{"1": 1.0}, ["2", {"3": 3}]]}
    sanitize_fieldname_types(data)
    assert data == {"x": [{1: 1.0}, ["2", {3: 3}]]}


@pytest.mark.parametrize("obj", ["abc", 3, (1, 2), None])
def test_sanitize_rejects_other_types(obj):
    with pytest.raises(TypeError):
        sanitize_fieldname_types(obj)


# list_parsed_sections / list_unparsed_sections


def test_sections_of_material_view():
    endf_file = EndfFile(str(PU244))
    material = endf_file[0]
    parsed_dict = EndfParserPy().parsefile(PU244)
    expected = tuple(s for s in list_parsed_sections(parsed_dict) if s != (0, 0))
    assert list_parsed_sections(material) == expected
    assert list_unparsed_sections(material) == ()


def test_sections_of_material_view_without_recipes():
    parser = EndfParserPy(endf_format="test")
    endf_file = EndfFile(str(PU244), parser=parser)
    material = endf_file[0]
    assert list_parsed_sections(material) == ()
    assert list_unparsed_sections(material) == tuple(material.sections())


def test_sections_of_other_mappings():
    data = EndfParserPy().parsefile(PU244, include=[(1, 451)])
    expected_parsed = list_parsed_sections(data)
    expected_unparsed = list_unparsed_sections(data)
    assert (1, 451) in expected_parsed
    assert (8, 457) in expected_unparsed
    wrapped = EndfDict(data)
    assert list_parsed_sections(wrapped) == expected_parsed
    assert list_unparsed_sections(wrapped) == expected_unparsed
