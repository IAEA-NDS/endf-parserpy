"""endf-cli match with an invalid query: a clean message and exit status 2
(grep convention), distinct from 1 for no match."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

CU63 = Path(__file__).resolve().parent / "testdata" / "n_2925_29-Cu-63.endf"
SLASH_HINT = "the EndfPaths in a query must start with /"


def run_cli(argv):
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "query,detail,hint",
    [
        ("3/1/ZA == 29063", "unexpected '/' at column 2", True),
        ("ZA == 29063", "unexpected 'ZA' at column 1", True),
        ("/3/1/ZA == 1 & 1/451/LRP == 1", "unexpected '/' at column 17", True),
        ("exists(3/1)", "unexpected '3' at column 8", True),
        ("/3/1/ZA ==", "unexpected end of the query", False),
        ("/3/1/ZA = 1", "unexpected character '=' at column 9", False),
        ("/3/1/ZA == 1 && /1/451/LRP == 1", "unexpected '&' at column 15", False),
        ("", "unexpected end of the query", False),
    ],
)
def test_invalid_query(query, detail, hint):
    result = run_cli(["match", "--query", query, str(CU63)])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert lines[0] == f"match: invalid query {query!r}: {detail}"
    assert (SLASH_HINT in result.stderr) == hint


def test_caret_under_the_error():
    result = run_cli(["match", "--query", "/3/1/ZA = 1", str(CU63)])
    lines = result.stderr.splitlines()
    assert lines[1] == "  /3/1/ZA = 1"
    assert lines[2] == "  " + " " * 8 + "^"


def test_missing_query():
    result = run_cli(["match", str(CU63)])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("match: no query given; use --query")


def test_valid_queries_keep_their_exit_codes():
    hit = run_cli(["match", "--query", "/3/1/ZA == 29063", str(CU63)])
    assert hit.returncode == 0
    assert hit.stdout.startswith("match: ")
    miss = run_cli(["match", "--query", "/3/1/ZA == 1", str(CU63)])
    assert miss.returncode == 1
    assert miss.stdout == "" and miss.stderr == ""


def test_help_gives_the_exit_codes():
    result = run_cli(["match", "--help"])
    assert result.returncode == 0
    text = " ".join(result.stdout.split())
    assert (
        "exit status: 0 if at least one material matched, 1 if none did, "
        "2 if the query is invalid or a file or material could not be parsed"
    ) in text
