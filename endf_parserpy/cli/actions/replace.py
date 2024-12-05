############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2024/12/05
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from glob import glob
import os
import sys
from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    create_backup_file,
    determine_include,
)
from endf_parserpy import EndfPath


COMMAND_NAME = "replace"


def add_subparser(subparsers):
    parser_replace = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_replace)
    parser_replace.add_argument(
        "-n",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_replace.add_argument(
        "endfpath", type=str, help="EndfPath to object in ENDF file"
    )
    parser_replace.add_argument(
        "sourcefile", type=str, help="file from which object should be retrieved"
    )
    parser_replace.add_argument(
        "destfile",
        nargs="+",
        type=str,
        help="file(s) in which information should be inserted/replaced",
    )


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    create_backup = not args["no_backup"]
    endfpath = EndfPath(args["endfpath"])
    sourcefile = args["sourcefile"]
    izm = args["ignore_zero_mismatch"]
    izm = False if izm is None else izm
    override_args = {
        "ignore_zero_mismatch": izm,
        "ignore_send_records": True,
        "ignore_missing_tpid": True,
    }
    if len(endfpath) <= 2:
        parser = get_endf_parser(args, override_args)
    else:
        # it's about a subtle replacement inside an MF/MT
        # section and not just swapping out the entire MF/MT section
        override_args["preserve_value_strings"] = True
        parser = get_endf_parser(args, override_args)

    destfiles = []
    for fp in args["destfile"]:
        curfiles1 = glob(fp)
        curfiles2 = [fp]
        if all(f1 == f2 for f1, f2 in zip(curfiles1, curfiles2)):
            if not os.path.exists(fp):
                print(f"File {fp} does not exist", file=sys.stderr)
                sys.exit(1)
        destfiles.extend(glob(fp))
    retcode = _replace_element(
        parser, endfpath, sourcefile, destfiles, create_backup=create_backup
    )
    sys.exit(retcode)


def _replace_element(parser, endfpath, sourcefile, destfiles, create_backup):
    if len(endfpath) <= 2:
        include = []
    else:
        include = determine_include(endfpath)
    source_dict = parser.parsefile(sourcefile, include=include)
    obj = endfpath.get(source_dict)
    del source_dict
    for outfile in destfiles:
        dest_dict = parser.parsefile(outfile, include=include)
        endfpath.set(dest_dict, obj)
        if create_backup:
            create_backup_file(outfile)
        parser.writefile(outfile, dest_dict, overwrite=(not create_backup))
    return 0
