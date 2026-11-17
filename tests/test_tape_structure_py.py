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


# --- no SEND records at all ------------------------------------------------

# A format without SEND records: ``send`` given globally (or per MF), with
# a recipe of MF3 that ends without SEND; MF3/MT1 and MF3/MT2 follow each
# other without a record between them.
NO_SEND_GLOBAL = {"send": False}
NO_SEND_MF3 = {"mf": {3: {"send": False}}}
_HEAD_MF3 = "[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD\n"
_ZEROS = " 0.000000+0" * 2 + "          0" * 4
_HEAD = " 2.605600+4 5.545400+1" + "          0" * 4


def _ln(text, mat, mf, mt):
    return text.ljust(66) + f"{mat:4d}{mf:2d}{mt:3d}"


def _no_send_tape(*sections):
    """A tape of MAT=2631 with the HEAD records of the sections MF3/MT
    (``sections``, an MT number or a line given as it is), without SEND
    records."""
    lines = [_ln(" tape id", 1, 0, 0)]
    lines += [_ln(_HEAD, 2631, 3, s) if isinstance(s, int) else s for s in sections]
    lines += [_ln(_ZEROS, 2631, 0, 0), _ln(_ZEROS, 0, 0, 0), _ln(_ZEROS, -1, 0, 0)]
    return "\n".join(lines) + "\n"


def _no_send_recipes(send=""):
    return {0: {0: get_recipe_dict("endf6")[0][0]}, 3: _HEAD_MF3 + send}


@pytest.mark.parametrize("spec", [NO_SEND_GLOBAL, NO_SEND_MF3])
def test_no_send_records_parse(spec):
    tape = _no_send_tape(1, 2)
    parser = EndfParserPy(recipes=_no_send_recipes(), tape_structure=spec)
    material = parser.parse(tape)
    assert sorted(material) == [0, 3]
    assert sorted(material[3]) == [1, 2]
    assert material[3][2] == {
        "MAT": 2631,
        "MF": 3,
        "MT": 2,
        "ZA": 26056.0,
        "AWR": 55.454,
    }
    as_list = EndfParserPy(
        recipes=_no_send_recipes(), tape_structure=spec, material_form="list"
    ).parse(tape)
    assert _labels(as_list) == [(0, 0), (3, 1), (3, 2)]
    # read verbatim, each section is its line, without a SEND record
    verbatim = parser.parse(tape, exclude=[3])
    assert verbatim[3] == {
        1: [_ln(_HEAD, 2631, 3, 1) + "\n"],
        2: [_ln(_HEAD, 2631, 3, 2) + "\n"],
    }


@pytest.mark.parametrize("spec", [NO_SEND_GLOBAL, NO_SEND_MF3])
def test_no_send_records_write(spec):
    tape = _no_send_tape(1, 2)
    parser = EndfParserPy(
        recipes=_no_send_recipes(), tape_structure=spec, include_linenum=False
    )
    for material in (parser.parse(tape), parser.parse(tape, exclude=[3])):
        written = parser.write(material)
        # no SEND records; the FEND, MEND and TEND records
        assert [line.rstrip() for line in written] == _lines_of(tape)
        assert parser.parse(written) == parser.parse(tape)


@pytest.mark.parametrize(
    "spec, rule", [(NO_SEND_GLOBAL, "global rule"), (NO_SEND_MF3, "rule of MF=3")]
)
def test_no_send_records_recipe_with_send(spec, rule):
    with pytest.raises(ValueError) as exc:
        EndfParserPy(recipes=_no_send_recipes("SEND\n"), tape_structure=spec)
    assert str(exc.value) == (
        "the recipe for MF=3 ends with a SEND record, but the tape structure has "
        f"no SEND record after the sections of MF=3 ({rule}); remove SEND from "
        'the recipe or set "send": True'
    )


def test_no_send_records_send_in_the_data():
    send = _ln(_ZEROS, 2631, 3, 0)
    tape = _no_send_tape(1, 2, send)
    parser = EndfParserPy(recipes=_no_send_recipes(), tape_structure=NO_SEND_GLOBAL)
    for kwargs in ({}, {"exclude": [3]}):
        with pytest.raises(UnexpectedControlRecordError) as exc:
            parser.parse(tape, **kwargs)
        assert str(exc.value) == (
            "Unexpected SEND record after section MF=3/MT=2 of MAT=2631: the tape "
            "structure has no SEND record after this section, in control record "
            "of line 4."
        )


