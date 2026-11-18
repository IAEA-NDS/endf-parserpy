"""Writing arrays in the list form (lists, numpy arrays) in dict mode raises
a ValueError that names the array_type option, instead of the error of the
conversion of a list to a dict."""

import copy
import types
from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp
from endf_parserpy.cpp_parsers.endf_parser_cpp import _cpp_module_entry

np = pytest.importorskip("numpy")

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"
FIX = 'write_opts={"array_type": "numpy"}'


@pytest.fixture(scope="module")
def module():
    return _cpp_module_entry("endf6_ext")


@pytest.mark.parametrize("form", ("numpy", "list"))
@pytest.mark.parametrize("write_opts", ({}, {"array_type": "dict"}))
def test_module_write_of_list_form_in_dict_mode(module, form, write_opts):
    material = module.parse_endf_file(str(CU63), None, None, {"array_type": form})
    with pytest.raises(ValueError) as err:
        module.write_endf(material, None, None, write_opts)
    message = str(err.value)
    assert FIX in message
    assert "dictionary update sequence" not in message
    assert "an array of the data to write is a `list`" in message


def test_module_write_of_numpy_array_in_dict_mode(module):
    material = module.parse_endf_file(
        str(CU63), None, [(1, 451)], {"array_type": "numpy"}
    )
    section = next(s for s in material if isinstance(s, dict) and s["MF"] == 1)
    # the lists of text lines (HSUB, DESCRIPTION) in the dict form, so that
    # the first array in the list form is the numpy array MFx of the
    # directory
    for key, value in list(section.items()):
        if isinstance(value, list):
            section[key] = {i + 1: line for i, line in enumerate(value)}
    assert isinstance(section["MFx"], np.ndarray)
    with pytest.raises(ValueError) as err:
        module.write_endf(material, None, None, {})
    assert "an array of the data to write is a `numpy.ndarray`" in str(err.value)
    assert FIX in str(err.value)


@pytest.mark.parametrize("form", ("numpy", "list"))
def test_module_write_with_the_option_works(module, form):
    opts = {"array_type": form}
    material = module.parse_endf_file(str(CU63), None, None, opts)
    reference = module.write_endf(
        module.parse_endf_file(str(CU63), None, None, {}), None, None, {}
    )
    assert module.write_endf(material, None, None, opts) == reference


def test_parser_without_the_option(module):
    material = EndfParserCpp(array_type="numpy").parsefile(CU63)
    with pytest.raises(ValueError) as err:
        EndfParserCpp().write(material)
    assert FIX in str(err.value)
    # the parser with the option passes it to the module
    assert EndfParserCpp(array_type="numpy").write(material) == (
        EndfParserCpp().write(EndfParserCpp().parsefile(CU63))
    )


def test_other_mapping_is_still_converted(module):
    material = module.parse_endf_file(str(CU63), None, [(1, 451)], {})
    reference = module.write_endf(material, None, None, {})
    section = next(s for s in material if isinstance(s, dict) and s["MF"] == 1)
    section["DESCRIPTION"] = types.MappingProxyType(section["DESCRIPTION"])
    assert module.write_endf(material, None, None, {}) == reference
