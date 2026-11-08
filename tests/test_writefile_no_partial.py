############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""writefile leaves no file behind if the writing fails.

Both parsers write the file only if the writing succeeds: after an error
of the conversion of the data or of the file stream, the file is not
created, and an existing file is unchanged. EndfParserPy builds the text
in memory, EndfParserCpp streams it; both write into a temporary file next
to the file, which becomes the file only on success. Otherwise the result is
that of writing the file with open(): the same bytes as before, the
permissions given by the umask for a new file, an existing file keeps its
permissions and inode, a symbolic link is followed, and an existing file
is only overwritten with overwrite=True. No temporary file is left
behind.
"""

import ast
import os
import stat
import subprocess
import sys
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSERS = [EndfParserCpp, EndfParserPy]


def _mf3_tab1(np, mt=1, mat=125):
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
            "NBT": [np],
            "INT": [2],
            "E": [1e-5 * (1.0 + i) ** 1.5 for i in range(np)],
            "xs": [(-1) ** i * 3.25 / (1.0 + i) for i in range(np)],
        },
    }


def _tape(sections, tpid=True):
    tape = {}
    if tpid:
        tape[0] = {0: {"MAT": 1, "MF": 0, "MT": 0, "TAPEDESCR": "test tape"}}
    for sec in sections:
        tape.setdefault(sec["MF"], {})[sec["MT"]] = sec
    return tape


def _good_tape():
    return _tape([_mf3_tab1(3 * 50000), _mf3_tab1(7, mt=2)])


def _bad_tape():
    # the second section has a table with fewer values than energies, which
    # is detected after the first section (more than the 1 MB that the
    # C++ writer collects before it writes to the file) has been written
    bad = _mf3_tab1(5, mt=2)
    bad["xstable"]["xs"] = bad["xstable"]["xs"][:4]
    return _tape([_mf3_tab1(3 * 50000), bad])


def _expected_bytes(parser, tape):
    return "\n".join(parser.write(tape)).encode("latin-1")


def _umask():
    mask = os.umask(0o022)
    os.umask(mask)
    return mask


posix_only = pytest.mark.skipif(
    os.name != "posix", reason="POSIX permissions and inodes"
)


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_error_leaves_no_file(ParserCls, tmp_path):
    filename = tmp_path / "out.endf"
    with pytest.raises(Exception):
        ParserCls().writefile(filename, _bad_tape())
    assert not filename.exists()
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_missing_tpid_leaves_no_file(ParserCls, tmp_path):
    # the check of the TPID section runs after all sections are written
    filename = tmp_path / "should_not_be_written.endf"
    with pytest.raises(Exception) as excinfo:
        ParserCls().writefile(filename, _tape([_mf3_tab1(3 * 50000)], tpid=False))
    assert "TPID" in str(excinfo.value)
    assert not filename.exists()
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_error_leaves_existing_file_unchanged(ParserCls, tmp_path):
    filename = tmp_path / "out.endf"
    filename.write_bytes(b"previous content\n")
    os.chmod(filename, 0o640)
    before = os.stat(filename)
    with pytest.raises(Exception):
        ParserCls().writefile(filename, _bad_tape(), overwrite=True)
    after = os.stat(filename)
    assert filename.read_bytes() == b"previous content\n"
    assert (after.st_ino, after.st_mode, after.st_mtime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
    )
    assert os.listdir(tmp_path) == ["out.endf"]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_success_writes_the_same_bytes(ParserCls, tmp_path):
    parser = ParserCls()
    tape = _good_tape()
    filename = tmp_path / "out.endf"
    parser.writefile(filename, tape)
    assert filename.read_bytes() == _expected_bytes(parser, tape)
    assert os.listdir(tmp_path) == ["out.endf"]


def test_both_parsers_write_the_same_bytes(tmp_path):
    tape = _good_tape()
    EndfParserCpp().writefile(tmp_path / "cpp.endf", tape)
    EndfParserPy().writefile(tmp_path / "py.endf", tape)
    assert (tmp_path / "cpp.endf").read_bytes() == (tmp_path / "py.endf").read_bytes()
    assert sorted(os.listdir(tmp_path)) == ["cpp.endf", "py.endf"]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_overwrite_semantics(ParserCls, tmp_path):
    parser = ParserCls()
    tape = _good_tape()
    filename = tmp_path / "out.endf"
    filename.write_bytes(b"previous content\n")
    with pytest.raises(FileExistsError):
        parser.writefile(filename, tape)
    with pytest.raises(FileExistsError):
        parser.writefile(filename, tape, overwrite=False)
    assert filename.read_bytes() == b"previous content\n"
    parser.writefile(filename, tape, overwrite=True)
    assert filename.read_bytes() == _expected_bytes(parser, tape)
    # a longer file is truncated
    filename.write_bytes(b"x" * (len(_expected_bytes(parser, tape)) + 1000))
    parser.writefile(filename, tape, overwrite=True)
    assert filename.read_bytes() == _expected_bytes(parser, tape)
    # overwrite=True also writes a file that does not exist
    other = tmp_path / "new.endf"
    parser.writefile(other, tape, overwrite=True)
    assert other.read_bytes() == _expected_bytes(parser, tape)
    assert sorted(os.listdir(tmp_path)) == ["new.endf", "out.endf"]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_missing_directory_raises_file_not_found(ParserCls, tmp_path):
    filename = tmp_path / "missing" / "out.endf"
    with pytest.raises(FileNotFoundError) as excinfo:
        ParserCls().writefile(filename, _good_tape())
    assert excinfo.value.filename == str(filename)
    assert os.listdir(tmp_path) == []


@posix_only
@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("umask", [0o022, 0o077, 0o002])
def test_new_file_permissions_follow_umask(ParserCls, tmp_path, umask):
    filename = tmp_path / "out.endf"
    previous = os.umask(umask)
    try:
        ParserCls().writefile(filename, _good_tape())
    finally:
        os.umask(previous)
    assert stat.S_IMODE(os.stat(filename).st_mode) == 0o666 & ~umask


@posix_only
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_existing_file_keeps_inode_and_permissions(ParserCls, tmp_path):
    parser = ParserCls()
    tape = _good_tape()
    filename = tmp_path / "out.endf"
    filename.write_bytes(b"previous content\n")
    os.chmod(filename, 0o604)
    os.link(filename, tmp_path / "hardlink.endf")
    before = os.stat(filename)
    parser.writefile(filename, tape, overwrite=True)
    after = os.stat(filename)
    assert after.st_ino == before.st_ino
    assert stat.S_IMODE(after.st_mode) == 0o604
    assert (tmp_path / "hardlink.endf").read_bytes() == _expected_bytes(parser, tape)
    assert sorted(os.listdir(tmp_path)) == ["hardlink.endf", "out.endf"]


def _symlink_or_skip(src, dst):
    try:
        os.symlink(src, dst)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links not supported")


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_symlink_is_followed(ParserCls, tmp_path):
    parser = ParserCls()
    tape = _good_tape()
    (tmp_path / "data").mkdir()
    target = tmp_path / "data" / "target.endf"
    target.write_bytes(b"previous content\n")
    link = tmp_path / "link.endf"
    _symlink_or_skip(target, link)
    parser.writefile(link, tape, overwrite=True)
    assert link.is_symlink()
    assert target.read_bytes() == _expected_bytes(parser, tape)
    # an error changes neither the link nor its target
    content = target.read_bytes()
    with pytest.raises(Exception):
        parser.writefile(link, _bad_tape(), overwrite=True)
    assert link.is_symlink()
    assert target.read_bytes() == content
    assert os.listdir(tmp_path / "data") == ["target.endf"]
    assert sorted(os.listdir(tmp_path)) == ["data", "link.endf"]


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_dangling_symlink_creates_its_target(ParserCls, tmp_path):
    parser = ParserCls()
    tape = _good_tape()
    (tmp_path / "data").mkdir()
    target = tmp_path / "data" / "target.endf"
    link = tmp_path / "link.endf"
    _symlink_or_skip(target, link)
    with pytest.raises(Exception):
        parser.writefile(link, _bad_tape())
    assert link.is_symlink() and not target.exists()
    assert os.listdir(tmp_path / "data") == []
    parser.writefile(link, tape)
    assert link.is_symlink()
    assert target.read_bytes() == _expected_bytes(parser, tape)
    assert os.listdir(tmp_path / "data") == ["target.endf"]


@posix_only
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root writes into directories without write permission",
)
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_existing_file_in_read_only_directory(ParserCls, tmp_path):
    # the file is writable, the directory is not: no temporary file can be
    # created next to it, but the file can be overwritten as with open()
    parser = ParserCls()
    tape = _good_tape()
    directory = tmp_path / "readonly"
    directory.mkdir()
    filename = directory / "out.endf"
    filename.write_bytes(b"previous content\n")
    os.chmod(directory, 0o555)
    try:
        with pytest.raises(Exception):
            parser.writefile(filename, _bad_tape(), overwrite=True)
        assert filename.read_bytes() == b"previous content\n"
        parser.writefile(filename, tape, overwrite=True)
        assert filename.read_bytes() == _expected_bytes(parser, tape)
        assert os.listdir(directory) == ["out.endf"]
        with pytest.raises(PermissionError):
            parser.writefile(directory / "new.endf", tape)
    finally:
        os.chmod(directory, 0o755)


_STREAM_ERROR_SCRIPT = """
import os, resource, signal, sys
from endf_parserpy import EndfParserCpp, EndfParserPy
sys.path.insert(0, sys.argv[1])
from test_writefile_no_partial import _good_tape
# files are limited to 200000 bytes: a write beyond fails with EFBIG
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (200000, 200000))
directory, mode = sys.argv[2], sys.argv[3]
results = []
for cls in (EndfParserCpp, EndfParserPy):
    parser = cls()
    if mode == "cpp_function" and cls is not EndfParserCpp:
        continue
    try:
        if mode == "cpp_function":
            parser._write_endf_file(
                os.path.join(directory, "direct.endf"),
                _good_tape(), None, None, parser.write_opts,
            )
        else:
            parser.writefile(
                os.path.join(directory, mode + ".endf"), _good_tape(),
                overwrite=True,
            )
        results.append("no error")
    except Exception as exc:
        results.append(type(exc).__name__ + ": " + str(exc))
