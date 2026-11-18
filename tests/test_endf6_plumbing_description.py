"""set_description and insert_description: lines up to 66 characters are
padded, a longer line raises a ValueError naming it (nothing is cut)."""

import copy
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.endf6_plumbing import (
    get_description,
    insert_description,
    set_description,
)

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"


@pytest.fixture(scope="module")
def cu63():
    return EndfParserCpp().parsefile(CU63, include=[(1, 451)])


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
def test_lines_up_to_66_characters_are_padded_and_written(cls, cu63):
    material = copy.deepcopy(cu63)
    text = "short line\n" + "x" * 66 + "\n"
    set_description(material, text)
    section = material[1][451]
    assert section["NWD"] == 2 + 5
    assert section["DESCRIPTION"] == {1: "short line".ljust(66), 2: "x" * 66}
    parser = cls()
    lines = parser.write(material)
    reparsed = EndfParserCpp().parse(lines, include=[(1, 451)])
    assert reparsed[1][451]["DESCRIPTION"] == section["DESCRIPTION"]


@pytest.mark.parametrize("length", (67, 80))
def test_longer_line_raises_naming_line_and_length(cu63, length):
    material = copy.deepcopy(cu63)
    before = copy.deepcopy(material)
    text = "first\nsecond\n" + "y" * length + "\nlast"
    with pytest.raises(ValueError) as err:
        set_description(material, text)
    message = str(err.value)
    assert message == (
        f"line 3 of the description has {length} characters, but a line of "
        "the description (a TEXT record) can have at most 66 characters"
    )
    # nothing changed, nothing cut
    assert material == before


def test_first_long_line_is_named(cu63):
    material = copy.deepcopy(cu63)
    with pytest.raises(ValueError, match="^line 1 of the description has 70 "):
        set_description(material, "z" * 70 + "\n" + "w" * 90)


def test_insert_description_counts_lines_of_the_new_description(cu63):
    material = copy.deepcopy(cu63)
    before = copy.deepcopy(material)
    with pytest.raises(ValueError, match="^line 3 of the description has 67 "):
        insert_description(material, "ok\n" + "v" * 67, after_line=1)
    assert material == before
    insert_description(material, "a new line", after_line=1)
    lines = get_description(material).splitlines()
    assert lines[1].rstrip() == "a new line"
    assert material[1][451]["NWD"] == before[1][451]["NWD"] + 1
