#!/usr/bin/env python
"""Write the results of the framing conformance cases to a JSON file.

usage:
  python tools/snapshot_framing_messages.py <output.json>

Runs every case of ``tests/test_tape_structure_conformance.py`` (the valid
and damaged inputs of the framing of a tape, with the filters
``include``/``exclude`` and with and without ``ignore_send_records``) with
the ``endf_parserpy`` that is imported, and writes the exact messages of
``EndfParserPy``, ``EndfParserCpp`` (if its C++ module can be imported)
and ``check_framing``, and the output of both writers, as the golden file
of the test does. Run it with two versions of the package (e.g. with
``PYTHONPATH`` pointing to two checkouts) and compare the files to see
every message that changed between them.
"""

import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    tests = Path(__file__).resolve().parent.parent / "tests"
    sys.path.insert(0, str(tests))
    import test_tape_structure_conformance as conformance

    cpp_class = conformance._cpp_class()
    results = {
        name: conformance.run_case(name, cpp_class) for name in conformance.CASES
    }
    results["write"] = conformance.run_writes(cpp_class)
    Path(argv[1]).write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(f"{len(results) - 1} cases written to {argv[1]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
