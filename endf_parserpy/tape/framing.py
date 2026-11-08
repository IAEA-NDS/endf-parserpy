############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Check of the framing records of an ENDF tape.

An ENDF-6 tape is a tape head (TPID) followed by materials. Every
section ends with a SEND record ``[MAT, MF, 0]``, every MF of a
material with a FEND record ``[MAT, 0, 0]``, every material with a
MEND record ``[0, 0, 0]``, and the tape with a TEND record
``[-1, 0, 0]``; only blank lines may follow it. The columns 1-66 of
these records hold zeros or are blank.

:func:`check_framing` checks these rules for a whole file, as a full
parse with :class:`~endf_parserpy.EndfParserPy` does, but for any
number of materials. It is the complement of the parsing of the
sections one by one by :class:`~endf_parserpy.tape.EndfFile`, which
hands each section to the parser with generated FEND/MEND/TEND records,
so that the parsers do not see those of the file.

The records are taken from the structural scan of the tape index (see
:mod:`.index`), which collects the records that matter for the
framing (the first record of every run of section records, every other
record and the blank lines) in its bulk scan; the check then looks at
these records only. The control fields of the framing records are
read strictly here (see :func:`.records._strict_control_int`), while
the index reads them leniently.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional

from .errors import TapeStructureError
from .index import (
    TapeIndex,
    _DEFAULT_CHUNK_BYTES,
    _EV_BLANK,
    _EV_NO_TPID,
    _EV_RECORD,
    _EV_SECTION,
    _EV_TPID,
    _ScanState,
    _scan_file_into,
)
from .records import _MAT_COLS, _MF_COLS, _MT_COLS, _strict_control_int


@dataclass(frozen=True)
class FramingProblem:
    """A violation of the framing rules found by :func:`check_framing`.

    Attributes
    ----------
    line : int
        Number of the line of the file (counting from 1) at which the
        problem is found. For a record that is missing, this is the line
        at which it is missing, i.e. the next record of the file, or the
        last line of the file if the file ends without it.
    message : str
        Description of the problem.
    """

    line: int
    message: str

    def __str__(self):
        return f"line {self.line}: {self.message}"


# the names of the control fields and their columns (counting from 1)
_CTRL_FIELDS = (
    ("MAT", _MAT_COLS, "67-70"),
    ("MF", _MF_COLS, "71-72"),
    ("MT", _MT_COLS, "73-75"),
)

_NON_PRINTABLE = re.compile(rb"[^\x20-\x7e]")
# a number of the form ` 0.000000+0`, `0.0`, `0`: as the plain number of
# EndfParserPy (fortran_utils._match_plain_number)
_PLAIN_NUMBER = re.compile(rb" *([+-]?(?:[0-9]*\.)?[0-9]+)(?:([+-][0-9]+))? *")
_INT_NUMBER = re.compile(rb" *[+-]?[0-9]+ *")
_FIELD_WIDTH = 11

_AFTER_TEND = (
    "only blank lines may follow the TEND record (the end of the tape), "
    "found a line that is not blank"
)


def _is_parser_blank(line):
    """Whether a line is blank for the parsers: only blanks and tabs."""
    return line.rstrip(b"\r").strip(b" \t") == b""


def _is_zero_float(field, accept_spaces, accept_d_exponent):
    """Whether a float field reads as zero, as with ``fortstr2float``."""
    if field.strip() == b"":
        return True
    m = _PLAIN_NUMBER.fullmatch(field)
    if m is not None:
        return float(m.group(1)) == 0.0
    text = field.decode("latin-1")
    if accept_spaces:
        text = text.replace(" ", "")
    if accept_d_exponent:
        text = text.replace("D", "E").replace("d", "e")
    text = re.sub(r"(?<=[0-9])([+-])", r"E\1", text)
    try:
        return float(text) == 0.0
    except ValueError:
        return False


def _is_zero_int(field):
    """Whether an integer field is blank or holds the integer zero."""
    if field.strip() == b"":
        return True
    return _INT_NUMBER.fullmatch(field) is not None and int(field) == 0


def _nonzero_fields(line, accept_spaces, accept_d_exponent):
    """Return the numbers (from 1) of the fields 1-6 that are not zero."""
    content = line[:66].ljust(66)
    bad = []
    for k in range(6):
        field = content[k * _FIELD_WIDTH : (k + 1) * _FIELD_WIDTH]
        if k < 2:
            ok = _is_zero_float(field, accept_spaces, accept_d_exponent)
        else:
            ok = _is_zero_int(field)
        if not ok:
            bad.append(k + 1)
    return bad


