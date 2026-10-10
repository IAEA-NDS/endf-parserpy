############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from ..cmd_utils import (
    add_common_cmd_parser_args,
    get_endf_parser,
    open_endf_file,
)
from glob import glob
import sys


COMMAND_NAME = "validate"

STRICT_DEFAULT_ARGS = {
    "ignore_number_mismatch": False,
    "ignore_zero_mismatch": False,
    "ignore_varspec_mismatch": False,
    "accept_spaces": False,
    "ignore_blank_lines": False,
    "ignore_send_records": False,
    "ignore_missing_tpid": False,
    "accept_nan_inf": False,
    "accept_d_exponent": False,
}


def add_subparser(subparsers):
    parser_validate = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_validate, defaults=STRICT_DEFAULT_ARGS)
    parser_validate.add_argument("files", nargs="+", help="files for validation")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    files = []
    for fp in args["files"]:
        matches = glob(fp)
        # keep a non-matching pattern or a missing literal path so that it
        # is reported as a failed file rather than silently dropped
        files.extend(matches if matches else [fp])
    retcode = _validate_endf_files(parser, files)
    sys.exit(retcode)


def _validate_file(parser, file):
    """Validate every section of every material of ``file``.

    Returns ``(ok, detail)``; ``detail`` is ``None`` on success and a
    human-readable failure description otherwise. The file is opened as
    an :class:`EndfFile`, so single- and multi-material files are
    validated the same way -- a tape is valid only if every section of
    every material parses.
    """
    try:
        endf_file = open_endf_file(file, parser, on_error="raise")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    multi = len(endf_file) > 1
    for material in endf_file:
        for mf, mt in material.sections():
            try:
                material[mf, mt]
            except Exception as exc:  # noqa: BLE001
                prefix = (
                    f"material #{material.position} (MAT {material.mat}), "
                    if multi
                    else ""
                )
                return False, f"{prefix}section MF={mf}/MT={mt}:\n{exc}"
    return True, None


def _validate_endf_files(parser, files):
    any_failed = False
    file_status_list = []
    for file in files:
        ok, detail = _validate_file(parser, file)
        file_status_list.append((file, "ok" if ok else "failed"))
        if not ok:
            any_failed = True
            print("\n" + "=" * 80)
            print(f"  Validation of {file} failed for the following reason:\n")
            print(detail)

    print("\n========== VALIDATION SUMMARY ==========")
    for file_status in file_status_list:
        print(f"{file_status[1]} - {file_status[0]}")
    retcode = 1 if any_failed else 0
    return retcode
