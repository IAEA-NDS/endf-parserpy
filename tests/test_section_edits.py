"""EndfFile edits of a material with several sections with the same label."""

import pickle
from pathlib import Path

import pytest

from endf_parserpy import (
    AmbiguousSectionError,
    EndfFile,
    EndfParserPy,
)
from endf_parserpy.tape import SectionRenderError, TapeStructureError

TESTDATA = Path(__file__).parent / "testdata"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"
H1_GAMINR = TESTDATA / "gendf" / "h1_gaminr.gam"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"

IZAM = [0.0, 952420.0, 952422.0]


@pytest.fixture(scope="module")
def gendf_parser():
    return EndfParserPy(endf_format="gendf")


@pytest.fixture(params=["eager", "deferred"])
def mode(request):
    return request.param


@pytest.fixture
def am241(gendf_parser, mode):
    with EndfFile(AM241, parser=gendf_parser, check_edits=mode) as ef:
        yield ef


def izam(material):
    return [material[3, 102, k]["IZAM"] for k in range(len(labels(material, 3, 102)))]


def labels(material, mf, mt):
    return [key for key in material.sections() if key == (mf, mt)]


def reread(endf_file, parser):
    """The materials of the written tape, in the list form."""
    from endf_parserpy import parse_tape

    return parse_tape(endf_file.to_string(), parser=parser, on_error="raise")


# -- a no-op edit ----------------------------------------------------------------


def test_untouched_and_no_op_edits_are_byte_identical(am241, gendf_parser):
    original = AM241.read_text()
    assert am241.to_string() == original
    material = am241[0]
    assert not material.is_modified
    for k in range(3):
        material[3, 102, k] = material[3, 102, k].detach()
    material[1, 451] = material[1, 451].detach()
    assert material.is_modified
    assert am241.to_string() == original


def test_export_after_a_no_op_edit(am241, tmp_path):
    am241[0]["#2"] = am241[0]["#2"].detach()
    target = tmp_path / "out.gendf"
    am241.export(target)
    assert target.read_bytes() == AM241.read_bytes()


# -- replacing --------------------------------------------------------------------------


def test_replace_by_occurrence(am241, gendf_parser):
    material = am241[0]
    section = material[3, 102, 1].detach()
    section["IZAM"] = 952421.0
    material[3, 102, 1] = section
    assert izam(material) == [0.0, 952421.0, 952422.0]
    assert material.sections() == [(1, 451), (3, 102), (3, 102), (3, 102)]
    written = reread(am241, gendf_parser)[0]
    assert [s["IZAM"] for s in written[2:]] == [0.0, 952421.0, 952422.0]


def test_replace_by_position_and_path(am241, gendf_parser):
    section = am241["#0/#3"].detach()
    section["IZAM"] = 1.0
    am241["#0/#3"] = section
    section = am241["9543#0/3/102#0"].detach()
    section["IZAM"] = 2.0
    am241["9543#0/3/102#0"] = section
    other = am241[0]["3/102#1"].detach()
    other["IZAM"] = 3.0
    am241[0]["3/102#1"] = other
    assert izam(am241[0]) == [2.0, 3.0, 1.0]
    written = reread(am241, gendf_parser)[0]
    assert [s["IZAM"] for s in written[2:]] == [2.0, 3.0, 1.0]


def test_set_fields_by_occurrence(am241):
    am241["#0/3/102#1/IZAM"] = 5.0
    am241[0]["3/102#2/IZAM"] = 6.0
    am241[0]["#1/IZAM"] = 7.0
    assert izam(am241[0]) == [7.0, 5.0, 6.0]


def test_live_view_of_a_repeated_section():
    parser = EndfParserPy(endf_format="gendf")
    with EndfFile(AM241, parser=parser, check_edits="deferred") as ef:
        view = ef[0][3, 102, 2]
        view["IZAM"] = 9.0
        assert izam(ef[0]) == [0.0, 952420.0, 9.0]
        assert ef[0].is_modified
        written = reread(ef, parser)[0]
        assert written[4]["IZAM"] == 9.0


def test_live_view_taken_before_the_material_switches_to_its_sequence():
    parser = EndfParserPy(endf_format="gendf")
    with EndfFile(AM241, parser=parser, check_edits="deferred") as ef:
        mf1 = ef[0][1, 451]
        del ef[0][3, 102, 0]  # the material now has its sequence
        mf1["TEMPIN"] = 1.0
        written = reread(ef, parser)[0]
        assert written[1]["TEMPIN"] == 1.0
        assert [s["IZAM"] for s in written[2:]] == [952420.0, 952422.0]


def test_edits_of_a_unique_label_and_of_a_repeated_one_combine(am241, gendf_parser):
    am241["#0/1/451/TEMPIN"] = 2.0
    am241["#0/3/102#0/IZAM"] = 3.0
    written = reread(am241, gendf_parser)[0]
    assert written[1]["TEMPIN"] == 2.0
    assert [s["IZAM"] for s in written[2:]] == [3.0, 952420.0, 952422.0]


def test_eager_check_of_a_repeated_section(gendf_parser):
    with EndfFile(AM241, parser=gendf_parser) as ef:
        section = ef[0][3, 102, 1].detach()
        section["NZ"] = "not a number"
        with pytest.raises(SectionRenderError):
            ef[0][3, 102, 1] = section
        assert not ef[0].is_modified