def test_no_send_records_copies_are_one_section():
    # nothing separates two copies of a section, so that they are read as
    # one section (of two lines), even if the section may repeat
    tape = _no_send_tape(1, 1)
    spec = dict(NO_SEND_GLOBAL, repeat=True)
    parser = EndfParserPy(
        recipes=_no_send_recipes(), tape_structure=spec, material_form="list"
    )
    assert _labels(parser.parse(tape)) == [(0, 0), (3, 1)]
    material = parser.parse(tape, exclude=[3])
    assert _labels(material) == [(0, 0), (3, 1)]
    assert len(material[1]) == 2


def test_no_send_records_tape_layer(tmp_path):
    from endf_parserpy.tape import TapeIndex, check_framing

    path = tmp_path / "no_send.endf"
    tape = _no_send_tape(1, 2)
    path.write_text(tape, encoding="latin-1")
    for spec in (NO_SEND_GLOBAL, NO_SEND_MF3):
        assert check_framing(path, tape_structure=spec) == []
        for index in (
            TapeIndex.from_file(path, tape_structure=spec),
            TapeIndex.from_lines(_lines_of(tape), tape_structure=spec),
        ):
            assert len(index) == 1
            assert [key for key, _ in index[0].section_list] == [(3, 1), (3, 2)]
    # under the rules of ENDF-6, the SEND records are missing
    assert [p.line for p in check_framing(path)] == [3, 4]
    # a SEND record in the data: the line of the error of the parser
    path.write_text(_no_send_tape(1, 2, _ln(_ZEROS, 2631, 3, 0)), encoding="latin-1")
    problems = check_framing(path, tape_structure=NO_SEND_GLOBAL)
    assert [p.line for p in problems] == [4]
    assert "found a SEND record (MAT/MF/MT 2631/3/0)" in problems[0].message


# --- writing ---------------------------------------------------------------


def _lines_of(text):
    return text.rstrip("\n").split("\n")


def _ctrl(lines):
    # the control columns of the lines (the framing), the data of the
    # parsed sections being compared by parsing them again
    return [line[66:75] for line in lines]


def test_write_list_form_of_endf6():
    parser = EndfParserPy()
    as_dict = parser.parsefile(str(PU))
    as_list = EndfParserPy(material_form="list").parsefile(str(PU))
    assert parser.write(as_list) == parser.write(as_dict)
    parser = EndfParserPy(include_linenum=False)
    assert _ctrl(parser.write(as_list)) == _ctrl(
        _lines_of(PU.read_text(encoding="latin-1"))
    )


def test_write_free_order_and_repeats():
    text = _text("tpid", "457", "452", "451", "457", "mend", "tend")
    parser = EndfParserPy(
        tape_structure=FREE, material_form="list", include_linenum=False
    )
    material = parser.parse(text)
    written = parser.write(material)
    assert _ctrl(written) == _ctrl(_lines_of(text))
    assert parser.parse(written) == material
    # the verbatim sections are written as they are
    material = parser.parse(text, exclude=[1, 8])

    def data(lines):
        return [line for line in lines if line[72:75] != "  0"]

    assert data(parser.write(material)) == data(_lines_of(text))


def test_write_without_send_after_451():
    text = _no_send_text("tpid", "451", "452", "fend1", "457", "mend", "tend")
    parser = _no_send_parser(include_linenum=False)
    lines = _lines_of(text)
    for form in ("dict", "list"):
        p = _no_send_parser(include_linenum=False, material_form=form)
        material = p.parse(text)
        written = p.write(material)
        assert _ctrl(written) == _ctrl(lines)
        assert p.parse(written) == material
    # MF1 read verbatim: its lines as in the file, without SEND after MT451
    written = parser.write(parser.parse(text, exclude=[1]))
    first_fend = lines.index(_blocks()["fend1"][0].decode())
    assert written[1:first_fend] == lines[1:first_fend]


def test_write_blank_end_records():
    parser = EndfParserPy(tape_structure={"end_record_fill": "blank"})
    lines = parser.write(EndfParserPy().parsefile(str(PU)))
    ends = [line for line in lines if line[72:75] == "  0" and line[:66].strip() == ""]
    assert len(ends) == 7  # 3 SEND, 2 FEND, MEND, TEND
    zeros = EndfParserPy().write(EndfParserPy().parsefile(str(PU)))
    assert parser.write(EndfParserPy().parsefile(str(PU)), zero_as_blank=False) == zeros


def _pu_list():
    return EndfParserPy(material_form="list").parsefile(str(PU))


