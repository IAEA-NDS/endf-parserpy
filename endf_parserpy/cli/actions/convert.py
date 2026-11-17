############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/03/24
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2025-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
import json
from pathlib import Path
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
)
from endf_parserpy import parse_tape_file, write_tape_file
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
    materials = parse_tape_file(sourcefile, parser=parser, on_error="raise")
    # A single-material tape is written as a JSON object, a multi-material
    # tape as a JSON array of material objects (design decision D); the
    # json->endf direction tells the two apart by container type.
    # A material in the list form (e.g. of gendf) is a JSON array, so that
    # such a tape is always written as the array of its materials.
    if len(materials) == 1 and not isinstance(materials[0], list):
        payload = materials[0]
    else:
        payload = materials
    with open(destfile, "w") as f:
        json.dump(payload, f, **json_dump_kwargs)
    return 0


def _convert_to_endf(parser, sourcefile, destfile):
    with open(sourcefile, "r") as f:
        endf_data = json.load(f)
    # A JSON array is a multi-material tape, a JSON object a single
    # material; both are written through the multi-material tape writer.
    # A material of a tape is an object (the nested form) or an array of
    # its sections (the list form).
    materials = endf_data if isinstance(endf_data, list) else [endf_data]
    for material in materials:
        if isinstance(material, list):
            for section in material:
                if isinstance(section, dict):
                    sanitize_fieldname_types(section)
        else:
            sanitize_fieldname_types(material)
    write_tape_file(materials, destfile, parser=parser)
    return 0