def test_invalid_edits_reports_repeated_sections(gendf_parser):
    with EndfFile(AM241, parser=gendf_parser, check_edits="deferred") as ef:
        ef[0][3, 102, 1]["NZ"] = "not a number"
        report = ef.invalid_edits()
        assert [(p, mf, mt) for p, mf, mt, _ in report] == [(0, 3, 102)]


# -- deleting ---------------------------------------------------------------------------


def test_delete_by_occurrence_and_position(am241, gendf_parser):
    material = am241[0]
    del material[3, 102, 1]
    assert izam(material) == [0.0, 952422.0]
    del am241["#0/#2"]
    assert izam(material) == [0.0]
    assert material.sections() == [(1, 451), (3, 102)]
    # one section is left with the label, which names it again
    assert material[3, 102]["IZAM"] == 0.0
    written = reread(am241, gendf_parser)[0]
    assert [(s["MF"], s["MT"]) for s in written] == [(0, 0), (1, 451), (3, 102)]


def test_delete_a_field_by_occurrence(gendf_parser):
    with EndfFile(AM241, parser=gendf_parser, check_edits="deferred") as ef:
        del ef["#0/3/102#2/IZAM"]
        assert "IZAM" not in ef[0][3, 102, 2]
        assert "IZAM" in ef[0][3, 102, 1]


# -- inserting --------------------------------------------------------------------------


def test_insert_section_after_the_copies(am241, gendf_parser):
    material = am241[0]
    section = material[3, 102, 1].detach()
    section["IZAM"] = 952421.0
    assert material.insert_section(section) == 4
    assert izam(material) == IZAM + [952421.0]
    written = reread(am241, gendf_parser)[0]
    assert [s["IZAM"] for s in written[2:]] == IZAM + [952421.0]


def test_insert_section_at_a_position(am241):
    material = am241[0]
    section = material[3, 102, 1].detach()
    section["IZAM"] = 1.0
    assert material.insert_section(section, 1) == 1
    assert izam(material) == [1.0] + IZAM
    with pytest.raises(IndexError, match="out of range for an insertion"):
        material.insert_section(section, 9)


def test_new_label_goes_after_the_last_smaller_label(gendf_parser, mode):
    with EndfFile(H1_GAMINR, parser=gendf_parser, check_edits=mode) as ef:
        material = ef[0]
        before = material.sections()
        assert before == [
            (1, 451),
            (23, 501),
            (26, 502),
            (23, 504),
            (26, 504),
            (23, 525),
        ]
        section = material[23, 501].detach()
        section["MT"] = 502
        material[23, 502] = section
        assert material.sections() == [
            (1, 451),
            (23, 501),
            (23, 502),
            (26, 502),
            (23, 504),
            (26, 504),
            (23, 525),
        ]
        written = reread(ef, gendf_parser)[0]
        assert [(s["MF"], s["MT"]) for s in written[1:]] == material.sections()


def test_new_label_in_a_material_with_repeats(am241):
    material = am241[0]
    section = material[3, 102, 0].detach()
    section["MT"] = 18
    material[3, 18] = section
    assert material.sections() == [(1, 451), (3, 18), (3, 102), (3, 102), (3, 102)]


# -- errors -----------------------------------------------------------------------------


def test_a_repeated_label_without_occurrence_is_ambiguous(am241):
    material = am241[0]
    section = material[3, 102, 0].detach()
    with pytest.raises(AmbiguousSectionError):
        material[3, 102] = section
    with pytest.raises(AmbiguousSectionError):
        del material[3, 102]
    with pytest.raises(AmbiguousSectionError):
        am241["#0/3/102/IZAM"] = 1.0
    with pytest.raises(IndexError, match="occurrence 3 out of range"):
        material[3, 102, 3] = section
    with pytest.raises(IndexError, match="section position 4 out of range"):
        del am241["#0/#4"]
    assert not material.is_modified


# -- the forms of the material ----------------------------------------------------------


def test_to_tape_dict_points_to_the_list_form(am241, gendf_parser):
    with pytest.raises(TapeStructureError) as excinfo:
        am241[0].to_tape_dict()
    assert str(excinfo.value) == (
        "MF=3/MT=102 occurs 3 times in this material; the nested form "
        "{MF: {MT: section}} holds one section per MF/MT; use to_tape_list() "
        "for the list form"
    )
    tape = am241[0].to_tape_list()
    assert len(tape) == 5
    assert gendf_parser.write(tape) == AM241.read_text().splitlines()


def test_to_tape_dict_after_removing_the_copies(am241):
    del am241[0][3, 102, 2]
    del am241[0][3, 102, 1]
    tape = am241[0].to_tape_dict()
    assert sorted(tape) == [0, 1, 3]
    assert list(tape[3]) == [102]


def test_pickle_keeps_the_sequence(am241):
    del am241[0][3, 102, 0]
    am241["#0/3/102#0/IZAM"] = 1.0
    copy = pickle.loads(pickle.dumps(am241))
    assert copy.to_string() == am241.to_string()
    assert izam(copy[0]) == [1.0, 952422.0]


# -- ENDF-6 keeps the overlay ---------------------------------------------------------------


def test_endf6_edits_do_not_use_the_sequence():
    with EndfFile(CU63, parser=EndfParserPy(), check_edits="deferred") as ef:
        material = ef[0]
        material[3, 2]["AWR"] = 1.0
        section = material[3, 2].detach()
        section["MT"] = 3
        del material[3, 3]
        material[3, 3] = section
        del material["3/1#0"]
        assert ef._materials[0].sequence is None
        assert material.sections() == sorted(material.sections())
