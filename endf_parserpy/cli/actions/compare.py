############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2024/10/06
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
)
import sys
from endf_parserpy import compare_objects


COMMAND_NAME = "compare"


def add_subparser(subparsers):
    parser_compare = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_compare)
    parser_compare.add_argument(
        "--atol", type=float, default=1e-8, help="absolute tolerance"
    )
    parser_compare.add_argument(
        "--rtol", type=float, default=1e-6, help="relative tolerance"
    )
    parser_compare.add_argument("files", nargs=2, help="files for comparison")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    files = args["files"]
    atol = args["atol"]
    rtol = args["rtol"]
    retcode = _compare_endf_files(parser, files, atol=atol, rtol=rtol)
    sys.exit(retcode)


def _compare_endf_files(parser, files, atol, rtol):
    if len(files) != 2:
        print("Expecting exactly two files for the comparison", file=sys.stderr)
        sys.exit(1)
    endf_dict1 = parser.parsefile(files[0])
    endf_dict2 = parser.parsefile(files[1])
    is_equal = compare_objects(
        endf_dict1, endf_dict2, atol=atol, rtol=rtol, fail_on_diff=False
    )
    retcode = 0 if is_equal else 1
    return retcode
