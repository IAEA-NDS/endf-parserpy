import pickle
import pytest
from pathlib import Path

from endf_parserpy import EndfParserFactory, TapeIndex
from endf_parserpy.tape import (
    split_materials,
    MaterialIndexEntry,
    SectionIndexEntry,
    TapeStructureError,
)
from endf_parserpy.tape.index import _endf_float


TESTDATA = Path(__file__).parent / "testdata"
ENDF_FILE = TESTDATA / "n_2925_29-Cu-63.endf"
RAW_EXCLUDE = tuple(range(1, 100))


@pytest.fixture(scope="module")
def parser():
    # the index is recipe-free; the parser is only used by the tests to
    # build canonical material text and to cross-check section keys
    return EndfParserFactory.create(select="python")


@pytest.fixture(scope="module")
def single(parser):
    with open(ENDF_FILE) as fh:
        raw = [line.rstrip("\n") for line in fh]
    return parser.write(parser.parse(raw, exclude=RAW_EXCLUDE))


def _make_multi(single, n=2):
    tpid, tend = single[0], single[-1]
    body = single[1:-1]
    return [tpid] + body * n + [tend]


# --------------------------------------------------------------------------
# the implicit-exponent ENDF float parser
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        (" 9.223800+4", 92238.0),
        ("-1.234567+8", -1.234567e8),
        (" 1.5", 1.5),
        ("6.140220-1", 0.614022),
        (" 2.0e3", 2000.0),
        # Fortran double-precision exponent
        ("5.438673D-4", 5.438673e-4),
        (" 1.0000D+11", 1.0e11),
        ("    2.5d3", 2500.0),
        ("           ", None),
        ("garbage", None),
    ],
)
def test_endf_float(text, expected):
    assert _endf_float(text) == expected


# --------------------------------------------------------------------------
# building the index
# --------------------------------------------------------------------------


def test_index_basic(single):
    multi = _make_multi(single, n=3)
    index = TapeIndex.from_lines(multi)

    assert len(index) == 3
    assert [m.position for m in index] == [0, 1, 2]
    assert index.tpid_line == multi[0]
    for material in index:
        assert isinstance(material, MaterialIndexEntry)
        assert material.sections  # at least one section
        for entry in material.sections.values():
            assert isinstance(entry, SectionIndexEntry)
            assert entry.length > 0
            assert entry.line_count > 0


def test_index_sections_match_parser(parser, single):
    multi = _make_multi(single, n=2)
    index = TapeIndex.from_lines(multi)
    chunks = list(split_materials(multi))

    for material, chunk in zip(index, chunks):
        parsed = parser.parse(chunk, exclude=RAW_EXCLUDE)
        expected = {(mf, mt) for mf in parsed if mf != 0 for mt in parsed[mf]}
        assert set(material.sections) == expected


def test_index_za_awr(single):
    index = TapeIndex.from_lines(_make_multi(single, n=2))
    for material in index:
        # n_2925_29-Cu-63.endf -> Cu-63 -> ZA = 1000*29 + 63
        assert material.za == 29063
        assert material.awr is not None and material.awr > 0


def test_by_mat_returns_all_repeats(single):
    # repeating one material mimics a PENDF tape: same MAT, many entries
    index = TapeIndex.from_lines(_make_multi(single, n=4))
    mat = index[0].mat
    assert index.by_mat(mat) == [0, 1, 2, 3]
    assert index.by_mat(999999) == []


def test_by_za_lookup(single):
    index = TapeIndex.from_lines(_make_multi(single, n=2))
    assert index.by_za(29063) == [0, 1]
    assert index.by_za(1) == []


# --------------------------------------------------------------------------
# byte offsets against a real file on disk
# --------------------------------------------------------------------------


def test_index_byte_offsets(single, tmp_path):
    multi = _make_multi(single, n=3)
    tape_file = tmp_path / "tape.endf"
    tape_file.write_bytes(("\n".join(multi) + "\n").encode("latin-1"))
    raw = tape_file.read_bytes()

    index = TapeIndex.from_file(tape_file)
    assert raw[index.tpid_offset : index.tpid_offset + index.tpid_length] == (
        multi[0] + "\n"
    ).encode("latin-1")

    for material in index:
        chunk = raw[
            material.byte_offset : material.byte_offset + material.byte_length
        ].decode("latin-1")
        lines = chunk.splitlines()
        # the material spans its first record through its MEND record
        assert _control(lines[-1]) == (0, 0, 0)  # MEND
        for (mf, mt), entry in material.sections.items():
            sec = raw[entry.offset : entry.offset + entry.length].decode("latin-1")
            sec_lines = sec.splitlines()
            assert len(sec_lines) == entry.line_count
            first_mat, first_mf, first_mt = _control(sec_lines[0])
            assert (first_mf, first_mt) == (mf, mt)
            assert _control(sec_lines[-1])[2] == 0  # SEND


def test_from_file_and_from_lines_agree(single, tmp_path):
    multi = _make_multi(single, n=2)
    tape_file = tmp_path / "tape.endf"
    tape_file.write_bytes(("\n".join(multi) + "\n").encode("latin-1"))

    idx_file = TapeIndex.from_file(tape_file)
    idx_lines = TapeIndex.from_lines(multi)
    for mf, ml in zip(idx_file, idx_lines):
        assert mf.byte_offset == ml.byte_offset
        assert mf.byte_length == ml.byte_length
        assert mf.sections.keys() == ml.sections.keys()


def test_index_source_stamp(single, tmp_path):
    tape_file = tmp_path / "tape.endf"
    tape_file.write_bytes(("\n".join(_make_multi(single)) + "\n").encode("latin-1"))
    index = TapeIndex.from_file(tape_file)

    stat = tape_file.stat()
    assert index.source == str(tape_file)
    assert index.source_size == stat.st_size
    assert index.source_mtime_ns == stat.st_mtime_ns


# --------------------------------------------------------------------------
# picklability and errors
# --------------------------------------------------------------------------


def test_index_pickle_roundtrip(single):
    index = TapeIndex.from_lines(_make_multi(single, n=2))
    restored = pickle.loads(pickle.dumps(index))

    assert len(restored) == len(index)
    assert restored.by_mat(index[0].mat) == index.by_mat(index[0].mat)
    for a, b in zip(index, restored):
        assert (a.position, a.mat, a.za) == (b.position, b.mat, b.za)
        assert a.sections.keys() == b.sections.keys()


def test_index_empty_input():
    with pytest.raises(TapeStructureError, match="does not contain any records"):
        TapeIndex.from_lines([])


def test_index_missing_tpid():
    not_a_tpid = " " * 66 + "1234 3  1"
    with pytest.raises(TapeStructureError, match="tape head"):
        TapeIndex.from_lines([not_a_tpid])


def test_index_dangling_material():
    tpid = " " * 66 + "   1 0  0"
    record = " " * 66 + "1234 3  1"
    with pytest.raises(TapeStructureError, match="ends in the middle"):
        TapeIndex.from_lines([tpid, record])


def _control(line):
    def field(text):
        try:
            return int(text)
        except ValueError:
            return 0

    return field(line[66:70]), field(line[70:72]), field(line[72:75])
