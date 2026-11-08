############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/08
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
in chunks and never holds it wholly in memory. Within a chunk, the
records are taken in windows of consecutive records of equal byte
width, and the control fields of all records of a window are compared
in one bulk operation -- with ``numpy`` if it is installed, otherwise
with Python big-integer arithmetic -- so the per-record work runs in C.
A record of another width (e.g. a CRLF line among LF lines, or a line
with sequence numbers) merely starts the next window. The result is
identical to that of the record-by-record scan used by
:meth:`TapeIndex.from_lines`, for well-formed and malformed tapes
alike.
"""

import os
import re
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

# The kinds of the records collected by a scan with ``_ScanState.events``
# (see framing.py): the event ``(kind, offset, line, MAT, MF, MT)`` gives
# the byte offset of the record, its bytes without the newline (or None
# for a section event) and its control numbers as read by _control_int.
# A section event stands for the first record of a run of records of a
# section (MAT, MF and MT positive) with equal control fields; every
# other record that is not blank is a record event, and a blank record a
# blank event. The scan of the index alone collects no events.
_EV_TPID = 0
_EV_NO_TPID = 1
_EV_BLANK = 2
_EV_SECTION = 3
_EV_RECORD = 4


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

    Holds the tape head once found and the progress of the MAT/MF/MT
    state machine -- the material under construction, the section under
    construction and the list of finished materials. The same state is
    driven record by record by :func:`_scan_record` and run by run by
    the bulk scan of :func:`_scan_rows`; both feed it through the shared
    :func:`_consume_run`, and it is carried across the blocks of a file.
    """

    __slots__ = (
        "materials",
        "cur",
        "sec_key",
        "sec_offset",
        "sec_length",
        "sec_lines",
        "prev_ctrl",
        "tpid",
        "head_done",
        "ignore_missing_tpid",
        "done",
        "events",
        "lenient",
    )

    def __init__(self, ignore_missing_tpid=False, events=None, lenient=False):
        self.ignore_missing_tpid = ignore_missing_tpid
        # the positions of the MEND and TEND records are not relied upon
        # (the scan of endf-cli validate with ignore_send_records, see
        # framing.py): a TEND record does not end the scan, a section of
        # another MAT number ends the open material, and so does the end
        # of the file
        self.lenient = lenient
        # a list to which the records that matter for the framing structure
        # are appended (see framing.py), or None (the index alone)
        self.events = events
        self.materials = []
        self.cur = None  # the MaterialIndexEntry under construction, or None
        self.sec_key = None  # (MF, MT) of the section under construction
        self.sec_offset = 0
        self.sec_length = 0
        self.sec_lines = 0
        # the control field of the previous record if a record with an
        # equal control field continues the section under construction
        self.prev_ctrl = None
        self.tpid = None  # (line, offset, length) of the tape head, once found
        self.head_done = False  # the tape head phase is over (see _scan_tpid)
        self.done = False  # a TEND record has been seen

    def flush_section(self):
        # store a section that was left open (e.g. a missing SEND record)
        if self.sec_key is not None and self.cur is not None:
            self.cur.sections[self.sec_key] = SectionIndexEntry(
                self.sec_offset, self.sec_length, self.sec_lines
            )
        self.sec_key = None

    def close_material(self, end):
        """Store the open material, which ends at the offset ``end``."""
        self.flush_section()
        self.cur.byte_length = end - self.cur.byte_offset
        self.materials.append(self.cur)
        self.cur = None

    def result(self, end=None):
        """Return ``(materials, tpid)`` of a finished scan.

        ``tpid`` is ``None`` if the tape has no tape head and the scan
        ran with ``ignore_missing_tpid``. ``end`` is the size of the
        file, at which a lenient scan ends an open material.
        """
        if not self.head_done:
            raise TapeStructureError("the tape does not contain any records")
        if self.cur is not None and self.lenient and end is not None:
            self.close_material(end)
        if self.cur is not None:
            raise TapeStructureError(
                "the tape ends in the middle of a material; the final MEND or "
                "TEND record is missing"
            )
        return self.materials, self.tpid


