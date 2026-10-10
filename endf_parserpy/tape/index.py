############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Structural index of a multi-material ENDF tape.

The index records, for every material on a tape, its MAT number, the
ZA/AWR identifiers read from the first HEAD record, the byte range it
occupies in the file and the byte range of every (MF, MT) section it
contains.

It is built by a single linear scan that inspects only the *structural*
parts of the ENDF-6 format: the MAT/MF/MT control fields (columns
67-75) and the universal HEAD-record layout (``C1=ZA``, ``C2=AWR``). No
ENDF recipe is consulted and no section body is interpreted, so the
index is cheap to build and completely independent of the parsing
engine.

The scan is memory-bounded: :meth:`TapeIndex.from_file` reads the file
in chunks and never holds it wholly in memory. When ``numpy`` is
installed and the tape is a uniform array of fixed-width records (the
common case), a vectorized fast path extracts every record's control
field in one bulk operation per chunk; it produces an index identical
to the streaming line-by-line scan it falls back to for any tape that
is not uniform-width.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .errors import TapeStructureError
from .records import _control_int, _MAT_COLS, _MF_COLS, _MT_COLS, _CTRL_COLS

try:
    import numpy as _np
except ImportError:  # pragma: no cover - numpy is an optional accelerator
    _np = None

# default read granularity for from_file(); bounds peak memory during
# indexing to a small multiple of this regardless of the tape size
_DEFAULT_CHUNK_BYTES = 16 << 20


def _endf_float(field_text):
    """Parse an 11-column ENDF number field; return ``None`` on failure.

    ENDF numbers may use an implicit exponent, e.g. ``9.223800+4`` for
    ``9.223800e+4``, and a Fortran double-precision exponent, e.g.
    ``5.438673D-4``, is accepted as well. ``None`` is returned rather
    than raising, so that an unparsable identifier field never aborts an
    index build.

    This is a deliberately minimal number parser, kept independent of
    the parsing engine so the index stays recipe- and engine-free; it
    only needs to recover the ZA/AWR identifiers from a HEAD record.
    """
    text = field_text.strip().replace("D", "e").replace("d", "e")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        pass
    # implicit-exponent form: a sign that is neither the leading sign
    # nor preceded by 'e'/'E' marks the start of the exponent
    for i in range(len(text) - 1, 0, -1):
        if text[i] in "+-" and text[i - 1] not in "eE":
            try:
                return float(text[:i] + "e" + text[i:])
            except ValueError:
                return None
    return None


def _read_za_awr(line):
    """Read ``(ZA, AWR)`` from the C1/C2 fields of a HEAD record."""
    za = _endf_float(line[0:11])
    awr = _endf_float(line[11:22])
    za_int = int(round(za)) if za is not None else None
    return za_int, awr


@dataclass
class SectionIndexEntry:
    """Location of one (MF, MT) section within the tape file.

    Attributes
    ----------
    offset : int
        Byte offset of the section's first record.
    length : int
        Total byte length of the section, including its SEND record.
    line_count : int
        Number of records in the section, including its SEND record.
    """

    offset: int
    length: int
    line_count: int


@dataclass
class MaterialIndexEntry:
    """Location and identity of one material on the tape.

    Instances are intended to be treated as read-only.

    Attributes
    ----------
    position : int
        Zero-based position of the material on the tape; this is the
        material's canonical identity (see design decision D1).
    mat : int
        ENDF MAT number. Not unique: PENDF tapes repeat the same
        MAT at different temperatures.
    za : int or None
        ZA identifier (``1000*Z + A``) from the first HEAD record, or
        ``None`` if it could not be read.
    awr : float or None
        Atomic weight ratio from the first HEAD record, or ``None``.
    byte_offset : int
        Byte offset of the material's first record.
    byte_length : int
        Total byte length of the material, including its MEND record.
    sections : dict[tuple[int, int], SectionIndexEntry]
        The (MF, MT) sections contained in the material.
    """

    position: int
    mat: int
    za: Optional[int]
    awr: Optional[float]
    byte_offset: int
    byte_length: int
    sections: Dict[Tuple[int, int], SectionIndexEntry] = field(default_factory=dict)


