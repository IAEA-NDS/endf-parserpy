############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/08
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Check an installed endf-parserpy, e.g. a wheel before its tests.

usage:
  python tools/check_installed_package.py [--not-under <dir>]...

Imports endf_parserpy and fails (exit status 1)
- if the package is imported from a directory given with ``--not-under``
  (e.g. the source checkout, so that the tests that follow run against
  the installed package and not against the checkout);
- if one of the C++ modules is missing or cannot be imported;
- if ``_bulk_body_info()`` of a C++ module does not name a row kernel
  tier that is built and supported.

It prints the location and version of the package, the tags of the
installed wheel, the interpreter and machine, and the selected tier of
each C++ module. It needs nothing but the package (no numpy, no pytest),
so that it can also run as the test command of cibuildwheel.
"""

import argparse
import importlib
import os
import platform
import sys

# the C++ modules of the package (see setup.py)
CPP_MODULES = ("endf6", "endf6_ext", "errorr", "jendl", "pendf", "test")


def _is_under(path, directory):
    path = os.path.normcase(os.path.realpath(path))
    directory = os.path.normcase(os.path.realpath(directory))
    try:
        return os.path.commonpath([path, directory]) == directory
    except ValueError:
        # e.g. on different drives (Windows)
        return False


def _wheel_tags():
    # the Tag lines of the WHEEL file of the installed distribution
    try:
        from importlib.metadata import distribution
    except ImportError:
        return []
    try:
        text = distribution("endf-parserpy").read_text("WHEEL") or ""
    except Exception:
        return []
    return [
        ln.split(":", 1)[1].strip() for ln in text.splitlines() if ln.startswith("Tag:")
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--not-under", action="append", default=[], metavar="DIR")
    args = ap.parse_args()

    errors = []
    import endf_parserpy

    location = os.path.dirname(os.path.realpath(endf_parserpy.__file__))
    print(f"endf_parserpy {endf_parserpy.__version__} from {location}")
    print(f"wheel tags: {', '.join(_wheel_tags()) or 'none found'}")
    print(
        f"Python {sys.version.split()[0]} ({platform.python_implementation()}), "
        f"machine {platform.machine()}, {platform.platform()}"
    )
    for directory in args.not_under:
        if _is_under(location, directory):
            errors.append(
                f"endf_parserpy is imported from {location}, below {directory}"
            )

    for name in CPP_MODULES:
        modname = "endf_parserpy.cpp_parsers." + name
        try:
            mod = importlib.import_module(modname)
        except Exception as exc:
            errors.append(f"{modname}: cannot be imported ({exc!r})")
            continue
        info = mod._bulk_body_info()
        selected = info["selected"]
        tier = info["tiers"].get(selected, {})
        built = [n for n, t in info["tiers"].items() if t["built"]]
        print(f"{modname}: selected {selected}, built {' '.join(built)}")
        if not (tier.get("built") and tier.get("supported")):
            errors.append(
                f"{modname}: selected tier {selected!r} not built and supported"
            )

    for err in errors:
        print("ERROR: " + err)
    if errors:
        sys.exit(1)
    print("check passed")


if __name__ == "__main__":
    main()