def test_write_checks_the_list():
    parser = EndfParserPy()
    material = _pu_list()
    with pytest.raises(ValueError) as exc:
        parser.write([material[0], material[2], material[1], material[3]])
    assert str(exc.value) == (
        "cannot write the section MF=1/MT=451 at position 2 of the list after "
        "MF=1/MT=452: the tape structure requires ascending MT within an MF"
    )
    with pytest.raises(ValueError) as exc:
        parser.write([material[0], material[3], material[1]])
    assert str(exc.value) == (
        "cannot write the section MF=1/MT=451 at position 2 of the list after "
        "MF=8/MT=457: the tape structure requires ascending MF"
    )
    with pytest.raises(ValueError) as exc:
        EndfParserPy(tape_structure=dict(FREE, repeat=False)).write(
            material + [material[3]]
        )
    assert str(exc.value) == (
        "cannot write the section MF=8/MT=457 at position 4 of the list: "
        "MF=8/MT=457 already occurs at position 3, and the tape structure does "
        "not allow a repeated section"
    )
    with pytest.raises(ValueError) as exc:
        parser.write(material[1:2] + material[:1])
    assert str(exc.value) == (
        "the tape head (MF=0/MT=0) must be the first section of the list, found "
        "at position 1"
    )
    with pytest.raises(TypeError) as exc:
        parser.write(material[:1] + [3])
    assert str(exc.value) == (
        "a section must be a dict (parsed) or a list of strings (unparsed), got "
        "int at position 1 of the list"
    )


@pytest.mark.parametrize("form", ["dict", "list"])
def test_mat_rule(form):
    parser = EndfParserPy(material_form=form)
    material = parser.parsefile(str(PU))
    if form == "dict":
        material[8][457]["MAT"] = 3565
    else:
        material[3]["MAT"] = 3565
    with pytest.raises(ValueError) as exc:
        parser.write(material)
    position = 3
    assert str(exc.value) == (
        f"section MF=8/MT=457 at position {position} of the list has MAT=3565, "
        "but the material has MAT=3564 (from the section MF=1/MT=451); all "
        "sections of a material must have the same MAT number (the tape head "
        "MF=0/MT=0 is not counted)"
    )


def test_verbatim_lines_must_agree():
    parser = EndfParserPy()
    material = parser.parsefile(str(PU), exclude=[8])
    lines = material[8][457]
    lines[3] = lines[3][:66] + "3564 8458" + lines[3][75:]
    with pytest.raises(ValueError) as exc:
        parser.write(material)
    assert str(exc.value) == (
        "line 4 of the section MF=8/MT=457 given as a list of lines has "
        "MAT/MF/MT 3564/8/458, which differ from 3564/8/457 of its first line"
    )


def check_write_of_several_materials(parser_class, tmp_path):
    """``write`` and ``writefile`` of a list of materials raise an error
    with a hint to ``write_tape``; valid materials are written as before.
    Also used for EndfParserCpp (test_tape_structure_cpp.py)."""
    parser = parser_class()
    as_list = parser_class(material_form="list").parsefile(str(PU))
    as_dict = parser_class().parsefile(str(PU))
    verbatim = parser_class(material_form="list").parsefile(str(PU), exclude=[1, 8])
    # the tape head given as a list of lines, as EndfFile gives it
    verbatim_head = [parser.write(as_list)[:1]] + as_list[1:]
    hint = "; use write_tape for a tape of several materials"
    as_list_kind = "a list of sections"
    as_dict_kind = "a dict {MF: {MT: section}}"
    for materials, kind, pos in (
        ([as_list, as_list], as_list_kind, 0),
        ([as_dict, as_dict], as_dict_kind, 0),
        ([verbatim, verbatim], as_list_kind, 0),
        ([verbatim_head], as_list_kind, 0),
        ([as_list[0], as_list], as_list_kind, 1),
    ):
        expected = (
            f"write writes one material, but the element at position {pos} of "
            f"the list is itself a material ({kind})" + hint
        )
        with pytest.raises(TypeError) as exc:
            parser.write(materials)
        assert str(exc.value) == expected
        with pytest.raises(TypeError) as exc:
            parser.writefile(tmp_path / "out.endf", materials)
        assert str(exc.value) == expected
        assert not (tmp_path / "out.endf").exists()
    # no false positives: a material in the nested form, in the list form,
    # with sections given as lists of lines, and the empty list
    text = parser.write(as_dict)
    assert parser.write(as_list) == text
    # (the lines of a section read verbatim are those of the file)
    assert _ctrl(parser.write(verbatim)) == _ctrl(text)
    assert parser.write(verbatim_head) == text
    assert parser_class(ignore_missing_tpid=True).write([]) == text[-2:]


def test_write_of_several_materials(tmp_path):
    check_write_of_several_materials(EndfParserPy, tmp_path)
