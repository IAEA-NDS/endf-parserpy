############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lexically split a multi-material ENDF tape into single-material tapes.

An ENDF *tape* may contain several materials. Each material is terminated
by a MEND record and the whole tape by a TEND record. This module splits
such a tape into chunks, where each chunk is itself a valid single-material
tape (tape head + one material + tape end) that can be handed to an
ordinary single-material parser.

The splitting is purely lexical: only the MAT/MF/MT control fields in
columns 67-75 of each line are inspected. No ENDF recipe is consulted and
the content of the records is never interpreted.
"""

from .errors import TapeStructureError
from .records import _control_numbers, TEND_LINE


def split_materials(lines, keep_blank_lines=False):
    """Yield single-material tapes from a multi-material ENDF tape.

    Parameters
    ----------
    lines : Iterable[str]
        The lines of a (possibly multi-material) ENDF tape. May be a
        list, an open file object, or any other iterable of strings.
        Trailing line breaks are stripped.
    keep_blank_lines : bool
        If ``False`` (the default), blank lines are dropped. If ``True``,
        a blank line before the tape end (TEND) record is kept in the
        single-material tape where it occurs, so that a parser that
        rejects blank lines (``ignore_blank_lines=False``) rejects it:
        a blank line before the first material in the first tape (before
        its TPID record), one after a MEND record in the tape of that
        material. Lines after the TEND record are dropped in both cases.

    Yields
    ------
    list[str]
        For each material on the tape, a list of lines forming a
        self-contained single-material tape: the tape head (TPID)
        record, the material's records (including its MEND record)
        and a tape end (TEND) record.

    Raises
    ------
    TapeStructureError
        If the tape does not begin with a TPID record, or if it ends
        in the middle of a material.

    Notes
    -----
    Without ``keep_blank_lines``, blank lines (e.g. padding between
    materials) are not preserved.
    """
    for chunk, _ in _split_materials_with_lines(lines, keep_blank_lines):
        yield chunk


def _split_materials_with_lines(lines, keep_blank_lines=False):
    """Yield the single-material tapes of :func:`split_materials`, each
    with the list of the numbers (counting from 1) of the lines of the
    tape ``lines`` given by its lines between the TPID and the TEND
    record (with ``keep_blank_lines``, the blank lines before the TPID
    record of the first tape are not counted)."""
    line_iter = enumerate(lines, start=1)

    # locate the tape head (TPID): the first non-blank record
    tpid = None
    leading = []
    for _, raw in line_iter:
        line = raw.rstrip("\r\n")
        if line.strip() == "":
            leading.append(line)
            continue
        tpid = line
        break
    if tpid is None:
        raise TapeStructureError("the tape does not contain any records")

    mat, mf, mt = _control_numbers(tpid)
    if mat < 0 or mf != 0 or mt != 0:
        raise TapeStructureError(
            "the tape does not begin with a tape head (TPID) record "
            f"(found MAT={mat}, MF={mf}, MT={mt}); a multi-material tape "
            "must start with a TPID record"
        )
    # with keep_blank_lines, the blank lines before the TPID record are
    # given to the parser with the first material, so that the lines of
    # the first tape are those of the file
    head = leading + [tpid] if keep_blank_lines else [tpid]

    current = []
    numbers = []
    # the number of records (non-blank lines) in current
    records = 0
    # with keep_blank_lines, a complete material is held back until the
    # next record, so that blank lines after its MEND record join it
    done = None
    for number, raw in line_iter:
        line = raw.rstrip("\r\n")
        if line.strip() == "":
            if not keep_blank_lines:
                # inter-material and padding blank lines are not preserved
                continue
            if done is not None:
                done[0].append(line)
                done[1].append(number)
            else:
                current.append(line)
                numbers.append(number)
            continue
        if done is not None:
            yield head + done[0] + [TEND_LINE], done[1]
            head = [tpid]
            done = None
        mat, mf, mt = _control_numbers(line)
        if mat == -1:
            # tape end (TEND) record: nothing meaningful follows
            break
        current.append(line)
        numbers.append(number)
        records += 1
        if mat == 0 and mf == 0 and mt == 0:
            # MEND record: the current material is complete
            if records > 1:
                if keep_blank_lines:
                    done = (current, numbers)
                else:
                    yield head + current + [TEND_LINE], numbers
                    head = [tpid]
            elif keep_blank_lines and len(current) > 1:
                # only blank lines before a MEND record: rejected by
                # the parser as a material with these lines
                done = (current, numbers)
            current = []
            numbers = []
            records = 0

    if done is not None:
        yield head + done[0] + [TEND_LINE], done[1]
    if records:
        raise TapeStructureError(
            "the tape ends in the middle of a material; the final "
            "MEND or TEND record is missing"
        )
    if keep_blank_lines and current:
        # blank lines before the TEND record and after the last MEND
        # record without a material to join: given to the parser as a
        # tape of their own, which it rejects
        yield head + current + [TEND_LINE], numbers
