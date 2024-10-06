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
    determine_include,
)
from endf_parserpy import EndfPath


COMMAND_NAME = "explain"


def add_subparser(subparsers):
    parser_explain = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_explain)
    parser_explain.add_argument(
        "endfpath", type=str, help="EndfPath to the variable that should be explained"
    )
    parser_explain.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args, allow_cpp=False)
    _explain_endf_variable(parser, args["endfpath"], args["file"])


def _explain_endf_variable(parser, endfpath, file):
    endfpath = EndfPath(endfpath)
    include = determine_include(endfpath)
    parser.parsefile(file, include=include)
    parser.explain(endfpath)
