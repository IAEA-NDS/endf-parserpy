############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests for the `load_file_into_memory` option of EndfParserCpp.

By default, EndfParserCpp.parsefile reads the complete file into memory
and parses it from there; with load_file_into_memory=False, the file is
read through a file stream while it is parsed. Strings passed to parse
are parsed in place. All three ways must give the same result, also for
empty, short and truncated files, whose errors must be the same. A file
is read into memory allocated for its size; a file whose size is not
known in advance, e.g. a named pipe, is read in chunks.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserFactory


TESTDATA = Path(__file__).parent / "testdata"
FILES = ["n_2925_29-Cu-63.endf", "tsl_Al.endf"]


@pytest.mark.parametrize("filename", FILES)
@pytest.mark.parametrize(
    "selection",
    [{}, {"exclude": (3,)}, {"include": ((1, 451), 4)}],
    ids=["all", "exclude", "include"],
)
def test_parse_results_independent_of_reading_mode(filename, selection):
    path = str(TESTDATA / filename)
    in_memory = EndfParserCpp().parsefile(path, **selection)
    streamed = EndfParserCpp(load_file_into_memory=False).parsefile(path, **selection)
    from_string = EndfParserCpp().parse(Path(path).read_text(), **selection)
    assert streamed == in_memory
    assert from_string == in_memory


def test_option_in_read_opts():
    assert EndfParserCpp().read_opts["load_file_into_memory"] is True
    parser = EndfParserCpp(load_file_into_memory=False)
    assert parser.read_opts["load_file_into_memory"] is False


def test_missing_file_raises_in_both_modes(tmp_path):
    missing = str(tmp_path / "missing.endf")
    for load in (True, False):
        with pytest.raises(Exception, match="failed to open file"):
            EndfParserCpp(load_file_into_memory=load).parsefile(missing)


def _outcome(func):
    try:
        return func()
    except Exception as exc:
        return (type(exc), str(exc))


def _all_ways(path, **kwargs):
    in_memory = _outcome(lambda: EndfParserCpp(**kwargs).parsefile(path))
    streamed = _outcome(
        lambda: EndfParserCpp(load_file_into_memory=False, **kwargs).parsefile(path)
    )
    text = Path(path).read_bytes().decode("latin-1")
    from_string = _outcome(lambda: EndfParserCpp(**kwargs).parse(text))
    return in_memory, streamed, from_string


# sizes around the chunk size (64 KiB) used if the size of a file is unknown
@pytest.mark.parametrize(
    "size", [0, 1, 81, 400, 65535, 65536, 65537, 131072, 131073, None]
)
def test_file_sizes(tmp_path, size):
    data = (TESTDATA / "n_2925_29-Cu-63.endf").read_bytes()
    assert len(data) > 131073
    if size is not None:
        data = data[:size]
    path = tmp_path / "data.endf"
    path.write_bytes(data)
    for kwargs in ({}, {"ignore_blank_lines": True}):
        in_memory, streamed, from_string = _all_ways(str(path), **kwargs)
        assert streamed == in_memory
        assert from_string == in_memory


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes not available")
def test_named_pipe(tmp_path):
    # the size of a pipe is unknown: its content is read in chunks; the
    # data is written by another process, as the parser holds the GIL
    source = TESTDATA / "n_2925_29-Cu-63.endf"
    fifo = tmp_path / "pipe.endf"
    os.mkfifo(fifo)
    code = "import shutil, sys; shutil.copyfileobj(open(sys.argv[1], 'rb'), open(sys.argv[2], 'wb'))"
    writer = subprocess.Popen([sys.executable, "-c", code, str(source), str(fifo)])
    try:
        result = EndfParserCpp().parsefile(str(fifo))
    finally:
        writer.wait(timeout=60)
    assert result == EndfParserCpp().parse(source.read_bytes().decode("latin-1"))


@pytest.mark.parametrize("load", [True, False])
def test_option_accepted_by_parser_factory(load):
    path = str(TESTDATA / "tsl_Al.endf")
    cpp_parser = EndfParserFactory.create(select="cpp", load_file_into_memory=load)
    py_parser = EndfParserFactory.create(
        select="python", load_file_into_memory=load, print_cache_info=False
    )
    assert isinstance(cpp_parser, EndfParserCpp)
    assert cpp_parser.read_opts["load_file_into_memory"] is load
    assert (
        py_parser.parsefile(path)[7][4]["AWR"]
        == cpp_parser.parsefile(path)[7][4]["AWR"]
    )
