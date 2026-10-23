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

"""Regular blocks of three trailing indices with array_type="numpy".

The recipes MF4/MT1 and MF4/MT2 of the test flavor
(endf_recipes/test/endf_recipe_mf4.py) define a variable that is one
block of three indices, X[i,j,k], and a variable with a leading index
and a block of three indices for each value of it, Y[i][j,k,l]. With
array_type="numpy", both parsers return these blocks as numpy arrays with
three dimensions, also if a dimension is zero. The C++ writer reads such
arrays directly from memory (IndexShifter::get_item_nd); the output must
be the same as for the same values given as lists, also for arrays that
are not C-contiguous or of type float32.
"""

import copy
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfFloat

np = pytest.importorskip("numpy")


def _parser(name, mode):
    kwargs = dict(endf_format="test", array_type=mode, ignore_missing_tpid=True)
    if name == "python":
        return EndfParserPy(print_cache_info=False, **kwargs)
    return EndfParserCpp(**kwargs)


def _value(*idcs):
    return float(sum(10.0**p * v for p, v in enumerate(reversed(idcs)))) + 0.5


def _mt1_dict():
    ni, nj, nk = 3, 2, 4
    x = {
        i: {j: {k: _value(i, j, k) for k in range(1, nk + 1)} for j in range(1, nj + 1)}
        for i in range(1, ni + 1)
    }
    sec = {"MAT": 1, "MF": 4, "MT": 1, "NI": ni, "NJ": nj, "NK": nk}
    sec.update({"NW": {i: nj * nk for i in range(1, ni + 1)}, "X": x})
    return sec


# shapes (NJ[i], NK[i], NL[i]) of the blocks of Y, including empty ones
MT2_SHAPES = [(2, 3, 2), (1, 2, 3), (0, 2, 2), (2, 0, 3), (3, 1, 1)]


def _mt2_dict():
    sec = {"MAT": 1, "MF": 4, "MT": 2, "NI": len(MT2_SHAPES)}
    sec.update({"NJ": {}, "NK": {}, "NL": {}, "NW": {}, "Y": {}})
    for i, (nj, nk, nl) in enumerate(MT2_SHAPES, start=1):
        sec["NJ"][i], sec["NK"][i], sec["NL"][i] = nj, nk, nl
        if nj > 0:
            sec["NW"][i] = {j: nk * nl for j in range(1, nj + 1)}
        if nj > 0 and nk > 0:
            sec["Y"][i] = {
                j: {
                    k: {l: _value(i, j, k, l) for l in range(1, nl + 1)}
                    for k in range(1, nk + 1)
                }
                for j in range(1, nj + 1)
            }
    return sec


def _text(section):
    writer = EndfParserPy(
        endf_format="test",
        array_type="dict",
        print_cache_info=False,
        check_arrays=False,
    )
    return writer.write({4: {section["MT"]: section}})


@pytest.fixture(scope="module", params=[1, 2])
def text(request):
    section = _mt1_dict() if request.param == 1 else _mt2_dict()
    return request.param, "\n".join(_text(section))


_RESULTS = {}


def _parse(text, name, mode):
    key = (text, name, mode)
    if key not in _RESULTS:
        _RESULTS[key] = _parser(name, mode).parse(text)
    return copy.deepcopy(_RESULTS[key])


def _exact(obj):
    if isinstance(obj, np.ndarray):
        return ("ndarray", str(obj.dtype), obj.shape, _exact(obj.tolist()))
    if isinstance(obj, EndfFloat):
        return ("EndfFloat", float(obj).hex(), obj.get_original_string())
    if isinstance(obj, float):
        return ("float", obj.hex())
    if isinstance(obj, dict):
        return ("dict", {k: _exact(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ("list", [_exact(v) for v in obj])
    return (type(obj).__name__, obj)


def _blocks(mt, section):
    return [section["X"]] if mt == 1 else section["Y"]


def _expected_shapes(mt):
    if mt == 1:
        return [(3, 2, 4)]
    return MT2_SHAPES


@pytest.mark.parametrize("name", ["cpp", "python"])
def test_numpy_shapes(text, name):
    mt, text = text
    section = _parse(text, name, "numpy")[4][mt]
    blocks = _blocks(mt, section)
    assert all(isinstance(b, np.ndarray) and b.dtype == np.float64 for b in blocks)
    assert [b.shape for b in blocks] == _expected_shapes(mt)


@pytest.mark.parametrize("mode", ["dict", "list", "numpy"])
def test_same_result_both_parsers(text, mode):
    mt, text = text
    assert _exact(_parse(text, "python", mode)) == _exact(_parse(text, "cpp", mode))


def test_numpy_values_as_list_mode(text):
    mt, text = text
    numpy_blocks = _blocks(mt, _parse(text, "cpp", "numpy")[4][mt])
    list_blocks = _blocks(mt, _parse(text, "cpp", "list")[4][mt])
    assert [b.tolist() for b in numpy_blocks] == list_blocks


@pytest.mark.parametrize("mode", ["dict", "list", "numpy"])
@pytest.mark.parametrize("name", ["cpp", "python"])
def test_roundtrip(text, name, mode):
    mt, text = text
    written = _parser(name, mode).write(_parse(text, name, mode))
    assert "\n".join(written) == text


def _strided(blk):
    # a view of every other element in the last dimension
    shape = blk.shape[:-1] + (2 * blk.shape[-1],)
    big = np.zeros(shape, dtype=blk.dtype)
    big[..., ::2] = blk
    return big[..., ::2]


VARIANTS = {
    "as parsed": lambda blk: blk,
    "fortran order": np.asfortranarray,
    "transposed view": lambda blk: np.ascontiguousarray(blk.T).T,
    "strided view": _strided,
    "float32": lambda blk: blk.astype(np.float32),
}


def _map_blocks(mt, endf_dict, func):
    section = endf_dict[4][mt]
    if mt == 1:
        section["X"] = func(section["X"])
    else:
        section["Y"] = [func(b) for b in section["Y"]]
    return endf_dict


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_cpp_writer_numpy_as_lists(text, variant):
    mt, text = text
    data = _map_blocks(mt, _parse(text, "cpp", "numpy"), VARIANTS[variant])
    as_lists = _map_blocks(mt, copy.deepcopy(data), lambda b: b.tolist())
    written = _parser("cpp", "numpy").write(data)
    assert written == _parser("cpp", "list").write(as_lists)
    if variant != "float32":
        assert "\n".join(written) == text