def _iter_file_records(fh):
    """Yield ``(byte_length, line)`` for each record of a binary file.

    Records are delimited by ``"\\n"`` only, matching binary-mode file
    iteration. ``byte_length`` includes the terminator; ``line`` has a
    trailing ``"\\n"`` removed (a preceding ``"\\r"`` is kept, since the
    scanner reads only the control columns and strips it itself where
    text is needed). Iterating the handle keeps memory O(1).
    """
    for raw in fh:
        if raw.endswith(b"\n"):
            yield len(raw), raw[:-1]
        else:
            yield len(raw), raw


def _iter_line_records(lines):
    """Yield ``(byte_length, line)`` for an iterable of text lines.

    Byte lengths assume each line is terminated by a single ``"\\n"``,
    so the offsets they produce are only exact for a file written that
    way.
    """
    for line in lines:
        encoded = line.rstrip("\r\n").encode("latin-1", errors="replace")
        yield len(encoded) + 1, encoded


class _ScanState:
    """Carried state of a structural tape scan.

    Holds the progress of the MAT/MF/MT state machine -- the material
    under construction, the section under construction and the list of
    finished materials. The same state is driven record by record by
    the streaming :func:`_scan` and run by run, across block
    boundaries, by the vectorized :func:`_scan_chunk_runs`; both feed it
    through the shared :func:`_consume_run`.
    """

    __slots__ = (
        "materials",
        "cur",
        "sec_key",
        "sec_offset",
        "sec_length",
        "sec_lines",
        "done",
        "uniform",
    )

    def __init__(self):
        self.materials = []
        self.cur = None  # the MaterialIndexEntry under construction, or None
        self.sec_key = None  # (MF, MT) of the section under construction
        self.sec_offset = 0
        self.sec_length = 0
        self.sec_lines = 0
        self.done = False  # a TEND record has been seen
        self.uniform = True  # cleared if the tape proves not uniform-width

    def flush_section(self):
        # store a section that was left open (e.g. a missing SEND record)
        if self.sec_key is not None and self.cur is not None:
            self.cur.sections[self.sec_key] = SectionIndexEntry(
                self.sec_offset, self.sec_length, self.sec_lines
            )
        self.sec_key = None


def _consume_run(st, mat, mf, mt, offset, length, line_count, head_line):
    """Apply one record, or one run of identical-control records, to ``st``.

    This is the single classification of a record by its MAT/MF/MT
    control field, shared by the streaming :func:`_scan` and the
    vectorized :func:`_scan_chunk_runs` so the structural state machine
    lives in exactly one place.

    ``offset``, ``length`` and ``line_count`` describe the record or run
    being consumed; ``head_line`` is the decoded text of its first
    record, read for the ZA/AWR identifiers only when the run opens a
    new material. The state ``st`` is updated in place and ``st.done``
    is set once the tape end (TEND) record is reached.
    """
    if mat == -1:  # TEND: end of tape
        st.done = True
        return
    if mat > 0 and mf > 0 and mt > 0:  # regular section record(s)
        if st.cur is None:
            za, awr = _read_za_awr(head_line)
            # built up field by field as the scan proceeds; byte_length
            # stays a placeholder until the closing MEND record is seen
            st.cur = MaterialIndexEntry(
                position=len(st.materials),
                mat=mat,
                za=za,
                awr=awr,
                byte_offset=offset,
                byte_length=0,
            )
        if (mf, mt) != st.sec_key:
            st.flush_section()
            st.sec_key = (mf, mt)
            st.sec_offset = offset
            st.sec_length = 0
            st.sec_lines = 0
        st.sec_length += length
        st.sec_lines += line_count
    elif mf != 0 and mt == 0:  # SEND: end of section
        if st.sec_key is not None and st.cur is not None:
            st.cur.sections[st.sec_key] = SectionIndexEntry(
                st.sec_offset, st.sec_length + length, st.sec_lines + line_count
            )
        st.sec_key = None
    elif mat == 0 and mf == 0 and mt == 0:  # MEND: end of material
        st.flush_section()
        if st.cur is not None:
            st.cur.byte_length = offset + length - st.cur.byte_offset
            st.materials.append(st.cur)
            st.cur = None
    else:  # FEND (mat > 0, mf == 0, mt == 0), or any other record
        # a section cannot continue across such a record
        st.flush_section()


