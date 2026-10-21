############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Writing arrays given as sequences other than lists with EndfParserCpp.

With array_type="list", the writer accepts any sequence for an array. It
converted every sequence other than a list into a new list on each access
of an element, which made writing take time quadratic in the length of the
array. Such sequences are now indexed directly; the written output must be
identical to that of lists.
"""

from pathlib import Path
from collections.abc import Sequence
import pytest
from endf_parserpy import EndfParserCpp


TESTFILES = [
    str(Path(__file__).parent / "testdata" / f)
    for f in ("n_2925_29-Cu-63.endf", "tsl_Al.endf")
]


class _ReadOnlySequence(Sequence):
    # a read-only view of a list, like those of the tape module
    def __init__(self, data):
        self._data = data

    def __getitem__(self, i):
        return self._data[i]

    def __len__(self):
        return len(self._data)


def _convert(x, seqtype):
    if isinstance(x, dict):
        return {k: _convert(v, seqtype) for k, v in x.items()}
    if isinstance(x, list):
        return seqtype([_convert(v, seqtype) for v in x])
    return x


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.mark.parametrize("filename", TESTFILES)
@pytest.mark.parametrize("seqtype", [tuple, _ReadOnlySequence], ids=["tuple", "view"])
def test_sequences_written_like_lists(filename, seqtype):
    parser = EndfParserCpp(array_type="list")
    data = parser.parsefile(filename)
    reference = _lines(parser.write(data))
    assert _lines(parser.write(_convert(data, seqtype))) == reference


@pytest.mark.parametrize("filename", TESTFILES)
def test_sequences_written_from_files(filename, tmp_path):
    parser = EndfParserCpp(array_type="list")
    data = parser.parsefile(filename)
    out_list = tmp_path / "list.endf"
    out_tuple = tmp_path / "tuple.endf"
    parser.writefile(str(out_list), data)
    parser.writefile(str(out_tuple), _convert(data, tuple))
    assert out_tuple.read_bytes() == out_list.read_bytes()
