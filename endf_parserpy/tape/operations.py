############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Eager multi-material parsing and writing of ENDF tapes.

These functions add support for ENDF files that contain several
materials (multi-material *tapes*, including PENDF files that
repeat the same material at different temperatures). A tape is split
into single-material chunks by :func:`~endf_parserpy.tape.splitter.split_materials`
and each chunk is handed to an ordinary single-material parser. The
single-material parser itself is used unchanged.

Each operation comes as a pair, mirroring the ``parse`` / ``parsefile``
naming of the single-material parser: the bare name works on an
in-memory ENDF-6 string, the ``_file`` variant on a file path.
"""

import os

from ..endf_parser_factory import EndfParserFactory
from .splitter import split_materials
from .records import (
    _control_numbers,
    TEND_LINE,
    DEFAULT_TPID_LINE,
    _strip_leading_tpid,
    _strip_trailing_tend,
)


_VALID_ON_ERROR = ("raise", "mark")


class _FailedUnit:
    """Base for the placeholders of ENDF data that could not be parsed.

    Holds the triggering ``exception`` and the ``raw_lines`` of the
    unit; keeping the original text lets the unit be written back
    verbatim. Subclassed by :class:`FailedMaterial` (a whole material)
    and by the internal ``FailedSection`` (a single MF/MT section).

    Attributes
    ----------
    exception : Exception
        The exception raised while parsing the unit.
    raw_lines : list[str]
        The raw ENDF-6 text of the unit.
    """

    def __init__(self, exception, raw_lines):
        self.exception = exception
        self.raw_lines = list(raw_lines)


class FailedMaterial(_FailedUnit):
    """Placeholder for a material that could not be parsed.

    Returned by :func:`parse_tape` and :func:`iter_parse_tape` (and
    their ``_file`` variants) in place of a parsed material dictionary
    when ``on_error="mark"`` and the parsing of that material failed.
    Passing a :class:`FailedMaterial` back to :func:`write_tape` writes
    its original lines verbatim.

    Attributes
    ----------
    exception : Exception
        The exception raised while parsing the material.
    raw_lines : list[str]
        The lines of the single-material tape that failed to parse.
    """

    @property
    def mat(self):
        """MAT number of the failed material, or ``None`` if unknown."""
        for line in self.raw_lines:
            mat, mf, mt = _control_numbers(line)
            if mat > 0 and mf > 0 and mt > 0:
                return mat
        return None

    def __repr__(self):
        return f"FailedMaterial(mat={self.mat}, exception={self.exception!r})"


def _ensure_parser(parser):
    if parser is None:
        return EndfParserFactory.create(select="fastest")
    return parser


def _check_on_error(on_error):
    if on_error not in _VALID_ON_ERROR:
        raise ValueError(f"on_error must be one of {_VALID_ON_ERROR}, got {on_error!r}")


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------


def _iter_materials(lines, parser, exclude, include, on_error):
    """Split ``lines`` into materials and parse them one at a time."""
    for chunk in split_materials(lines):
        try:
            yield parser.parse(chunk, exclude=exclude, include=include)
        except Exception as exc:
            if on_error == "raise":
                raise
            yield FailedMaterial(exc, chunk)


def iter_parse_tape(text, *, parser=None, exclude=None, include=None, on_error="mark"):
    """Parse a multi-material ENDF tape, yielding one material at a time.

    Parameters
    ----------
    text : str
        The ENDF-6 formatted tape as a single string, as produced by
        :func:`write_tape` or :meth:`~endf_parserpy.EndfFile.to_string`.
        To parse a file on disk, use :func:`iter_parse_tape_file`.
    parser : EndfParserBase, optional
        The single-material parser used for each material. Defaults to
        ``EndfParserFactory.create(select="fastest")``.
    exclude, include : optional
        MF / (MF, MT) sections to exclude from / restrict the parsing
        to. Forwarded unchanged to the single-material parser and
        applied to every material.
    on_error : {"raise", "mark"}
        With ``"raise"`` the first material that fails to parse aborts
        the iteration. With ``"mark"`` (the default) a failing material
        is yielded as a :class:`FailedMaterial` and parsing continues.

    Yields
    ------
    dict or FailedMaterial
        The parsed material dictionary (same shape as the result of a
        single-material ``parsefile``), or a :class:`FailedMaterial`.

    Notes
    -----
    Only one material is held in parsed form at a time, so the parsed
    data does not accumulate; for a tape too large to hold in memory at
    all, parse it from disk with :func:`iter_parse_tape_file`.

    The arguments are validated when this function is called; the
    returned iterator then yields the materials lazily.
    """
    _check_on_error(on_error)
    parser = _ensure_parser(parser)
    # not a generator itself, so _check_on_error runs at the call rather
    # than being deferred to the first iteration of the result
    return _iter_materials(text.splitlines(), parser, exclude, include, on_error)


def iter_parse_tape_file(
    path, *, parser=None, exclude=None, include=None, on_error="mark"
):
    """Parse a multi-material ENDF tape from a file, one material at a time.

    The file counterpart of :func:`iter_parse_tape`; the ``path``
    argument is a file path (``str`` or :class:`os.PathLike`). The file
    is read incrementally, so peak memory use is bounded by the largest
    single material rather than by the size of the whole tape. See
    :func:`iter_parse_tape` for the remaining parameters.
    """
    _check_on_error(on_error)
    parser = _ensure_parser(parser)
    # validate eagerly (above), then delegate to the generator that
    # holds the file open for the duration of the iteration
    return _iter_parse_file(os.fspath(path), parser, exclude, include, on_error)


def _iter_parse_file(path, parser, exclude, include, on_error):
    """Generator backing :func:`iter_parse_tape_file`; holds the file open."""
    # bytes are mapped to characters with Latin-1 as by the parsers
    with open(path, "r", encoding="latin-1") as fh:
        yield from _iter_materials(fh, parser, exclude, include, on_error)


def parse_tape(text, *, parser=None, exclude=None, include=None, on_error="mark"):
    """Parse a multi-material ENDF tape string into a list of materials.

    This is the eager counterpart of :func:`iter_parse_tape`; see there
    for a description of the parameters. To parse a file on disk, use
    :func:`parse_tape_file`.

    Returns
    -------
    list
        One entry per material, in tape order. Each entry is either a
        parsed material dictionary or, for a material that failed to
        parse with ``on_error="mark"``, a :class:`FailedMaterial`.
    """
    return list(
        iter_parse_tape(
            text, parser=parser, exclude=exclude, include=include, on_error=on_error
        )
    )


def parse_tape_file(path, *, parser=None, exclude=None, include=None, on_error="mark"):
    """Parse a multi-material ENDF tape file into a list of materials.

    The file counterpart of :func:`parse_tape`; the ``path`` argument is
    a file path (``str`` or :class:`os.PathLike`). See :func:`parse_tape`
    for the return value and :func:`iter_parse_tape` for the parameters.
    """
    return list(
        iter_parse_tape_file(
            path, parser=parser, exclude=exclude, include=include, on_error=on_error
        )
    )


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------


def _material_lines(material, parser, exclude, include):
    # A material given as a list of ENDF-6 lines, or as a FailedMaterial,
    # is written verbatim -- no parse, no render. A parsed material
    # dictionary is rendered by the single-material parser.
    if isinstance(material, FailedMaterial):
        return list(material.raw_lines)
    if isinstance(material, list):
        return list(material)
    return parser.write(material, exclude=exclude, include=include)


def _iter_tape_chunks(materials, parser, exclude, include):
    """Yield a multi-material tape as text chunks, one material at a time.

    The first chunk is the tape head (TPID) -- the first material's own,
    or :data:`~endf_parserpy.tape.records.DEFAULT_TPID_LINE` when no
    material carries one (so an empty material list still yields a valid
    TPID + TEND tape). Then comes one chunk per material (its records
    through the MEND record), and the last chunk is the tape end (TEND);
    every chunk ends with a newline. Each material is written with an
    ordinary single-material parser and its own per-material TPID/TEND
    records are stripped.

    ``materials`` is consumed lazily, so when it is a generator the
    whole tape is never held in memory at once.
    """
    parser = _ensure_parser(parser)
    tpid_emitted = False
    final_tend = None
    for material in materials:
        lines = _material_lines(material, parser, exclude, include)
        lines, tend = _strip_trailing_tend(lines)
        if tend is not None:
            final_tend = tend
        lines, tpid = _strip_leading_tpid(lines)
        if not tpid_emitted:
            # the assembled tape must open with a TPID: use the first
            # material's own, or a default when it carries none
            yield (tpid if tpid is not None else DEFAULT_TPID_LINE) + "\n"
            tpid_emitted = True
        if lines:
            yield "\n".join(lines) + "\n"
    if not tpid_emitted:
        # no materials at all -- still emit a valid (empty) tape
        yield DEFAULT_TPID_LINE + "\n"
    yield (final_tend if final_tend is not None else TEND_LINE) + "\n"


def write_tape(materials, *, parser=None, exclude=None, include=None):
    """Assemble materials into a single multi-material ENDF tape string.

    A :class:`FailedMaterial` is written verbatim from its stored lines.

    Parameters
    ----------
    materials : Iterable
        The materials, in the desired tape order. Each entry is either
        a parsed material dictionary (rendered by the parser), a
        ``list`` of raw ENDF-6 lines, or a :class:`FailedMaterial` -- the
        latter two are written *verbatim*, with no intermediate parse or
        render, so an already-formatted material is copied through
        unchanged.
    parser : EndfParserBase, optional
        Parser used to write each material *dictionary*. Defaults to
        ``EndfParserFactory.create(select="fastest")``.
    exclude, include : optional
        Forwarded unchanged to the single-material parser's ``write``.

    Returns
    -------
    str
        The assembled tape as a single ENDF-6 formatted string, ending
        with a newline. This necessarily holds the whole tape in
        memory; to write a large tape with bounded memory, use
        :func:`write_tape_file`.
    """
    return "".join(_iter_tape_chunks(materials, parser, exclude, include))


def write_tape_file(
    materials, path, *, parser=None, exclude=None, include=None, overwrite=False
):
    """Assemble materials and write the tape to a file.

    The file counterpart of :func:`write_tape`; ``path`` is a file path
    (``str`` or :class:`os.PathLike`). An existing file is only
    overwritten when ``overwrite=True``. See :func:`write_tape` for the
    remaining parameters.

    Each material is rendered and written before the next is pulled
    from ``materials``, so when ``materials`` is a generator the peak
    memory stays bounded by the size of a single material rather than
    by the size of the whole tape.
    """
    path = os.fspath(path)
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(
            f"file {path} already exists; pass overwrite=True to replace it"
        )
    # newline="" disables newline translation so the tape is written with
    # LF terminators on every platform (text mode would emit CRLF on Windows)
    # (and each character is written as the byte with the same code)
    with open(path, "w", newline="", encoding="latin-1") as fh:
        for chunk in _iter_tape_chunks(materials, parser, exclude, include):
            fh.write(chunk)
