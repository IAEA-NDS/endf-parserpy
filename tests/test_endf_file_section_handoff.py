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
same as joining the lines ``raw.splitlines()`` and the wrapper records
with ``"\\n"`` (the previous form), whatever the line breaks of the text.
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


def _joined(ef, entry, raw):
    lines = [ef.index.tpid_line] + raw.splitlines()
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