def _ctrl(mat, mf, mt):
    return f"MAT/MF/MT {mat}/{mf}/{mt}"


def _describe(kind, numbers):
    """Describe a record found in the file."""
    mat, mf, mt = numbers
    if kind == "section":
        return f"a record of section MF={mf}/MT={mt} of MAT {mat}"
    if kind == "other":
        return (
            f"a record with {_ctrl(mat, mf, mt)}, which is neither a record "
            "of a section nor a SEND, FEND, MEND or TEND record"
        )
    return f"a {kind} record ({_ctrl(mat, mf, mt)})"


def _kind(mat, mf, mt):
    """Classify a record by its control numbers.

    As the tape index, any record with MAT=-1 is taken as a TEND record
    (with the wrong numbers if MF or MT is not zero).
    """
    if mat == -1:
        return "TEND"
    if mt != 0:
        if mat > 0 and mf > 0 and mt > 0:
            return "section"
        return "other"
    if mf != 0:
        return "SEND"
    if mat == 0:
        return "MEND"
    return "FEND"


class _Checker:
    """The state machine of the framing check.

    ``level`` is the position in the structure, as in ``split_sections``
    of EndfParserPy: 3 within a section, 2 after its SEND record, 1 after
    a FEND record, 0 after the tape head or a MEND record, -1 after the
    TEND record. ``mat``, ``mf`` and ``mt`` are the numbers of the last
    section.
    """

    def __init__(self, check_ascii, number_opts):
        # the results of the checks of the control fields and of the
        # columns 1-66 by their text: framing records repeat a few forms
        self.ctrl_cache = {}
        self.content_cache = {}
        self.check_ascii = check_ascii
        self.number_opts = number_opts
        self.problems = []  # (offset, message)
        self.level = 0
        self.mat = self.mf = self.mt = None
        self.materials = 0
        # the (MF, MT) sections of the current material
        self.sections = set()
        # the numbers of the section if its SEND record was assumed for a
        # record with an invalid control field (see check_framing)
        self.assumed_send = None

    def problem(self, offset, message):
        self.problems.append((offset, message))

    def expected(self):
        """Describe what may follow at the current position."""
        mat, mf, mt = self.mat, self.mf, self.mt
        if self.level == 3:
            return (
                f"a record of section MF={mf}/MT={mt} of MAT {mat} or its SEND "
                f"record ({_ctrl(mat, mf, 0)})"
            )
        if self.level == 2:
            return (
                f"a section of MF={mf} of MAT {mat} or the FEND record "
                f"({_ctrl(mat, 0, 0)})"
            )
        if self.level == 1:
            return f"a section of MAT {mat} or the MEND record " f"({_ctrl(0, 0, 0)})"
        if self.materials == 0:
            return f"a section or the TEND record ({_ctrl(-1, 0, 0)})"
        return f"a section of a new material or the TEND record ({_ctrl(-1, 0, 0)})"

    def mismatch(self, offset, kind, numbers, note=None):
        message = f"expected {self.expected()}, found {_describe(kind, numbers)}"
        if note:
            message += f"; {note}"
        self.problem(offset, message)

    def control_numbers(self, offset, line):
        """Read the control fields of a framing record strictly.

        Return the numbers, or ``None`` after reporting an invalid field.
        """
        ctrl = line[_MAT_COLS.start : _MT_COLS.stop]
        cached = self.ctrl_cache.get(ctrl)
        if cached is None:
            numbers = []
            invalid = []
            for name, cols, columns in _CTRL_FIELDS:
                value = _strict_control_int(line[cols])
                if value is None:
                    field = line[cols].decode("latin-1")
                    invalid.append(
                        f'invalid {name} field "{field}" (columns {columns})'
                    )
                numbers.append(value)
            cached = (tuple(numbers), ", ".join(invalid))
            self.ctrl_cache[ctrl] = cached
        numbers, invalid = cached
        if invalid:
            self.problem(offset, invalid)
            return None
        return numbers

    def check_line(self, offset, line, kind):
        """The checks of the characters of a framing record."""
        if self.check_ascii:
            m = _NON_PRINTABLE.search(line.rstrip(b"\r"))
            if m is not None:
                what = "line" if kind in ("other", "blank") else f"{kind} record"
                self.problem(
                    offset,
                    f"column {m.start() + 1} of the {what} contains the "
                    f"byte 0x{m.group(0)[0]:02x}, which is not a printable ASCII "
                    "character (codes 32 to 126) as required by the ENDF-6 "
                    "format; use the option accept_non_ascii=True to accept it",
                )
        if kind in ("SEND", "FEND", "MEND", "TEND"):
            content = line[:66].rstrip(b"\r")
            bad = self.content_cache.get(content)
            if bad is None:
                bad = _nonzero_fields(content, *self.number_opts)
                self.content_cache[content] = bad
            if bad:
                if len(bad) == 1:
                    fields = f"field {bad[0]} is"
                else:
                    fields = "fields " + ", ".join(str(k) for k in bad) + " are"
                text = content.decode("latin-1").rstrip()
                self.problem(
                    offset,
                    f"the fields 1-6 (columns 1-66) of the {kind} record must "
                    f'be zero or blank, but {fields} not: "{text}"',
                )

    def section(self, offset, numbers):
        mat, mf, mt = numbers
        level = self.level
        assumed_send, self.assumed_send = self.assumed_send, None
        if level == 3 and (mat, mf, mt) == (self.mat, self.mf, self.mt):
            return  # the section continues (e.g. after a blank line)
        if level == 2 and numbers == assumed_send:
            # the record with the invalid field was a line of the section
            self.level = 3
            return
        if level == 3 and (mf, mt) == (self.mf, self.mt):
            # e.g. a damaged MAT field in a line of the section, which
            # remains the current section
            self.mismatch(offset, "section", numbers)
            return
        if level == 3:
            self.mismatch(
                offset,
                "section",
                numbers,
                f"the SEND record of section MF={self.mf}/MT={self.mt} is missing",
            )
        elif level == 2 and mat == self.mat and mf != self.mf:
            self.mismatch(
                offset,
                "section",
                numbers,
                f"the FEND record of MF={self.mf} is missing",
            )
        elif level in (1, 2) and mat != self.mat:
            missing = "MEND record is" if level == 1 else "FEND and MEND records are"
            self.mismatch(
                offset,
                "section",
                numbers,
                f"the {missing} missing",
            )
        if level == 0 or mat != self.mat:  # a new material
            self.materials += 1
            self.sections = set()
        elif (mf, mt) in self.sections:
            self.problem(
                offset,
                f"section MF={mf}/MT={mt} of MAT {mat} occurs a second time "
                "in the material",
            )
        self.sections.add((mf, mt))
        self.mat, self.mf, self.mt = mat, mf, mt
        self.level = 3

    def end_record(self, offset, kind, numbers):
        """Apply a SEND, FEND, MEND or TEND record (or another one)."""
        self.assumed_send = None
        mat, mf, mt = numbers
        level = self.level
        if kind == "SEND":
            if level == 3:
                if (mat, mf, mt) != (self.mat, self.mf, 0):
                    self.mismatch(offset, kind, numbers)
                self.level = 2
            else:
                self.mismatch(offset, kind, numbers)
        elif kind == "FEND":
            if level == 3:
                self.mismatch(
                    offset,
                    kind,
                    numbers,
                    f"the SEND record of section MF={self.mf}/MT={self.mt} is "
                    "missing",
                )
                self.level = 1
            elif level == 2:
                if mat != self.mat:
                    self.mismatch(offset, kind, numbers)
                self.level = 1
            else:
                self.mismatch(offset, kind, numbers)
        elif kind == "MEND":
            if level in (2, 3):
                missing = (
                    "SEND and FEND records are" if level == 3 else "FEND record is"
                )
                self.mismatch(offset, kind, numbers, f"the {missing} missing")
                self.level = 0
            elif level == 1:
                self.level = 0
            else:
                self.mismatch(offset, kind, numbers)
        elif kind == "TEND":
            if level > 0:
                missing = {
                    1: "MEND record is",
                    2: "FEND and MEND records are",
                    3: "SEND, FEND and MEND records are",
                }[level]
                self.mismatch(offset, kind, numbers, f"the {missing} missing")
            elif numbers != (-1, 0, 0):
                self.mismatch(offset, kind, numbers)
            self.level = -1
        else:
            self.mismatch(offset, kind, numbers)

    def end_of_file(self, offset):
        missing = {
            3: "SEND, FEND, MEND and TEND records",
            2: "FEND, MEND and TEND records",
            1: "MEND and TEND records",
            0: "TEND record",
        }[self.level]
        verb = "is" if self.level == 0 else "are"
        self.problem(offset, f"the file ends here, the {missing} {verb} missing")


