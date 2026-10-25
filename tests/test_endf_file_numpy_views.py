############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""numpy arrays in the section views of EndfFile.

A section parsed with ``array_type="numpy"`` contains numpy arrays. Both
view kinds hand them out as read-only numpy views of the canonical
array, so that an in-place change can neither corrupt a frozen section
nor bypass the write-through of a live one. A live view writes into an
array by a path ending at an element or by assigning a whole array;
``detach()`` copies the arrays; views compare element by element.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")

import endf_parserpy
from endf_parserpy import EndfFile, EndfParserFactory


TESTDATA = Path(__file__).parent / "testdata"
ENDF_FILE = TESTDATA / "n_2925_29-Cu-63.endf"
XS = "#0/3/1/xstable/xs"
# a two-dimensional block: b[2] of the first subsection of MF6/MT5
BLOCK = "#0/6/5/subsection/0/b/2"


@pytest.fixture(params=["python", "cpp"])
def parser(request):
    try:
        return EndfParserFactory.create(select=request.param, array_type="numpy")
    except Exception:
        pytest.skip(f"{request.param} backend unavailable")


def _reread(ef, parser, tmp_path):
    out = tmp_path / "out.endf"
    ef.export(out, overwrite=True)
    return EndfFile(out, parser=parser)


@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_arrays_are_read_only_views(parser, check_edits):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits=check_edits)
    section = ef["#0/3/1"]
    xs = section["xstable"]["xs"]
    assert isinstance(xs, np.ndarray)
    assert not xs.flags.writeable
    # a view of the canonical array, no copy
    assert np.shares_memory(xs, section._target["xstable"]["xs"])
    for arr in (xs, ef[XS], ef[0][3, 1]["xstable/xs"]):
        with pytest.raises(ValueError, match="read-only"):
            arr[0] = 123.0
    block = ef[BLOCK]
    assert block.ndim == 2 and not block.flags.writeable
    with pytest.raises(ValueError, match="read-only"):
        block[1, 1] = 0.5
    # a row of a block reached by a path is read-only as well
    row = ef[BLOCK + "/1"]
    assert row.ndim == 1 and not row.flags.writeable
    # the rejected edits changed nothing: no section is edited
    assert not ef[0].is_modified
    assert ef.to_string() == EndfFile(ENDF_FILE, parser=parser).to_string()


def test_frozen_view_rejects_edits_that_would_corrupt_cache(parser):
    ef = EndfFile(ENDF_FILE, parser=parser)
    original = float(ef[XS][0])
    with pytest.raises(ValueError):
        ef["#0/3/1"]["xstable"]["xs"][0] = 123.0
    with pytest.raises(TypeError):
        ef["#0/3/1"]["xstable/xs/0"] = 123.0
    assert float(ef[XS][0]) == original


def test_eager_path_writes(parser, tmp_path):
    ef = EndfFile(ENDF_FILE, parser=parser)
    cached = ef["#0/3/1"]
    xs = ef[XS].copy()
    ef[XS + "/0"] = 2 * xs[0]
    block = ef[BLOCK].copy()
    ef[BLOCK + "/1/1"] = 0.5 * block[1, 1]
    ef["#0/3/2/xstable/xs"] = ef["#0/3/2/xstable/xs"] * 3
    # the previously retrieved (frozen) section is unchanged
    assert cached["xstable/xs"][0] == xs[0]
    again = _reread(ef, parser, tmp_path)
    assert again[XS][0] == pytest.approx(2 * xs[0])
    assert np.array_equal(again[XS][1:], xs[1:])
    assert again[BLOCK][1, 1] == pytest.approx(0.5 * block[1, 1])
    assert again["#0/3/2/xstable/xs"] == pytest.approx(
        EndfFile(ENDF_FILE, parser=parser)["#0/3/2/xstable/xs"] * 3
    )


def test_live_element_writes_go_through(parser, tmp_path):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits="deferred")
    section = ef["#0/3/1"]
    xs = section["xstable/xs"]
    old0 = float(xs[0])
    section["xstable/xs/0"] = 2 * old0
    # the read-only view shares the canonical data and shows the edit
    assert xs[0] == 2 * old0
    assert ef[0].is_modified
    mf6 = ef["#0/6/5"]
    old11 = float(mf6["subsection/0/b/2"][1, 1])
    mf6["subsection/0/b/2/1/1"] = 0.5 * old11  # an element of a 2-D block
    sub = mf6["subsection/0"]
    sub["b/2/0/1"] = 0.25  # through a nested live view
    again = _reread(ef, parser, tmp_path)
    assert again[XS][0] == pytest.approx(2 * old0)
    assert again[BLOCK][1, 1] == pytest.approx(0.5 * old11)
    assert again[BLOCK][0, 1] == pytest.approx(0.25)


