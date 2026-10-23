############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/23
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Writing numpy arrays with several dimensions with EndfParserCpp.

The writer reads the elements of a numpy array with one dimension per
remaining index of a variable directly from memory, e.g. the regular
blocks b[j] of MF6 LAW=1 (two dimensions for the indices k and m), using
the shape and strides of the array. The output must be the same as for
the same values given as lists, also for arrays that are not
C-contiguous (Fortran order, strided views), of another float type, or
empty.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp

np = pytest.importorskip("numpy")


TESTDATA = Path(__file__).parent / "testdata"


@pytest.fixture(scope="module")
def mf6_numpy():
    # MF6/MT5 of Cu-63: blocks b[j] with two and more columns
    parser = EndfParserCpp(array_type="numpy")
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    return parser.parsefile(path, include=[(6, 5)])


def _blocks(endf_dict):
    for sub in endf_dict[6][5]["subsection"]:
        if sub.get("LAW") == 1:
            yield sub


def _map_blocks(endf_dict, func):
    for sub in _blocks(endf_dict):
        sub["b"] = [func(blk) for blk in sub["b"]]
    return endf_dict


def _strided(blk):
    # a view of every other column of a larger array
    big = np.zeros((blk.shape[0], 2 * blk.shape[1]), dtype=blk.dtype)
    big[:, ::2] = blk
    return big[:, ::2]


VARIANTS = {
    "as parsed": lambda blk: blk,
    "fortran order": np.asfortranarray,
    "transposed view": lambda blk: np.ascontiguousarray(blk.T).T,
    "strided view": _strided,
    "float32": lambda blk: blk.astype(np.float32),
}


def _as_lists(blk):
    return [[float(v) for v in row] for row in blk]


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_written_as_lists(mf6_numpy, variant):
    import copy

    parser = EndfParserCpp(array_type="numpy")
    func = VARIANTS[variant]
    data = _map_blocks(copy.deepcopy(mf6_numpy), func)
    assert any(
        blk.ndim == 2 and blk.shape[1] > 1 for s in _blocks(data) for blk in s["b"]
    )
    expected = _map_blocks(copy.deepcopy(data), _as_lists)
    list_parser = EndfParserCpp(array_type="list")
    assert parser.write(data) == list_parser.write(expected)


def test_original_output(mf6_numpy):
    parser = EndfParserCpp(array_type="numpy")
    list_parser = EndfParserCpp(array_type="list")
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    list_dict = list_parser.parsefile(path, include=[(6, 5)])
    assert parser.write(mf6_numpy) == list_parser.write(list_dict)
