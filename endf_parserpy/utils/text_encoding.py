############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Mapping between the bytes of ENDF-6 files and Python strings.

Both :class:`~endf_parserpy.EndfParserPy` and
:class:`~endf_parserpy.EndfParserCpp` map every byte of an ENDF-6 file
to the character with the same code and back (the Latin-1 or ISO 8859-1
encoding), independently of the operating system. Therefore no file can
fail to decode, the columns of a line are byte positions in both
parsers, and reading and writing a file reproduces its bytes. A string
can only be written to an ENDF-6 file, and only correspond to the
content of one, if all its characters are in the range U+0000 to U+00FF.

The functions of this module are used by both parsers, so that they
raise the same errors with the same messages.
"""

import re
import unicodedata
from endf_parserpy.interpreter.custom_exceptions import InvalidCharacterError


ENDF_ENCODING = "latin-1"

# characters that do not correspond to a single byte
_non_latin1 = re.compile("[^\x00-\xff]")


def describe_char(char):
    """Describe a character by its code point and, if known, its name."""
    code = ord(char)
    name = unicodedata.name(char, "")
    name = f", {name}" if name != "" else ""
    return f"U+{code:04X}{name}"


def line_content(line):
    """Return a line without its line ending (LF, CRLF or CR)."""
    if line.endswith("\n"):
        line = line[:-1]
    if line.endswith("\r"):
        line = line[:-1]
    return line


def _input_position(text, pos):
    lineno = text.count("\n", 0, pos) + 1
    column = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return lineno, column


def raise_input_error(text, lineno=None, column=None):
    """Raise the error for a string to be parsed with a character above U+00FF.

    Without ``lineno`` and ``column`` (counting from 1), the position of
    the first such character in ``text`` is determined; otherwise ``text``
    is the line. Also called by the C++ parser.
    """
    if lineno is None:
        pos = _non_latin1.search(text).start()
        char = text[pos]
        lineno, column = _input_position(text, pos)
    else:
        char = text[column - 1]
    raise InvalidCharacterError(
        f"line {lineno}, column {column} of the input contains the character "
        f"{describe_char(char)}, which does not correspond to a byte of an "
        "ENDF-6 file: the parsers map each byte to the character with the "
        "same code (Latin-1), so only characters up to U+00FF can occur "
        "(read the file with parsefile or decode it with the Latin-1 encoding)"
    )


def encode_input(text):
    """Encode a string to be parsed to bytes (Latin-1)."""
    try:
        return text.encode(ENDF_ENCODING)
    except UnicodeEncodeError:
        raise_input_error(text)


def check_input(lines):
    """Check that the strings to be parsed only contain characters up to U+00FF.

    ``lines`` is a string or a list of strings (lines).
    """
    if isinstance(lines, str):
        if not lines.isascii():
            encode_input(lines)
        return
    for i, line in enumerate(lines):
        if line.isascii():
            continue
        try:
            line.encode(ENDF_ENCODING)
        except UnicodeEncodeError as exc:
            raise_input_error(line, i + 1, exc.start + 1)


def check_text_value(value, what):
    """Check that a string can be written to an ENDF-6 file.

    Raises an error if ``value`` contains a character above U+00FF, which
    does not correspond to a byte. ``what`` names the value in the
    message, e.g. ``the string in variable AUTH``.
    Also called by the C++ parser.
    """
    m = _non_latin1.search(value)
    if m is not None:
        raise InvalidCharacterError(
            f"{what} contains the character {describe_char(m.group(0))} "
            f"at position {m.start() + 1}, which cannot be written to an "
            "ENDF-6 file: each character must correspond to one byte, i.e. "
            "be in the range U+0000 to U+00FF (Latin-1)"
        )


def verbatim_line_name(lineno, mf, mt):
    """Name of a line of a section given as a list of strings, in messages."""
    return f"line {lineno} of the section MF={mf}/MT={mt} given as a list of strings"


def check_verbatim_line(line, lineno, mf, mt):
    """Check a line of a section given as a list of strings before writing.

    Characters above U+00FF are rejected. ``lineno`` counts from 1.
    Also called by the C++ parser.
    """
    check_text_value(line, verbatim_line_name(lineno, mf, mt))