print(repr(results))
"""


def _run_with_file_size_limit(tmp_path, mode):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in [env.get("PYTHONPATH", ""), os.getcwd()] if p
    )
    res = subprocess.run(
        [
            sys.executable,
            "-c",
            _STREAM_ERROR_SCRIPT,
            os.path.dirname(os.path.abspath(__file__)),
            str(tmp_path),
            mode,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return ast.literal_eval(res.stdout.strip().splitlines()[-1])


linux_only = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="needs RLIMIT_FSIZE"
)


@linux_only
def test_stream_error_leaves_no_file(tmp_path):
    # the text (more than 200000 bytes) does not fit into the file size
    # limit: an error of the writing, as for a full disk
    for mode in ("new", "existing"):
        if mode == "existing":
            (tmp_path / "existing.endf").write_bytes(b"previous content\n")
        results = _run_with_file_size_limit(tmp_path, mode)
        assert len(results) == 2 and all(r != "no error" for r in results), results
    assert os.listdir(tmp_path) == ["existing.endf"]
    assert (tmp_path / "existing.endf").read_bytes() == b"previous content\n"


@linux_only
def test_cpp_stream_error_is_an_error(tmp_path):
    # the C++ function that writes the (temporary) file reports an error
    # of the stream instead of returning normally
    results = _run_with_file_size_limit(tmp_path, "cpp_function")
    assert len(results) == 1 and "failed to write file" in results[0], results
