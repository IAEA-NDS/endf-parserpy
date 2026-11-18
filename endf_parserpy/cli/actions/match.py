############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.matching import (
    eval_tree_print,
    expr_parser,
)
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
    parsed_material_dict,
)
from glob import glob
import re
import sys


COMMAND_NAME = "match"


# exit status for an invalid query, as for a file that cannot be parsed
# (grep exits with 2 for an error, 1 if nothing matched)
EXIT_ERROR = 2

# a path without the leading slash, e.g. 3/1/ZA, at the start of the query
# or after an operator or bracket
_PATH_WITHOUT_SLASH = re.compile(r"(?:^|[\s(!&|<>=])[A-Za-z0-9_*]+/")


def add_subparser(subparsers):
    parser_search = subparsers.add_parser(
        COMMAND_NAME,
        epilog="exit status: 0 if at least one material matched, 1 if none "
        "did, 2 if the query is invalid or a file or material could not "
        "be parsed",
    )
    add_common_cmd_parser_args(parser_search)
    parser_search.add_argument("files", nargs="+", help="files to match")
    parser_search.add_argument(
        "--query",
        "-q",
        type=str,
        help="search expression, e.g. '/3/1/ZA >= 26056'; the EndfPaths in "
        "it start with /",
    )


def _fail(message):
    """Print a clean error and exit with status 2."""
    print(f"match: {message}", file=sys.stderr)
    sys.exit(EXIT_ERROR)


def _query_error(expr, exc):
    """The message for a query that the expression parser rejects."""
    column = getattr(exc, "column", None)
    token = getattr(exc, "token", None)
    char = getattr(exc, "char", None)
    if token is not None and getattr(token, "type", None) == "$END":
        what = "unexpected end of the query"
        column = len(expr.rstrip()) + 1
    elif token is not None:
        what = f"unexpected {str(token)!r} at column {column}"
    elif char is not None:
        what = f"unexpected character {char!r} at column {column}"
    else:
        what = str(exc).strip().splitlines()[0]
    lines = [f"invalid query {expr!r}: {what}"]
    if isinstance(column, int) and column > 0 and "\n" not in expr:
        lines.append(f"  {expr}")
        lines.append("  " + " " * (column - 1) + "^")
    if _PATH_WITHOUT_SLASH.search(expr) or (
        token is not None and getattr(token, "type", None) == "PATH_ELEMENT"
    ):
        lines.append(
            "the EndfPaths in a query must start with /, e.g. /3/1/ZA "
            "instead of 3/1/ZA"
        )
    return "\n".join(lines)


def _parse_query(expr):
    """The parse tree of the query ``expr``, or exit with status 2."""
    if expr is None:
        _fail("no query given; use --query, e.g. --query '/3/1/ZA >= 26056'")
    try:
        return expr_parser.parse(expr)
    except ImportError as exc:
        _fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        # the errors of the lark parser (lark.exceptions.LarkError)
        _fail(_query_error(expr, exc))


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    expr = args["query"]
    tree = _parse_query(expr)
    parser = get_endf_parser(args)
    files = []
    for fp in args["files"]:
        matches = glob(fp)
        # keep a non-matching pattern or a missing literal path so that it
        # is reported as a parse failure rather than silently dropped
        files.extend(matches if matches else [fp])
    retcode = _match_endf_files(parser, files, tree)
    sys.exit(retcode)


def _match_endf_files(parser, files, tree):
    any_failed = False
    any_match = False
    for file in files:
        try:
            endf_file = open_endf_file(file, parser, on_error="raise")
        except Exception:  # noqa: BLE001
            any_failed = True
            print(f"parsing failed: {file}", file=sys.stderr)
            continue
        multi = len(endf_file) > 1
        for material in endf_file:
            label = file
            if multi:
                label = f"{file} (material #{material.position}, MAT {material.mat})"
            try:
                endf_dict = parsed_material_dict(material)
            except Exception:  # noqa: BLE001
                any_failed = True
                print(f"parsing failed: {label}", file=sys.stderr)
                continue
            opts = {"filename": label, "print": "match"}
            if eval_tree_print(tree, endf_dict, opts):
                any_match = True

    # grep-like exit status: 2 if a file or material could not be parsed,
    # otherwise 0 when at least one material matched and 1 when none did
    # (2 also for an invalid query, see _parse_query)
    if any_failed:
        return EXIT_ERROR
    return 0 if any_match else 1
