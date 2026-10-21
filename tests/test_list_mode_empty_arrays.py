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

"""Empty inner arrays with array_type="list": EndfParserPy as EndfParserCpp.

The C++ code creates the element of a nested array before the inner
loop that fills it, also if this loop has no iterations, e.g. the array
al[i] of the Legendre coefficients of an incident energy with NL[i]=0 in
MF4. EndfParserCpp therefore returns an empty list for such an element.
EndfParserPy creates the elements at the same places (taken from the
annotation of the recipe, see interpreter/numpy_annotation.py), so that
both parsers return the same result, and it writes these results back.
With array_type="dict", such elements are absent, as before.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfFloat


TESTDATA = Path(__file__).parent / "testdata"


def _exact(obj):
    if isinstance(obj, EndfFloat):
        return ("EndfFloat", float(obj).hex(), obj.get_original_string())
    if isinstance(obj, float):
        return ("float", obj.hex())
    if isinstance(obj, dict):
        return ("dict", {k: _exact(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ("list", [_exact(v) for v in obj])
    return (type(obj).__name__, obj)


def _py_parser(**kwargs):
    return EndfParserPy(print_cache_info=False, ignore_missing_tpid=True, **kwargs)


@pytest.fixture(scope="module")
def mf4_text():
    # MF4 with NL[i]=0 for the first, the second and the last energy
    parser = _py_parser(array_type="dict", loglevel=40)
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    section = parser.parsefile(path, include=[(4, 2)])[4][2]
    for i in (1, 2, max(section["al"])):
        del section["al"][i]
        section["NL"][i] = 0
    writer = _py_parser(array_type="dict", check_arrays=False)
    return "\n".join(writer.write({4: {2: section}}))


@pytest.fixture(scope="module")
def mt455_text():
    # MF1/MT455 with energy-dependent decay constants (LDG=1) and
    # NNF=0 precursor families: the arrays lambda[k] and alpha[k] are empty
    section = {
        "MAT": 9437,
        "ZA": 94239.0,
        "AWR": 236.9986,
        "LDG": 1,
        "LNU": 2,
        "NNF": 0,
        "NE": 2,
        "E_interpol": {"NBT": [2], "INT": [2]},
        "E": [1e-5, 2e7],
        "Eint": [1e-5, 2e7],
        "nubar_d": [0.0165, 0.009],
        "NBT": [2],
        "INT": [2],
    }
    writer = _py_parser(array_type="list", check_arrays=False)
    return "\n".join(writer.write({1: {455: section}}))


def _empty_elements(endf_dict, case):
    if case == "mf4":
        al = endf_dict[4][2]["al"]
        return [al[0], al[1], al[-1]], len(al)
    sec = endf_dict[1][455]
    return sec["lambda"] + sec["alpha"], len(sec["lambda"])


@pytest.mark.parametrize("case", ["mf4", "mt455"])
@pytest.mark.parametrize("mode", ["list", "list_slow"])
def test_same_result_as_cpp_parser(case, mode, mf4_text, mt455_text):
    text = mf4_text if case == "mf4" else mt455_text
    py_dict = _py_parser(array_type=mode, loglevel=40).parse(text)
    cpp_dict = EndfParserCpp(array_type="list", ignore_missing_tpid=True).parse(text)
    assert _exact(py_dict) == _exact(cpp_dict)
    empty, num = _empty_elements(py_dict, case)
    assert all(e == [] for e in empty)
    assert num == (22 if case == "mf4" else 2)


@pytest.mark.parametrize("case", ["mf4", "mt455"])
@pytest.mark.parametrize("mode", ["list", "list_slow", "numpy"])
def test_roundtrip(case, mode, mf4_text, mt455_text):
    if mode == "numpy":
        pytest.importorskip("numpy")
    text = mf4_text if case == "mf4" else mt455_text
    parser = _py_parser(array_type=mode, loglevel=40)
    assert parser.write(parser.parse(text)) == text.split("\n")


def test_dict_mode_unchanged(mf4_text):
    endf_dict = _py_parser(array_type="dict", loglevel=40).parse(mf4_text)
    al = endf_dict[4][2]["al"]
    assert 1 not in al and 2 not in al and len(al) == 19
