############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/10/06
# Last modified:   2026/11/23
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################


import os
import re
import sys
from copy import copy
import argparse
from .. import (
    EndfParserCpp,
    EndfFile,
    EndfMaterialPath,
)
from ..interpreter.custom_exceptions import ParserException
from ..tape import SectionParseError


# The name of the operating system as platform.system() gives it for the
# systems that atomic_rename knows (from sys.platform, which saves the
# import of platform); the value of sys.platform for any other.
OS_NAME = {"win32": "Windows", "linux": "Linux", "darwin": "Darwin"}.get(
    sys.platform, sys.platform
)


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
    ("print_cache_info", bool, True, None, False, True, False),
    ("endf_format", str, None, None, True, True, True),
    ("loglevel", int, None, None, False, True, True),
    ("preserve_value_strings", bool, True, False, True, True, True),
    ("include_linenum", bool, True, False, True, True, True),
    ("prefer_noexp", bool, True, False, True, True, True),
    ("skip_intzero", bool, True, False, True, True, True),
    ("abuse_signpos", bool, True, False, True, True, True),
    ("standard_form_on_tie", bool, True, False, True, True, True),
    ("keep_E", bool, True, False, True, True, True),
    ("array_type", str, None, None, True, True, True),
)


# the hints of the error messages of the parsers that name a constructor
# argument, and their form on the command line, where each such argument
# is an option (see ENDF_PARSER_ARGS)
_CLI_HINTS = (
    (
        "create the parser with ignore_blank_lines=True",
        "use the option --ignore_blank_lines",
    ),
    # EndfParserPy and EndfParserCpp
    ("Set `accept_nan_inf=True` to allow", "Use the option --accept_nan_inf to allow"),
    ("Set `accept_nan_inf=true` to allow", "Use the option --accept_nan_inf to allow"),
    # the check of the framing records (validate)
    (
        "use the option accept_non_ascii=True to accept it",
        "use the option --accept_non_ascii to accept it",
    ),
)


def cli_message(text):
    """An error message of a parser as shown by a command: the hints that
    name an argument of the parser constructor name the option instead."""
    for parser_hint, cli_hint in _CLI_HINTS:
        text = text.replace(parser_hint, cli_hint)
    return text


# the errors of a parse of the commands: EndfFile raises SectionParseError
# for a section, with the error of the parser as its cause; the functions
# of endf_parserpy.utils (e.g. update_directory) raise the errors of the
# Python parser (ParserException) also with the C++ parser
PARSE_ERRORS = (SectionParseError, ParserException)


def parse_failure_detail(exc):
    """Describe why a section failed to parse.

    For a :class:`SectionParseError`, this is the line of the file at
    which the section starts and the message of the error raised by the
    parser (its cause), with the line numbers it gives counted in the
    file (see :attr:`SectionParseError.detail`). The name of the error is
    added for a built-in exception other than ``RuntimeError`` (the
    errors of the C++ parser), whose message may not say what failed,
    e.g. ``IndexError: list index out of range``. For another error, it
    is its message.
    """
    if not isinstance(exc, SectionParseError) or exc.__cause__ is None:
        return str(exc)
    parts = []
    if exc.line is not None:
        parts.append(f"The section starts at line {exc.line} of the file.")
    cause = exc.__cause__
    message = exc.detail if exc.detail is not None else str(cause)
    message = message.strip("\n")
    if type(cause).__module__ == "builtins" and not isinstance(cause, RuntimeError):
        message = f"{type(cause).__name__}: {message}"
    parts.append(message)
    return "\n".join(parts)


def parse_error_message(exc):
    """The message of a failed parse as the commands show it.

    For a :class:`SectionParseError`, its message (which section failed)
    followed by :func:`parse_failure_detail` on the next lines; for
    another error, its message. The hints name the options of the
    command line (see :func:`cli_message`).
    """
    if isinstance(exc, SectionParseError) and exc.__cause__ is not None:
        text = f"{exc}\n{parse_failure_detail(exc)}"
    else:
        text = str(exc).strip("\n")
    return cli_message(text)


def fail_on_parse_error(command, what, exc, status=1):
    """Print the error of the failed parse of ``what`` (e.g. the name of
    a file) on stderr, without a traceback, and exit with ``status``."""
    print(
        f"{command}: cannot parse {what}: {parse_error_message(exc)}",
        file=sys.stderr,
    )
    sys.exit(status)


def located_parse_error(exc, endf_file, positions=None):
    """The error to report for the failed parse ``exc`` of a part of
    ``endf_file`` that is larger than a section.

    Such a parse (e.g. of a material by
    :func:`~endf_parserpy.parse_tape_file` or
    :func:`~endf_parserpy.update_directory`) gives the line numbers of
    the parsed text, which are those of the file only for the first
    material. The materials at ``positions`` (all if ``None``) are then
    parsed section by section, and the :class:`SectionParseError` of the
    first section that fails is returned, which names the section and
    gives the lines of the file. If all sections parse, or ``exc`` is a
    :class:`SectionParseError` itself, ``exc`` is returned.
    """
    if isinstance(exc, SectionParseError):
        return exc
    if positions is None:
        positions = range(len(endf_file))
    try:
        for position in positions:
            material = endf_file[position]
            for k in range(len(material.sections())):
                try:
                    material[f"#{k}"]
                except SectionParseError as found:
                    return found
    except Exception:  # noqa: BLE001
        pass
    return exc


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
        elif arg_str == "print_cache_info":
            help_text = "Deprecated and ignored: it has no effect"
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


