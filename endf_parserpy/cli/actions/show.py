############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2025/05/26
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    determine_include,
)
from endf_parserpy import EndfPath
from endf_parserpy.utils.user_tools import show_content


COMMAND_NAME = "show"


def add_subparser(subparsers):
    parser_show = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_show)
    parser_show.add_argument(
        "endfpath", type=str, help="EndfPath to section or value to display"
    )
    parser_show.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    _show_file_content(parser, args["endfpath"], args["file"])
    sys.exit(0)


def _show_file_content(parser, endfpath, file):
    endfpath = EndfPath(endfpath)
    include = determine_include(endfpath)
    endf_dict = parser.parsefile(file, include=include)
    cont = endfpath.get(endf_dict)
    show_content(cont)
