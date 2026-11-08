############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/17
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""ENDF-6 record-level helpers shared across the tape interface.

This module is the single home for the *structural* knowledge of the
ENDF-6 record layout that several tape submodules need:

* the fixed columns of the MAT/MF/MT control fields,
* parsing those control fields into integers (leniently for the
  index, strictly for the check of the framing records),
* building synthetic control-only records (FEND/MEND/TEND and the tape
  head), and
* trimming the framing records (SEND, leading TPID, trailing TEND) off a
  list of raw lines.

None of this consults an ENDF recipe or interprets a record body, so the
helpers are cheap and independent of the parsing engine. Centralising
them here keeps the column layout defined in exactly one place.
"""

import re


# The MAT/MF/MT control fields occupy fixed columns of every ENDF
# record: MAT in columns 67-70, MF in 71-72 and MT in 73-75. These
# zero-based byte slices are the single definition of that layout; every
# tape submodule that inspects a control field imports them from here.
_MAT_COLS = slice(66, 70)
_MF_COLS = slice(70, 72)
_MT_COLS = slice(72, 75)
_CTRL_COLS = slice(66, 75)


def _control_int(field):
    """Parse an integer from a MAT/MF/MT control field.

    A blank or non-numeric field reads as zero, consistent with the
    ENDF convention for blank control fields. Accepts ``str`` or
    ``bytes`` -- ``int()`` handles both and strips surrounding spaces.
    """
    try:
        return int(field)
    except ValueError:
        return 0


# A MAT, MF or MT field as the parsers read it: blank (zero), or an
# integer with an optional sign and blanks only before and after it
_STRICT_INT = re.compile(rb" *[+-]?[0-9]+ *")


def _strict_control_int(field):
    """Parse a MAT/MF/MT control field strictly; ``None`` if invalid.

    ``field`` is ``bytes``. A blank field reads as zero; otherwise the
    field must consist of optional blanks, an optional sign, at least one
    digit and optional blanks. This is the rule of the parsers for the
    control fields; unlike :func:`_control_int`, which the structural
    index uses, non-numeric text is not read as zero.
    """
    if _STRICT_INT.fullmatch(field) is not None:
        return int(field)
    if field.strip(b" ") == b"":
        return 0
    return None


def _control_numbers(line):
    """Return the ``(MAT, MF, MT)`` integers of an ENDF line.

    The control fields occupy columns 67-70 (MAT), 71-72 (MF) and
    73-75 (MT). Blank or non-numeric control fields are interpreted as
    zero, consistent with how blank control fields are treated
    throughout ENDF-6.
    """
    return (
        _control_int(line[_MAT_COLS]),
        _control_int(line[_MF_COLS]),
        _control_int(line[_MT_COLS]),
    )


def _control_line(mat, mf, mt):
    """Build a control-only ENDF record.

    The 66-column body is left blank and the MAT/MF/MT control fields
    are filled in their fixed columns. Used for the synthetic
    FEND/MEND/TEND records and the default tape head.
    """
    return " " * 66 + f"{mat:>4}{mf:>2}{mt:>3}"


# A tape end (TEND) record: MAT=-1, MF=0, MT=0, all value fields blank.
# This synthetic record is only ever used as input to a single-material
# parser, so no trailing sequence number is required.
TEND_LINE = _control_line(-1, 0, 0)

# A default tape head (TPID) record: a blank 66-column label followed by
# MAT=1, MF=0, MT=0. Emitted when a tape is assembled from materials
# that carry no TPID of their own, so that an assembled tape -- an empty
# one included -- always begins with a valid TPID record.
DEFAULT_TPID_LINE = _control_line(1, 0, 0)


def _strip_send(lines):
    """Drop a trailing SEND record from a section's raw lines.

    The structural index spans a section through its SEND record, but
    the writer re-emits the SEND itself, so a raw section handed to the
    writer must not already carry one.

    A SEND record is identified precisely, by MF>0 and MT=0; the
    FEND/MEND/TEND records (which also have MT=0) are deliberately not
    stripped, so a caller-supplied raw section is trimmed only when it
    genuinely ends with its own SEND.
    """
    if lines:
        _, mf, mt = _control_numbers(lines[-1])
        if mf > 0 and mt == 0:
            return lines[:-1]
    return list(lines)


def _strip_leading_tpid(lines):
    """Drop a leading TPID record; return ``(lines, tpid_or_None)``."""
    if lines:
        _, mf, mt = _control_numbers(lines[0])
        if mf == 0 and mt == 0:
            return lines[1:], lines[0]
    return lines, None


def _strip_trailing_tend(lines):
    """Drop a trailing TEND record; return ``(lines, tend_or_None)``."""
    if lines:
        mat, _, _ = _control_numbers(lines[-1])
        if mat == -1:
            return lines[:-1], lines[-1]
    return lines, None
