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

"""Writing a tape whose TPID record has a blank MAT field.

The TPID record of many evaluated files (e.g. ENDF/B-VIII.1) leaves the
MAT field blank. EndfFile passes the TPID record verbatim to the writer,
which must read the blank MAT field as zero, as EndfParserPy does,
instead of failing. Both parsers must give the same output.
"""

from pathlib import Path
import pytest

from endf_parserpy import EndfParserFactory, EndfFile, EndfParserPy


TESTDATA = Path(__file__).parent / "testdata"
SOURCE_FILES = ["n_2925_29-Cu-63.endf", "tsl_Al.endf", "dec-094_Pu_244.endf"]
ATYPES = ["dict", "list", "numpy"]
BLANK_MAT_TPID = " ENDF/B-VIII.1".ljust(66) + "     0  0"


def _create(select, atype):
    if atype == "numpy":
        pytest.importorskip("numpy")
    try:
        return EndfParserFactory.create(select=select, array_type=atype)
    except Exception:
        pytest.skip(f"{select} backend unavailable")


def _blank_mat_copy(name, tmp_path):
    """A copy of a test file whose TPID record has a blank MAT field."""
    data = (TESTDATA / name).read_bytes()
    first, rest = data.split(b"\n", 1)
    path = tmp_path / ("blankmat_" + name)
    path.write_bytes(BLANK_MAT_TPID.encode("latin-1") + b"\n" + rest)
    return path


def _reference(path):
    """The tape as written by EndfParserPy from its raw sections."""
    return EndfFile(path, parser=EndfParserPy()).to_string()


@pytest.mark.parametrize("name", SOURCE_FILES)
@pytest.mark.parametrize("atype", ATYPES)
@pytest.mark.parametrize("select", ["python", "cpp"])
def test_to_string_and_export_with_blank_mat_tpid(name, atype, select, tmp_path):
    path = _blank_mat_copy(name, tmp_path)
    parser = _create(select, atype)
    expected = _reference(path)
    assert expected.splitlines()[0] == BLANK_MAT_TPID + "    0"
    ef = EndfFile(path, parser=parser)
    assert ef.to_string() == expected
    out = tmp_path / "out.endf"
    ef.export(out)
    assert out.read_bytes() == expected.encode("latin-1")


@pytest.mark.parametrize("name", SOURCE_FILES)
@pytest.mark.parametrize("select", ["python", "cpp"])
def test_round_trip_keeps_data_records(name, select, tmp_path):
    # the data records (columns 1-75) are kept verbatim; the framing
    # records (SEND/FEND/MEND/TEND, MT=0) are regenerated
    path = _blank_mat_copy(name, tmp_path)
    ef = EndfFile(path, parser=_create(select, "dict"))

    def data_records(text):
        return [x[:75] for x in text.splitlines() if x[72:75].strip() not in ("", "0")]

    original = path.read_bytes().decode("latin-1")
    assert data_records(ef.to_string()) == data_records(original)


@pytest.mark.parametrize("atype", ATYPES)
@pytest.mark.parametrize("select", ["python", "cpp"])
@pytest.mark.parametrize("check_edits", ["eager", "deferred"])
def test_edit_and_export_with_blank_mat_tpid(atype, select, check_edits, tmp_path):
    path = _blank_mat_copy("n_2925_29-Cu-63.endf", tmp_path)
    parser = _create(select, atype)
    ef = EndfFile(path, parser=parser, check_edits=check_edits)
    awr = ef["#0/3/1/AWR"]
    ef["#0/3/1/AWR"] = 2 * awr  # an eager edit is rendered here
    ef["#0/3/2"] = ef["#0/3/2"].detach()
    text = ef.to_string()
    assert text.splitlines()[0] == BLANK_MAT_TPID + "    0"
    # the edited sections are written; re-reading gives the edited value
    out = tmp_path / "out.endf"
    out.write_bytes(text.encode("latin-1"))
    again = EndfFile(out, parser=parser)
    assert again["#0/3/1/AWR"] == pytest.approx(2 * awr)
    assert again["#0/3/2"] == ef["#0/3/2"]


@pytest.mark.parametrize("select", ["python", "cpp"])
def test_writer_accepts_verbatim_tpid_with_blank_mat(select):
    parser = _create(select, "dict")
    material = parser.parse((TESTDATA / "n_2925_29-Cu-63.endf").read_text())
    material[0][0] = [BLANK_MAT_TPID]
    lines = parser.write(material)
    assert lines[0][:75] == BLANK_MAT_TPID
    assert lines == EndfParserPy().write(material)
