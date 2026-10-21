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

"""Tests for `array_type="numpy"` specific to EndfParserPy.

EndfParserPy determines the form of the arrays from the annotation of the
recipe parse trees (endf_parserpy.interpreter.numpy_annotation) and the
assignments executed while parsing, and must return exactly the same
result as EndfParserCpp: the same container types, dtypes, shapes and
values, also for empty arrays and variables whose kind depends on the
branch of the recipe.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")

from endf_parserpy import EndfParserCpp, EndfParserPy, EndfFloat
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.interpreter import numpy_arrays


TESTDATA = Path(__file__).parent / "testdata"
FILES = ["n_2925_29-Cu-63.endf", "tsl_Al.endf"]


def _exact(obj):
    """Representation with container types, dtypes, shapes and exact values."""
    if isinstance(obj, np.ndarray):
        return ("ndarray", str(obj.dtype), obj.shape, obj.tobytes())
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
    return EndfParserPy(print_cache_info=False, **kwargs)


def _ni(LS, NE, F):
    return {"LS": LS, "LB": 5, "NE": NE, "E": [10.0**i for i in range(NE)], "F": F}


# NI-type subsections of MF33 with rectangular and triangular matrices,
# including 1x1 matrices, whose form cannot be told from the row lengths
NI_SUBSECTIONS = [
    (_ni(0, 4, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, -0.9]]), False),
    (_ni(1, 4, [[0.1, 0.2, 0.3], [0.5, 0.6], [0.9]]), True),
    (_ni(0, 2, [[0.25]]), False),
    (_ni(1, 2, [[0.75]]), True),
    (
        {
            "LB": 6,
            "NER": 2,
            "NEC": 2,
            "ER": [1e-5, 2e7],
            "EC": [1e-5, 2e7],
            "F": [[0.5]],
        },
        False,
    ),
]


@pytest.fixture(scope="module")
def mf33_text():
    subsection = {
        "XMF1": 0.0,
        "XLFS1": 0.0,
        "MAT1": 0,
        "MT1": 102,
        "NC": 0,
        "NI": len(NI_SUBSECTIONS),
        "ni_subsection": [ni for ni, _ in NI_SUBSECTIONS],
    }
    section = {
        "MAT": 2925,
        "MF": 33,
        "MT": 102,
        "ZA": 29063.0,
        "AWR": 62.389,
        "MTL": 0,
        "NL": 1,
        "subsection": [subsection],
    }
    parser = _py_parser(array_type="list")
    return "\n".join(parser.write({33: {102: section}}))


@pytest.mark.parametrize("value_strings", [False, True])
@pytest.mark.parametrize("filename", FILES)
def test_same_result_as_cpp_parser(filename, value_strings):
    path = str(TESTDATA / filename)
    opts = dict(array_type="numpy", preserve_value_strings=value_strings)
    py_parser = _py_parser(**opts)
    cpp_parser = EndfParserCpp(**opts)
    py_dict = py_parser.parsefile(path)
    cpp_dict = cpp_parser.parsefile(path)
    assert _exact(py_dict) == _exact(cpp_dict)
    assert py_parser.write(py_dict) == cpp_parser.write(cpp_dict)


def test_matrix_form_follows_definition(mf33_text):
    opts = dict(array_type="numpy", ignore_missing_tpid=True)
    py_dict = _py_parser(**opts).parse(mf33_text)
    cpp_dict = EndfParserCpp(**opts).parse(mf33_text)
    assert _exact(py_dict) == _exact(cpp_dict)
    ni = py_dict[33][102]["subsection"][0]["ni_subsection"]
    for (orig, triangular), parsed in zip(NI_SUBSECTIONS, ni):
        F = parsed["F"]
        if triangular:
            assert isinstance(F, list)
            assert all(isinstance(row, np.ndarray) for row in F)
            assert [row.tolist() for row in F] == orig["F"]
        else:
            assert isinstance(F, np.ndarray)
            assert F.shape == (len(orig["F"]), len(orig["F"][0]))
            assert F.tolist() == orig["F"]
    list_parser = _py_parser(array_type="list", ignore_missing_tpid=True)
    expected = list_parser.write(list_parser.parse(mf33_text))
    assert _py_parser(**opts).write(py_dict) == expected


def _mt455(LNU, NNF):
    section = {"MAT": 9437, "ZA": 94239.0, "AWR": 236.9986, "LDG": 0, "LNU": LNU}
    section["NNF"] = NNF
    if NNF > 0:
        section["lambda"] = [0.0133 * (k + 1) for k in range(NNF)]
    if LNU == 1:
        section["nubar_d"] = 0.0165
    else:
        section.update(
            Eint=[1e-5, 4e6, 2e7], nubar_d=[0.0165, 0.0165, 0.009], NBT=[3], INT=[2]
        )
    parser = _py_parser(array_type="list")
    return "\n".join(parser.write({1: {455: section}}))


@pytest.mark.parametrize("NNF", [0, 2])
@pytest.mark.parametrize("LNU", [1, 2])
def test_kind_follows_branch(LNU, NNF):
    # nubar_d is a float (LNU=1) or the column of a TAB1 record (LNU=2),
    # lambda[k] is not assigned if the loop has no iterations (NNF=0)
    text = _mt455(LNU, NNF)
    opts = dict(array_type="numpy", ignore_missing_tpid=True)
    py_dict = _py_parser(**opts).parse(text)
    cpp_dict = EndfParserCpp(**opts).parse(text)
    assert _exact(py_dict) == _exact(cpp_dict)
    section = py_dict[1][455]
    if LNU == 1:
        assert type(section["nubar_d"]) is float
    else:
        assert section["nubar_d"].dtype == np.float64
        assert section["NBT"].dtype == np.int64
    assert ("lambda" in section) == (NNF > 0)


@pytest.fixture(scope="module")
def mf4_text_with_empty_arrays():
    # MF4 with Legendre coefficients a[i,l], l=1..NL[i], and NL[i]=0 for
    # the first, the second and the last incident energy
    parser = _py_parser(array_type="dict", check_arrays=False, loglevel=40)
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    section = parser.parsefile(path, include=[(4, 2)])[4][2]
    for i in (1, 2, max(section["al"])):
        del section["al"][i]
        section["NL"][i] = 0
    return "\n".join(parser.write({4: {2: section}}))


@pytest.mark.parametrize("value_strings", [False, True])
def test_empty_arrays(mf4_text_with_empty_arrays, value_strings):
    # the C++ code creates the array al[i] of each incident energy before
    # the loop over l, also if this loop has no iterations
    opts = dict(
        array_type="numpy",
        ignore_missing_tpid=True,
        preserve_value_strings=value_strings,
    )
    py_dict = _py_parser(**opts).parse(mf4_text_with_empty_arrays)
    cpp_dict = EndfParserCpp(**opts).parse(mf4_text_with_empty_arrays)
    assert _exact(py_dict) == _exact(cpp_dict)
    al = py_dict[4][2]["al"]
    assert len(al) == len(py_dict[4][2]["NL"])
    for i in (0, 1, -1):
        if value_strings:
            assert al[i] == []
        else:
            assert al[i].dtype == np.float64 and al[i].shape == (0,)


def test_custom_recipe():
    # the annotation of the recipe does not depend on the recipes of the
    # package
    recipe = get_recipe_dict("endf6-ext")[3] + "\n"
    parser = _py_parser(array_type="numpy", recipes={3: recipe}, cache_dir=False)
    path = str(TESTDATA / "n_2925_29-Cu-63.endf")
    py_dict = parser.parsefile(path, include=[(3, 1)])
    cpp_dict = EndfParserCpp(array_type="numpy").parsefile(path, include=[(3, 1)])
    assert _exact(py_dict[3][1]) == _exact(cpp_dict[3][1])


def test_parser_does_not_import_compiler():
    # the Python parser does not depend on the C++ code generator
    code = (
        "import sys\n"
        "from endf_parserpy import EndfParserPy\n"
        "p = EndfParserPy(array_type='numpy', print_cache_info=False)\n"
        f"p.parsefile({str(TESTDATA / 'tsl_Al.endf')!r})\n"
        "mods = [m for m in sys.modules if m.startswith('endf_parserpy.compiler')]\n"
        "assert mods == [], mods\n"
    )
    root = str(Path(__file__).parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([sys.executable, "-c", code], check=True, env=env)


def test_numpy_to_python():
    data = {
        1: {"a": [1.0, 2.0], "b": np.array([1, 2], dtype=np.int16)},
        2: {"c": [np.float32(0.5), [np.array([[1.0], [2.0]])]], "d": "x"},
    }
    converted = numpy_arrays.numpy_to_python(data)
    assert converted == {
        1: {"a": [1.0, 2.0], "b": [1, 2]},
        2: {"c": [0.5, [[[1.0], [2.0]]]], "d": "x"},
    }
    assert type(converted[1]["b"][0]) is int
    assert type(converted[2]["c"][0]) is float
    # the argument is not modified, unchanged parts are not copied
    assert isinstance(data[1]["b"], np.ndarray)
    assert converted[1]["a"] is data[1]["a"]
    unchanged = {1: {"a": [1.0, 2.0]}}
    assert numpy_arrays.numpy_to_python(unchanged) is unchanged


def test_numpy_to_python_without_numpy(monkeypatch):
    monkeypatch.delitem(sys.modules, "numpy")
    data = {1: {"a": [1.0]}}
    assert numpy_arrays.numpy_to_python(data) is data
