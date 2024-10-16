############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2024/10/16
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.utils.matching import (
    eval_tree_print,
    expr_parser,
)
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
)
from glob import glob
import sys


COMMAND_NAME = "match"


def add_subparser(subparsers):
    parser_search = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_search)
    parser_search.add_argument("files", nargs="+", help="files to match")
    parser_search.add_argument("--query", "-q", type=str, help="search expression")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    files = []
    expr = args["query"]
    tree = expr_parser.parse(expr)
    for fp in args["files"]:
        files.extend(glob(fp))
    retcode = _match_endf_files(parser, files, tree)
    sys.exit(retcode)


def _match_endf_files(parser, files, tree):
    any_failed = False
    file_status_list = []
    for file in files:
        file_failed = False
        try:
            endf_dict = parser.parsefile(file)
        except Exception as exc:
            file_failed = True
            any_failed = True
            print(f"parsing failed: {file}")

        if file_failed:
            continue

        opts = {"filename": file, "print": "match"}
        retval = eval_tree_print(tree, endf_dict, opts)

    retcode = 1 if any_failed else 0
    return retcode