def _scan(records):
    """Scan an iterator of ``(byte_length, line)`` records.

    Return ``(materials, (tpid_line, offset, length))``. The iterator is
    consumed lazily, so a streaming source (see :func:`_iter_file_records`)
    keeps peak memory independent of the tape size.

    Only the structural fields are read. The MAT/MF/MT control fields
    occupy the fixed byte slice ``[66:75]`` of every record; since all
    records of a section share that slice, a record whose slice is
    unchanged from its predecessor is known to continue the current
    section and is accumulated without parsing any integer. This fast
    path covers the great majority of records; a record that starts a
    new run is classified by the shared :func:`_consume_run`.
    """
    st = _ScanState()
    prev_ctrl = None  # the [66:75] control slice of the previous record
    offset = 0
    tpid = None

    records = iter(records)

    # the tape head (TPID) is the first non-blank record
    for byte_length, part in records:
        if part.strip():
            mat = _control_int(part[_MAT_COLS])
            mf = _control_int(part[_MF_COLS])
            mt = _control_int(part[_MT_COLS])
            if mat < 0 or mf != 0 or mt != 0:
                raise TapeStructureError(
                    "the tape does not begin with a tape head (TPID) "
                    f"record (found MAT={mat}, MF={mf}, MT={mt})"
                )
            tpid = (part.rstrip(b"\r").decode("latin-1"), offset, byte_length)
            offset += byte_length
            break
        offset += byte_length
    if tpid is None:
        raise TapeStructureError("the tape does not contain any records")

    for byte_length, part in records:
        ctrl = part[_CTRL_COLS]

        # fast path: the control fields are unchanged, so this record
        # continues the section currently under construction
        if ctrl == prev_ctrl:
            st.sec_length += byte_length
            st.sec_lines += 1
            offset += byte_length
            continue

        if not part.strip():  # blank padding record
            offset += byte_length
            continue

        mat = _control_int(ctrl[0:4])
        mf = _control_int(ctrl[4:6])
        mt = _control_int(ctrl[6:9])
        _consume_run(st, mat, mf, mt, offset, byte_length, 1, part.decode("latin-1"))
        if st.done:  # TEND: nothing meaningful follows
            break
        # only a run of regular section records can be extended by the
        # fast path; after any framing record the next record restarts
        prev_ctrl = ctrl if (mat > 0 and mf > 0 and mt > 0) else None
        offset += byte_length

    if st.cur is not None:
        raise TapeStructureError(
            "the tape ends in the middle of a material; the final MEND or "
            "TEND record is missing"
        )
    return st.materials, tpid


