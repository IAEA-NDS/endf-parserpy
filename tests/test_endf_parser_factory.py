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
