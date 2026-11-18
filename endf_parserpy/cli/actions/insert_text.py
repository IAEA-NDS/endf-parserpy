############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
from ..cmd_utils import (
    PARSE_ERRORS,
    add_common_cmd_parser_args,
    fail_on_parse_error,
    located_parse_error,
    get_endf_parser,
    open_endf_file_or_exit,
    export_endf_file,
    format_material_table,
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
    parser_instext.add_argument(
        "-m",
        "--material",
        type=str,
        default=None,
        help="material selector (#k, MAT or MAT#k) identifying which "
        "material to modify on a multi-material tape",
    )
    parser_instext.add_argument("file", type=str, help="ENDF file")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    create_backup = not args["no_backup"]
    _insert_mf1mt451_description(
        parser, args["line"], args["material"], args["file"], create_backup
    )
    sys.exit(0)


def _select_material(endf_file, selector):
    """Return the MaterialView selected by ``selector``.

    With no selector a single-material file resolves to its only
    material; a multi-material file is rejected with a listing.
    """
    if selector is None:
        if len(endf_file) == 1:
            return endf_file[0]
        msg = (
            f"the file holds {len(endf_file)} materials; choose one with "
            "-m/--material (#k for tape position k, MAT or MAT#k):\n"
            + format_material_table(endf_file)
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
    try:
        return endf_file[selector]
    except Exception as exc:  # noqa: BLE001
        print(f"cannot select material {selector!r}: {exc}", file=sys.stderr)
        sys.exit(1)


def _insert_mf1mt451_description(parser, line_no, selector, file, create_backup):
    endf_file = open_endf_file_or_exit(COMMAND_NAME, file, parser)
    material = _select_material(endf_file, selector)
    text = sys.stdin.read()
    # insert_description() and update_directory() need a complete
    # single-material tape dict with MF1/MT451 as a parsed mapping; the
    # other sections may stay as their raw on-disk lines.
    try:
        mat_dict = material.to_tape_dict()
        mat_dict[1][451] = material[1, 451].detach()
        insert_description(mat_dict, text, after_line=line_no)
        update_directory(mat_dict, parser)
    except PARSE_ERRORS as exc:
        exc = located_parse_error(exc, endf_file, [material.position])
        fail_on_parse_error(COMMAND_NAME, file, exc)
    endf_file[f"#{material.position}/1/451"] = mat_dict[1][451]
    export_endf_file(endf_file, file, create_backup)
