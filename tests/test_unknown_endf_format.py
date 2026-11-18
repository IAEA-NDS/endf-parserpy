"""An unknown endf_format raises the same TypeError in both parsers and in
the factory; the ImportError of EndfParserCpp is kept for a known flavor
whose module is missing."""

import importlib
import warnings

import pytest

from endf_parserpy import EndfParserCpp, EndfParserFactory, EndfParserPy
from endf_parserpy.cpp_parsers import endf_parser_cpp

MESSAGE = "There isn't any format specification associated with the name `bogus`"


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
def test_unknown_flavor_raises_type_error(cls):
    with pytest.raises(TypeError) as err:
        cls(endf_format="bogus")
    assert str(err.value) == MESSAGE


def test_unknown_flavor_does_not_import_the_cpp_module(monkeypatch):
    imported = []
    real_import = importlib.import_module

    def import_module(name, *args, **kwargs):
        imported.append(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(endf_parser_cpp.importlib, "import_module", import_module)
    with pytest.raises(TypeError, match="format specification"):
        EndfParserCpp(endf_format="bogus")
    assert imported == []


@pytest.mark.parametrize("select", ("fastest", "cpp", "python"))
def test_factory_unknown_flavor_without_warning(select):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(TypeError) as err:
            EndfParserFactory.create(endf_format="bogus", select=select)
    assert str(err.value) == MESSAGE


@pytest.mark.parametrize("flavor", ("endf6", "endf6-ext@0.19"))
def test_known_flavor_with_missing_module_raises_import_error(monkeypatch, flavor):
    def missing(entry_name):
        raise ImportError(f"no entry `{entry_name}`")

    monkeypatch.setattr(endf_parser_cpp, "_cpp_module_entry", missing)
    with pytest.raises(ImportError, match="Probably the module could not be compiled"):
        EndfParserCpp(endf_format=flavor)


def test_factory_fastest_falls_back_for_missing_module(monkeypatch):
    def missing(entry_name):
        raise ImportError(f"no entry `{entry_name}`")

    monkeypatch.setattr(endf_parser_cpp, "_cpp_module_entry", missing)
    with pytest.warns(UserWarning, match="C\\+\\+ parser not available"):
        parser = EndfParserFactory.create(endf_format="endf6", select="fastest")
    assert type(parser) is EndfParserPy
