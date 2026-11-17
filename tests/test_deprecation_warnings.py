############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The deprecation warnings of the package respect the warning filters.

The package used to call ``warnings.simplefilter("always",
DeprecationWarning)`` at import, which put a filter in front of those of
the user, so that neither ``-W ignore`` nor ``warnings.filterwarnings``
could silence a deprecation warning. The package no longer changes the
filters; its deprecation warnings are attributed to the code that calls
into the package (endf_parserpy.utils.deprecation), so that Python's
default filters show them when that code is ``__main__`` and the user's
filters decide otherwise.
"""

import importlib
import os
import subprocess
import sys
import textwrap
import warnings

import pytest

import endf_parserpy
import endf_parserpy.cpp_parsers as cpp_parsers
from endf_parserpy import EndfParserFactory, EndfParserPy
from endf_parserpy.interpreter.endf_parser import BasicEndfParser, EndfParser
from endf_parserpy.interpreter.endf_recipe_utils import get_recipe_parser

# the directory that contains the package under test
PACKAGE_PARENT = os.path.dirname(
    os.path.dirname(os.path.abspath(endf_parserpy.__file__))
)

CACHE_MESSAGE = "the arguments `cache_dir` and `print_cache_info` are deprecated"
SHIM_MESSAGE = "The module endf_parserpy.cpp_parsers.endf6 is deprecated"


def _cpp_available():
    try:
        importlib.import_module("endf_parserpy.cpp_parsers._flavors")
    except ImportError:
        return False
    return True


needs_cpp = pytest.mark.skipif(not _cpp_available(), reason="C++ module is not built")


def _forget_shim(monkeypatch, name):
    monkeypatch.delitem(sys.modules, "endf_parserpy.cpp_parsers." + name, False)
    monkeypatch.delattr(cpp_parsers, name, False)


# --- in this process ---------------------------------------------------


def test_package_does_not_change_the_filters():
    # importing every module of the package that issues deprecation
    # warnings leaves the filters as they are
    code = textwrap.dedent(
        """
        import warnings
        try:
            import numpy  # adds filters of its own at import
        except ImportError:
            pass
        before = list(warnings.filters)
        import endf_parserpy
        import endf_parserpy.interpreter.endf_parser
        import endf_parserpy.interpreter.endf_recipe_utils
        import endf_parserpy.cpp_parsers._historical_modules
        import endf_parserpy.utils.deprecation
        print(warnings.filters == before)
        """
    )
    assert _run(code).stdout.strip() == "True"


@pytest.mark.parametrize(
    "construct",
    [
        lambda: EndfParserPy(cache_dir="unused"),
        lambda: EndfParserPy(print_cache_info=True),
        lambda: EndfParserFactory.create(select="python", print_cache_info=True),
        lambda: get_recipe_parser("unused"),
        lambda: EndfParser(),
        lambda: BasicEndfParser(),
    ],
    ids=[
        "cache_dir",
        "print_cache_info",
        "factory",
        "recipe_utils",
        "EndfParser",
        "Basic",
    ],
)
def test_warning_names_calling_code_and_can_be_ignored(construct):
    with pytest.warns(DeprecationWarning) as record:
        construct()
    assert [w.filename for w in record] == [__file__]
    # a filter of the user silences it
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        construct()
    assert [w for w in record if issubclass(w.category, DeprecationWarning)] == []


@needs_cpp
def test_shim_warning_can_be_ignored(monkeypatch):
    _forget_shim(monkeypatch, "endf6")
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        warnings.filterwarnings(
            "ignore", message="The module endf_parserpy.cpp_parsers"
        )
        importlib.import_module("endf_parserpy.cpp_parsers.endf6")
    assert record == []


# --- default filters, in a fresh process -------------------------------


def _run(code, *options, env_extra=None):
    env = dict(os.environ)
    env.pop("PYTHONWARNINGS", None)
    env["PYTHONPATH"] = os.pathsep.join(
        [PACKAGE_PARENT] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    if env_extra:
        env.update(env_extra)
    res = subprocess.run(
        [sys.executable, *options, "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return res


CACHE_CODE = (
    "from endf_parserpy import EndfParserPy\nEndfParserPy(cache_dir='unused')\n"
)
SHIM_CODE = "import endf_parserpy.cpp_parsers.endf6\n"


@pytest.mark.parametrize(
    "code, message",
    [
        (CACHE_CODE, CACHE_MESSAGE),
        pytest.param(SHIM_CODE, SHIM_MESSAGE, marks=needs_cpp),
    ],
    ids=["cache_dir", "shim"],
)
def test_default_filters_show_warning_of_main(code, message):
    # called from __main__ (a script, python -c, an interactive session)
    res = _run(code)
    assert "DeprecationWarning: " + message in res.stderr
    assert res.stderr.startswith("<string>:")


@pytest.mark.parametrize(
    "code, message",
    [
        (CACHE_CODE, CACHE_MESSAGE),
        pytest.param(SHIM_CODE, SHIM_MESSAGE, marks=needs_cpp),
    ],
    ids=["cache_dir", "shim"],
)
def test_user_filters_silence_warning(code, message):
    # -W, PYTHONWARNINGS and a filter set by the script itself
    assert message not in _run(code, "-W", "ignore::DeprecationWarning").stderr
    res = _run(code, env_extra={"PYTHONWARNINGS": "ignore::DeprecationWarning"})
    assert message not in res.stderr
    code2 = "import warnings\nwarnings.simplefilter('ignore')\n" + code
    assert message not in _run(code2).stderr
    # and -W error turns it into an error
    env = dict(os.environ, PYTHONPATH=PACKAGE_PARENT)
    env.pop("PYTHONWARNINGS", None)
    res = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0 and message in res.stderr


@pytest.mark.parametrize(
    "code, message",
    [
        (CACHE_CODE, CACHE_MESSAGE),
        pytest.param(SHIM_CODE, SHIM_MESSAGE, marks=needs_cpp),
    ],
    ids=["cache_dir", "shim"],
)
def test_default_filters_hide_warning_of_other_module(code, message, tmp_path):
    # called from a module other than __main__ (e.g. a library that uses
    # the package): hidden by Python's default filters, as other
    # DeprecationWarnings, and shown with -W default
    (tmp_path / "uses_package.py").write_text(code)
    main = "import uses_package\n"
    env = {"PYTHONPATH": os.pathsep.join([PACKAGE_PARENT, str(tmp_path)])}
    assert message not in _run(main, env_extra=env).stderr
    res = _run(main, "-W", "default::DeprecationWarning", env_extra=env)
    assert message in res.stderr
    assert "uses_package.py:" in res.stderr
