############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/01
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Exceptions raised by the multi-material tape interface."""

from ..errors import EndfParserpyError


class TapeError(EndfParserpyError):
    """Base class for all errors raised by the tape interface."""


class TapeStructureError(TapeError):
    """Raised when the structure of an ENDF tape is malformed.

    Examples are a tape that does not begin with a tape head (TPID)
    record, or a tape that ends in the middle of a material because the
    final MEND or TEND record is missing.
    """


class AmbiguousMaterialError(TapeError, LookupError):
    """Raised when a MAT number matches several materials.

    PENDF tapes repeat the same MAT number at different
    temperatures. A lookup by MAT number then needs an ``occurrence``
    index to select among them.

    This is a lookup failure, so it also derives from the built-in
    :class:`LookupError`; code that handles lookup errors generically
    can catch it that way.
    """


class SectionParseError(TapeError):
    """Raised when a section fails to parse and ``on_error="raise"``.

    The exception raised by the parser is kept as the cause
    (``__cause__``). The section is parsed on its own, as a short tape
    made of the tape head (TPID) record of the file, the lines of the
    section and the end records, so that the line numbers in the message
    of the cause count the lines of this tape; :attr:`detail` gives them
    as lines of the file.

    Attributes
    ----------
    position : int or None
        Position of the material the section belongs to.
    mat, mf, mt : int or None
        The MAT, MF and MT numbers of the section.
    line : int or None
        Number (counting from 1) of the line of the file at which the
        section starts.
    detail : str or None
        The message of the cause with the line numbers it gives
        counted in the file, or ``None`` if there is no cause.
    """

    def __init__(
        self,
        message,
        *,
        position=None,
        mat=None,
        mf=None,
        mt=None,
        line=None,
        detail=None,
    ):
        super().__init__(message)
        self.position = position
        self.mat = mat
        self.mf = mf
        self.mt = mt
        self.line = line
        self.detail = detail


class SectionRenderError(TapeError):
    """Raised when an edited section fails to render to ENDF-6 text.

    In ``check_edits="eager"`` mode every edited section is rendered
    through the parser's writer right away; a section that no longer
    conforms to its ENDF recipe makes the writer fail, which is reported
    as this error with the writer's own exception kept as its cause. The
    same error is collected by
    :meth:`~endf_parserpy.EndfFile.invalid_edits`.
    """


class StaleSourceError(TapeError):
    """Raised when the source file changed after its index was built."""