def _scan_chunk_runs(buf, num_records, start_row, base, line_width, st):
    """Run the structural state machine over one block of whole records.

    ``buf`` holds at least ``num_records`` records of ``line_width``
    bytes; rows ``start_row`` onward are processed (``start_row`` skips
    the TPID in the first block). ``base`` is the byte offset of
    ``buf[0]`` within the file. The carried state ``st`` is updated in
    place; ``st.uniform`` is cleared and the scan abandoned if a row is
    not newline-terminated or a data record carries a blank control
    field.

    The MAT/MF/MT control field of every record is the byte slice
    ``[66:75]``; a section or material boundary is exactly a row whose
    control field differs from its predecessor, so the per-record scan
    collapses into a loop over *runs* of identical control fields. Each
    run is then classified by the shared :func:`_consume_run`.
    """
    if num_records <= start_row:
        return
    flat = _np.frombuffer(buf, dtype=_np.uint8)
    arr = flat[: num_records * line_width].reshape(num_records, line_width)
    # certain fixed-width check: the last byte of every record is "\n"
    if not bool(_np.all(arr[:, line_width - 1] == 0x0A)):
        st.uniform = False
        return
    ctrl = arr[:, _CTRL_COLS]  # the MAT/MF/MT control field of every record

    # segment the rows into runs of identical control fields
    window = ctrl[start_row:]
    if len(window) == 1:
        starts = [start_row]
    else:
        boundary = _np.any(window[1:] != window[:-1], axis=1)
        starts = [start_row] + (_np.flatnonzero(boundary) + 1 + start_row).tolist()
    ends = starts[1:] + [num_records]

    for start, end in zip(starts, ends):
        ctrl_field = ctrl[start].tobytes()
        run_offset = base + start * line_width
        run_length = (end - start) * line_width
        if not ctrl_field.strip():  # blank-control run
            if buf[start * line_width : end * line_width].strip():
                st.uniform = False  # a record with data but a blank control
                return
            continue
        mat = _control_int(ctrl_field[0:4])
        mf = _control_int(ctrl_field[4:6])
        mt = _control_int(ctrl_field[6:9])
        head_line = buf[start * line_width : start * line_width + line_width].decode(
            "latin-1"
        )
        _consume_run(st, mat, mf, mt, run_offset, run_length, end - start, head_line)
        if st.done:  # TEND: end of tape
            return


