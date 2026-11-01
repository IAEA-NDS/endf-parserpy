"""The bulk structural scan of TapeIndex.from_file.

``TapeIndex.from_file`` scans a tape in windows of records of equal
width, with numpy where it is installed and with a pure-Python kernel
otherwise. Both must yield exactly what the record-by-record ``_scan``
yields over the records of the file -- the same index, or the same
exception -- for any input, including tapes of mixed record widths and
malformed tapes. These tests compare the two on multi-material tapes
built at run time from the small test files, and on damaged variants.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import endf_parserpy
from endf_parserpy.tape import index as tape_index
from endf_parserpy.tape import TapeIndex


TESTDATA = Path(__file__).parent / "testdata"
SOURCES = [
    "n_2925_29-Cu-63.endf",  # 80-byte records
    "dec-094_Pu_244.endf",  # 75-byte records
    "n_3025_30-Zn-64.endf",
    "tsl_Al.endf",
]


def _lines(name):
    data = (TESTDATA / name).read_bytes().replace(b"\r\n", b"\n")
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


def _tape(names, seps=None):
    """Concatenate single-material files into one tape (TPID ... TEND)."""
    seps = seps or [b"\n"] * len(names)
    first = _lines(names[0])
    out = [first[0] + b"\n"]
    for name, sep in zip(names, seps):
        body = _lines(name)[1:-1]
        out.append(sep.join(body) + sep)
    out.append(first[-1] + b"\n")
    return b"".join(out)


def _canon(index):
    mats = []
    for m in index:
        secs = [(k, e.offset, e.length, e.line_count) for k, e in m.sections.items()]
        mats.append(
            (m.position, m.mat, m.za, m.awr, m.byte_offset, m.byte_length, secs)
        )
    return (index.tpid_line, index.tpid_offset, index.tpid_length, mats)


def _reference(path):
    """The record-by-record scan over the binary records of the file."""

    def records(fh):
        for raw in fh:
            yield len(raw), raw[:-1] if raw.endswith(b"\n") else raw

    try:
        with open(path, "rb") as fh:
            materials, tpid = tape_index._scan(records(fh))
        return _canon(TapeIndex(materials, *tpid))
    except Exception as exc:
        return (type(exc).__name__, str(exc))


def _from_file(path, **kwargs):
    try:
        return _canon(TapeIndex.from_file(path, **kwargs))
    except Exception as exc:
        return (type(exc).__name__, str(exc))


@pytest.fixture(params=["numpy", "python"])
def kernel(request, monkeypatch):
    if request.param == "numpy":
        if tape_index._np is None:
            pytest.skip("numpy not installed")
    else:
        monkeypatch.setattr(tape_index, "_np", None)
    return request.param


@pytest.fixture(scope="module")
def tape_bytes():
    return _tape(SOURCES)


def _damaged(tape):
    """Yield ``(name, bytes)`` damaged variants of a tape."""
    lines = tape.split(b"\n")[:-1]
    n = len(lines)
    # rows near the starts of the scan windows and inside sections
    rows = [1, 2, 1023, 1024, 1025, 5120, 5121, n // 3, n - 3]
    rows = sorted(set(i for i in rows if i < n - 2))

    def join(ls, sep=b"\n"):
        return sep.join(ls) + sep

    def ctrl(line, field):
        return line[:66] + field + line[75:]

    yield "intact", tape
    for i in rows:
        line = lines[i]
        before, after = lines[:i], lines[i + 1 :]
        for k in (0, 40, 66, 70):
            # two records in the space of one, the row width preserved
            two = line[:k] + b"\n" + line[k + 1 :]
            yield f"two_records_{i}_{k}", join(before + [two] + after)
        yield f"blank_full_{i}", join(before + [b" " * len(line), line] + after)
        yield f"blank_empty_{i}", join(before + [b"", line] + after)
        yield f"form_feed_{i}", join(before + [b"\x0c", line] + after)
        yield f"short_{i}", join(before + [line[:70]] + after)
        yield f"short_ctrl_{i}", join(before + [line[:60]] + after)
        yield f"long_{i}", join(before + [line + b"x" * 200] + after)
        yield f"crlf_one_{i}", join(before + [line + b"\r"] + after)
        yield f"tab_{i}", join(before + [line[:5] + b"\t" + line[6:]] + after)
        yield f"nonascii_{i}", join(before + [b"\xe9" + line[1:]] + after)
        yield f"dup3_{i}", join(before + [line] * 3 + after)
        yield f"dropped_{i}", join(before + after)
        yield f"blank_ctrl_{i}", join(before + [ctrl(line, b" " * 9)] + after)
        for tag, field in (
            ("mtx", line[66:72] + b" 1x"),
            ("underscore", line[66:72] + b"1_2"),
            ("plus", line[66:70] + b"+3" + line[72:75]),
            ("mt0", line[66:72] + b"  0"),
            ("mf0", line[66:70] + b" 0" + line[72:75]),
            ("matm1", b"  -1" + line[70:75]),
            ("mend", b"   0 0  0"),
            ("digits", "٣".encode() + line[68:75]),
        ):
            yield f"ctrl_{tag}_{i}", join(before + [ctrl(line, field)] + after)
        yield f"seq_stretch_{i}", join(
            before
            + [l + b"%5d" % j for j, l in enumerate(lines[i : i + 9])]
            + lines[i + 9 :]
        )
    for frac in (0.0001, 0.3, 0.7, 0.9999):
        cut = int(len(tape) * frac)
        yield f"truncated_{frac}", tape[:cut]
        yield f"truncated_eol_{frac}", tape[: tape.rfind(b"\n", 0, cut) + 1]
    yield "crlf", tape.replace(b"\n", b"\r\n")
    yield "crlf_alternating", b"".join(
        l + (b"\r\n" if j % 2 else b"\n") for j, l in enumerate(lines)
    )
    yield "no_final_newline", tape[:-1]
    yield "trailing_garbage", tape + lines[5] + b"\n" + b"x" * 30
    yield "no_tpid", join(lines[1:])
    yield "blank_before_tpid", b"\n" + b" " * 80 + b"\n" + tape
    yield "no_tend", join(lines[:-1])
    yield "no_mend_tend", join(lines[:-2])
    yield "empty", b""
    yield "blank_only", b"\n \n\t\n"
    yield "tpid_only", lines[0]


def test_bulk_scan_matches_record_scan_on_tapes(kernel, tmp_path):
    seps_mixed = [b"\n", b"\r\n", b"\n", b"\r\n"]
    tapes = {
        "mixed_widths": _tape(SOURCES),
        "crlf_per_material": _tape(SOURCES, seps_mixed),
        "uniform": _tape(SOURCES[:1] * 3 + SOURCES[2:3]),
        "decay_repeated": _tape(SOURCES[1:2] * 40),
    }
    for name, data in tapes.items():
        path = tmp_path / f"{name}.endf"
        path.write_bytes(data)
        expected = _reference(path)
        assert isinstance(expected[3], list) and len(expected[3]) > 1
        assert _from_file(path) == expected, name
        assert _from_file(path, chunk_bytes=4093) == expected, name


def test_bulk_scan_matches_record_scan_on_damaged_tapes(kernel, tmp_path):
    # two record widths, more records than the first scan windows hold
    tape = _tape(["tsl_Al.endf", "dec-094_Pu_244.endf"] * 2)
    path = tmp_path / "damaged.endf"
    for name, data in _damaged(tape):
        path.write_bytes(data)
        expected = _reference(path)
        assert _from_file(path) == expected, name
        assert _from_file(path, chunk_bytes=100003) == expected, name


def test_bulk_scan_small_blocks(kernel, tmp_path):
    # blocks shorter than a record force the block to grow
    tape = _tape(SOURCES[1:2] * 3)
    path = tmp_path / "small.endf"
    for name, data in _damaged(tape):
        if not name.startswith(("intact", "long", "two_records", "trunc", "crlf")):
            continue
        path.write_bytes(data)
        expected = _reference(path)
        for chunk in (50, 81, 997):
            assert _from_file(path, chunk_bytes=chunk) == expected, (name, chunk)


def test_two_records_in_one_row(kernel, tmp_path):
    # a row of the uniform width that holds two records is two records
    lines = _lines(SOURCES[0])
    i = 3000
    two = lines[i][:40] + b"\n" + lines[i][41:]
    path = tmp_path / "two.endf"
    path.write_bytes(b"\n".join(lines[:i] + [two] + lines[i + 1 :]) + b"\n")
    index = TapeIndex.from_file(path)
    assert _canon(index) == _reference(path)
    total = sum(e.line_count for e in index[0].sections.values())
    intact = tmp_path / "intact.endf"
    intact.write_bytes(b"\n".join(lines) + b"\n")
    assert total != sum(
        e.line_count for e in TapeIndex.from_file(intact)[0].sections.values()
    )


def test_from_file_without_numpy(tmp_path):
    # in a process where numpy cannot be imported, the index is the same
    path = tmp_path / "tape.endf"
    path.write_bytes(_tape(SOURCES, [b"\n", b"\r\n", b"\n", b"\n"]))
    code = (
        "import sys, pickle\n"
        "sys.modules['numpy'] = None\n"
        "from endf_parserpy.tape import TapeIndex\n"
        "import endf_parserpy.tape.index as ti\n"
        "assert ti._np is None\n"
        f"idx = TapeIndex.from_file({str(path)!r})\n"
        "assert sys.modules['numpy'] is None\n"
        "sys.stdout.buffer.write(pickle.dumps(idx))\n"
    )
    env = dict(os.environ)
    pkg_root = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(
        [pkg_root] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, cwd=tmp_path, env=env
    )
    assert result.returncode == 0, result.stderr.decode()
    import pickle

    assert _canon(pickle.loads(result.stdout)) == _reference(path)
    assert _canon(TapeIndex.from_file(path)) == _reference(path)