def _line_numbers(path, offsets):
    """Map byte offsets of a file to line numbers (counting from 1).

    Also return the number of lines of the file. The file is read once,
    in blocks.
    """
    targets = sorted(set(offsets))
    result = {}
    count = 0
    pos = 0
    k = 0
    last_byte = b""
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_DEFAULT_CHUNK_BYTES)
            if not chunk:
                break
            end = pos + len(chunk)
            while k < len(targets) and targets[k] < end:
                result[targets[k]] = count + chunk.count(b"\n", 0, targets[k] - pos) + 1
                k += 1
            count += chunk.count(b"\n")
            pos = end
            last_byte = chunk[-1:]
    num_lines = count + (1 if last_byte not in (b"", b"\n") else 0)
    for offset in targets[k:]:
        result[offset] = max(num_lines, 1)
    return result, num_lines


def _tail_after(path, offset):
    """Return the offset of the first line after ``offset`` that is not
    blank (only blanks and tabs, see :func:`_is_parser_blank`), or None.
    """
    with open(path, "rb") as fh:
        fh.seek(offset)
        pos = offset
        rest = b""
        while True:
            chunk = fh.read(_DEFAULT_CHUNK_BYTES)
            data = rest + chunk
            lines = data.split(b"\n")
            rest = lines.pop() if chunk else b""
            for line in lines:
                if not _is_parser_blank(line):
                    return pos
                pos += len(line) + 1
            if not chunk:
                if rest and not _is_parser_blank(rest):
                    return pos
                return None


