############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/03/24
# Last modified:   2025/05/10
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
import json
from pathlib import Path
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
)
from endf_parserpy.utils.user_tools import sanitize_fieldname_types


COMMAND_NAME = "convert"


def add_subparser(subparsers):
    parser_convert = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_convert)
    formats = ["endf", "json"]
    parser_convert.add_argument(
        "sourcefile", type=str, help="file that should be converted"
    )
    parser_convert.add_argument(
        "destfile", type=str, help="new file with the desired format"
    )
    parser_convert.add_argument(
        "--indent", type=int, nargs="?", help="Indent used for JSON output formatting"
    )
    parser_convert.add_argument(
        "--to", type=str, choices=formats, required=True, help="Destination file format"
    )


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    sourcefile = Path(args["sourcefile"])
    destfile = Path(args["destfile"])
    dest_format = args["to"]
    json_dump_kwargs = {
        "indent": args["indent"],
    }
    if not sourcefile.is_file():
        print(f"File {sourcefile} does not exist")
        sys.exit(1)
    if destfile.is_file():
        print(f"The destination file {destfile} already exists. Aborting.")
        sys.exit(1)
    if dest_format == "endf":
        retcode = _convert_to_endf(parser, sourcefile, destfile)
    elif dest_format == "json":
        retcode = _convert_to_json(parser, sourcefile, destfile, json_dump_kwargs)
    sys.exit(retcode)


def _convert_to_json(parser, sourcefile, destfile, json_dump_kwargs):
    destfile = Path(destfile)
    endf_dict = parser.parsefile(sourcefile)
    with open(destfile, "w") as f:
        json.dump(endf_dict, f, **json_dump_kwargs)
    return 0


def _convert_to_endf(parser, sourcefile, destfile):
    with open(sourcefile, "r") as f:
        endf_dict = json.load(f)
    sanitize_fieldname_types(endf_dict)
    parser.writefile(destfile, endf_dict)
    return 0
