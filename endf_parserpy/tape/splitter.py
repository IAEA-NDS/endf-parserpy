############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/11
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


def split_materials(lines):
    """Yield single-material tapes from a multi-material ENDF tape.

    Parameters
    ----------
    lines : Iterable[str]
        The lines of a (possibly multi-material) ENDF tape. May be a
        list, an open file object, or any other iterable of strings.
        Trailing line breaks are stripped.

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
    Blank lines (e.g. padding between materials) are not preserved.
    """
    for chunk, _ in _split_materials_with_lines(lines):
        yield chunk


def _split_materials_with_lines(lines):
    """Yield the single-material tapes of :func:`split_materials`, each
    with the list of the numbers (counting from 1) of the lines of the
    tape ``lines`` given by its lines between the TPID and the TEND
    record."""
    line_iter = enumerate(lines, start=1)

    # locate the tape head (TPID): the first non-blank record
    tpid = None
    for _, raw in line_iter:
        line = raw.rstrip("\r\n")
        if line.strip() == "":
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

    current = []
    numbers = []
    for number, raw in line_iter:
        line = raw.rstrip("\r\n")
        if line.strip() == "":
            # inter-material and padding blank lines are not preserved
            continue
        mat, mf, mt = _control_numbers(line)
        if mat == -1:
            # tape end (TEND) record: nothing meaningful follows
            break
        current.append(line)
        numbers.append(number)
        if mat == 0 and mf == 0 and mt == 0:
            # MEND record: the current material is complete
            if len(current) > 1:
                yield [tpid] + current + [TEND_LINE], numbers
            current = []
            numbers = []

    if current:
        raise TapeStructureError(
            "the tape ends in the middle of a material; the final "
            "MEND or TEND record is missing"
        )
