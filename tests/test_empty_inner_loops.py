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

"""Arrays of variables that occur several times in an inner loop.

In the test recipe MF7/MT3 (endf_recipes/test/endf_recipe_mf7.py), the
variable NW[i,j] is read in the loop over j and also gives the limit of
the loop over k inside it, so that the element NW[i] used to be created
only inside the loop over j. If that loop had no iterations for some i
(NJ[i] = 0), the element was missing:

- EndfParserCpp raised `IndexError: index out of range` for a later i
  (parsing and writing), and in list mode a missing first element shifted
  the positions of all others;
- EndfParserPy left a hole (None) in list mode or omitted the key in dict
  mode.

Now the element of each leading index is created before the loop of the
next index, so that an inner loop without iterations gives an empty
element, as for the other arrays (C, L, B here): an empty dict, list or
numpy array.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSERS = [EndfParserCpp, EndfParserPy]
ARRAY_TYPES = ["dict", "list", "numpy"]

# NW[i,j] for each i (the length of each list is NJ[i])
SHAPES = {
    "gap": [[1], [], [2]],
    "leading": [[], [1]],
    "trailing": [[1], []],
    "all empty": [[], []],
    "inner gap": [[1, 0, 1]],
    "mixed": [[0, 2], [], [1], []],
}


def _section(shape):
    d = {"MAT": 1, "MF": 7, "MT": 3, "NI": len(shape)}
    d.update({"NJ": {}, "NW": {}, "C": {}, "L": {}, "B": {}})
    for i, nws in enumerate(shape, start=1):
        d["NJ"][i] = len(nws)
        for j, nw in enumerate(nws, start=1):
            d["C"].setdefault(i, {})[j] = float(10 * i + j)
            d["L"].setdefault(i, {})[j] = 0
            d["NW"].setdefault(i, {})[j] = nw
            for k in range(1, nw + 1):
                d["B"].setdefault(i, {}).setdefault(j, {})[k] = float(
                    100 * i + 10 * j + k
                )
    return d


def _parser(ParserCls, array_type="dict"):
    kwargs = dict(
        endf_format="test",
        ignore_missing_tpid=True,
        ignore_send_records=True,
        array_type=array_type,
    )
    if ParserCls is EndfParserPy:
        kwargs["print_cache_info"] = False
    return ParserCls(**kwargs)


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _text(shape):
    return _lines(_parser(EndfParserPy).write({7: {3: _section(shape)}}))


def _plain(obj):
    # numpy arrays as (dtype, list) for comparisons
    if hasattr(obj, "dtype") and hasattr(obj, "tolist"):
        return (str(obj.dtype), obj.tolist())
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


def _expected(name, shape, array_type):
    # NW, C and L have the same structure: one element per i, with one
    # value per j (empty if NJ[i] = 0)
    def per_i(values):
        if array_type == "dict":
            return {i: dict(enumerate(v, start=1)) for i, v in enumerate(values, 1)}
        if array_type == "list":
            return [list(v) for v in values]
        return [(dt, list(v)) for dt, v in values]

    if array_type == "numpy":
        nw = per_i([("int64", nws) for nws in shape])
        c = per_i(
            [
                ("float64", [float(10 * i + j) for j in range(1, len(nws) + 1)])
                for i, nws in enumerate(shape, 1)
            ]
        )
    else:
        nw = per_i(shape)
        c = per_i(
            [
                [float(10 * i + j) for j in range(1, len(nws) + 1)]
                for i, nws in enumerate(shape, 1)
            ]
        )
    return nw, c


@pytest.mark.parametrize("atype", ARRAY_TYPES)
@pytest.mark.parametrize("name", sorted(SHAPES))
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_empty_inner_loop_gives_empty_element(ParserCls, name, atype):
    shape = SHAPES[name]
    res = _parser(ParserCls, atype).parse(_text(shape))[7][3]
    nw, c = _expected(name, shape, atype)
    assert _plain(res["NW"]) == nw
    assert _plain(res["C"]) == c
    # NW has the same structure as C, which is read in the same record
    if atype == "dict":
        assert res["NW"].keys() == res["C"].keys()
    else:
        assert len(res["NW"]) == len(res["C"]) == len(shape)


@pytest.mark.parametrize("atype", ARRAY_TYPES)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_both_parsers_agree(name, atype):
    text = _text(SHAPES[name])
    res = [_plain(_parser(P, atype).parse(text)[7][3]) for P in PARSERS]
    assert res[0] == res[1]


@pytest.mark.parametrize("atype", ARRAY_TYPES)
@pytest.mark.parametrize("name", sorted(SHAPES))
@pytest.mark.parametrize("ParserCls", PARSERS)
def test_round_trip(ParserCls, name, atype):
    text = _text(SHAPES[name])
    parser = _parser(ParserCls, atype)
    res = parser.parse(text)
    assert _lines(parser.write(res)) == text