def _consume_run(st, mat, mf, mt, offset, length, line_count, head_line):
    """Apply one record, or one run of identical-control records, to ``st``.

    This is the single classification of a record by its MAT/MF/MT
    control field, shared by the record-wise :func:`_scan_record` and
    the bulk :func:`_scan_rows` so the structural state machine lives in
    exactly one place.

    ``offset``, ``length`` and ``line_count`` describe the record or run
    being consumed; ``head_line`` is the decoded text of its first
    record, read for the ZA/AWR identifiers only when the run opens a
    new material. The state ``st`` is updated in place and ``st.done``
    is set once the tape end (TEND) record is reached.
    """
    if mat == -1 and not st.lenient:  # TEND: end of tape
        st.done = True
        return
    if mat > 0 and mf > 0 and mt > 0:  # regular section record(s)
        if st.lenient and st.cur is not None and mat != st.cur.mat:
            st.close_material(offset)
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
            st.close_material(offset + length)
    else:  # FEND (mat > 0, mf == 0, mt == 0), or any other record
        # a section cannot continue across such a record
        st.flush_section()


def _scan_tpid(st, part, offset, byte_length):
    """Examine one record that precedes the tape head.

    Return whether the record was consumed. Blank records are skipped;
    the first non-blank record must be the tape head (TPID), which is
    stored in ``st.tpid``. With ``ignore_missing_tpid``, a first record
    that is not a tape head starts the material data instead: ``st.tpid``
    stays ``None`` and ``False`` is returned, so that the caller applies
    the record as a regular record.
    """
    if part.strip():
        mat = _control_int(part[_MAT_COLS])
        mf = _control_int(part[_MF_COLS])
        mt = _control_int(part[_MT_COLS])
        if mat < 0 or mf != 0 or mt != 0:
            if st.ignore_missing_tpid:
                st.head_done = True
                return False
            if st.events is not None:
                st.events.append((_EV_NO_TPID, offset, part, mat, mf, mt))
            raise TapeStructureError(
                "the tape does not begin with a tape head (TPID) "
                f"record (found MAT={mat}, MF={mf}, MT={mt})"
            )
        st.tpid = (part.rstrip(b"\r").decode("latin-1"), offset, byte_length)
        st.head_done = True
        if st.events is not None:
            st.events.append((_EV_TPID, offset, part, mat, mf, mt))
    elif st.events is not None:
        st.events.append((_EV_BLANK, offset, part, 0, 0, 0))
    return True


def _scan_record(st, part, offset, byte_length):
    """Apply one record that follows the tape head to ``st``.

    ``part`` is the record without its ``"\\n"`` terminator and
    ``byte_length`` its byte length including the terminator. Only the
    structural fields are read. The MAT/MF/MT control fields occupy the
    fixed byte slice ``[66:75]`` of every record; since all records of a
    section share that slice, a record whose slice equals that of its
    predecessor continues the current section and is accumulated without
    parsing any integer. A blank record is skipped; any other record is
    classified by the shared :func:`_consume_run`.
    """
    ctrl = part[_CTRL_COLS]
    if ctrl == st.prev_ctrl:
        st.sec_length += byte_length
        st.sec_lines += 1
        return
    if not part.strip():  # blank padding record
        if st.events is not None:
            st.events.append((_EV_BLANK, offset, part, 0, 0, 0))
        return
    mat = _control_int(ctrl[0:4])
    mf = _control_int(ctrl[4:6])
    mt = _control_int(ctrl[6:9])
    if st.events is not None:
        regular = mat > 0 and mf > 0 and mt > 0
        st.events.append(
            (_EV_SECTION if regular else _EV_RECORD, offset, part, mat, mf, mt)
        )
    _consume_run(st, mat, mf, mt, offset, byte_length, 1, part.decode("latin-1"))
    # only a run of regular section records can be continued; after
    # any framing record the next record restarts
    st.prev_ctrl = ctrl if (mat > 0 and mf > 0 and mt > 0) else None


