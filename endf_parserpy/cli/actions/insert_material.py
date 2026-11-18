############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/18
# Last modified:   2026/11/18
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


COMMAND_NAME = "insert-material"


def add_subparser(subparsers):
    parser_insert = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_insert)
    parser_insert.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_insert.add_argument(
        "--source-path",
        dest="source_path",
        type=str,
        required=True,
        help="required: material selector (#k or MAT#k) of the material to "
        "insert from the source file",
    )
    parser_insert.add_argument(
        "--after",
        dest="after",
        type=str,
        default=None,
        help="material selector (#k or MAT#k) in the target after which the "
        "material is inserted; if omitted, the material is appended at the "
        "end of the tape",
    )
    parser_insert.add_argument(
        "sourcefile", type=str, help="file the material is taken from"
    )
    parser_insert.add_argument(
        "destfile",
        nargs="+",
        type=str,
        help="tape file(s) the material is inserted into",
    )


def _fail(message):
    """Print a clean one-line error and exit with status 1."""
    print(f"insert-material: {message}", file=sys.stderr)
    sys.exit(1)


def _material_view(endf_file, spec, role):
    """Resolve a material selector to a :class:`MaterialView`, or exit.

    ``spec`` must address a whole material (a bare selector, no MF/MT);
    a section-depth path is rejected, since ``insert`` operates on whole
    materials only.
    """
    resolved = resolve_material_path(endf_file, spec)
    if EndfMaterialPath(resolved).depth != "material":
        _fail(
            f"the {role} path {spec!r} must select a whole material "
            "(e.g. '#0' or '2925#0'), not a section"
        )
    try:
        return endf_file[resolved]
    except Exception as exc:  # noqa: BLE001
        _fail(f"cannot select the {role} material {spec!r}: {exc}")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    create_backup = not args["no_backup"]
    destfiles = []
    for fp in args["destfile"]:
        matches = glob(fp)
        if not matches:
            _fail(f"file {fp} does not exist")
        destfiles.extend(matches)
    retcode = _insert_material(
        parser,
        args["source_path"],
        args["after"],
        args["sourcefile"],
        destfiles,
        create_backup,
    )
    sys.exit(retcode)


def _insert_material(
    parser, source_spec, after_spec, sourcefile, destfiles, create_backup
):
    try:
        source = open_endf_file(sourcefile, parser)
    except Exception as exc:  # noqa: BLE001
        _fail(f"cannot read source file {sourcefile}: {exc}")
    source_material = _material_view(source, source_spec, "source")
    # to_tape_dict() keeps untouched sections as their raw on-disk lines,
    # so the inserted material is carried over verbatim; append_material()
    # ignores the MF=0 tape-head entry it also contains.
    material_dict = source_material.to_tape_dict()
    mat = source_material.mat
    za = source_material.za
    awr = source_material.awr
    for outfile in destfiles:
        try:
            dest = open_endf_file(outfile, parser)
        except Exception as exc:  # noqa: BLE001
            _fail(f"cannot read target file {outfile}: {exc}")
        after_pos = None
        if after_spec is not None:
            after_pos = _material_view(dest, after_spec, "target").position
        try:
            dest.append_material(material_dict, mat=mat, za=za, awr=awr)
        except Exception as exc:  # noqa: BLE001
            _fail(f"cannot insert the material into {outfile}: {exc}")
        if after_pos is not None:
            # append_material() put the new material last; move it so it
            # sits right after the anchor material
            new_index = len(dest) - 1
            order = (
                list(range(after_pos + 1))
                + [new_index]
                + list(range(after_pos + 1, new_index))
            )
            dest.reorder(order)
        export_endf_file(dest, outfile, create_backup)
    return 0
