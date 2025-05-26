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
    create_backup_file,
)
from endf_parserpy import update_directory


COMMAND_NAME = "update-directory"


def add_subparser(subparsers):
    parser_update_dir = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_update_dir)
    parser_update_dir.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_update_dir.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    create_backup = not args["no_backup"]
    _update_mf1mt451_directory(parser, args["file"], create_backup)
    sys.exit(0)


def _update_mf1mt451_directory(parser, file, create_backup):
    endf_dict = parser.parsefile(file, include=[(1, 451)])
    update_directory(endf_dict, parser, read_opts=parser.read_opts)
    if create_backup:
        create_backup_file(file)
    parser.writefile(file, endf_dict, overwrite=(not create_backup))
