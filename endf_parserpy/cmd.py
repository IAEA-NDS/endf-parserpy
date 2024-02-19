############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2024/02/19
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import argparse
import sys
import logging
import platform
from glob import glob
import os
from .endf_parser import EndfParser
from .accessories import EndfPath
from .debugging_utils import compare_objects

os_name = platform.system()


def atomic_rename(src, dst):
    if os_name == "Windows":
        os.rename(src, dst)
    elif os_name in ("Linux", "Darwin"):
        os.link(src, dst)
        os.unlink(src)


def validate_endf_files(parser, files):

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


def compare_endf_files(parser, files, atol, rtol):
    if len(files) != 2:
        print("Expecting exactly two files for the comparison", file=sys.stderr)
        sys.exit(1)
    endf_dict1 = parser.parsefile(files[0])
    endf_dict2 = parser.parsefile(files[1])
    is_equal = compare_objects(
        endf_dict1, endf_dict2, atol=atol, rtol=rtol, fail_on_diff=False
    )
    retcode = 0 if is_equal else 1
    return retcode


def replace_element(parser, endfpath, sourcefile, destfiles, create_backup):
    endfpath = EndfPath(endfpath)
    if len(endfpath) == 1:
        include = (endfpath[0],)
    else:
        include = ((endfpath[0], endfpath[1]),)
    source_dict = parser.parsefile(sourcefile, include=include)
    obj = endfpath.get(source_dict)
    del source_dict
    for outfile in destfiles:
        dest_dict = parser.parsefile(outfile, include=include)
        endfpath.set(dest_dict, obj)
        if create_backup:
            backup_file = outfile
            backup_created = False
            for i in range(10):
                backup_file += ".bak"
                try:
                    atomic_rename(outfile, backup_file)
                    backup_created = True
                    break
                except OSError:
                    pass
            if not backup_created:
                print("Unable to create backup file", file=sys.stderr)
                return 1
        parser.writefile(outfile, dest_dict, overwrite=(not create_backup))
    return 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="endf_parserpy.cmd", description="endf_parserpy command-line utility"
    )
    parser.add_argument(
        "-s", "--strict", action="store_true", help="switch to enable strict mode"
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    parser_validate = subparsers.add_parser("validate")
    parser_validate.add_argument("files", nargs="+", help="files for validation")

    parser_compare = subparsers.add_parser("compare")
    parser_compare.add_argument(
        "--atol", type=float, default=1e-8, help="absolute tolerance"
    )
    parser_compare.add_argument(
        "--rtol", type=float, default=1e-6, help="relative tolerance"
    )
    parser_compare.add_argument("files", nargs=2, help="files for comparison")

    parser_replace = subparsers.add_parser("replace")
    parser_replace.add_argument(
        "-nb",
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

    args = parser.parse_args()
    strict_mode = args.strict

    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)

    ignore_number_mismatch = not strict_mode
    ignore_zero_mismatch = not strict_mode
    fuzzy_matching = not strict_mode
    parser = EndfParser(
        ignore_number_mismatch=ignore_number_mismatch,
        ignore_zero_mismatch=ignore_zero_mismatch,
        fuzzy_matching=fuzzy_matching,
        ignore_varspec_mismatch=False,
        accept_spaces=False,
        ignore_blank_lines=False,
        ignore_send_records=False,
        ignore_missing_tpid=False,
    )

    if args.subcommand == "validate":
        files = []
        for fp in args.files:
            files.extend(glob(fp))
        retcode = validate_endf_files(parser, files)
        sys.exit(retcode)
    elif args.subcommand == "compare":
        files = args.files
        atol = args.atol
        rtol = args.rtol
        retcode = compare_endf_files(parser, files, atol=atol, rtol=rtol)
        sys.exit(retcode)
    elif args.subcommand == "replace":
        create_backup = not args.no_backup
        endfpath = args.endfpath
        sourcefile = args.sourcefile
        destfiles = []
        for fp in args.destfile:
            curfiles1 = glob(fp)
            curfiles2 = [fp]
            if all(f1 == f2 for f1, f2 in zip(curfiles1, curfiles2)):
                if not os.path.exists(fp):
                    print(f"File {fp} does not exist", file=sys.stderr)
                    sys.exit(1)
            destfiles.extend(glob(fp))
        retcode = replace_element(
            parser, endfpath, sourcefile, destfiles, create_backup=create_backup
        )
        sys.exit(retcode)

    # should not arrive here
    sys.exit(1)
