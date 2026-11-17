############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import sys
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
    resolve_material_path,
    section_names,
    selector_of,
)
from endf_parserpy import EndfMaterialPath
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
    endf_file = open_endf_file(file, parser)
    resolved = resolve_material_path(endf_file, endfpath)
    mp = EndfMaterialPath(resolved)
    if mp.depth == "mf":
        # an MF-depth path does not address data; list the MT sections
        # present in that MF (EndfFile itself rejects MF-level access),
        # with MT#k for an MT that occurs several times
        material = endf_file[selector_of(resolved)]
        keys = [key for key in material.sections() if key[0] == mp.mf]
        names = sorted(
            section_names(keys), key=lambda name: int(name.split("/")[1].split("#")[0])
        )
        mts = [name.split("/")[1] for name in names]
        if mts:
            joined = ", ".join(mts)
            print(f"  MF={mp.mf} sections (MT): {joined}")
        else:
            print(f"  no MF={mp.mf} section in this material")
        return
    try:
        cont = endf_file[resolved]
    except Exception as exc:  # noqa: BLE001
        print(f"cannot access {resolved}: {exc}", file=sys.stderr)
        sys.exit(1)
    # A material-depth path yields a MaterialView, which is not a plain
    # mapping; list its sections instead of dumping fields.
    if hasattr(cont, "sections"):
        print(f"  #{cont.position}  MAT={cont.mat}  ZA={cont.za}  AWR={cont.awr}")
        print("  sections (MF/MT):")
        for name in section_names(cont.sections()):
            print(f"    {name}")
        return
    # A section/field path yields a read-only section view; detach it to
    # a plain dict/list, which is what show_content() consumes.
    if hasattr(cont, "detach"):
        cont = cont.detach()
    show_content(cont)
