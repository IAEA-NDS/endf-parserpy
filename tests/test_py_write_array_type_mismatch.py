"""EndfParserPy: writing arrays in the list form (lists, numpy arrays) in
dict mode raises an error that names the array_type option."""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.interpreter.custom_exceptions import UnavailableIndexError

np = pytest.importorskip("numpy")

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"
INCLUDE = [(1, 451), (3, 1)]
FIX = 'EndfParserPy(array_type="numpy")'


@pytest.mark.parametrize("form", ("list", "numpy"))
@pytest.mark.parametrize("check_arrays", (True, False))
def test_list_form_in_dict_mode(form, check_arrays):
    material = EndfParserCpp(array_type=form).parsefile(CU63, include=INCLUDE)
    with pytest.raises(UnavailableIndexError) as err:
        EndfParserPy(check_arrays=check_arrays).write(material)
    message = str(err.value)
    assert "the array HSUB is a `list`, but writing with array_type" in message
    assert FIX in message
    assert "index 1 does not exist" not in message


def test_numpy_array_in_dict_mode():
    material = EndfParserCpp(array_type="numpy").parsefile(CU63, include=INCLUDE)
    section = material[1][451]
    # the lists of text lines in the dict form, so that the first array in
    # the list form is the numpy array MFx of the directory
    for key, value in list(section.items()):
        if isinstance(value, list):
            section[key] = {i + 1: line for i, line in enumerate(value)}
    assert isinstance(section["MFx"], np.ndarray)
    with pytest.raises(UnavailableIndexError) as err:
        EndfParserPy().write(material)
    assert "the array MFx is a `numpy.ndarray`" in str(err.value)


@pytest.mark.parametrize("form", ("list", "numpy"))
def test_with_the_option_writes(form):
    material = EndfParserCpp(array_type=form).parsefile(CU63, include=INCLUDE)
    reference = EndfParserCpp().write(EndfParserCpp().parsefile(CU63, include=INCLUDE))
    assert EndfParserPy(array_type=form).write(material) == reference


def test_missing_index_of_a_dict_unchanged():
    material = EndfParserCpp().parsefile(CU63, include=INCLUDE)
    del material[1][451]["HSUB"][2]
    with pytest.raises(
        UnavailableIndexError, match="index 2 does not exist in array HSUB"
    ):
        EndfParserPy().write(material)
