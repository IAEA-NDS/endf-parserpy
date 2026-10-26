############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lines read as views into the data held in memory.

If the data is held in memory (`parse`, and `parsefile` with the default
load_file_into_memory=True), EndfParserCpp reads its lines as views into
that memory instead of copying each line. A short line, which is padded
with blanks, is still copied, and lines read through a file stream
(load_file_into_memory=False) are always copied. The results and error
messages must be the same in all cases, including line endings, blank
lines, short and long lines, non-ASCII characters, NUL characters,
truncated data, lookaheads and sections read verbatim.

The C++ module counts the lines read as views and as copies, so that the
tests can check that the lines are read as views where intended.
"""

import importlib
from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, parse_tape


TESTDATA = Path(__file__).parent / "testdata"
DECAY = TESTDATA / "dec-094_Pu_244.endf"
TSL = TESTDATA / "tsl_Al.endf"
NEUTRON = TESTDATA / "n_2925_29-Cu-63.endf"


def _outcome(func):
    try:
        return func()
    except Exception as exc:
        return (type(exc), str(exc))


def _all_ways(path, data, kwargs, selection):
    path.write_bytes(data)
    results = {
        "in_memory": _outcome(
            lambda: EndfParserCpp(**kwargs).parsefile(str(path), **selection)
        ),
        "file_stream": _outcome(
            lambda: EndfParserCpp(load_file_into_memory=False, **kwargs).parsefile(
                str(path), **selection
            )
        ),
        "str": _outcome(
            lambda: EndfParserCpp(**kwargs).parse(data.decode("latin-1"), **selection)
        ),
        "bytes": _outcome(lambda: EndfParserCpp(**kwargs).parse(data, **selection)),
    }
    return results


def _assert_same(results):
    reference = results["file_stream"]
    for way, result in results.items():
        assert result == reference, way


def _lines(path):
    return path.read_bytes().decode("latin-1").split("\n")[:-1]


def _join(lines, eol="\n", end=None):
    end = eol if end is None else end
    return (eol.join(lines) + end).encode("latin-1")


def _replace(line, pos, text):
    return line[:pos] + text + line[pos + len(text) :]


def _shorten(line):
    # without the sequence number and, for the end records, without
    # the MAT/MF/MT numbers that are zero (read as blanks)
    line = line[:75]
    for start, zero in ((72, "  0"), (70, " 0"), (66, "   0")):
        if line[start:] != zero:
            break
        line = line[:start]
    return line.rstrip()


def _mutations(lines):
    n = len(lines)
    mid = n // 2
    short = [_shorten(l) for l in lines]
    assert any(len(s) < 75 for s in short)
    yield "lf", _join(lines)
    yield "crlf", _join(lines, "\r\n")
    yield "crlf_without_final_newline", _join(lines, "\r\n", "")
    yield "cr_at_end_of_data", _join(lines, "\n", "\r")
    yield "cr_only", _join(lines, "\r")
    yield "double_cr", _join(
        [l + "\r" if i % 5 == 2 else l for i, l in enumerate(lines)]
    )
    yield "lone_cr", _join(
        [_replace(l, 30, "\r") if i in (3, mid) else l for i, l in enumerate(lines)]
    )
    yield "short_lines", _join(short)
    yield "short_lines_crlf", _join(short, "\r\n")
    yield "short_and_long_lines", _join(
        [l + " " * 10 if i % 2 else s for i, (l, s) in enumerate(zip(lines, short))]
    )
    yield "lines_cut_at_70", _join(
        [l[:70] if i % 7 == 3 else l for i, l in enumerate(lines)]
    )
    yield "line_cut_at_10", _join(
        [l[:10] if i == mid else l for i, l in enumerate(lines)]
    )
    yield "long_line", _join([l + "X" if i == mid else l for i, l in enumerate(lines)])
    yield "long_text_line", _join(
        [l + "XY" if i == 6 else l for i, l in enumerate(lines)]
    )
    yield "long_last_line", _join(lines[:-1] + [lines[-1] + "Z"], "\n", "")
    yield "blank_lines", _join(lines[:mid] + ["", " \t "] + lines[mid:])
    yield "blank_lines_at_end", _join(lines + ["", "   "])
    yield "blank_line_at_start", _join([""] + lines)
    yield "blank_line_before_tend", _join(lines[:-1] + [""] + lines[-1:])
    yield "latin1_text", _join(
        [_replace(l, 20, "\xe9") if i == 6 else l for i, l in enumerate(lines)]
    )
    yield "utf8_text", _join(
        [l[:20] + "\xc3\xa9" + l[21:] if i == 6 else l for i, l in enumerate(lines)]
    )
    yield "non_ascii_short_line", _join(
        [s + "\xe9" if i == 6 else s for i, s in enumerate(short)]
    )
    yield "control_character", _join(
        [_replace(l, 5, "\x01") if i == mid else l for i, l in enumerate(lines)]
    )
    yield "nul_in_text", _join(
        [_replace(l, 12, "\x00") if i == 6 else l for i, l in enumerate(lines)]
    )
    yield "nul_in_data", _join(
        [_replace(l, 3, "\x00") if i == mid else l for i, l in enumerate(lines)]
    )
    yield "nul_after_short_line", _join(
        [s + "\x00" if i == mid else s for i, s in enumerate(short)]
    )
    yield "nul_line", _join(lines[:mid] + ["\x00" * 80] + lines[mid:])
    yield "bad_mt", _join(
        [_replace(l, 72, "777") if i == mid else l for i, l in enumerate(lines)]
    )
    yield "bad_mt_short_line", _join(
        [_replace(s, 72, "777") if i == mid else s for i, s in enumerate(short)]
    )
    yield "bad_number", _join(
        [_replace(l, 13, "x") if i == mid else l for i, l in enumerate(lines)]
    )
    data = _join(lines)
    for frac in (0.001, 0.3, 0.5, 0.97):
        yield f"truncated_{frac}", data[: int(len(data) * frac)]
    yield "truncated_at_line_end", _join(lines[:mid])
    yield "without_tend", _join(lines[:-1])


OPTIONS = {
    "default": {},
    "ignore_blank_lines": {"ignore_blank_lines": True},
    "accept_non_ascii_false": {"accept_non_ascii": False},
    "validate_control_records": {"validate_control_records": True},
    "list_preserve": {"array_type": "list", "preserve_value_strings": True},
}


@pytest.mark.parametrize("option", sorted(OPTIONS))
@pytest.mark.parametrize("testfile", [DECAY, TSL], ids=lambda p: p.stem)
def test_same_outcome_as_file_stream(tmp_path, testfile, option):
    lines = _lines(testfile)
    path = tmp_path / "data.endf"
    for name, data in _mutations(lines):
        results = _all_ways(path, data, OPTIONS[option], {})
        reference = results["file_stream"]
        for way, result in results.items():
            assert result == reference, (name, way)


@pytest.mark.parametrize(
    "selection",
    [{"exclude": (1,)}, {"include": (8,)}, {"exclude": ((8, 457),)}],
    ids=["exclude_mf", "include_mf", "exclude_section"],
)
def test_sections_read_verbatim(tmp_path, selection):
    # sections not parsed are read verbatim; their lines are returned as
    # read, also if they are short or end with CRLF
    lines = _lines(DECAY)
    path = tmp_path / "data.endf"
    for data in (
        _join(lines),
        _join(lines, "\r\n"),
        _join([_shorten(l) for l in lines]),
        _join([l + "   " for l in lines]),
    ):
        _assert_same(_all_ways(path, data, {}, selection))
    # the lines of a section read verbatim are returned without the line
    # ending (with a newline instead) and without blanks added
    result = EndfParserCpp().parse(_join(lines, "\r\n"), **selection)
    verbatim = [
        v for mfd in result.values() for v in mfd.values() if isinstance(v, list)
    ]
    assert verbatim
    original_lines = {l + "\n" for l in lines}
    for section in verbatim:
        assert set(section) <= original_lines


def test_error_message_contains_line_as_read(tmp_path):
    # a full line is reported as read; a short line with the blanks added
    lines = _lines(DECAY)
    mid = len(lines) // 2
    full = _replace(lines[mid], 72, "777")
    cut = lines[mid][:60]
    for line, expected in ((full, full), (cut, cut.ljust(75))):
        data = _join(lines[:mid] + [line] + lines[mid + 1 :])
        kwargs = {"validate_control_records": True}
        results = _all_ways(tmp_path / "data.endf", data, kwargs, {})
        _assert_same(results)
        exc_type, message = results["in_memory"]
        assert "Line: " + expected in message


def _line_read_counts(parser, func):
    # numbers of lines read as views and as copies by func
    module = importlib.import_module(parser._parse_endf.__module__)
    module._line_read_counts(reset=True)
    func()
    return module._line_read_counts(reset=True)


@pytest.mark.parametrize("testfile", [DECAY, TSL, NEUTRON], ids=lambda p: p.stem)
@pytest.mark.parametrize(
    "selection",
    [{}, {"exclude": (3,)}, {"include": ((1, 451), 4)}],
    ids=["all", "exclude", "include"],
)
def test_lines_read_as_views_from_memory(testfile, selection):
    # in memory, every line is read as a view, also with lookaheads,
    # sections read verbatim and short lines (padded after reading)
    data = testfile.read_bytes()
    lines = data.decode("latin-1").splitlines()
    nlines = len(lines)
    parser = EndfParserCpp()
    funcs = [
        lambda: parser.parsefile(str(testfile), **selection),
        lambda: parser.parse(data.decode("latin-1"), **selection),
        lambda: parser.parse(data, **selection),
        lambda: parser.parse(_join(lines, "\r\n"), **selection),
    ]
    if not selection:
        # short end records (sections read verbatim stop at them)
        short = _join([_shorten(l) for l in lines])
        funcs.append(lambda: parser.parse(short))
    for func in funcs:
        views, copies = _line_read_counts(parser, func)
        assert copies == 0
        assert views >= nlines


@pytest.mark.parametrize("testfile", [DECAY, NEUTRON], ids=lambda p: p.stem)
def test_lines_copied_from_file_stream(testfile):
    parser = EndfParserCpp(load_file_into_memory=False)
    views, copies = _line_read_counts(parser, lambda: parser.parsefile(str(testfile)))
    assert views == 0
    assert copies >= len(testfile.read_bytes().splitlines())


def test_lines_read_as_views_in_multimaterial_tape():
    # the materials of a tape are parsed from strings (see parse_tape)
    first = DECAY.read_bytes().decode("latin-1").splitlines()
    second = TSL.read_bytes().decode("latin-1").splitlines()
    text = "\n".join(first[:-1] + second[1:]) + "\n"
    parser = EndfParserCpp()
    views, copies = _line_read_counts(
        parser, lambda: parse_tape(text, parser=parser, on_error="raise")
    )
    assert copies == 0
    assert views >= len(first) + len(second) - 2
