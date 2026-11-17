############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/18
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
from glob import glob
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
    resolve_material_path,
    export_endf_file,
)
from endf_parserpy import EndfMaterialPath


COMMAND_NAME = "remove-material"


def add_subparser(subparsers):
    parser_remove = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_remove)
    parser_remove.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_remove.add_argument(
        "material",
        type=str,
        help="material selector (#k or MAT#k) of the material to remove",
    )
    parser_remove.add_argument(
        "file",
        nargs="+",
        type=str,
        help="tape file(s) the material is removed from",
    )


def _fail(message):
    """Print a clean one-line error and exit with status 1."""
    print(f"remove-material: {message}", file=sys.stderr)
    sys.exit(1)


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    create_backup = not args["no_backup"]
    selector = args["material"]
    files = []
    for fp in args["file"]:
        matches = glob(fp)
        if not matches:
            _fail(f"file {fp} does not exist")
        files.extend(matches)
    for file in files:
        try:
            endf_file = open_endf_file(file, parser)
        except Exception as exc:  # noqa: BLE001
            _fail(f"cannot read {file}: {exc}")
        resolved = resolve_material_path(endf_file, selector)
        if EndfMaterialPath(resolved).depth != "material":
            _fail(
                f"the selector {selector!r} must select a whole material "
                "(e.g. '#0' or '2925#0'), not a section"
            )
        try:
            material = endf_file[resolved]
            position, mat = material.position, material.mat
            del endf_file[resolved]
        except Exception as exc:  # noqa: BLE001
            _fail(f"cannot remove material {selector!r} from {file}: {exc}")
        export_endf_file(endf_file, file, create_backup)
        print(f"removed material #{position} (MAT {mat}) from {file}")
    sys.exit(0)