def _vec_scan_file(fh, chunk_bytes):
    """Chunked vectorized structural scan of an open binary tape file.

    Read the tape in blocks of about ``chunk_bytes`` and apply the
    vectorized scan to each, so peak memory stays a small multiple of
    ``chunk_bytes`` regardless of the tape size. Return
    ``(materials, tpid)`` for a clean uniform fixed-width tape, or
    ``None`` for any tape that is not uniform-width or not cleanly
    structured; the caller then falls back to :func:`_scan`, which is
    the authority for both the index and any structural error.

    A tape whose only irregularity is an unterminated final TEND record
    and/or a few trailing blank lines is still accepted: the partial
    trailing record is trimmed, gated on that tail being benign (only
    whitespace, or a TEND record), so a genuinely truncated record is
    never silently dropped.
    """
    first = fh.read(chunk_bytes)
    if not first:
        return None
    first_nl = first.find(b"\n")
    if first_nl < 0:
        return None
    line_width = first_nl + 1
    # the control field ends at column 75, so a record must be wide
    # enough to contain it
    if line_width < 76:
        return None
    num0 = len(first) // line_width
    if num0 == 0:
        return None

    # locate the TPID -- the first record with a non-blank control field
    flat = _np.frombuffer(first, dtype=_np.uint8)
    arr0 = flat[: num0 * line_width].reshape(num0, line_width)
    if not bool(_np.all(arr0[:, line_width - 1] == 0x0A)):
        return None
    ctrl0 = arr0[:, _CTRL_COLS]
    nonblank = _np.any(ctrl0 != 0x20, axis=1)
    if not bool(_np.any(nonblank)):
        return None
    tpid_row = int(_np.argmax(nonblank))
    if tpid_row and first[: tpid_row * line_width].strip():
        return None  # non-blank content before the TPID
    head = ctrl0[tpid_row].tobytes()
    if (
        _control_int(head[0:4]) < 0
        or _control_int(head[4:6]) != 0
        or _control_int(head[6:9]) != 0
    ):
        return None  # not a TPID record (a TEND has MAT=-1)
    tpid_offset = tpid_row * line_width
    tpid = (
        first[tpid_offset : tpid_offset + line_width].rstrip(b"\r\n").decode("latin-1"),
        tpid_offset,
        line_width,
    )

    st = _ScanState()
    # scan the records of the first block that follow the TPID
    _scan_chunk_runs(first, num0, tpid_row + 1, 0, line_width, st)
    if not st.uniform:
        return None

    if not st.done:
        # continue with record-aligned blocks; rewind to the last whole
        # record of the first block so its partial tail is re-read
        read_size = max(1, chunk_bytes // line_width) * line_width
        fh.seek(num0 * line_width)
        base = num0 * line_width
        while not st.done:
            block = fh.read(read_size)
            if not block:
                break
            final = len(block) < read_size
            remainder = len(block) % line_width
            if remainder:
                # a partial trailing record: accept it only if benign
                tail = block[len(block) - remainder :]
                if tail.strip() and _control_int(tail[_MAT_COLS]) != -1:
                    return None
                block = block[: len(block) - remainder]
            if block:
                num_records = len(block) // line_width
                _scan_chunk_runs(block, num_records, 0, base, line_width, st)
                if not st.uniform:
                    return None
                base += len(block)
            if final:
                break

    if st.cur is not None:
        return None  # truncated tape -- let _scan raise the structural error
    return st.materials, tpid


class TapeIndex:
    """A structural index over the materials of an ENDF tape.

    Build one with :meth:`from_file` (exact on-disk byte offsets) or
    :meth:`from_lines`. The index supports ``len()``, iteration and
    integer position indexing, and provides :meth:`by_mat` and
    :meth:`by_za` secondary lookups. It is recipe-free and picklable.

    Attributes
    ----------
    materials : list[MaterialIndexEntry]
        The materials, in tape order.
    tpid_line : str
        The tape head (TPID) record.
    tpid_offset, tpid_length : int
        Byte location of the TPID record.
    source : str or None
        Path of the indexed file, if built with :meth:`from_file`.
    source_size, source_mtime_ns : int or None
        Size and modification time of the source file at index time;
        usable to detect that the file changed after indexing.
    """

    def __init__(
        self,
        materials,
        tpid_line,
        tpid_offset,
        tpid_length,
        source=None,
        source_size=None,
        source_mtime_ns=None,
    ):
        self.materials = list(materials)
        self.tpid_line = tpid_line
        self.tpid_offset = tpid_offset
        self.tpid_length = tpid_length
        self.source = source
        self.source_size = source_size
        self.source_mtime_ns = source_mtime_ns
        self._by_mat = {}
        self._by_za = {}
        for entry in self.materials:
            self._by_mat.setdefault(entry.mat, []).append(entry.position)
            if entry.za is not None:
                self._by_za.setdefault(entry.za, []).append(entry.position)

    @classmethod
    def from_file(cls, path, *, chunk_bytes=_DEFAULT_CHUNK_BYTES):
        """Build an index of the ENDF tape stored at ``path``.

        The tape is read in blocks of about ``chunk_bytes``, so peak
        memory during indexing stays a small multiple of ``chunk_bytes``
        regardless of the tape size.
        """
        path = os.fspath(path)
        with open(path, "rb") as fh:
            result = None
            if _np is not None:
                result = _vec_scan_file(fh, chunk_bytes)
                if result is None:
                    fh.seek(0)  # the fast path consumed part of the file
            if result is None:
                result = _scan(_iter_file_records(fh))
        materials, tpid = result
        stat = os.stat(path)
        return cls(
            materials,
            tpid[0],
            tpid[1],
            tpid[2],
            source=path,
            source_size=stat.st_size,
            source_mtime_ns=stat.st_mtime_ns,
        )

    @classmethod
    def from_lines(cls, lines, source=None):
        """Build an index from an iterable of ENDF tape lines.

        The lines are consumed lazily. Byte offsets are computed
        assuming a single ``"\\n"`` terminates each line; they are
        therefore only exact for a file written that way. Use
        :meth:`from_file` when exact on-disk offsets are required.
        """
        materials, tpid = _scan(_iter_line_records(lines))
        return cls(materials, tpid[0], tpid[1], tpid[2], source=source)

    def by_mat(self, mat):
        """Return the positions of all materials with this MAT number."""
        return list(self._by_mat.get(mat, ()))

    def by_za(self, za):
        """Return the positions of all materials with this ZA identifier."""
        return list(self._by_za.get(za, ()))

    def __len__(self):
        return len(self.materials)

    def __iter__(self):
        return iter(self.materials)

    def __getitem__(self, position):
        return self.materials[position]

    def __repr__(self):
        source = f", source={self.source!r}" if self.source else ""
        return f"TapeIndex({len(self.materials)} materials{source})"
