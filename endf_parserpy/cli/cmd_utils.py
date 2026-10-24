############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################


import os
import sys
import platform
from copy import copy
import argparse
from .. import (
    EndfParserPy,
    EndfParserCpp,
    EndfFile,
)


OS_NAME = platform.system()


ENDF_PARSER_ARGS = (
    # Content in tuples:
    #   1st element: name of argument
    #   2nd element: argument type
    #   3rd element: default if argument provided without value
    #   4th element: default value if argument not provided
    #   5th element: supported by cpp parser
    #   6th element: exposed on command line
    #   7th element: consider variable for choosing between cpp and Python parser
    ("ignore_number_mismatch", bool, True, None, True, True, True),
    ("ignore_zero_mismatch", bool, True, None, True, True, True),
    ("fuzzy_matching", bool, True, None, False, True, True),
    ("ignore_varspec_mismatch", bool, True, None, True, True, True),
    ("accept_spaces", bool, True, None, True, True, True),
    ("ignore_blank_lines", bool, True, None, True, True, True),
    ("ignore_send_records", bool, True, None, True, True, True),
    ("ignore_missing_tpid", bool, True, None, True, True, True),
    ("accept_nan_inf", bool, True, None, True, True, True),
    ("accept_d_exponent", bool, True, None, True, True, True),
    ("accept_non_ascii", bool, True, None, True, True, True),
    ("print_cache_info", bool, True, False, False, True, False),
    ("endf_format", str, None, None, True, True, True),
    ("loglevel", int, None, None, False, True, True),
    ("preserve_value_strings", bool, True, False, True, True, True),
    ("include_linenum", bool, True, False, True, True, True),
    ("prefer_noexp", bool, True, False, True, True, True),
    ("skip_intzero", bool, True, False, True, True, True),
    ("abuse_signpos", bool, True, False, True, True, True),
    ("keep_E", bool, True, False, True, True, True),
    ("array_type", str, None, None, True, True, True),
)


def add_common_cmd_parser_args(parser, defaults=None):
    """Add common arguments to command-line argument parser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to which the common ENDF parser arguments will be added.
    defaults : dict, optional
        Mapping ``{arg_name: default_value}`` overriding the default value of
        selected arguments for this command. The override is reflected both
        in the argparse-level default (so the user's CLI flag still wins)
        and in the rendered ``--help`` text.
    """
    defaults = defaults or {}
    parser.add_argument(
        "--no-cpp",
        dest="no_cpp",
        action="store_true",
        help="force the use of Python ENDF parser, even if faster C++ ENDF parser is available",
    )
    for arg_info in ENDF_PARSER_ARGS:
        arg_str, arg_type, arg_const, arg_def, cpp_sup, expose, imp = arg_info
        if not expose:
            continue
        if arg_str in defaults:
            arg_def = defaults[arg_str]
            help_text = (
                f"Default for this command: {arg_def}. "
                "Consult the help of the equally named EndfParserPy constructor argument"
            )
        else:
            help_text = "Consult the help of the equally named EndfParserPy constructor argument"
        kwargs = {
            "dest": arg_str,
            "const": arg_const,
            "default": arg_def,
            "help": help_text,
        }
        if arg_type == bool:
            kwargs["action"] = "store_const"
        else:
            kwargs["type"] = arg_type
            kwargs["nargs"] = "?"
        parser.add_argument(f"--{arg_str}", **kwargs)


def _map_cmd_args_to_endf_parser_args(args, cpp):
    """Map command-line args to END parser args."""
    arg_names = (v[0] for v in ENDF_PARSER_ARGS)
    cpp_support = (v[4] for v in ENDF_PARSER_ARGS)
    kwargs = {
        k: args[k]
        for k, cpp_sup in zip(arg_names, cpp_support)
        if k in args and args[k] is not None and (not cpp or cpp_sup)
    }
    return kwargs