def check_framing(
    path,
    *,
    ignore_send_records=False,
    ignore_blank_lines=False,
    ignore_missing_tpid=False,
    accept_non_ascii=False,
    accept_spaces=False,
    accept_d_exponent=False,
):
    """Check the framing records of the ENDF tape stored at ``path``.

    Return the list of :class:`FramingProblem` found, in the order of
    the lines of the file; an empty list if the framing is valid. The
    file is scanned once, by the bulk scan of the tape index, and only
    the records that are not part of a run of records of a section are
    looked at.

    The rules are those of the ENDF-6 format, as a full parse with
    :class:`~endf_parserpy.EndfParserPy` checks them, for any number of
    materials:

    * the tape head (TPID) is the first line (see :class:`TapeIndex`);
    * every section ends with a SEND record ``[MAT, MF, 0]`` with the
      MAT and MF numbers of the section, every MF of a material with a
      FEND record ``[MAT, 0, 0]`` with the MAT number of the material,
      every material with a MEND record ``[0, 0, 0]``, and the tape with
      a TEND record ``[-1, 0, 0]``; the sections of an MF and the MFs of
      a material follow each other without other records in between;
    * a section (MF/MT) occurs only once in a material (otherwise
      :class:`EndfFile` would only see one of them); the order of the
      sections is not checked, as by the parsers;
    * only blank lines (blanks and tabs) may follow the TEND record, and
      no other line may be blank;
    * the MAT, MF and MT fields of the framing records and of the tape
      head are blank (zero) or an integer with an optional sign and
      blanks only before and after it;
    * the fields 1-6 (columns 1-66) of the SEND, FEND, MEND and TEND
      records are zero or blank;
    * the framing records consist of printable ASCII characters.

    The sequence numbers (columns 76-80) are not checked. The records of
    the sections are not checked here, except for their MAT/MF/MT
    numbers, which delimit the sections: their content is checked by
    parsing the sections.

    The options relax the rules as the parser options of the same names
    do: ``ignore_send_records`` skips the checks of the position and the
    MAT/MF/MT numbers of the SEND, FEND, MEND and TEND records (missing
    or additional records included), of the sequence of the sections and
    of the lines after the TEND record, but not those of their control
    fields, their columns 1-66 (which EndfParserCpp checks also with this
    option) and their characters,
    ``ignore_blank_lines`` accepts blank lines anywhere,
    ``ignore_missing_tpid`` accepts a tape without a tape head (as
    :class:`TapeIndex`), ``accept_non_ascii`` accepts other characters,
    and ``accept_spaces`` and ``accept_d_exponent`` concern the reading
    of the zeros in the float fields of the framing records.
    """
    problems, _, _ = _check_framing_and_index(
        path,
        ignore_send_records=ignore_send_records,
        ignore_blank_lines=ignore_blank_lines,
        ignore_missing_tpid=ignore_missing_tpid,
        accept_non_ascii=accept_non_ascii,
        accept_spaces=accept_spaces,
        accept_d_exponent=accept_d_exponent,
    )
    return problems


