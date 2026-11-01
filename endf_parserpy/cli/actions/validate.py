############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/01
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
    "accept_non_ascii": False,
}


def add_subparser(subparsers):
    parser_validate = subparsers.add_parser(COMMAND_NAME)
    add_common_cmd_parser_args(parser_validate, defaults=STRICT_DEFAULT_ARGS)
    parser_validate.add_argument("files", nargs="+", help="files for validation")


def perform_action(args):
    assert args["subcommand"] == COMMAND_NAME
    parser = get_endf_parser(args)
    fast_parser = get_fast_parser(args)
    files = []
    for fp in args["files"]:
        matches = glob(fp)
        # keep a non-matching pattern or a missing literal path so that it
        # is reported as a failed file rather than silently dropped
        files.extend(matches if matches else [fp])
    retcode = _validate_endf_files(parser, files, fast_parser)
    sys.exit(retcode)


def get_fast_parser(args):
    """Return the parser of the fast validation path.

    It has the options of the parser of the per-section validation,
    except that it produces numpy arrays if numpy is available and
    lists otherwise, unless an array type is requested explicitly; the
    nested dictionaries are not needed to decide whether data parse.
    The C++ parser also checks the MAT/MF/MT numbers of every line, as
    the Python parser always does, so that the parsing of a section
    cannot extend into the next one (see :func:`_validate_material`).
    """
    override = {}
    if args.get("array_type") is None:
        override["array_type"] = "numpy" if _numpy_available() else "list"
    return get_endf_parser(
        args, override, cpp_only_args={"validate_control_records": True}
    )


def _numpy_available():
    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def _material_parses_at_once(endf_file, material, fast_parser):
    """Return whether all sections of ``material`` parse in one call.

    The sections are parsed as one tape built by
    :meth:`EndfFile._sections_tape`: every section has exactly the text
    with which the per-section validation parses it alone, and the
    framing records are generated as there, so the framing records of
    the file are not checked here either. As the C++ parser of the fast
    path checks the MAT/MF/MT numbers of every line, the parsing of a
    section cannot read the lines of another one; all sections must be
    present in the result.
    """
    keys = material.sections()
    try:
        text = endf_file._sections_tape(material.position, keys)
        result = fast_parser.parse(text)
        return all(mt in result.get(mf, ()) for mf, mt in keys)
    except Exception:  # noqa: BLE001
        return False


def _validate_file(parser, file, fast_parser=None):
    """Validate every section of every material of ``file``.

    Returns ``(ok, detail)``; ``detail`` is ``None`` on success and a
    human-readable failure description otherwise. The file is opened as
    an :class:`EndfFile`, so single- and multi-material files are
    validated the same way -- a tape is valid only if every section of
    every material parses.

    If ``fast_parser`` is given, all sections of a material are first
    parsed by it in a single call (see :func:`_material_parses_at_once`).
    Only if that fails, the sections of the material are parsed one by
    one with ``parser`` as without ``fast_parser``, which then decides
    whether the material is valid and describes the failure.
    """
    try:
        endf_file = open_endf_file(file, parser, on_error="raise")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    multi = len(endf_file) > 1
    for material in endf_file:
        if fast_parser is not None and _material_parses_at_once(
            endf_file, material, fast_parser
        ):
            continue
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


def _validate_endf_files(parser, files, fast_parser=None):
    any_failed = False
    file_status_list = []
    for file in files:
        ok, detail = _validate_file(parser, file, fast_parser)
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
