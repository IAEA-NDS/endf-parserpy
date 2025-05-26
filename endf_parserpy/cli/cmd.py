############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/02/05
# Last modified:   2025/05/26
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import argparse
import sys
import logging
import importlib
from endf_parserpy.interpreter.logging_utils import setup_logger
from endf_parserpy.utils.user_tools import show_content


ACTIONS = (
    "compare",
    "convert",
    "validate",
    "replace",
    "show",
    "update_directory",
    "insert_text",
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

    matching_module.perform_action(args)

    # should not arrive here
    sys.exit(1)


if __name__ == "__main__":
    cli_interface()
