############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import argparse
import sys
import logging
import importlib
import warnings
from endf_parserpy.interpreter.logging_utils import setup_logger
from endf_parserpy.utils.tolerated_mismatches import (
    EndfToleratedMismatchWarning,
    format_tolerated_mismatches,
)


ACTIONS = (
    "compare",
    "convert",
    "validate",
    "replace",
    "show",
    "list_materials",
    "update_directory",
    "insert_text",
    "insert_material",
    "remove_material",
    "explain",
    "match",
)


SUBMODULE_NAMES = tuple("endf_parserpy.cli.actions." + a for a in ACTIONS)
SUBMODULES = tuple(importlib.import_module(s) for s in SUBMODULE_NAMES)


def cli_interface():

    parser = argparse.ArgumentParser(
        prog="endf-cli", description="Command-line interface to ENDF files"
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    # add subparsers
    for submodule in SUBMODULES:
        submodule.add_subparser(subparsers)

    args = vars(parser.parse_args())
    logger = setup_logger(__name__, logging.WARNING)

    # execute subcommand
    matching_module = None
    for submodule in SUBMODULES:
        if args["subcommand"] != submodule.COMMAND_NAME:
            continue
        assert matching_module is None
        matching_module = submodule

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
