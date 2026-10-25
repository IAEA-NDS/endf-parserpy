############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Hand-off of a section from EndfFile to the parser as a single string.

EndfFile wraps the raw text of a section in a minimal single-material
tape. The tape is passed to the parser as one string, which must be the
same as joining the lines of the text (divided at ``"\\n"`` only, without
the ``"\\r"`` of CRLF line endings) and the wrapper records with ``"\\n"``,
whatever the line breaks of the text. Other characters at which
``str.splitlines()`` divides, e.g. FF or NEL in a TEXT record, stay in
their line, also when an untouched section is written.
"""

from pathlib import Path
import pytest

from endf_parserpy import EndfParserFactory, EndfFile
from endf_parserpy.tape.records import _control_line, TEND_LINE


TESTDATA = Path(__file__).parent / "testdata"
CU = TESTDATA / "n_2925_29-Cu-63.endf"


@pytest.fixture(params=["python", "cpp"])
def parser(request):
    try:
        return EndfParserFactory.create(select=request.param)
    except Exception:
        pytest.skip(f"{request.param} backend unavailable")


def _raw_lines(raw):
    # lines end at "\n" only (a "\r" before it is removed), as the
    # records of the structural index
    lines = raw.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _joined(ef, entry, raw):
    lines = [ef.index.tpid_line] + _raw_lines(raw)
    lines += [_control_line(entry.mat, 0, 0), _control_line(0, 0, 0), TEND_LINE]
    return "\n".join(lines)


@pytest.mark.parametrize(
    "raw",
    [
        "line 1\nline 2\n",
        "line 1\nline 2",
        "line 1\r\nline 2\r\n",
        "line 1\rline 2\n",
        "line 1\n\nline 2\n",
        "text \x85 more\nline 2\n",
        "a\x0bb\x0cc\x1cd\x1de\x1ef\n",
        "",
    ],
)
def test_mini_tape_equals_joined_lines(raw):
    ef = EndfFile(CU, parser=EndfParserFactory.create(select="python"))
    entry = ef.index[0]
    assert ef._mini_tape(entry, raw) == _joined(ef, entry, raw)


def test_mini_tape_of_every_section(parser):
    ef = EndfFile(CU, parser=parser)
    entry = ef.index[0]
    for (mf, mt), sec_entry in entry.sections.items():
        raw = ef._get_raw(0, mf, mt, sec_entry)
        assert ef._mini_tape(entry, raw) == _joined(ef, entry, raw)


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_sections_and_export_unchanged(parser, ending, tmp_path):
    lines = CU.read_bytes().decode("latin-1").splitlines()
    path = tmp_path / "tape.endf"
    # the last line without a line ending
    path.write_bytes(ending.join(lines).encode("latin-1"))
    ef = EndfFile(path, parser=parser)
    ref = parser.parse(lines)
    for mf, mt in ef[0].sections():
        assert ef[0][mf, mt] == ref[mf][mt]
    expected = "\n".join(parser.write(ref)) + "\n"
    ef = EndfFile(path, parser=parser)
    assert ef.to_string() == expected


def _with_text_chars(lines):
    # FF, NEL, VT and a lone CR in TEXT lines of the MF1/MT451 description
    lines = list(lines)
    for i, (pos, char) in enumerate([(5, "\x0c"), (8, "\x85"), (3, "\x0b")]):
        k = 10 + i
        assert lines[k][70:75] == " 1451"
        lines[k] = lines[k][:pos] + char + lines[k][pos + 1 :]
    lines[13] = lines[13][:4] + "\r" + lines[13][5:]
    return lines


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_line_break_characters_inside_lines(parser, ending, tmp_path):
    lines = _with_text_chars(CU.read_bytes().decode("latin-1").splitlines())
    path = tmp_path / "tape.endf"
    path.write_bytes((ending.join(lines) + ending).encode("latin-1"))
    ef = EndfFile(path, parser=parser)
    # parsed as by the parser itself
    ref = parser.parse("\n".join(lines))
    assert ef[0][1, 451] == ref[1][451]
    # an untouched section is written back with these characters
    written = ef.to_string().split("\n")
    for k in range(10, 14):
        assert written[k][:75] == lines[k][:75]
    assert ef.to_string() == "\n".join(parser.write(ref)) + "\n"
