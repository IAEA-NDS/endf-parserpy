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
from glob import glob
import sys


COMMAND_NAME = "validate"


def add_subparser(subparsers):
    parser_validate = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_validate)
    parser_validate.add_argument("files", nargs="+", help="files for validation")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    files = []
    for fp in args["files"]:
        files.extend(glob(fp))
    retcode = _validate_endf_files(parser, files)
    sys.exit(retcode)


def _validate_endf_files(parser, files):
    any_failed = False
    file_status_list = []
    for file in files:
        try:
            parser.parsefile(file)
            file_status_list.append((file, "ok"))
        except Exception as exc:
            any_failed = True
            file_status_list.append((file, "failed"))
            print("\n" + "=" * 80)
            print(f"  Validation of {file} failed for the following reason:\n")
            print(str(exc))

    print("\n========== VALIDATION SUMMARY ==========")
    for file_status in file_status_list:
        print(f"{file_status[1]} - {file_status[0]}")
    retcode = 1 if any_failed else 0
    return retcode
