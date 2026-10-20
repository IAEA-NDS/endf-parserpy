############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/20
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Line reading of EndfParserCpp for unusual line endings and file ends.

EndfParserCpp reads lines by searching the buffer of the input stream for
the line delimiter instead of extracting character by character. The
results must not depend on the line endings (LF or CRLF), on a missing
newline at the end of the data, on blank lines (with ignore_blank_lines)
or on whether a file is parsed in memory or through the file stream.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp


TESTFILE = Path(__file__).parent / "testdata" / "tsl_Al.endf"


@pytest.fixture(scope="module")
def reference():
    return EndfParserCpp().parsefile(str(TESTFILE))


def _variants(text):
    lines = text.splitlines()
    return {
        "lf": "\n".join(lines) + "\n",
        "no_final_newline": "\n".join(lines),
        "crlf": "\r\n".join(lines) + "\r\n",
        "crlf_no_final_newline": "\r\n".join(lines),
    }


@pytest.mark.parametrize(
    "variant", ["lf", "no_final_newline", "crlf", "crlf_no_final_newline"]
)
@pytest.mark.parametrize("load", [True, False], ids=["in_memory", "file_stream"])
def test_line_endings(tmp_path, reference, variant, load):
    text = _variants(TESTFILE.read_text())[variant]
    path = tmp_path / "data.endf"
    path.write_bytes(text.encode())
    parser = EndfParserCpp(load_file_into_memory=load)
    assert parser.parsefile(str(path)) == reference
    assert parser.parse(text) == reference


@pytest.mark.parametrize("load", [True, False], ids=["in_memory", "file_stream"])
def test_blank_lines_ignored(tmp_path, reference, load):
    lines = TESTFILE.read_text().splitlines()
    # blank lines inside sections, as accepted with ignore_blank_lines
    with_blanks = []
    for i, line in enumerate(lines):
        with_blanks.append(line)
        if i % 50 == 7:
            with_blanks.append("")
    path = tmp_path / "blanks.endf"
    path.write_text("\n".join(with_blanks) + "\n")
    parser = EndfParserCpp(ignore_blank_lines=True, load_file_into_memory=load)
    assert parser.parsefile(str(path)) == reference
    with pytest.raises(Exception):
        EndfParserCpp(load_file_into_memory=load).parsefile(str(path))


def test_long_lines_in_data(reference):
    # lines longer than the usual 80 characters (trailing text after the
    # sequence number) do not affect the parse result
    lines = TESTFILE.read_text().splitlines()
    text = "\n".join(
        line + " " * 200 if i % 3 == 0 else line for i, line in enumerate(lines)
    )
    assert EndfParserCpp().parse(text) == reference
