############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/17
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file_or_exit,
    format_material_table,
)


COMMAND_NAME = "list-materials"


def add_subparser(subparsers):
    parser_list = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_list)
    parser_list.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    endf_file = open_endf_file_or_exit(COMMAND_NAME, args["file"], parser)
    count = len(endf_file)
    label = "material" if count == 1 else "materials"
    print(f"{args['file']}: {count} {label}")
    print(format_material_table(endf_file))
    sys.exit(0)
