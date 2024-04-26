############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2024/04/26
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
from endf_parserpy.utils.accessories import EndfPath
from endf_parserpy.interpreter.endf_parser import EndfParser
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.endf6_plumbing import (
    update_directory,
    insert_description,
)
from endf_parserpy.utils.user_tools import show_content


os_name = platform.system()


def atomic_rename(src, dst):
    if os_name == "Windows":
        os.rename(src, dst)
    elif os_name in ("Linux", "Darwin"):
        os.link(src, dst)
        os.unlink(src)
    else:
        raise OSError(
            "Unknown operating system --- " + "atomic file renaming not possible"
        )


def create_backup_file(file):
    backup_file = file
    backup_created = False
    for i in range(10):
        backup_file += ".bak"
        try:
            atomic_rename(file, backup_file)
            backup_created = True
            break
        except OSError:
            pass
    if not backup_created:
        raise OSError(f"Unable to create backup file for {file}")


def determine_include(endfpath):
    endfpath = EndfPath(endfpath)
    if len(endfpath) == 1:
        include = (int(endfpath[0]),)
    else:
        include = ((int(endfpath[0]), int(endfpath[1])),)
    return include


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


def show_file_content(parser, endfpath, file):
    endfpath = EndfPath(endfpath)
    include = determine_include(endfpath)
    endf_dict = parser.parsefile(file, include=include)
    cont = endfpath.get(endf_dict)
    show_content(cont)


def update_mf1mt451_directory(parser, file, create_backup):
    endf_dict = parser.parsefile(file, include=[(1, 451)])
    update_directory(endf_dict, parser, **parser.read_opts)
    if create_backup:
        create_backup_file(file)
    parser.writefile(file, endf_dict, overwrite=(not create_backup))


def insert_mf1mt451_description(parser, line_no, file, create_backup):
    endf_dict = parser.parsefile(file, include=[(1, 451)])
    text = sys.stdin.read()
    insert_description(endf_dict, text, after_line=line_no)
    update_directory(endf_dict, parser)
    if create_backup:
        create_backup_file(file)
    parser.writefile(file, endf_dict, overwrite=(not create_backup))


def explain_endf_variable(parser, endfpath, file):
    endfpath = EndfPath(endfpath)
    include = determine_include(endfpath)
    parser.parsefile(file, include=include)
    parser.explain(endfpath)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="endf_parserpy.cmd", description="endf_parserpy command-line utility"
    )
    parser.add_argument(
        "--no-cache-info",
        action="store_true",
        help="suppress the message on cache location",
    )
    parser.add_argument(
        "-s", "--strict", action="store_true", help="switch to enable strict mode"
    )
    parser.add_argument(
        "-f", "--format", type=str, default="endf6", help="ENDF format flavor"
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

    parser_show = subparsers.add_parser("show")
    parser_show.add_argument(
        "endfpath", type=str, help="EndfPath to section or value to display"
    )
    parser_show.add_argument("file", type=str, help="ENDF file")

    parser_update_dir = subparsers.add_parser("update-directory")
    parser_update_dir.add_argument(
        "-nb",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_update_dir.add_argument("file", type=str, help="ENDF file")

    parser_instext = subparsers.add_parser("insert-text")
    parser_instext.add_argument(
        "-nb",
        "--no-backup",
        action="store_true",
        help="disable creation of backup file (suffix .bak)",
    )
    parser_instext.add_argument(
        "-l", "--line", type=int, default=0, help="after which line to insert the text"
    )
    parser_instext.add_argument("file", type=str, help="ENDF file")

    parser_explain = subparsers.add_parser("explain")
    parser_explain.add_argument(
        "endfpath", type=str, help="EndfPath to the variable that should be explained"
    )
    parser_explain.add_argument("file", type=str, help="ENDF file")

    args = parser.parse_args()
    strict_mode = args.strict
    endf_format = args.format

    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)

    print_cache_info = not args.no_cache_info
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
        print_cache_info=print_cache_info,
        endf_format=endf_format,
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
    elif args.subcommand == "show":
        show_file_content(parser, args.endfpath, args.file)
    elif args.subcommand == "update-directory":
        create_backup = not args.no_backup
        update_mf1mt451_directory(parser, args.file, create_backup)
    elif args.subcommand == "insert-text":
        create_backup = not args.no_backup
        insert_mf1mt451_description(parser, args.line, args.file, create_backup)
    elif args.subcommand == "explain":
        explain_endf_variable(parser, args.endfpath, args.file)

    # should not arrive here
    sys.exit(1)
