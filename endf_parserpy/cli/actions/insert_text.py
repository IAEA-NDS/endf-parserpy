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
from endf_parserpy.utils.endf6_plumbing import insert_description


COMMAND_NAME = "insert-text"


def add_subparser(subparsers):
    parser_instext = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_instext)
    parser_instext.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_instext.add_argument(
        "-l", "--line", type=int, default=0, help="after which line to insert the text"
    )
    parser_instext.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    create_backup = not args["no_backup"]
    _insert_mf1mt451_description(parser, args["line"], args["file"], create_backup)
    sys.exit(0)


def _insert_mf1mt451_description(parser, line_no, file, create_backup):
    endf_dict = parser.parsefile(file, include=[(1, 451)])
    text = sys.stdin.read()
    insert_description(endf_dict, text, after_line=line_no)
    update_directory(endf_dict, parser)
    if create_backup:
        create_backup_file(file)
    parser.writefile(file, endf_dict, overwrite=(not create_backup))
