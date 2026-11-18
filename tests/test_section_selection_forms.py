"""The ``include`` and ``exclude`` arguments of both parsers: an [MF, MT]
pair may be a list as well as a tuple, and a malformed entry raises."""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserPy, EndfParserCpp
from endf_parserpy.tape.operations import parse_tape, write_tape
from endf_parserpy.utils.user_tools import list_parsed_sections


CU63 = Path(__file__).parent / "testdata" / "n_2925_29-Cu-63.endf"

PARSERS = (EndfParserPy, EndfParserCpp)

# each selection with the same one in tuple form
SELECTIONS = (
    ([6, [3, 1]], (6, (3, 1))),
    ([[3, 1]], ((3, 1),)),
    ([[1, 451], [3, 2], 4], ((1, 451), (3, 2), 4)),
    (([3, 1], 6), ((3, 1), 6)),
    ([3], (3,)),
    (3, (3,)),
)

MALFORMED = (
    ([[3]], ValueError, "two numbers, not 1"),
    ([[3, 1, 2]], ValueError, "two numbers, not 3"),
    ([(3,)], ValueError, "two numbers, not 1"),
    (["3"], TypeError, "invalid entry '3'"),
    ([(3, "1")], TypeError, "must be ints"),
    ([3.0], TypeError, "invalid entry 3.0"),
    ([True], TypeError, "invalid entry True"),
    ("3", TypeError, "must be a sequence"),
    (3.0, TypeError, "must be a sequence"),
    ({3: 1}, TypeError, "must be a sequence"),
)


@pytest.fixture(scope="module")
def small_file(tmp_path_factory):
    """Cu-63 with its MF=1, 3 and 4 sections only, so that the Python
    parser is fast (the directory still lists the other sections)."""
    parser = EndfParserCpp()
    material = parser.parsefile(CU63, include=())
    for mf in list(material):
        if mf not in (0, 1, 3, 4):
            del material[mf]
    path = tmp_path_factory.mktemp("selection") / "cu63_small.endf"
    parser.writefile(path, material)
    return path


@pytest.fixture(scope="module")
def cu63_text(small_file):
    return small_file.read_text(encoding="latin-1")


@pytest.fixture(scope="module")
def full_materials(small_file):
    return {cls: cls().parsefile(small_file) for cls in PARSERS}


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("given,as_tuple", SELECTIONS, ids=repr)
@pytest.mark.parametrize("option", ("include", "exclude"))
def test_list_and_tuple_selections_parse_alike(
    cls, given, as_tuple, option, small_file
):
    parser = cls()
    expected = parser.parsefile(small_file, **{option: as_tuple})
    result = parser.parsefile(small_file, **{option: given})
    assert list_parsed_sections(result) == list_parsed_sections(expected)
    assert result == expected


@pytest.mark.parametrize("given,as_tuple", SELECTIONS, ids=repr)
@pytest.mark.parametrize("option", ("include", "exclude"))
def test_both_parsers_parse_the_same_sections(given, as_tuple, option, cu63_text):
    parsed = [
        list_parsed_sections(cls().parse(cu63_text, **{option: given}))
        for cls in PARSERS
    ]
    assert parsed[0] == parsed[1]
    if option == "include" and given == [6, [3, 1]]:
        # the example of the documentation
        assert (3, 1) in parsed[0] and (3, 2) not in parsed[0]
        assert all(mf in (3, 6) for mf, _ in parsed[0])
    if option == "exclude" and given == [[3, 1]]:
        assert (3, 1) not in parsed[0] and (3, 2) in parsed[0]


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("given,as_tuple", SELECTIONS, ids=repr)
@pytest.mark.parametrize("option", ("include", "exclude"))
def test_list_and_tuple_selections_write_alike(
    cls, given, as_tuple, option, full_materials, tmp_path
):
    parser = cls()
    material = full_materials[cls]
    expected = parser.write(material, **{option: as_tuple})
    assert parser.write(material, **{option: given}) == expected
    if option == "include" and given == [[3, 1]]:
        # more than the tape head and end
        assert len(expected) > 2
    path = tmp_path / "out.endf"
    parser.writefile(path, material, **{option: given})
    assert path.read_text(encoding="latin-1").splitlines() == expected


@pytest.mark.parametrize("given,as_tuple", SELECTIONS, ids=repr)
def test_both_parsers_write_the_same_sections(given, as_tuple, full_materials):
    written = [cls().write(full_materials[cls], include=given) for cls in PARSERS]
    assert written[0] == written[1]


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
def test_tape_operations_accept_list_pairs(cls, cu63_text):
    parser = cls()
    materials = parse_tape(cu63_text, parser=parser, include=[[3, 1]])
    expected = parse_tape(cu63_text, parser=parser, include=((3, 1),))
    assert list(list_parsed_sections(materials[0])) == [(3, 1)]
    assert materials == expected
    full = parse_tape(cu63_text, parser=parser)
    assert write_tape(full, parser=parser, include=[[3, 1]]) == write_tape(
        full, parser=parser, include=((3, 1),)
    )


@pytest.mark.parametrize("cls", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("bad,exc,match", MALFORMED, ids=repr)
@pytest.mark.parametrize("option", ("include", "exclude"))
def test_malformed_selection_raises(
    cls, bad, exc, match, option, small_file, cu63_text, full_materials, tmp_path
):
    parser = cls()
    with pytest.raises(exc, match=match) as parse_err:
        parser.parse(cu63_text, **{option: bad})
    assert f"`{option}`" in str(parse_err.value)
    with pytest.raises(exc, match=match):
        parser.parsefile(small_file, **{option: bad})
    with pytest.raises(exc, match=match):
        parser.write(full_materials[cls], **{option: bad})
    path = tmp_path / "out.endf"
    with pytest.raises(exc, match=match):
        parser.writefile(path, full_materials[cls], **{option: bad})
    assert not path.exists()


@pytest.mark.parametrize("bad,exc,match", MALFORMED, ids=repr)
def test_both_parsers_give_the_same_error(bad, exc, match, cu63_text):
    messages = []
    for cls in PARSERS:
        with pytest.raises(exc) as err:
            cls().parse(cu63_text, include=bad)
        messages.append(str(err.value))
    assert messages[0] == messages[1]