def get_endf_parser(args, args_override=None, allow_cpp=True, cpp_only_args=None):
    """Return ENDF parser object.

    ``cpp_only_args`` holds constructor arguments that only the C++
    parser accepts (e.g. ``validate_control_records``); they are passed
    if the C++ parser is chosen and do not influence that choice.
    """
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
        parser = EndfParserCpp(**cpp_parser_args, **(cpp_only_args or {}))
    else:
        from ..interpreter.endf_parser import EndfParserPy

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

    The CLI's ``--ignore_missing_tpid`` flag configures the parser; the
    same user intention is applied here to the structural index of the
    file, so that a file without a tape head can be opened at all. (In
    the library API, the parser option and the ``EndfFile`` option are
    deliberately independent.)
    """
    if "ignore_missing_tpid" not in kwargs:
        opts = getattr(parser, "read_opts", None) or {}
        kwargs["ignore_missing_tpid"] = bool(opts.get("ignore_missing_tpid") or False)
    return EndfFile(file, parser=parser, **kwargs)


def open_endf_file_or_exit(command, file, parser, status=1, **kwargs):
    """Open ``file`` with :func:`open_endf_file`; if it cannot be read
    (e.g. a missing file, or a tape that ends in the middle of a
    material), print the error on stderr, without a traceback, and exit
    with ``status``."""
    try:
        return open_endf_file(file, parser, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"{command}: cannot read {file}: {exc}", file=sys.stderr)
        sys.exit(status)


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


_MAT_OCCURRENCE = re.compile(r"[0-9]+#[0-9]+")


def is_material_qualified(raw_path):
    """Whether a CLI path begins with a material selector.

    The first component decides: ``MAT#k`` is a material selector, and so
    is ``#k`` when it stands alone or is followed by an MF number or a
    section position (``#0``, ``#0/3/2``, ``#0/#2``). A ``#k`` followed by
    a field name (``#2/IZAM``) is the section at position ``k`` of a
    single material, and a path that begins with an MF number
    (``3/102#1/IZAM``) has no material selector.
    """
    parts = [part.strip() for part in str(raw_path).strip().strip("/").split("/")]
    first = parts[0]
    if _MAT_OCCURRENCE.fullmatch(first):
        return True
    if not first.startswith("#"):
        return False
    if len(parts) == 1:
        return True
    second = parts[1]
    return second.isdigit() or second.startswith("#")


def resolve_material_path(endf_file, raw_path):
    """Resolve a CLI path argument to a material-qualified path string.

    A path that begins with a material selector (see
    :func:`is_material_qualified`) is treated as an
    :class:`~endf_parserpy.EndfMaterialPath` and used as given. Any
    other path is a plain :class:`~endf_parserpy.EndfPath`, which may
    begin with a section selector (``3/102#1``, ``#2/IZAM``); it is
    accepted only when ``endf_file`` holds a single material (it is then
    addressed against that material via the ``#0`` selector). On a
    multi-material file a selector-less path is rejected with a listing
    of the available materials. A bare ``#k`` is the material at tape
    position ``k``; the section at position ``k`` is ``#0/#k``.
    """
    # surrounding slashes are optional in CLI paths (e.g. "/3/2" and
    # "3/2" are the same); strip them so the path composes cleanly
    raw_path = str(raw_path).strip().strip("/")
    if is_material_qualified(raw_path):
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


def section_label_of(endf_file, material_path):
    """Return the label ``(MF, MT)`` of the section a material-qualified
    path addresses, also for a section selected by its position (``#k``).

    Raises the errors of the selection, e.g. :class:`IndexError` for a
    position that is out of range.
    """
    mp = EndfMaterialPath(material_path)
    if mp.section_position is None:
        return mp.mf, mp.mt
    material = endf_file[selector_of(material_path)]
    keys = material.sections()
    if mp.section_position >= len(keys):
        raise IndexError(
            f"section position {mp.section_position} out of range; the "
            f"material has {len(keys)} sections"
        )
    return keys[mp.section_position]


def section_names(keys):
    """The names ``MF/MT`` of the sections of a material, in its order,
    with ``#k`` added for a label that occurs several times."""
    counts = {}
    for key in keys:
        counts[key] = counts.get(key, 0) + 1
    seen = {}
    names = []
    for mf, mt in keys:
        if counts[(mf, mt)] > 1:
            k = seen.get((mf, mt), 0)
            seen[(mf, mt)] = k + 1
            names.append(f"{mf}/{mt}#{k}")
        else:
            names.append(f"{mf}/{mt}")
    return names


def selector_of(material_path):
    """Return the material-selector segment of a material-qualified path.

    ``material_path`` is a path string as produced by
    :func:`resolve_material_path`; the part before the first ``/`` is the
    material selector (``#k``, ``MAT`` or ``MAT#k``).
    """
    return str(material_path).strip("/").split("/")[0]