def _scan(records, ignore_missing_tpid=False):
    """Scan an iterator of ``(byte_length, line)`` records.

    Return ``(materials, tpid)`` with ``tpid = (line, offset, length)``,
    or ``tpid = None`` for a tape without a tape head scanned with
    ``ignore_missing_tpid``. The iterator is
    consumed lazily, so peak memory is independent of the number of
    records. Each record is applied by :func:`_scan_record`; a record
    that continues the current section is accumulated inline.
    """
    st = _ScanState(ignore_missing_tpid)
    offset = 0
    records = iter(records)

    # the tape head (TPID) is the first non-blank record
    for byte_length, part in records:
        if not _scan_tpid(st, part, offset, byte_length):
            # ignore_missing_tpid: the record starts the material data
            _scan_record(st, part, offset, byte_length)
        offset += byte_length
        if st.head_done:
            break

    if st.head_done:
        for byte_length, part in records:
            if part[_CTRL_COLS] == st.prev_ctrl:
                st.sec_length += byte_length
                st.sec_lines += 1
            else:
                _scan_record(st, part, offset, byte_length)
                if st.done:  # TEND: nothing meaningful follows
                    break
            offset += byte_length

    return st.result()


# A record must hold the complete control field (columns 67-75) and its
# terminator to be scanned in bulk; shorter records are scanned singly.
_MIN_BULK_WIDTH = _CTRL_COLS.stop + 1

# Bounds of the number of records examined by one bulk operation. The
# window grows while the records keep a uniform width and shrinks back
# after a record of another width, so the work spent on a window that
# turns out to be cut short stays small.
_MIN_WINDOW_ROWS = 1 << 10
_MAX_WINDOW_ROWS = 1 << 16

_NOT_NEWLINE = re.compile(b"[^\n]").search
_NONZERO = re.compile(b"[^\x00]").finditer


def _single_line_rows(buf, pos, num_rows, width):
    """Return how many leading rows hold exactly one record each.

    The ``num_rows`` rows of ``width`` bytes starting at ``buf[pos]``
    each end with ``"\\n"``, and the first row is a single record. A row
    can still contain further newlines (two short records whose widths
    add up to ``width``); the returned count stops before the first such
    row. Every row holds at least one newline, so the excess newline
    count of a prefix only grows with its length and is bisected.
    """
    end = pos + num_rows * width
    if buf.count(b"\n", pos, end) == num_rows:
        return num_rows
    lo, hi = 1, num_rows  # the first lo rows are single records, hi rows not
    while hi - lo > 1:
        mid = (lo + hi) // 2
        start = pos + lo * width
        if buf.count(b"\n", start, pos + mid * width) == mid - lo:
            lo = mid
        else:
            hi = mid
    return lo


def _bulk_rows_numpy(buf, pos, num_rows, width):
    """Find the uniform rows and their control-field runs using numpy.

    Return ``(n, starts)``: the rows ``[0, n)`` of ``width`` bytes from
    ``buf[pos]`` are single records, and ``starts`` lists the first row
    of every run of identical control fields among them. See
    :func:`_bulk_rows_python` for the variant used without numpy.
    """
    arr = _np.frombuffer(buf, dtype=_np.uint8, count=num_rows * width, offset=pos)
    arr = arr.reshape(num_rows, width)
    terminated = arr[:, width - 1] == 0x0A
    n = num_rows if terminated.all() else int(terminated.argmin())
    # a row holding a further newline contains more than one record
    inner = arr[:n, : width - 1] == 0x0A
    if inner.any():
        n = int(_np.argmax(inner.any(axis=1)))
    if n == 1:
        return 1, [0]
    ctrl = arr[:n, _CTRL_COLS]
    boundary = _np.flatnonzero(_np.any(ctrl[1:] != ctrl[:-1], axis=1))
    return n, [0] + (boundary + 1).tolist()


