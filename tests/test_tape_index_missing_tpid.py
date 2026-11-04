############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Indexing and opening tapes without a tape head (TPID record).

``TapeIndex`` requires the first non-blank record of a tape to be the
tape head. With ``ignore_missing_tpid=True``, a tape whose first record
is already a section record is accepted: the record starts the first
material and the ``tpid_*`` attributes of the index are ``None``. The
same option of :class:`EndfFile` is forwarded to the index; text and
dictionaries synthesized from such a file carry the default tape head,
so that a parser with default options reads them. The option is
deliberately independent of the identically named parser option.
"""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp
from endf_parserpy.tape import EndfFile, TapeIndex
from endf_parserpy.tape import index as tape_index
from endf_parserpy.tape.errors import TapeStructureError


TESTDATA = Path(__file__).parent / "testdata"
SOURCE = "n_2925_29-Cu-63.endf"


def _lines(name=SOURCE):
    data = (TESTDATA / name).read_bytes().replace(b"\r\n", b"\n")
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


def _tape_bytes(with_tpid=True, leading_blanks=0):
    lines = _lines()
    if not with_tpid:
        lines = lines[1:]
    lines = [b""] * leading_blanks + lines
    return b"\n".join(lines) + b"\n"


def _materials_canon(index, shift=0):
    # the material and section locations with all byte offsets reduced
    # by ``shift`` (the byte length of a removed tape head)
    mats = []
    for m in index:
        secs = sorted(
            (k, e.offset - shift, e.length, e.line_count) for k, e in m.sections.items()
        )
        mats.append(
            (m.position, m.mat, m.za, m.awr, m.byte_offset - shift, m.byte_length, secs)
        )
    return mats


@pytest.fixture(params=["numpy", "python"])
def kernel(request, monkeypatch):
    if request.param == "numpy":
        if tape_index._np is None:
            pytest.skip("numpy not installed")
    else:
        monkeypatch.setattr(tape_index, "_np", None)
    return request.param


def _write(tmp_path, data, name="tape.endf"):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_strict_index_rejects_headless_tape(kernel, tmp_path):
    path = _write(tmp_path, _tape_bytes(with_tpid=False))
    with pytest.raises(TapeStructureError, match="tape head"):
        TapeIndex.from_file(path)
    with pytest.raises(TapeStructureError, match="tape head"):
        TapeIndex.from_lines(l.decode("latin-1") for l in _lines()[1:])


@pytest.mark.parametrize("leading_blanks", [0, 2])
def test_lenient_index_matches_headful_index(kernel, tmp_path, leading_blanks):
    headful = TapeIndex.from_file(_write(tmp_path, _tape_bytes(), "a.endf"))
    path = _write(
        tmp_path, _tape_bytes(with_tpid=False, leading_blanks=leading_blanks), "b.endf"
    )
    lenient = TapeIndex.from_file(path, ignore_missing_tpid=True)
    assert lenient.tpid_line is None
    assert lenient.tpid_offset is None
    assert lenient.tpid_length is None
    # same materials and sections; offsets differ by the removed tape
    # head and the added blank records
    shift = headful.tpid_length - (leading_blanks * 1)
    assert _materials_canon(lenient) == _materials_canon(headful, shift=shift)
    assert lenient.by_mat(headful[0].mat) == [0]


def test_lenient_index_of_headful_tape_unchanged(kernel, tmp_path):
    path = _write(tmp_path, _tape_bytes())
    strict = TapeIndex.from_file(path)
    lenient = TapeIndex.from_file(path, ignore_missing_tpid=True)
    assert lenient.tpid_line == strict.tpid_line
    assert lenient.tpid_offset == strict.tpid_offset
    assert _materials_canon(lenient) == _materials_canon(strict)


def test_lenient_from_lines_agrees_with_from_file(kernel, tmp_path):
    path = _write(tmp_path, _tape_bytes(with_tpid=False))
    from_file = TapeIndex.from_file(path, ignore_missing_tpid=True)
    from_lines = TapeIndex.from_lines(
        (l.decode("latin-1") for l in _lines()[1:]), ignore_missing_tpid=True
    )
    assert from_lines.tpid_line is None
    assert _materials_canon(from_lines) == _materials_canon(from_file)


def test_empty_tape_still_raises_with_lenient_option(kernel):
    with pytest.raises(TapeStructureError, match="does not contain any records"):
        TapeIndex.from_lines([], ignore_missing_tpid=True)
    with pytest.raises(TapeStructureError, match="does not contain any records"):
        TapeIndex.from_lines(["", "   "], ignore_missing_tpid=True)


def test_endf_file_requires_option_for_headless_tape(tmp_path):
    path = _write(tmp_path, _tape_bytes(with_tpid=False))
    with pytest.raises(TapeStructureError, match="tape head"):
        EndfFile(path, parser=EndfParserCpp())


def test_endf_file_opens_headless_tape(tmp_path):
    # the sections of a headless tape parse with a parser with DEFAULT
    # options: the synthesized text carries the default tape head
    headful = EndfFile(
        _write(tmp_path, _tape_bytes(), "a.endf"), parser=EndfParserCpp()
    )
    headless = EndfFile(
        _write(tmp_path, _tape_bytes(with_tpid=False), "b.endf"),
        parser=EndfParserCpp(),
        ignore_missing_tpid=True,
    )
    assert len(headless) == len(headful) == 1
    sec = headless[0][3, 1]
    ref = headful[0][3, 1]
    assert sec["QM"] == ref["QM"]
    assert sec["xstable"]["xs"] == ref["xstable"]["xs"]


def test_cli_helper_forwards_parser_flag(tmp_path):
    from endf_parserpy.cli.cmd_utils import open_endf_file

    path = _write(tmp_path, _tape_bytes(with_tpid=False))
    with pytest.raises(TapeStructureError, match="tape head"):
        open_endf_file(path, EndfParserCpp())
    endf_file = open_endf_file(path, EndfParserCpp(ignore_missing_tpid=True))
    assert len(endf_file) == 1
