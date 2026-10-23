############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/23
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
With array_type="dict", such an element is an empty dictionary in both
parsers.
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


@pytest.mark.parametrize("case", ["mf4", "mt455"])
def test_dict_mode_same_result_as_cpp_parser(case, mf4_text, mt455_text):
    # the empty inner arrays are empty dictionaries in both parsers
    text = mf4_text if case == "mf4" else mt455_text
    py_dict = _py_parser(array_type="dict", loglevel=40).parse(text)
    cpp_dict = EndfParserCpp(array_type="dict", ignore_missing_tpid=True).parse(text)
    assert _exact(py_dict) == _exact(cpp_dict)
    if case == "mf4":
        al = py_dict[4][2]["al"]
        assert al[1] == {} and al[2] == {} and al[max(al)] == {} and len(al) == 22
    else:
        sec = py_dict[1][455]
        assert all(sec[v][k] == {} for v in ("lambda", "alpha") for k in (1, 2))


@pytest.mark.parametrize("parser_name", ["python", "cpp"])
@pytest.mark.parametrize("case", ["mf4", "mt455"])
def test_dict_mode_roundtrip(case, parser_name, mf4_text, mt455_text):
    # also with check_arrays=True (the default), the empty inner arrays
    # are accepted when writing
    text = mf4_text if case == "mf4" else mt455_text
    if parser_name == "python":
        parser = _py_parser(array_type="dict", loglevel=40)
    else:
        parser = EndfParserCpp(array_type="dict", ignore_missing_tpid=True)
    assert parser.write(parser.parse(text)) == text.split("\n")


# a recipe that the annotation does not support: the field A+B with two
# unknown variables, in a branch that is not executed for the data below
FALLBACK_RECIPE = """
[MAT, 3, MT/ 0.0, 0.0, N, L, 0, 0]HEAD
if L == 1:
    [MAT, 3, MT/ 0.0, 0.0, A+B, 0, 0, 0]CONT
endif
for i=1 to N:
    [MAT, 3, MT/ 0.0, 0.0, 0, 0, NL[i], 0/ {al[i,l]}{l=1 to NL[i]} ]LIST
endfor
SEND
"""


def _fallback_text():
    section = {"MAT": 1, "MF": 3, "MT": 1, "N": 2, "L": 0}
    section.update({"NL": {1: 0, 2: 1}, "al": {2: {1: 1.0}}})
    writer = _py_parser(
        array_type="dict", recipes={3: FALLBACK_RECIPE}, cache_dir=False
    )
    return "\n".join(writer.write({3: {1: section}}))


@pytest.mark.parametrize("mode", ["dict", "list", "list_slow", "numpy"])
def test_recipe_without_annotation(mode):
    # without the annotation, the arrays are parsed as before it was
    # introduced (elements are only created when values are assigned to
    # them), except with array_type="numpy", which depends on it
    if mode == "numpy":
        pytest.importorskip("numpy")
    from endf_parserpy.interpreter.custom_exceptions import RecipeAnnotationError

    parser = _py_parser(
        array_type=mode, recipes={3: FALLBACK_RECIPE}, cache_dir=False, loglevel=40
    )
    text = _fallback_text()
    if mode == "numpy":
        with pytest.raises(RecipeAnnotationError):
            parser.parse(text)
        return
    section = parser.parse(text)[3][1]
    al = section["al"]
    if mode == "dict":
        assert al == {2: {1: 1.0}}
    else:
        assert al == [[1.0]]
    assert parser.write({3: {1: section}}) == text.split("\n")


@pytest.mark.parametrize("mode", ["list", "list_slow", "numpy"])
def test_empty_arrays_after_failed_write(mode, mf4_text):
    # a failed write must not leave the array state options of the parser
    # behind: a later parse would skip the creation of the empty inner
    # arrays and silently return the result of the dict-based conversion
    if mode == "numpy":
        pytest.importorskip("numpy")
    parser = _py_parser(array_type=mode, loglevel=40)
    reference = None if mode == "numpy" else _exact(parser.parse(mf4_text))
    with pytest.raises(Exception):
        # the MF number of the section contradicts its key, which
        # raises before the recipe of the section is executed
        parser.write({4: {2: {"MF": 3, "MT": 2}}})
    py_dict = parser.parse(mf4_text)
    if reference is not None:
        assert _exact(py_dict) == reference
    al = py_dict[4][2]["al"]
    assert all(len(al[i]) == 0 for i in (0, 1, -1))
