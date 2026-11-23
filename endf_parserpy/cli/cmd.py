############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2026/11/23
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import argparse
import sys
import importlib
import warnings
from endf_parserpy.utils.tolerated_mismatches import (
    EndfToleratedMismatchWarning,
    format_tolerated_mismatches,
)


# The subcommands, in the order of the help text, and the modules in
# endf_parserpy.cli.actions that implement them. Only the module of the
# subcommand on the command line is imported and registered, which
# saves the import of the others when the program starts.
SUBCOMMANDS = {
    "compare": "compare",
    "convert": "convert",
    "validate": "validate",
    "replace": "replace",
    "show": "show",
    "list-materials": "list_materials",
    "update-directory": "update_directory",
    "insert-text": "insert_text",
    "insert-material": "insert_material",
    "remove-material": "remove_material",
    "explain": "explain",
    "match": "match",
}


def _subcommand_modules(argv):
    """Import the modules of the subcommands to register for ``argv``.

    The module of the subcommand that ``argv`` (the arguments without
    the program name) starts with, or else (help, a missing or unknown
    subcommand) those of all subcommands.
    """
    if argv and argv[0] in SUBCOMMANDS:
        commands = (argv[0],)
    else:
        commands = SUBCOMMANDS
    return [
        importlib.import_module("endf_parserpy.cli.actions." + SUBCOMMANDS[c])
        for c in commands
    ]


def _make_parser(submodules):
    parser = argparse.ArgumentParser(
        prog="endf-cli", description="Command-line interface to ENDF files"
    )
    # with a single subcommand registered, the metavar lists them all as
    # argparse does by default, so that the usage is always the same
    metavar = None
    if len(submodules) < len(SUBCOMMANDS):
        metavar = "{" + ",".join(SUBCOMMANDS) + "}"
    subparsers = parser.add_subparsers(dest="subcommand", metavar=metavar)
    subparsers.required = True
    for submodule in submodules:
        submodule.add_subparser(subparsers)
    return parser


def cli_interface():

    submodules = _subcommand_modules(sys.argv[1:])
    parser = _make_parser(submodules)
    args = vars(parser.parse_args())

    # execute subcommand
    (matching_module,) = (m for m in submodules if m.COMMAND_NAME == args["subcommand"])

    with _tolerated_mismatch_report():
        matching_module.perform_action(args)

    # should not arrive here
    sys.exit(1)


class _tolerated_mismatch_report:
    """Collect the warnings about tolerated mismatches of a subcommand.

    The subcommands parse the files section by section (see EndfFile),
    each section with tolerated mismatches giving a warning. They are
    collected and reported at the end, one summary per file on stderr,
    also if the subcommand exits with sys.exit. Other warnings are shown
    as usual. (validate reports the mismatches in its own output.)
    """

    def __enter__(self):
        self._catcher = warnings.catch_warnings()
        self._catcher.__enter__()
        warnings.simplefilter("always", EndfToleratedMismatchWarning)
        self._collected = []
        show = warnings.showwarning

        def showwarning(message, category, *args, **kwargs):
            if issubclass(category, EndfToleratedMismatchWarning):
                self._collected.append(message)
            else:
                show(message, category, *args, **kwargs)

        warnings.showwarning = showwarning
        return self

    def __exit__(self, *exc_info):
        self._catcher.__exit__(*exc_info)
        by_source = {}
        for w in self._collected:
            mismatches = by_source.setdefault(getattr(w, "source", None), [])
            mismatches.extend(getattr(w, "mismatches", ()))
        for source, mismatches in by_source.items():
            if mismatches:
                text = format_tolerated_mismatches(mismatches, source)
                print(f"endf-cli: warning: {text}", file=sys.stderr)
        return False


if __name__ == "__main__":
    cli_interface()
