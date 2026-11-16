import sys
import warnings
import pytest
from endf_parserpy import (
    EndfParserFactory,
    EndfParserPy,
    EndfParserCpp,
    EndfParserBase,
)


def test_python_parser_selection():
    parser = EndfParserFactory.create(select="python")
    assert type(parser) == EndfParserPy


def test_cpp_parser_selection():
    parser = EndfParserFactory.create(select="cpp")
    assert type(parser) == EndfParserCpp


def test_fastest_parser_selection():
    parser = EndfParserFactory.create(select="fastest")
    assert isinstance(parser, EndfParserBase)
    assert type(parser) == EndfParserCpp
    parser = EndfParserFactory.create(select="fastest", loglevel=20, warn_slow=False)
    assert isinstance(parser, EndfParserBase)
    assert type(parser) == EndfParserPy


def test_issuing_slow_warning():
    with pytest.warns(UserWarning, match="slow"):
        parser = EndfParserFactory.create(select="fastest", fuzzy_matching=True)
    with pytest.warns(UserWarning, match="slow"):
        parser = EndfParserFactory.create(select="fastest", loglevel=20)


def test_enforced_compatibility():
    with pytest.raises(ValueError, match="compat"):
        parser = EndfParserFactory.create(
            select="fastest", require_compat=True, loglevel=20
        )


@pytest.mark.parametrize("select", ["fastest", "cpp", "python"])
def test_numpy_array_type_without_numpy(monkeypatch, select):
    # a None entry in sys.modules makes `import numpy` fail
    monkeypatch.setitem(sys.modules, "numpy", None)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ImportError, match="requires the numpy package"):
            EndfParserFactory.create(select=select, array_type="numpy")


def test_unknown_endf_format_with_fastest():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(TypeError, match="format specification"):
            EndfParserFactory.create(select="fastest", endf_format="no-such-flavor")
