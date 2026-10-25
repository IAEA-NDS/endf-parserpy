"""EndfFile hands out no canonical containers outside the section views.

The ``predicate`` of ``EndfFile.query`` receives a field as a frozen view
hands it out, and ``MaterialView.to_tape_dict`` returns a detached copy,
so that neither can change the cached sections or the edit overlay
without the change being written (design note
``endf_file_path_addressing.md``, decision P3).
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfFile, EndfParserFactory


TESTDATA = Path(__file__).parent / "testdata"
ENDF_FILE = TESTDATA / "n_2925_29-Cu-63.endf"


def _create(select, array_type):
    try:
        return EndfParserFactory.create(select=select, array_type=array_type)
    except Exception:
        pytest.skip(f"{select} backend unavailable")


@pytest.fixture(params=["python", "cpp"])
def parser(request):
    return _create(request.param, "dict")


@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_query_predicate_cannot_change_containers(parser, check_edits):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits=check_edits)
    xs0 = ef["#0/3/1/xstable/xs"][0]

    def change_list(xs):
        xs[0] = 0.0
        return True

    def change_dict(xstable):
        xstable["xs"] = []
        return True

    with pytest.raises(TypeError, match="read-only"):
        ef.query("3/1/xstable/xs", predicate=change_list)
    with pytest.raises(TypeError, match="read-only"):
        ef.query("3/1/xstable", predicate=change_dict)
    assert ef["#0/3/1/xstable/xs"][0] == xs0
    assert not ef[0].is_modified
    # reading predicates work as before
    assert len(ef.query("3/1/xstable/xs", predicate=lambda xs: xs[0] == xs0)) == 1
    assert len(ef.query("3/1/xstable", predicate=lambda t: "xs" in t)) == 1
    assert len(ef.query("1/451/AWR", predicate=lambda awr: awr > 1.0)) == 1


@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_to_tape_dict_is_detached(parser, check_edits, tmp_path):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits=check_edits)
    section = ef[0][3, 1].detach()
    section["xstable"]["xs"][0] = 1.5
    ef[0][3, 1] = section  # MF3/MT1 is now in the edit overlay
    expected = ef.to_string()
    tape_dict = ef[0].to_tape_dict()
    assert tape_dict[3][1]["xstable"]["xs"][0] == 1.5
    tape_dict[3][1]["xstable"]["xs"][0] = 2.5
    tape_dict[3][1]["AWR"] = 99.0
    tape_dict[3][2].append(tape_dict[3][2][-1])  # untouched: raw lines
    tape_dict[0][0][0] = ""
    assert ef["#0/3/1/xstable/xs"][0] == 1.5
    assert ef["#0/3/1/AWR"] != 99.0
    assert ef.to_string() == expected
    # the copy is still a complete tape for the writer
    reparsed = parser.parse(parser.write(ef[0].to_tape_dict()))
    assert reparsed[3][1]["xstable"]["xs"][0] == 1.5


def test_to_tape_dict_copies_numpy_arrays():
    np = pytest.importorskip("numpy")
    parser = _create("cpp", "numpy")
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits="deferred")
    ef["#0/3/1/xstable/xs/0"] = 1.5
    expected = ef.to_string()
    xs = ef[0].to_tape_dict()[3][1]["xstable"]["xs"]
    assert isinstance(xs, np.ndarray) and xs.flags.writeable
    xs[0] = 2.5
    assert ef["#0/3/1/xstable/xs"][0] == 1.5
    assert ef.to_string() == expected
