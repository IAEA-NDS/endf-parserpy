"""EndfParserFactory.create takes every argument of both parser classes,
each with the default of the class that is selected."""

import inspect
import warnings

import pytest

from endf_parserpy import EndfParserCpp, EndfParserFactory, EndfParserPy
from endf_parserpy.cpp_parsers import endf_parser_cpp
from endf_parserpy.endf_recipes import get_tape_structure

FACTORY_ONLY = {"select", "warn_slow", "require_compat"}


def _params(func):
    return {
        name: p
        for name, p in inspect.signature(func).parameters.items()
        if name != "self"
    }


@pytest.mark.parametrize("cls", (EndfParserPy, EndfParserCpp), ids=lambda c: c.__name__)
def test_create_has_every_argument_of_the_classes(cls):
    create = _params(EndfParserFactory.create)
    missing = set(_params(cls.__init__)) - set(create)
    assert not missing


def test_create_has_no_argument_of_neither_class():
    create = set(_params(EndfParserFactory.create)) - FACTORY_ONLY
    classes = set(_params(EndfParserPy.__init__)) | set(_params(EndfParserCpp.__init__))
    assert create <= classes


@pytest.mark.parametrize(
    "select,cls",
    (("python", EndfParserPy), ("cpp", EndfParserCpp), ("fastest", EndfParserCpp)),
)
def test_defaults_are_those_of_the_selected_class(select, cls):
    # all arguments of the constructor, with their defaults, as recorded
    # for pickling (see _record_init_kwargs)
    parser = EndfParserFactory.create(select=select)
    assert type(parser) is cls
    assert parser._init_kwargs == cls()._init_kwargs


def test_fastest_falls_back_with_the_python_defaults(monkeypatch):
    def missing(entry_name):
        raise ImportError(f"no entry `{entry_name}`")

    monkeypatch.setattr(endf_parser_cpp, "_cpp_module_entry", missing)
    with pytest.warns(UserWarning, match="C\\+\\+ parser not available"):
        parser = EndfParserFactory.create(select="fastest")
    assert type(parser) is EndfParserPy
    assert parser._init_kwargs == EndfParserPy()._init_kwargs
    assert parser.write_opts["check_arrays"] is True


@pytest.mark.parametrize("value", (True, False))
def test_check_arrays_given(value):
    parser = EndfParserFactory.create(select="python", check_arrays=value)
    assert parser.write_opts["check_arrays"] is value


def test_check_arrays_true_is_python_only():
    with pytest.raises(ValueError, match="check_arrays"):
        EndfParserFactory.create(select="cpp", check_arrays=True)
    with pytest.raises(ValueError, match="require_compat"):
        EndfParserFactory.create(check_arrays=True, require_compat=True)
    with pytest.warns(UserWarning, match="check_arrays=True forces"):
        parser = EndfParserFactory.create(select="fastest", check_arrays=True)
    assert type(parser) is EndfParserPy
    # the default and False are compatible with both parsers
    for value in (None, False):
        parser = EndfParserFactory.create(check_arrays=value, require_compat=True)
        assert type(parser) is EndfParserCpp
    parser = EndfParserFactory.create(select="cpp", check_arrays=False)
    assert parser._init_kwargs == EndfParserCpp()._init_kwargs


@pytest.mark.parametrize(
    "select,cls", (("python", EndfParserPy), ("cpp", EndfParserCpp))
)
@pytest.mark.parametrize("material_form", (None, "dict", "list"))
def test_material_form(select, cls, material_form):
    parser = EndfParserFactory.create(select=select, material_form=material_form)
    assert type(parser) is cls
    assert parser.material_form == material_form
    with pytest.raises(ValueError, match="material_form"):
        EndfParserFactory.create(select=select, material_form="tuple")


def test_tape_structure_is_python_only():
    ts = get_tape_structure("endf6")
    parser = EndfParserFactory.create(select="python", tape_structure=ts)
    assert type(parser) is EndfParserPy
    assert parser.tape_structure == ts
    with pytest.raises(ValueError, match="`tape_structure` expected to be None"):
        EndfParserFactory.create(select="cpp", tape_structure=ts)
    with pytest.raises(ValueError, match="require_compat"):
        EndfParserFactory.create(tape_structure=ts, require_compat=True)
    with pytest.warns(UserWarning, match="tape_structure=.* forces the selection"):
        parser = EndfParserFactory.create(select="fastest", tape_structure=ts)
    assert type(parser) is EndfParserPy
    assert parser.tape_structure == ts
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        parser = EndfParserFactory.create(tape_structure=ts, warn_slow=False)
    assert type(parser) is EndfParserPy
