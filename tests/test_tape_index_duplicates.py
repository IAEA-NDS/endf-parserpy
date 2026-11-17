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

"""A section that occurs twice in a material of a tape.

A material holds one section per MF/MT. The tape index (and so
``EndfFile`` and ``endf-cli validate``) kept an entry only for the last
of several sections with the same MF/MT, so that the others were lost
silently; it now raises a ``TapeStructureError`` that names the section
and the lines at which both sections start. The damaged tapes are built
from the Cu-63 file of ``tests/testdata``: its MF3/MT1 section repeated
after its SEND record. A GENDF tape with nuclide production (three
MF3/MT102 sections) raises the error too, until the representation of
such materials is decided.
"""

from pathlib import Path

import pytest

import endf_parserpy.tape.index as index_module
from endf_parserpy import EndfFile, EndfParserPy, TapeIndex
from endf_parserpy.cli.actions import validate
from endf_parserpy.cli.cmd_utils import get_endf_parser
from endf_parserpy.tape import TapeStructureError, check_framing
from endf_parserpy.tape.framing import _check_framing_and_index
from test_validate_framing_records import _args

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU = TESTDATA / "n_2925_29-Cu-63.endf"
AM241 = TESTDATA / "gendf" / "am241_nuclide_production.gendf"


def _cu_lines():
    return CU.read_bytes().split(b"\n")[:-1]


def _mf3_mt1(lines):
    """The first line of MF3/MT1 and the line after its SEND record."""
    rows = [k for k, line in enumerate(lines) if line[70:75] == b" 3  1"]
    return rows[0], rows[-1] + 2


def _repeated(send=True, copies=2):
    """Cu-63 with MF3/MT1 repeated after its SEND record, with or without
    the SEND record of the copies; and the first lines (counting from 1)
    of the first two sections MF3/MT1."""
    lines = _cu_lines()
    first, after = _mf3_mt1(lines)
    section = lines[first:after] if send else lines[first : after - 1]
    out = lines[:after] + section * (copies - 1) + lines[after:]
    return out, (first + 1, after + 1)


def _write(path, lines):
    path.write_bytes(b"".join(line + b"\n" for line in lines))
    return path


def _message(lines):
    first, second = lines
    return (
        "section MF=3/MT=1 of MAT 2925 occurs a second time in the material "
        f"at position 0: the sections start in lines {first} and {second}; a "
        "material can hold only one section with the same MF and MT numbers"
    )


def _from_lines(lines):
    return TapeIndex.from_lines([line.decode("latin-1") for line in lines])


@pytest.mark.parametrize("send", [True, False], ids=["send", "no_send"])
def test_from_lines(send):
    # without its SEND record, the copy ends where the next section starts
    # (the section is stored when it is left open)
    lines, starts = _repeated(send=send)
    with pytest.raises(TapeStructureError) as exc:
        _from_lines(lines)
    assert str(exc.value) == _message(starts)


@pytest.mark.parametrize("numpy", [True, False], ids=["numpy", "no_numpy"])
@pytest.mark.parametrize("chunk_bytes", [None, 4096])
@pytest.mark.parametrize("send", [True, False], ids=["send", "no_send"])
def test_from_file(send, chunk_bytes, numpy, tmp_path, monkeypatch):
    # the bulk scan with and without numpy, and in small blocks
    if numpy:
        pytest.importorskip("numpy")
    else:
        monkeypatch.setattr(index_module, "_np", None)
    lines, starts = _repeated(send=send)
    path = _write(tmp_path / "repeated.endf", lines)
    kwargs = {} if chunk_bytes is None else {"chunk_bytes": chunk_bytes}
    with pytest.raises(TapeStructureError) as exc:
        TapeIndex.from_file(path, **kwargs)
    assert str(exc.value) == _message(starts)


def test_first_repetition_is_named(tmp_path):
    # three sections MF3/MT1: the error names the first two
    lines, starts = _repeated(copies=3)
    with pytest.raises(TapeStructureError) as exc:
        TapeIndex.from_file(_write(tmp_path / "three.endf", lines))
    assert str(exc.value) == _message(starts)


def test_copies_without_send_between_are_one_section():
    # without a record between them, the copies are one longer section,
    # as the parsers read them
    lines = _cu_lines()
    first, after = _mf3_mt1(lines)
    data = lines[first : after - 1]
    merged = lines[: after - 1] + data + lines[after - 1 :]
    entry = _from_lines(merged)[0].sections[(3, 1)]
    assert entry.line_count == 2 * len(data) + 1


def test_same_section_in_two_materials():
    # two materials with the same MAT (as the temperatures of a PENDF
    # tape) each hold their sections
    lines = _cu_lines()
    tape = lines[:-1] + lines[1:-1] + lines[-1:]
    index = _from_lines(tape)
    assert len(index) == 2
    assert index[0].sections.keys() == index[1].sections.keys()


def test_valid_file_unchanged(tmp_path):
    index = TapeIndex.from_file(CU)
    assert index[0].sections[(3, 1)].offset == 70065


def test_endf_file(tmp_path):
    lines, starts = _repeated()
    path = _write(tmp_path / "repeated.endf", lines)
    with pytest.raises(TapeStructureError) as exc:
        EndfFile(path, parser=EndfParserPy())
    assert str(exc.value) == _message(starts)


@pytest.mark.parametrize("option", [(), ("--ignore_send_records",)])
def test_validate(option, tmp_path):
    """validate reports the repetition as a problem of the framing records
    and the error of the index."""
    lines, starts = _repeated()
    path = _write(tmp_path / "repeated.endf", lines)
    problems, index, error = _check_framing_and_index(
        path, ignore_send_records=bool(option)
    )
    assert index is None
    assert str(error) == _message(starts)
    assert problems == check_framing(path, ignore_send_records=bool(option))
    assert [p.line for p in problems] == [starts[1]]
    assert "occurs a second time in the material" in problems[0].message
    args = _args("--no-cpp", *option)
    ok, detail = validate._validate_file(
        get_endf_parser(args), str(path), validate.get_fast_parser(args)
    )
    assert not ok
    assert detail.startswith("framing records (SEND/FEND/MEND/TEND):\n")
    assert _message(starts) in detail


def test_gendf_nuclide_production():
    # NJOY GROUPR writes the production of each nuclide as an MF3 section
    # with the MT of the reaction: three sections MF3/MT102
    lines = AM241.read_bytes().split(b"\n")[:-1]
    starts = [
        k + 1
        for k, line in enumerate(lines)
        if line[70:75] == b" 3102" and lines[k - 1][70:75] != b" 3102"
    ]
    assert len(starts) == 3
    expected = (
        "section MF=3/MT=102 of MAT 9543 occurs a second time in the material "
        f"at position 0: the sections start in lines {starts[0]} and "
        f"{starts[1]}"
    )
    with pytest.raises(TapeStructureError, match=expected):
        TapeIndex.from_file(AM241)
    parser = EndfParserPy(endf_format="gendf", ignore_send_records=True)
    with pytest.raises(TapeStructureError, match=expected):
        EndfFile(AM241, parser=parser)