def _bulk_rows_python(buf, pos, num_rows, width):
    """Find the uniform rows and their control-field runs without numpy.

    Same contract as :func:`_bulk_rows_numpy`. Each control column is
    gathered across the rows by an extended slice and read as one big
    integer, one byte per row; shifting it by one byte and XOR-ing with
    itself leaves a non-zero byte exactly where a row's column differs
    from its predecessor's, so the comparison runs in C.
    """
    end = pos + num_rows * width
    terminators = buf[pos + width - 1 : end : width]
    if terminators == b"\n" * num_rows:
        n = num_rows
    else:
        n = _NOT_NEWLINE(terminators).start()
    n = _single_line_rows(buf, pos, n, width)
    if n == 1:
        return 1, [0]
    end = pos + n * width
    mask = (1 << (8 * (n - 1))) - 1
    diff = 0
    for col in range(_CTRL_COLS.start, _CTRL_COLS.stop):
        column = int.from_bytes(buf[pos + col : end : width], "big")
        diff |= (column >> 8) ^ (column & mask)
    if not diff:
        return n, [0]
    return n, [0] + [m.start() + 1 for m in _NONZERO(diff.to_bytes(n - 1, "big"))]


def _scan_rows(st, buf, pos, num_rows, width, starts, base):
    """Apply ``num_rows`` single-record rows of ``width`` bytes to ``st``.

    ``starts`` lists the first row of every run of identical control
    fields. A run of regular section records is applied as a whole,
    exactly as :func:`_scan_record` applies its records one by one;
    every other run (framing or blank records) is applied record by
    record.
    """
    ends = starts[1:] + [num_rows]
    for start, end in zip(starts, ends):
        offset = pos + start * width
        ctrl = buf[offset + _CTRL_COLS.start : offset + _CTRL_COLS.stop]
        if ctrl == st.prev_ctrl:
            st.sec_length += (end - start) * width
            st.sec_lines += end - start
            continue
        mat = _control_int(ctrl[0:4])
        mf = _control_int(ctrl[4:6])
        mt = _control_int(ctrl[6:9])
        if mat > 0 and mf > 0 and mt > 0:
            head_line = buf[offset : offset + width].decode("latin-1")
            run_length = (end - start) * width
            if st.events is not None:
                st.events.append((_EV_SECTION, base + offset, None, mat, mf, mt))
            _consume_run(
                st, mat, mf, mt, base + offset, run_length, end - start, head_line
            )
            st.prev_ctrl = ctrl
            continue
        # framing or blank records: as _scan_record, one by one; all of
        # them share the control field just parsed
        for row in range(start, end):
            offset = pos + row * width
            part = buf[offset : offset + width - 1]
            if not part.strip():  # blank record
                if st.events is not None:
                    st.events.append((_EV_BLANK, base + offset, part, 0, 0, 0))
                continue
            if st.events is not None:
                st.events.append((_EV_RECORD, base + offset, part, mat, mf, mt))
            _consume_run(st, mat, mf, mt, base + offset, width, 1, "")
            st.prev_ctrl = None
            if st.done:
                return


