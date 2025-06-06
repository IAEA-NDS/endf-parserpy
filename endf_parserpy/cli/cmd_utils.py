############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2025/06/06
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import os
import platform
from copy import copy
import argparse
from .. import (
    EndfParserPy,
    EndfParserCpp,
    EndfPath,
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


def add_common_cmd_parser_args(parser):
    """Add common arguments to command-line argument parser."""
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
        kwargs = {
            "dest": arg_str,
            "const": arg_const,
            "default": arg_def,
            "help": "Consult the help of the equally named EndfParserPy constructor argument",
        }
        if arg_type == bool:
            kwargs["action"] = "store_const"
        else:
            kwargs["type"] = arg_type
            kwargs["nargs"]: "?"
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


def determine_include(endfpath):
    endfpath = EndfPath(endfpath)
    if len(endfpath) == 0:
        include = tuple()
    elif len(endfpath) == 1:
        include = (int(endfpath[0]),)
    else:
        include = ((int(endfpath[0]), int(endfpath[1])),)
    return include


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
