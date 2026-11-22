"""The start of ``endf-cli`` and of the package.

``endf-cli`` imports and registers only the subcommand on the command
line, and all of them for the help text and for a missing or unknown
subcommand; the output of the program is the same either way. Neither
``import endf_parserpy`` nor a subcommand reading a small file in the
default dictionary mode imports numpy.
"""

import contextlib
import importlib
import io
import os
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