def test_live_in_place_edit_raises_instead_of_being_lost(parser, tmp_path):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits="deferred")
    with pytest.raises(ValueError, match="read-only"):
        ef["#0/3/1"]["xstable"]["xs"][0] = 123.0
    with pytest.raises(ValueError, match="read-only"):
        ef["#0/3/1"]["xstable/xs"] *= 2
    assert not ef[0].is_modified
    assert ef[XS][0] != 123.0


def test_live_whole_array_assignment(parser, tmp_path):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits="deferred")
    section = ef["#0/3/1"]
    new_xs = section["xstable/xs"] * 2  # a new, writable array
    section["xstable/xs"] = new_xs
    assert ef[0].is_modified
    # a read-only array (of another view) is copied on assignment
    other = ef["#0/3/2"]
    other["xstable/xs"] = section["xstable/xs"]
    assigned = other._target["xstable"]["xs"]
    assert assigned.flags.writeable
    assert not np.shares_memory(assigned, section._target["xstable"]["xs"])
    other["xstable/xs/0"] = 7.0  # the copy is editable by path
    again = _reread(ef, parser, tmp_path)
    assert np.array_equal(again[XS], new_xs)
    assert again["#0/3/2/xstable/xs"][0] == pytest.approx(7.0)


@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_detach_copies_arrays(parser, check_edits):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits=check_edits)
    view = ef["#0/6/5"]
    plain = view.detach()
    canonical = view._target
    for path in ("subsection/0/b/2", "subsection/0/b/0"):
        arr = plain
        ref = canonical
        for key in path.split("/"):
            key = int(key) if key.isdigit() else key
            arr, ref = arr[key], ref[key]
        assert arr.flags.writeable
        assert arr.dtype == ref.dtype and arr.shape == ref.shape
        assert not np.shares_memory(arr, ref)
    plain["subsection"][0]["b"][2][1, 1] = -1.0
    assert ef[BLOCK][1, 1] != -1.0
    assert not ef[0].is_modified
    # a detached section can be edited and assigned back
    ef["#0/6/5"] = plain
    assert ef[BLOCK][1, 1] == -1.0


@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_equality(parser, check_edits):
    ef = EndfFile(ENDF_FILE, parser=parser, check_edits=check_edits)
    view = ef["#0/3/1"]
    plain = view.detach()
    assert view == plain and plain == view
    assert view == ef["#0/3/1"]
    assert not (view != plain)
    # numpy data compare element by element with list data
    listparser = EndfParserFactory.create(
        select="python" if "Py" in type(parser).__name__ else "cpp",
        array_type="list",
    )
    listed = EndfFile(ENDF_FILE, parser=listparser)["#0/3/1"]
    assert view == listed and listed == view
    plain["xstable"]["xs"][0] += 1.0
    assert view != plain
    assert not (view == plain)
    assert ef["#0/6/5"] != view


def test_query_with_numpy_fields(parser):
    ef = EndfFile(ENDF_FILE, parser=parser)
    xs = ef[XS].copy()
    assert len(ef.query("3/1/xstable/xs", xs)) == 1
    assert len(ef.query("3/1/xstable/xs", list(xs))) == 1
    assert ef.query("3/1/xstable/xs", xs + 1) == []

    def mutate(arr):
        arr[0] = 0.0
        return True

    with pytest.raises(ValueError, match="read-only"):
        ef.query("3/1/xstable/xs", predicate=mutate)
    assert ef[XS][0] == xs[0]
    with pytest.raises(ValueError, match="non-hashable"):
        ef.build_index("3/1/xstable/xs")


def test_views_without_numpy(tmp_path):
    # the tape modules work and never import numpy if it is unavailable
    code = (
        "import sys\n"
        "sys.modules['numpy'] = None\n"
        "from endf_parserpy import EndfFile, EndfParserPy\n"
        "import endf_parserpy.tape.views as views\n"
        f"ef = EndfFile({str(ENDF_FILE)!r}, parser=EndfParserPy(),"
        " check_edits='deferred')\n"
        "s = ef['#0/3/1']\n"
        "plain = s.detach()\n"
        "assert s == plain\n"
        "s['xstable/xs/0'] = 2.0\n"
        "assert ef['#0/3/1/xstable/xs/0'] == 2.0\n"
        "assert ef[0].is_modified\n"
        "ef.to_string()\n"
        "assert sys.modules['numpy'] is None\n"
        "print('ok')\n"
    )
    env = dict(os.environ)
    pkg_root = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(
        [pkg_root] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "ok"
