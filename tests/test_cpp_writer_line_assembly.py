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

"""Assembly of the lines written by EndfParserCpp.

The C++ writer refills one line buffer per record, writes TAB1/TAB2 bodies
directly into a buffer of lines and collects the output in one buffer,
which becomes the string returned by write() or the content of the file
of writefile(). The tests compare the output with that of EndfParserPy
for LIST and TAB1 records of various lengths, with and without line
numbers, including the wrap of the line number after 99999, sections
given as lists of lines, and the bytes of the file written by writefile().
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


def _mf1_mt452_list(nc, mat=125):
    return {
        "MAT": mat,
        "MF": 1,
        "MT": 452,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "LNU": 1,
        "NC": nc,
        "C": {k: 0.5 + k * 1.25e-3 * (-1) ** k for k in range(1, nc + 1)},
    }


def _mf3_tab1(np, nbt=None, intcode=None, mt=1, mat=125):
    if nbt is None:
        nbt = [np] if np > 0 else []
        intcode = [2] * len(nbt)
    return {
        "MAT": mat,
        "MF": 3,
        "MT": mt,
        "ZA": 1001.0,
        "AWR": 0.9991673,
        "QM": -1.5e6,
        "QI": -1.5e6,
        "LR": 0,
        "xstable": {
            "NBT": list(nbt),
            "INT": list(intcode),
            "E": [1e-5 * (1.0 + i) ** 1.5 for i in range(np)],
            "xs": [(-1) ** i * 3.25 / (1.0 + i) for i in range(np)],
        },
    }


def _tape(sections):
    tape = {}
    for sec in sections:
        tape.setdefault(sec["MF"], {})[sec["MT"]] = sec
    return tape


SIZES = [0, 1, 2, 3, 5, 6, 7, 12, 13]


@pytest.mark.parametrize("include_linenum", [True, False])
@pytest.mark.parametrize("nc", [1, 5, 6, 7, 12, 13, 600])
def test_list_record_lines_agree_with_python_writer(nc, include_linenum):
    tape = _tape([_mf1_mt452_list(nc)])
    lines_py = EndfParserPy(include_linenum=include_linenum).write(tape)
    lines_cpp = EndfParserCpp(include_linenum=include_linenum).write(tape)
    assert lines_cpp == lines_py


TAB1_SIZES = [(np, nr) for np in SIZES for nr in [1, 2, 3, 4, 7] if nr <= np]


@pytest.mark.parametrize("include_linenum", [True, False])
@pytest.mark.parametrize("np, nr", TAB1_SIZES)
def test_tab1_record_lines_agree_with_python_writer(np, nr, include_linenum):
    nbt = [np * (i + 1) // nr for i in range(nr)]
    intcode = [1 + i % 5 for i in range(nr)]
    tape = _tape([_mf3_tab1(np, nbt, intcode), _mf3_tab1(np, nbt, intcode, mt=2)])
    lines_py = EndfParserPy(include_linenum=include_linenum).write(tape)
    lines_cpp = EndfParserCpp(include_linenum=include_linenum).write(tape)
    assert lines_cpp == lines_py


def test_empty_tab1_record():
    tape = _tape([_mf3_tab1(0)])
    lines_py = EndfParserPy().write(tape)
    lines_cpp = EndfParserCpp().write(tape)
    assert lines_cpp == lines_py


def test_line_number_wraps_in_list_body():
    # 100002 body lines: the line number wraps from 99999 to 1
    nc = 6 * 100002
    tape = _tape([_mf1_mt452_list(nc)])
    lines = EndfParserCpp().write(tape)
    section = lines[:-4]  # without SEND, FEND, MEND, TEND
    numbers = [int(line[75:80]) for line in section]
    assert numbers == [(i % 99999) + 1 for i in range(len(section))]
    assert len(section) == 100004
    assert [line[75:80] for line in lines[-4:]] == ["99999", "    0", "    0", "    0"]
    assert all(len(line) == 80 for line in lines)
    lines_nonum = EndfParserCpp(include_linenum=False).write(tape)
    assert lines_nonum == [line[:75] for line in lines]


@pytest.mark.parametrize("include_linenum", [True, False])
def test_several_sections_and_verbatim_sections(include_linenum):
    sections = [_mf1_mt452_list(8), _mf3_tab1(10), _mf3_tab1(4, mt=102)]
    tape = _tape(sections)
    parser = EndfParserCpp(include_linenum=include_linenum)
    lines = parser.write(tape)
    # the MF3/MT2 section as a list of lines (written verbatim)
    verbatim = EndfParserCpp().write(_tape([_mf3_tab1(7, mt=2)]))
    tape[3][2] = [line for line in verbatim if line[72:75] == "  2"]
    lines_verbatim = parser.write(tape)
    lines_py = EndfParserPy(include_linenum=include_linenum).write(tape)
    assert lines_verbatim == lines_py
    assert len(lines_verbatim) == len(lines) + len(tape[3][2]) + 1


@pytest.mark.parametrize("include_linenum", [True, False])
def test_writefile_bytes_equal_write_output(tmp_path, include_linenum):
    sections = [_mf1_mt452_list(6 * 3000 + 1), _mf3_tab1(3 * 40000 + 2)]
    tape = _tape(sections)
    parser = EndfParserCpp(include_linenum=include_linenum)
    lines = parser.write(tape)
    filename = tmp_path / "out.endf"
    parser.writefile(filename, tape)
    content = filename.read_bytes()
    assert content == "\n".join(lines).encode("latin-1")


def test_writefile_keeps_lines_written_before_an_error(tmp_path):
    # the lines written before an exception are in the file, as when the
    # output went directly to the file stream
    good = _mf3_tab1(3 * 50000)
    bad = _mf3_tab1(5, mt=2)
    bad["xstable"]["xs"] = bad["xstable"]["xs"][:4]
    tape = _tape([good, bad])
    parser = EndfParserCpp()
    filename = tmp_path / "out.endf"
    with pytest.raises(Exception):
        parser.writefile(filename, tape)
    content = filename.read_bytes().decode("latin-1")
    expected = parser.write(_tape([good]))
    # lines of the first section with its SEND record, and the HEAD record
    # and the first line of the TAB1 record of the second section, written
    # before the inconsistent table is detected
    lines_bad = EndfParserCpp().write(_tape([_mf3_tab1(5, mt=2)]))[:2]
    assert content == "\n".join(expected[:-3] + lines_bad) + "\n"
