############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2024/02/13
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import argparse
import sys
import logging
from glob import glob
from .endf_parser import EndfParser


def validate_endf_files(files, strict=False):

    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)

    ignore_number_mismatch = not strict
    ignore_zero_mismatch = not strict
    fuzzy_matching = not strict
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


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="endf_parserpy.cmd", description="endf_parserpy command-line utility"
    )

    parser.add_argument(
        "action",
        choices=["validate"],
        help="the action to perform (at the moment only `validate`)",
    )
    parser.add_argument(
        "-s", "--strict", action="store_true", help="switch to enable strict mode"
    )
    parser.add_argument("files", nargs="+", help="files for applying the action")

    args = parser.parse_args()
    action = args.action
    strict_mode = args.strict
    files = []
    for fp in args.files:
        files.extend(glob(fp))

    if action == "validate":
        retcode = validate_endf_files(files, strict_mode)
        sys.exit(retcode)

    # should not arrive here
    sys.exit(1)
