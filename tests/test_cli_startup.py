"""The start of ``endf-cli`` and of the package.

``endf-cli`` imports and registers only the subcommand on the command
line, and all of them for the help text and for a missing or unknown
subcommand; the output of the program is the same either way. Neither
``import endf_parserpy`` nor a subcommand reading a small file in the
default dictionary mode imports numpy, the Python parser, the recipe
parser, the recipes or the modules of the standard library in
``_NOT_AT_START``; they are imported when they are used.
"""

import contextlib
import importlib
import io
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import endf_parserpy
from endf_parserpy.cli import cmd


TESTDATA = Path(__file__).parent / "testdata"
SMALL = str(TESTDATA / "dec-094_Pu_244.endf")


def _run_python(code):
    env = dict(os.environ)
    pkg_root = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(
        [pkg_root] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )


def _modules_after(argv):
    """The modules loaded by a run of ``endf-cli argv``, and its exit code."""
    code = (
        "import sys\n"
        f"sys.argv = ['endf-cli'] + {argv!r}\n"
        "from endf_parserpy.cli.cmd import cli_interface\n"
        "try:\n"
        "    cli_interface()\n"
        "except SystemExit as exc:\n"
        "    code = exc.code\n"
        "sys.stderr.write('\\nMODULES ' + ' '.join(sorted(sys.modules)))\n"
        "sys.stderr.write('\\nEXIT ' + repr(code))\n"
    )
    result = _run_python(code)
    tail = result.stderr.rsplit("\nMODULES ", 1)
    assert len(tail) == 2, result.stderr
    modules, exit_code = tail[1].split("\nEXIT ")
    return set(modules.split()), exit_code


def test_import_does_not_import_numpy():
    result = _run_python(
        "import sys\n"
        "import endf_parserpy\n"
        "assert 'numpy' not in sys.modules, 'numpy imported'\n"
    )
    assert result.returncode == 0, result.stderr


def _action_modules(modules):
    return {m for m in modules if m.startswith("endf_parserpy.cli.actions.")}


@pytest.mark.parametrize(
    "argv",
    [["show", "1/451/ZA", SMALL], ["list-materials", SMALL]],
    ids=["show", "list-materials"],
)
def test_subcommand_imports_neither_numpy_nor_other_subcommands(argv):
    modules, exit_code = _modules_after(argv)
    assert exit_code == "0"
    assert "numpy" not in modules
    expected = {"endf_parserpy.cli.actions." + cmd.SUBCOMMANDS[argv[0]]}
    assert _action_modules(modules) == expected


def test_validate_imports_only_its_subcommand():
    # (validate parses with array_type="numpy" if numpy is installed)
    modules, exit_code = _modules_after(["validate", SMALL])
    assert exit_code == "0"
    assert _action_modules(modules) == {"endf_parserpy.cli.actions.validate"}


def test_help_registers_all_subcommands():
    modules, exit_code = _modules_after(["--help"])
    assert exit_code == "0"
    for name in cmd.SUBCOMMANDS.values():
        assert "endf_parserpy.cli.actions." + name in modules


def test_subcommand_table():
    # the table lists the modules in endf_parserpy.cli.actions, each
    # under the name of its subcommand
    actions_dir = Path(cmd.__file__).parent / "actions"
    names = {p.stem for p in actions_dir.glob("*.py") if p.stem != "__init__"}
    assert set(cmd.SUBCOMMANDS.values()) == names
    for command, name in cmd.SUBCOMMANDS.items():
        module = importlib.import_module("endf_parserpy.cli.actions." + name)
        assert module.COMMAND_NAME == command


