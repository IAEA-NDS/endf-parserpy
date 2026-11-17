"""Section selectors in EndfMaterialPath and the reads of EndfFile."""

from pathlib import Path

import pytest

from endf_parserpy import (
    EndfFile,
    EndfMaterialPath,
    EndfParserPy,
    EndfPath,
    AmbiguousSectionError,
)
from endf_parserpy.tape import TapeStructureError

TESTDATA = Path(__file__).parent / "testdata"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"


@pytest.fixture(params=["eager", "deferred"])
def am241(request):
    parser = EndfParserPy(endf_format="gendf")
    with EndfFile(AM241, parser=parser, check_edits=request.param) as ef:
        yield ef


@pytest.fixture(scope="module")
def cu63():
    with EndfFile(CU63, parser=EndfParserPy()) as ef:
        yield ef


# -- EndfMaterialPath ---------------------------------------------------------


@pytest.mark.parametrize(
    "spec, depth, mf, mt, occurrence, position, subpath",
    [
        ("9543#0", "material", None, None, None, None, None),
        ("9543#0/3", "mf", 3, None, None, None, None),
        ("9543#0/3/102", "section", 3, 102, None, None, None),
        ("9543#0/3/102#2", "section", 3, 102, 2, None, None),
        ("9543#0/3/102#2/IZAM", "field", 3, 102, 2, None, "IZAM"),
        ("#0/#2", "section", None, None, None, 2, None),
        ("#0/#2/IZAM", "field", None, None, None, 2, "IZAM"),
        ("9543/3/102#1/sigma/1", "field", 3, 102, 1, None, "sigma/1"),
    ],
)
def test_material_path_with_section_selector(
    spec, depth, mf, mt, occurrence, position, subpath
):
    mp = EndfMaterialPath(spec)
    assert mp.depth == depth
    assert (mp.mf, mp.mt) == (mf, mt)
    assert mp.section_occurrence == occurrence
    assert mp.section_position == position
    if subpath is None:
        assert mp.subpath is None
    else:
        assert mp.subpath == EndfPath(subpath)


@pytest.mark.parametrize(
    "spec, message",
    [
        ("#0/3/#1", "the section selector '#1' must be the first element after"),
        ("#0/3/102/#1", "a section selector can only follow the material selector"),
        ("#0/3/102#x", "invalid section selector '102#x'"),
        ("#0/#x", "invalid section selector '#x'"),
        ("#0/3#1/102", "MF and MT must be integers"),
    ],
)
def test_invalid_material_paths(spec, message):
    with pytest.raises(ValueError, match=message):
        EndfMaterialPath(spec)


# -- EndfFile ---------------------------------------------------------------------


def test_read_repeated_sections_by_occurrence_and_position(am241):
    assert am241["#0/3/102#0/IZAM"] == 0
    assert am241["9543#0/3/102#2/IZAM"] == 952422
    assert am241["#0/#2/IZAM"] == 952420
    assert am241["#0/#0"]["MT"] == 451
    assert am241.get("#0/3/102#1")["IZAM"] == 952420


def test_ambiguous_label_through_endf_file(am241):
    with pytest.raises(AmbiguousSectionError) as excinfo:
        am241["#0/3/102"]
    assert str(excinfo.value) == (
        "MF=3/MT=102 matches 3 sections at positions [1, 2, 3]; use "
        "material[3, 102, k] or 3/102#k to select one"
    )
    with pytest.raises(AmbiguousSectionError):
        am241[0][3, 102]


def test_out_of_range_through_endf_file(am241):
    with pytest.raises(IndexError, match="occurrence 3 out of range"):
        am241["#0/3/102#3"]
    with pytest.raises(IndexError, match="section position 4 out of range"):
        am241["#0/#4"]
    with pytest.raises(KeyError, match="this material has no MF=3/MT=1 section"):
        am241["#0/3/1#0"]


def test_material_view_keys(am241):
    material = am241[0]
    assert material[3, 102, 1]["IZAM"] == 952420
    assert material["3/102#2/IZAM"] == 952422
    assert material["#1"]["IZAM"] == 0
    assert material[1, 451]["MT"] == 451
    assert material["1/451/MT"] == 451
    with pytest.raises(KeyError, match="does not address a section"):
        material["3"]
    with pytest.raises(KeyError, match="non-negative int"):
        material[3, 102, -1]
    with pytest.raises(KeyError, match=r"\(MF, MT, k\)"):
        material[3]


def test_material_view_contains(am241):
    material = am241[0]
    assert (3, 102) in material
    assert (3, 102, 2) in material
    assert (3, 102, 3) not in material
    assert "#3" in material
    assert "#4" not in material
    assert "3/102#1/IZAM" in material
    assert "3/102#1/nokey" not in material
    with pytest.raises(AmbiguousSectionError):
        "3/102" in material
    assert "#0/3/102#2/IZAM" in am241
    assert "#0/3/102#3" not in am241
    with pytest.raises(AmbiguousSectionError):
        "#0/3/102/IZAM" in am241


def test_the_sections_agree_with_the_parsed_material(am241):
    parsed = EndfParserPy(endf_format="gendf").parsefile(AM241)
    material = am241[0]
    for k, (mf, mt) in enumerate(material.sections()):
        assert material[f"#{k}"].detach() == EndfPath(f"#{k}").get(parsed)
        # the position k is the list element k + 1 of the parsed material
        assert material[f"#{k}"].detach() == parsed[k + 1]


def test_one_of_repeated_sections_is_read_only_for_now(am241):
    view = am241[0][3, 102, 1]
    with pytest.raises(TypeError):
        view["IZAM"] = 1.0
    with pytest.raises(NotImplementedError, match="occurs 3 times"):
        am241["#0/3/102#1/IZAM"] = 1.0
    with pytest.raises(NotImplementedError):
        del am241[0][3, 102, 1]
    with pytest.raises(NotImplementedError):
        am241[0]["#2"] = view.detach()
    with pytest.raises(AmbiguousSectionError):
        am241[0][3, 102] = view.detach()


def test_to_tape_dict_with_repeated_sections(am241):
    with pytest.raises(TapeStructureError, match="MF=3/MT=102 occurs 3 times"):
        am241[0].to_tape_dict()


def test_selectors_on_an_endf6_material(cu63):
    material = cu63[0]
    keys = material.sections()
    assert material["#0"]["MT"] == 451
    for k in (0, 5, len(keys) - 1):
        mf, mt = keys[k]
        assert cu63[f"#0/#{k}/MT"] == mt
        assert material[mf, mt, 0]["MF"] == mf
        assert cu63[f"#0/{mf}/{mt}#0/MF"] == mf
    with pytest.raises(IndexError, match="matches 1 section$"):
        material[3, 1, 1]


def test_edits_by_selector_of_a_unique_label():
    with EndfFile(CU63, parser=EndfParserPy(), check_edits="deferred") as ef:
        ef["#0/3/1#0/AWR"] = 1.5
        assert ef[0][3, 1]["AWR"] == 1.5
        position = ef[0].sections().index((3, 2))
        ef[f"#0/#{position}/AWR"] = 2.5
        assert ef[0][3, 2]["AWR"] == 2.5
        del ef[0]["3/2#0"]
        assert (3, 2) not in ef[0]
