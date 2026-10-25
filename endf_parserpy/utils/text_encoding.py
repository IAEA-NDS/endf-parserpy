############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/25
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

With the option ``accept_non_ascii=False``, both parsers reject
characters outside printable ASCII (codes 32 to 126), as required by
the ENDF-6 format, in the lines they read and in the text they write.

The functions of this module are used by both parsers, so that they
raise the same errors with the same messages.
"""

import re
import unicodedata
from endf_parserpy.interpreter.custom_exceptions import InvalidCharacterError


ENDF_ENCODING = "latin-1"

# characters that do not correspond to a single byte
_non_latin1 = re.compile("[^\x00-\xff]")
# characters other than printable ASCII (codes 32 to 126)
_non_printable_ascii = re.compile("[^\x20-\x7e]")
# the leading integer of a field as read by the C++ parser (atoi)
_leading_int = re.compile("[ \t\n\v\f\r]*([+-]?[0-9]+)")

_ESCAPES = {"\t": "\\t", "\r": "\\r", "\n": "\\n"}


def _escape_char(char):
    escaped = _ESCAPES.get(char)
    if escaped is not None:
        return escaped
    code = ord(char)
    if code <= 0xFF:
        return f"\\x{code:02x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def describe_char(char):
    """Describe a character by its code point and, if known, its name."""
    code = ord(char)
    name = unicodedata.name(char, "")
    name = f", {name}" if name != "" else ""
    return f"U+{code:04X}{name}"


def escape_text(text):
    """Make characters outside printable ASCII visible in a message.

    TAB, CR and LF become ``\\t``, ``\\r`` and ``\\n``, other characters
    up to U+00FF (bytes of an ENDF-6 file) ``\\xhh``, e.g. ``\\x92``,
    and characters above U+00FF ``\\uhhhh`` or ``\\Uhhhhhhhh``.
    Printable ASCII characters, including the backslash, are unchanged,
    as in the messages of the C++ parser.
    """
    if _non_printable_ascii.search(text) is None:
        return text
    return _non_printable_ascii.sub(lambda m: _escape_char(m.group(0)), text)


def long_line_hint(line):
    """A hint for an error message if a line is longer than 80 columns.

    Empty for a line of at most 80 columns (without the line ending).
    """
    length = len(line_content(line))
    if length <= 80:
        return ""
    return (
        f"\nHint: the line is longer than 80 columns ({length} columns; "
        "non-ASCII multi-byte characters or text beyond column 80?)"
    )


def describe_byte(code):
    """Describe a byte (a character up to U+00FF) outside printable ASCII."""
    if code == 0x09:
        what = "TAB"
    elif code == 0x0D:
        what = "carriage return"
    elif code < 0x20 or code == 0x7F:
        what = "control character"
    elif 0x80 <= code <= 0x9F:
        what = "likely a Windows-1252 character"
    else:
        what = "non-ASCII, e.g. Latin-1 or part of a UTF-8 multi-byte character"
    return f"byte 0x{code:02x} ({what})"


def _lenient_int(text):
    m = _leading_int.match(text)
    return int(m.group(1)) if m is not None else 0


def line_content(line):
    """Return a line without its line ending (LF, CRLF or CR)."""
    if line.endswith("\n"):
        line = line[:-1]
    if line.endswith("\r"):
        line = line[:-1]
    return line


def raise_non_ascii_line_error(lineno, column, mat, mf, mt, code):
    """Raise the error for a line with a character outside printable ASCII.

    ``lineno`` and ``column`` count from 1, ``code`` is the code of the
    character (the byte). Also called by the C++ parser.
    """
    raise InvalidCharacterError(
        f"line {lineno}, column {column} (MAT/MF/MT {mat}/{mf}/{mt}) "
        f"contains {describe_byte(code)}, which is not a printable ASCII "
        "character (codes 32 to 126) as required by the ENDF-6 format; "
        "use the option accept_non_ascii=True to accept it"
    )


def check_line_ascii(line, lineno, width=11):
    """Raise an error if a line has a character outside printable ASCII.

    The line ending is not checked. ``lineno`` counts from 1; MAT, MF and
    MT of the message are read from the control columns of the line.
    """
    content = line_content(line)
    m = _non_printable_ascii.search(content)
    if m is None:
        return
    ofs = 6 * width
    mat = _lenient_int(content[ofs : ofs + 4])
    mf = _lenient_int(content[ofs + 4 : ofs + 6])
    mt = _lenient_int(content[ofs + 6 : ofs + 9])
    raise_non_ascii_line_error(lineno, m.start() + 1, mat, mf, mt, ord(m.group(0)))


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


def check_text_value(value, what, accept_non_ascii=True):
    """Check that a string can be written to an ENDF-6 file.

    Raises an error if ``value`` contains a character above U+00FF, which
    does not correspond to a byte, or, if ``accept_non_ascii`` is
    ``False``, a character outside printable ASCII (codes 32 to 126).
    ``what`` names the value in the message, e.g. ``the string in
    variable AUTH``. Also called by the C++ parser.
    """
    m = _non_latin1.search(value)
    if m is not None:
        raise InvalidCharacterError(
            f"{what} contains the character {describe_char(m.group(0))} "
            f"at position {m.start() + 1}, which cannot be written to an "
            "ENDF-6 file: each character must correspond to one byte, i.e. "
            "be in the range U+0000 to U+00FF (Latin-1)"
        )
    if accept_non_ascii:
        return
    m = _non_printable_ascii.search(value)
    if m is not None:
        char = m.group(0)
        raise InvalidCharacterError(
            f"{what} contains the character {_escape_char(char)} "
            f"({describe_char(char)}) at position {m.start() + 1}, which is "
            "not a printable ASCII character (codes 32 to 126) as required "
            "by the ENDF-6 format; use the option accept_non_ascii=True to "
            "write it"
        )


def verbatim_line_name(lineno, mf, mt):
    """Name of a line of a section given as a list of strings, in messages."""
    return f"line {lineno} of the section MF={mf}/MT={mt} given as a list of strings"


def check_verbatim_line(line, lineno, mf, mt, accept_non_ascii=True):
    """Check a line of a section given as a list of strings before writing.

    Characters above U+00FF are rejected and, if ``accept_non_ascii`` is
    ``False``, characters outside printable ASCII in the columns that are
    written, i.e. the first 75 columns without the line ending.
    ``lineno`` counts from 1. A line given as ``bytes`` is checked as
    its characters with the same codes (Latin-1), as which it is
    written. Also called by the C++ parser.
    """
    if isinstance(line, bytes):
        line = line.decode(ENDF_ENCODING)
    what = verbatim_line_name(lineno, mf, mt)
    check_text_value(line, what)
    if not accept_non_ascii:
        check_text_value(line_content(line)[:75], what, False)