def _parse(parser, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = ("args", vars(parser.parse_args(argv)))
        except SystemExit as exc:
            result = ("exit", exc.code)
    return result, out.getvalue(), err.getvalue()


_ARGVS = [
    [],
    ["--help"],
    ["-h"],
    ["-h", "show"],
    ["bogus"],
    ["shwo", SMALL],
    ["list_materials", SMALL],
    ["--bogus"],
    ["show"],
    ["show", "1/451", SMALL, "--bogus"],
    ["show", "1/451", SMALL],
    ["validate", "--no-such-option", SMALL],
    ["match", "--help", "extra"],
] + [[c, "--help"] for c in cmd.SUBCOMMANDS]


def _argv_id(argv):
    return " ".join("FILE" if a == SMALL else a for a in argv) or "(none)"


@pytest.mark.parametrize("argv", _ARGVS, ids=_argv_id)
def test_output_as_with_all_subcommands(argv, monkeypatch):
    # the help texts, usage and error messages, and the parsed arguments,
    # are those of the parser with all subcommands registered
    monkeypatch.setenv("COLUMNS", "80")
    full = cmd._make_parser(cmd._subcommand_modules([]))
    lazy = cmd._make_parser(cmd._subcommand_modules(argv))
    assert _parse(lazy, argv) == _parse(full, argv)


# modules of the standard library that the start does not need
_NOT_AT_START = (
    "numpy",
    "secrets",
    "tempfile",
    "logging",
    "fractions",
    "typing",
    "platform",
)

# the modules of the interpreter that the package uses without the
# Python parser
_INTERPRETER_HELPERS = {
    "endf_parserpy.interpreter",
    "endf_parserpy.interpreter.custom_exceptions",
    "endf_parserpy.interpreter.endf_utils",
    "endf_parserpy.interpreter.fortran_utils",
    "endf_parserpy.interpreter.helpers",
}


def _modules_after_code(code):
    """The modules loaded by ``code`` in a fresh process."""
    result = _run_python(
        "import sys\n" + code + "\nprint('MODULES ' + ' '.join(sorted(sys.modules)))\n"
    )
    assert result.returncode == 0, result.stderr
    return set(result.stdout.rsplit("MODULES ", 1)[1].split())


def _recipe_modules(modules):
    """The modules of endf_recipes other than the catalogue."""
    return {
        m
        for m in modules
        if m.startswith("endf_parserpy.endf_recipes.")
        and m != "endf_parserpy.endf_recipes.catalogue"
    }


def _check_start(modules):
    interpreter = {m for m in modules if m.startswith("endf_parserpy.interpreter")}
    assert interpreter <= _INTERPRETER_HELPERS
    assert "endf_parserpy.recipe_parser.parser" not in modules
    assert [m for m in _NOT_AT_START if m in modules] == []


def test_import_loads_neither_parser_nor_recipes():
    modules = _modules_after_code("import endf_parserpy")
    _check_start(modules)
    assert _recipe_modules(modules) == set()


@pytest.mark.parametrize(
    "argv",
    [["show", "1/451/ZA", SMALL], ["list-materials", SMALL]],
    ids=["show", "list-materials"],
)
def test_subcommand_loads_only_the_tape_structure_of_its_flavor(argv):
    modules, exit_code = _modules_after(argv)
    assert exit_code == "0"
    _check_start(modules)
    # of the default flavor endf6-ext, the tape structure, not the recipes
    assert _recipe_modules(modules) == {
        "endf_parserpy.endf_recipes.tape_structures",
        "endf_parserpy.endf_recipes.tape_structures.endf6_ext",
    }


def test_parse_with_cpp_parser_loads_no_recipes():
    pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    modules = _modules_after_code(
        "from endf_parserpy import EndfParserCpp\n"
        f"EndfParserCpp(endf_format='jendl').parsefile({SMALL!r})"
    )
    _check_start(modules)
    assert _recipe_modules(modules) == {
        "endf_parserpy.endf_recipes.tape_structures",
        "endf_parserpy.endf_recipes.tape_structures.jendl",
    }


def test_python_parser_and_recipes_imported_when_used():
    modules = _modules_after_code(
        "import endf_parserpy\n"
        "from endf_parserpy import EndfParserFactory\n"
        "from endf_parserpy.endf_recipes import get_recipe_dict\n"
        "assert get_recipe_dict('pendf')[1][451]\n"
        "parser = EndfParserFactory.create(select='python')\n"
        "assert isinstance(parser, endf_parserpy.EndfParserPy)\n"
        f"assert parser.parsefile({SMALL!r})[1][451]['MAT'] == 3564\n"
    )
    assert "endf_parserpy.interpreter.endf_parser" in modules
    assert "endf_parserpy.recipe_parser.parser" in modules
    folders = {m.split(".")[2] for m in _recipe_modules(modules) if m.count(".") == 2}
    # pendf derives from endf6, and the parser uses endf6-ext, which
    # takes a recipe from jendl; the other flavors are not imported
    assert {"pendf", "endf6", "endf6_ext", "jendl"} <= folders
    assert {"errorr", "gendf", "test"} & folders == set()


def test_public_names_resolve_on_access():
    # in a fresh process, in which the Python parser is not imported yet
    code = (
        "import endf_parserpy\n"
        "names = dir(endf_parserpy)\n"
        "assert all(n in names for n in endf_parserpy.__all__), names\n"
        "assert 'endf_parserpy.interpreter.endf_parser' not in sys.modules\n"
        "ns = {}\n"
        "exec('from endf_parserpy import *', ns)\n"
        "assert sorted(n for n in ns if n != '__builtins__')"
        " == sorted(endf_parserpy.__all__)\n"
        "from endf_parserpy.interpreter import endf_parser\n"
        "for name in ('EndfParserPy', 'EndfParser', 'BasicEndfParser'):\n"
        "    assert ns[name] is getattr(endf_parser, name)\n"
        "    assert getattr(endf_parserpy.interpreter, name) is ns[name]\n"
        "from endf_parserpy import recipe_parser\n"
        "assert recipe_parser.parse_recipe is recipe_parser.parser.parse_recipe\n"
        "assert 'parse_recipe' in dir(recipe_parser)\n"
        "assert 'endf6' in dir(endf_parserpy.endf_recipes)\n"
        "assert endf_parserpy.endf_recipes.endf6.endf_recipe_dictionary\n"
    )
    _modules_after_code(code)
    with pytest.raises(AttributeError, match="no attribute 'NoSuchName'"):
        endf_parserpy.NoSuchName


def test_parsers_pickled_without_the_python_parser_imported():
    # pickled in this process, unpickled in a fresh one
    parsers = [endf_parserpy.EndfParserPy(endf_format="jendl")]
    try:
        parsers.append(endf_parserpy.EndfParserCpp(endf_format="jendl"))
    except ImportError:
        pass
    data = pickle.dumps(parsers)
    code = (
        "import pickle\n"
        "import endf_parserpy\n"
        "assert 'endf_parserpy.interpreter.endf_parser' not in sys.modules\n"
        f"parsers = pickle.loads({data!r})\n"
        "assert type(parsers[0]) is endf_parserpy.EndfParserPy\n"
        "assert all(isinstance(p, endf_parserpy.EndfParserBase) for p in parsers)\n"
        "assert all(p._init_kwargs['endf_format'] == 'jendl' for p in parsers)\n"
        f"assert parsers[-1].parsefile({SMALL!r})[1][451]['MAT'] == 3564\n"
    )
    _modules_after_code(code)


def test_plain_value_of_a_fraction():
    from fractions import Fraction
    from endf_parserpy.utils.tolerated_mismatches import plain_value

    assert plain_value(Fraction(6, 3)) == 2
    assert type(plain_value(Fraction(6, 3))) is int
    assert plain_value(Fraction(1, 4)) == 0.25
    assert plain_value("x") == "x"
