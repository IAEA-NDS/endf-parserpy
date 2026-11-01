############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/01
# Last modified:   2026/11/01
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Discarded EndfParserPy objects and their resources are freed.

The recipe parser backtracks by raising an internal exception. A raised
exception references the frames it passes through, and each frame its
calling frames, so an exception kept beyond the parse would keep the
callers' local variables alive, among them the EndfParserPy instance
whose recipes are parsed during its construction.

Each EndfParserPy object has its own logger, with the log level given
by its ``loglevel`` argument, which must not be kept by the logging
module after the object is discarded.
"""

import gc
import logging
from contextlib import contextmanager
import weakref
import pytest
from endf_parserpy import EndfParserPy
from endf_parserpy.recipe_parser import parse_recipe, RecipeSyntaxError
from endf_parserpy.recipe_parser.parser import _Backtrack


REC = "[MAT,3,MT/ a, b, c, d, e, f] CONT\n"
# recipes that require backtracking, with and without a syntax error
RECIPES = {
    "valid": "x := (a + b) / c\nif x > 0 and (y < 1 or z == 2):\n"
    + REC
    + "endif\n[MAT,3,MT/ a, b, c, d, e/f, NP/ E / xs] TAB1 (xstable)\n",
    "malformed": "x := (a + b\n",
    "malformed_record": "[MAT,3,MT/ a, b, c, d, e, f] FOO\n",
    "malformed_block": "for i=1 to N:\n" + REC,
}


class _Sentinel:
    pass


def _parse_with_local_object(recipe):
    sentinel = _Sentinel()
    try:
        parse_recipe(recipe)
    except RecipeSyntaxError:
        pass
    return weakref.ref(sentinel)


@pytest.mark.parametrize("name", sorted(RECIPES))
def test_parse_recipe_releases_caller_frames(name):
    ref = _parse_with_local_object(RECIPES[name])
    gc.collect()
    assert ref() is None


def test_discarded_parser_instances_are_freed():
    refs = []
    for _ in range(3):
        parser = EndfParserPy()
        refs.append(weakref.ref(parser))
        del parser
        gc.collect()
        assert all(ref() is None for ref in refs)


@pytest.mark.parametrize("name", sorted(k for k in RECIPES if "malformed" in k))
def test_syntax_error_not_chained_to_internal_exception(name):
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe(RECIPES[name])
    err = excinfo.value
    assert not isinstance(err.__context__, _Backtrack)
    assert not isinstance(err.__cause__, _Backtrack)
    assert err.__context__ is None and err.__cause__ is None


@contextmanager
def unconfigured_logging():
    # without handlers of the root logger (e.g. those pytest adds for
    # each test), as in a program that does not configure logging
    root = logging.getLogger()
    saved = root.handlers[:]
    for handler in saved:
        root.removeHandler(handler)
    try:
        yield root
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in saved:
            root.addHandler(handler)


def test_discarded_parser_loggers_are_freed():
    EndfParserPy()
    gc.collect()
    num_loggers = len(logging.Logger.manager.loggerDict)
    handler_refs = []
    with unconfigured_logging():
        for _ in range(3):
            parser = EndfParserPy()
            handler_refs.extend(weakref.ref(h) for h in parser.logger.handlers)
            del parser
            gc.collect()
    assert len(logging.Logger.manager.loggerDict) == num_loggers
    assert len(handler_refs) == 3
    assert all(ref() is None for ref in handler_refs)


def test_parser_loggers_with_own_levels(capsys):
    with unconfigured_logging():
        verbose = EndfParserPy(loglevel=logging.INFO)
        quiet = EndfParserPy(loglevel=logging.ERROR)
        assert verbose.logger.isEnabledFor(logging.INFO)
        assert not quiet.logger.isEnabledFor(logging.WARNING)
        verbose.logger.info("message one")
        quiet.logger.warning("message two")
        quiet.logger.error("message three")
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(f" - {verbose.name} - INFO - message one")
    assert lines[1].endswith(f" - {quiet.name} - ERROR - message three")


def test_parser_logger_uses_configured_root_handler(capsys):
    with unconfigured_logging() as root:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("root: %(levelname)s %(message)s"))
        root.addHandler(handler)
        parser = EndfParserPy(loglevel=logging.INFO)
        assert parser.logger.handlers == []
        parser.logger.info("message")
    assert capsys.readouterr().err == "root: INFO message\n"


def test_parser_logger_respects_logging_disable(capsys):
    with unconfigured_logging():
        parser = EndfParserPy(loglevel=logging.INFO)
        assert parser.logger.isEnabledFor(logging.INFO)
        logging.disable(logging.INFO)
        try:
            parser.logger.info("message")
        finally:
            logging.disable(logging.NOTSET)
    assert capsys.readouterr().err == ""