def _scan_block(st, buf, end, base):
    """Apply the whole records ``buf[:end]`` to ``st``.

    ``buf[end - 1]`` is a newline and ``base`` the file offset of
    ``buf[0]``. The records are taken in windows of consecutive records
    of one byte width: :func:`_bulk_rows_numpy` -- or, without numpy or
    for a short window, where its fixed cost dominates,
    :func:`_bulk_rows_python` -- locates the extent of the window and
    the runs of identical control fields within it in one bulk
    operation, and :func:`_scan_rows` applies those runs. A record of a
    different width merely starts the next window, so records of mixed
    widths (CRLF and LF line ends, records with or without sequence
    numbers) keep the scan in bulk mode. Records too short to hold the
    control field, and those before the tape head, are applied singly.
    """
    pos = 0
    window = _MIN_WINDOW_ROWS
    while pos < end:
        nl = buf.find(b"\n", pos, end)
        width = nl + 1 - pos
        if not st.head_done or width < _MIN_BULK_WIDTH:
            if not st.head_done:
                if not _scan_tpid(st, buf[pos:nl], base + pos, width):
                    # ignore_missing_tpid: the record starts the material
                    # data
                    _scan_record(st, buf[pos:nl], base + pos, width)
            else:
                _scan_record(st, buf[pos:nl], base + pos, width)
            if st.done:
                return
            pos = nl + 1
            continue
        num_rows = min((end - pos) // width, window)
        if _np is not None and num_rows > _MIN_WINDOW_ROWS:
            n, starts = _bulk_rows_numpy(buf, pos, num_rows, width)
        else:
            n, starts = _bulk_rows_python(buf, pos, num_rows, width)
        if n == num_rows:
            window = min(4 * window, _MAX_WINDOW_ROWS)
        else:
            window = _MIN_WINDOW_ROWS
        _scan_rows(st, buf, pos, n, width, starts, base)
        if st.done:
            return
        pos += n * width


def _scan_file(fh, chunk_bytes, ignore_missing_tpid=False):
    """Structural scan of an open binary tape file.

    Return ``(materials, tpid)``, the same result as :func:`_scan` over
    the records of the file, raising the same
    errors. Records are delimited by ``"\\n"`` only; a record keeps a
    preceding ``"\\r"``. The file is read in blocks of about
    ``chunk_bytes``, each trimmed to whole records (a partial final
    record is re-read with the next block), so peak memory stays a small
    multiple of ``chunk_bytes`` unless a single record is longer.
    """
    st = _ScanState(ignore_missing_tpid)
    _scan_file_into(st, fh, chunk_bytes)
    return st.result()


def _scan_file_into(st, fh, chunk_bytes):
    """Apply the records of an open binary tape file to ``st``.

    The scan of :func:`_scan_file`, which ends at the TEND record or at
    the end of the file; the state is not checked for completeness.
    """
    base = 0
    read_size = chunk_bytes
    while not st.done:
        buf = fh.read(read_size)
        if not buf:
            break
        end = buf.rfind(b"\n") + 1
        if end == 0:
            if len(buf) < read_size:  # an unterminated final record
                if not st.head_done:
                    if not _scan_tpid(st, buf, base, len(buf)):
                        _scan_record(st, buf, base, len(buf))
                else:
                    _scan_record(st, buf, base, len(buf))
                break
            # a record longer than the block: read a larger block
            read_size *= 2
            fh.seek(base)
            continue
        read_size = chunk_bytes
        _scan_block(st, buf, end, base)
        base += end
        if end < len(buf):
            fh.seek(base)


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
    tpid_line : str or None
        The tape head (TPID) record, or ``None`` for a tape without a
        tape head indexed with ``ignore_missing_tpid=True``.
    tpid_offset, tpid_length : int or None
        Byte location of the TPID record, or ``None`` (see
        ``tpid_line``).
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
    def from_file(
        cls,
        path,
        *,
        chunk_bytes=_DEFAULT_CHUNK_BYTES,
        ignore_missing_tpid=False,
    ):
        """Build an index of the ENDF tape stored at ``path``.

        The tape is read in blocks of about ``chunk_bytes``, so peak
        memory during indexing stays a small multiple of ``chunk_bytes``
        regardless of the tape size. With ``ignore_missing_tpid=True``, a
        tape whose first record is already a section record (instead of
        the tape head demanded by the ENDF-6 format) is accepted: the
        record starts the first material and the ``tpid_*`` attributes of
        the index are ``None``.
        """
        path = os.fspath(path)
        with open(path, "rb") as fh:
            materials, tpid = _scan_file(fh, chunk_bytes, ignore_missing_tpid)
        return cls._from_scan(path, materials, tpid)

    @classmethod
    def _from_scan(cls, path, materials, tpid):
        """Build the index of the file ``path`` from the result of its scan.

        ``materials`` and ``tpid`` are the result of :func:`_scan_file`
        (or of ``_ScanState.result``) for the file, which is still as it
        was scanned.
        """
        stat = os.stat(path)
        tpid = tpid if tpid is not None else (None, None, None)
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
    def from_lines(cls, lines, source=None, *, ignore_missing_tpid=False):
        """Build an index from an iterable of ENDF tape lines.

        The lines are consumed lazily. Byte offsets are computed
        assuming a single ``"\\n"`` terminates each line; they are
        therefore only exact for a file written that way. Use
        :meth:`from_file` when exact on-disk offsets are required. For
        ``ignore_missing_tpid`` see :meth:`from_file`.
        """
        materials, tpid = _scan(_iter_line_records(lines), ignore_missing_tpid)
        tpid = tpid if tpid is not None else (None, None, None)
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