def get_endf_parser(args, args_override=None, allow_cpp=True):
    """Return ENDF parser object."""
    args_override = {} if args_override is None else args_override
    parser_args = {**args, **args_override}
    no_cpp = parser_args["no_cpp"] or (not allow_cpp)
    py_parser_args = _map_cmd_args_to_endf_parser_args(parser_args, False)
    cpp_parser_args = _map_cmd_args_to_endf_parser_args(parser_args, True)
    rel_py_parser_args = copy(py_parser_args)
    rel_cpp_parser_args = copy(cpp_parser_args)
    for cur_arg, *_, imp in ENDF_PARSER_ARGS:
        if not imp and cur_arg in rel_py_parser_args:
            rel_py_parser_args.pop(cur_arg)
        if not imp and cur_arg in rel_cpp_parser_args:
            rel_cpp_parser_args.pop(cur_arg)
    can_use_cpp = (
        not no_cpp
        and set(rel_py_parser_args) == set(rel_cpp_parser_args)
        and all(
            rel_cpp_parser_args[k] == rel_py_parser_args[k] for k in rel_py_parser_args
        )
    )
    if can_use_cpp:
        parser = EndfParserCpp(**cpp_parser_args)
    else:
        parser = EndfParserPy(**py_parser_args)
    return parser


def atomic_rename(src, dst):
    if OS_NAME == "Windows":
        os.rename(src, dst)
    elif OS_NAME in ("Linux", "Darwin"):
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


def export_endf_file(endf_file, file, create_backup):
    """Write ``endf_file`` back to ``file``, optionally keeping a backup.

    :meth:`EndfFile.export` needs the source file intact while it copies
    the untouched sections verbatim, so when a backup is requested the
    tape is first written to a sibling temporary file; only then is the
    original moved aside as the ``.bak`` backup and the new file moved
    into its place.
    """
    if create_backup:
        tmp = file + ".endf-cli-tmp"
        endf_file.export(tmp, overwrite=True)
        create_backup_file(file)
        atomic_rename(tmp, file)
    else:
        endf_file.export(file, overwrite=True)


def open_endf_file(file, parser, **kwargs):
    """Open ``file`` as an :class:`EndfFile`, the uniform CLI access object.

    A single-material file is simply an :class:`EndfFile` of length one,
    so the same object transparently handles single- and multi-material
    files, and individual sections are parsed only when accessed.
    """
    return EndfFile(file, parser=parser, **kwargs)


def parsed_material_dict(material):
    """Return a fully parsed ``{MF: {MT: section}}`` dict for ``material``.

    Every section of the :class:`MaterialView` is accessed (and hence
    parsed) and detached to a plain ``dict``, yielding the same data
    structure the single-file parser used to return from ``parsefile``.
    The tape-level MF=0/MT=0 head is not a material section and is left
    out, so the result describes the material's own data only.
    """
    endf_dict = {}
    for mf, mt in material.sections():
        endf_dict.setdefault(mf, {})[mt] = material[mf, mt].detach()
    return endf_dict


def format_material_table(endf_file):
    """Return a human-readable listing of the materials in ``endf_file``."""
    lines = []
    for mv in endf_file:
        lines.append(f"  #{mv.position}  MAT={mv.mat}  ZA={mv.za}  AWR={mv.awr}")
    return "\n".join(lines)


def resolve_material_path(endf_file, raw_path):
    """Resolve a CLI path argument to a material-qualified path string.

    A path containing ``#`` is treated as an
    :class:`~endf_parserpy.EndfMaterialPath` and used as given. A path
    without ``#`` is a plain :class:`~endf_parserpy.EndfPath`; it is
    accepted only when ``endf_file`` holds a single material (it is then
    addressed against that material via the ``#0`` selector). On a
    multi-material file a selector-less path is rejected with a listing
    of the available materials.
    """
    # surrounding slashes are optional in CLI paths (e.g. "/3/2" and
    # "3/2" are the same); strip them so the path composes cleanly
    raw_path = str(raw_path).strip().strip("/")
    if "#" in raw_path:
        return raw_path
    if len(endf_file) == 1:
        return f"#0/{raw_path}" if raw_path else "#0"
    msg = (
        f"the file holds {len(endf_file)} materials; prefix the path with "
        "a material selector (#k for the material at tape position k, or "
        "MAT#k for the k-th material with that MAT number):\n"
        + format_material_table(endf_file)
    )
    print(msg, file=sys.stderr)
    sys.exit(1)


def selector_of(material_path):
    """Return the material-selector segment of a material-qualified path.

    ``material_path`` is a path string as produced by
    :func:`resolve_material_path`; the part before the first ``/`` is the
    material selector (``#k``, ``MAT`` or ``MAT#k``).
    """
    return str(material_path).strip("/").split("/")[0]