def _check_framing_and_index(path, *, ignore_missing_tpid=False, **options):
    """Check the framing records of a file and build its index in one scan.

    Return ``(problems, index, error)``: the result of
    :func:`check_framing` with the same options, and the
    :class:`TapeIndex` of the file built by
    :meth:`TapeIndex.from_file` with ``ignore_missing_tpid``, or ``None``
    and the :class:`TapeStructureError` that it raises.
    """
    path = os.fspath(path)
    events = []
    st = _ScanState(ignore_missing_tpid, events)
    index = error = None
    with open(path, "rb") as fh:
        try:
            _scan_file_into(st, fh, _DEFAULT_CHUNK_BYTES)
            index = TapeIndex._from_scan(path, *st.result())
        except TapeStructureError as exc:
            # e.g. no tape head: the event _EV_NO_TPID is the last one
            error = exc
    return _check_events(path, events, **options), index, error


def _check_events(
    path,
    events,
    *,
    ignore_send_records=False,
    ignore_blank_lines=False,
    accept_non_ascii=False,
    accept_spaces=False,
    accept_d_exponent=False,
):
    """Apply the rules of :func:`check_framing` to the events of a scan."""
    check_structure = not ignore_send_records
    checker = _Checker(
        check_ascii=not accept_non_ascii,
        number_opts=(accept_spaces, accept_d_exponent),
    )
    end_offset = None  # the offset after the TEND record
    for kind, offset, line, mat, mf, mt in events:
        if checker.level == -1:
            # a TEND record with an invalid field, after which the index
            # goes on scanning
            if kind == _EV_BLANK and _is_parser_blank(line):
                continue
            checker.problem(offset, _AFTER_TEND)
            break
        if kind == _EV_BLANK:
            if not _is_parser_blank(line):
                # e.g. a form feed, which the index skips as blank
                checker.check_line(offset, line, "blank")
                if check_structure:
                    checker.problem(
                        offset,
                        "the line holds whitespace other than blanks and tabs; "
                        "it is neither a blank line nor a record",
                    )
            elif not ignore_blank_lines:
                checker.problem(offset, "blank line")
            continue
        if kind == _EV_TPID:
            checker.control_numbers(offset, line.rstrip(b"\r").ljust(75))
            continue
        if kind == _EV_NO_TPID:
            checker.problem(
                offset,
                "the tape does not begin with a tape head (TPID) record "
                f"(found {_ctrl(mat, mf, mt)})",
            )
            return _with_line_numbers(path, checker.problems)
        if kind == _EV_SECTION:
            if check_structure:
                checker.section(offset, (mat, mf, mt))
            continue
        # a record that does not belong to a section for the index
        padded = line.rstrip(b"\r").ljust(75)
        numbers = checker.control_numbers(offset, padded)
        strict = numbers if numbers is not None else (mat, mf, mt)
        rec_kind = _kind(*strict)
        if rec_kind == "section":  # e.g. "+3" read as 3 by both
            if check_structure:
                checker.section(offset, strict)
            continue
        checker.check_line(offset, line, rec_kind)
        if mat == -1:  # the index ends its scan with this record
            end_offset = offset + len(line) + 1
        if not check_structure or (numbers is None and rec_kind == "other"):
            continue
        if numbers is None:
            # an invalid field is reported; the record is taken as the one
            # expected at this position, so that no further problems follow
            # from it
            expected = {3: "SEND", 2: "FEND", 1: "MEND", 0: "TEND"}.get(checker.level)
            if expected is not None:
                rec_kind = expected
                if expected == "SEND":
                    numbers_send = (checker.mat, checker.mf, checker.mt)
                strict = {
                    "SEND": (checker.mat, checker.mf, 0),
                    "FEND": (checker.mat, 0, 0),
                    "MEND": (0, 0, 0),
                    "TEND": (-1, 0, 0),
                }[expected]
        checker.end_record(offset, rec_kind, strict)
        if numbers is None and rec_kind == "SEND":
            checker.assumed_send = numbers_send
    if check_structure:
        if end_offset is not None:
            tail = _tail_after(path, end_offset)
            if tail is not None:
                checker.problem(tail, _AFTER_TEND)
        elif checker.level >= 0:
            checker.end_of_file(None)
    return _with_line_numbers(path, checker.problems)


def _with_line_numbers(path, problems):
    """Return the problems ``(offset, message)`` as FramingProblem objects.

    An offset of ``None`` stands for the end of the file (its last line).
    """
    if not problems:
        return []
    offsets = [offset for offset, _ in problems if offset is not None]
    lines, num_lines = _line_numbers(path, offsets)
    result = []
    for offset, message in problems:
        line = lines[offset] if offset is not None else max(num_lines, 1)
        result.append(FramingProblem(line, message))
    return result
