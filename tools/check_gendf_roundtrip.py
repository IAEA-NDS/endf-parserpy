############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/16
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Check the round trip of GENDF tapes with the ``gendf`` flavor.

usage:
  python tools/check_gendf_roundtrip.py [--parser py|cpp|both]
      [--no-compare-parsers] [--njoy-number-forms] <files>...

For each GENDF tape (NJOY GROUPR or GAMINR output), every section of
every material is parsed on its own and written back, and the data lines
(the records of the section without its end record, all 80 columns) are
compared with those of the file, in order. The tape is divided into
materials at their MEND records and into sections at a change of MF/MT
or an end record, by this script itself, so that materials with the
same MAT (one per temperature) and sections that are not in ascending
order, both usual on GENDF tapes, are taken as they are. Each section is
handed to the parser as a short tape: the TPID record of the file, the
section, and SEND, FEND, MEND and TEND records.

The framing records of the file (SEND, FEND, MEND, TEND) are not
compared: NJOY writes no SEND after MF1/MT451 and no FEND records
between the MFs of a material, which the writers of endf-parserpy do not
reproduce.

By default, the sections are parsed and written with
``preserve_value_strings=True``, so that the text of every number is
kept. With ``--njoy-number-forms``, they are written from the values
instead, with ``prefer_noexp=True`` and ``standard_form_on_tie=True``,
which give the forms of NJOY in most, but not all, fields.

With ``--parser both`` (the default), the round trip is checked with
EndfParserPy and, if its C++ module ``gendf`` can be imported, with
EndfParserCpp, and the dictionaries of the two parsers are compared in
the ``dict``, ``list`` and ``numpy`` modes (``numpy`` only if NumPy is
installed); ``--no-compare-parsers`` skips this comparison.

One line is printed per file with the numbers of materials, sections and
failed sections per check, followed by the first failures of the file.
Sections with the same MF/MT in a material (e.g. nuclide production in
MF3) are checked one by one and reported, but are no failure.
The exit status is 1 if a check fails for any file, 2 for a usage error.
"""

import argparse
import math
import sys
from collections import Counter


TPID_DEFAULT = " " * 66 + "   1 0  0    0"
MAX_DETAILS = 5


def control_numbers(line):
    """Return the MAT, MF and MT numbers of a line (columns 67-75)."""
    try:
        return int(line[66:70]), int(line[70:72]), int(line[72:75])
    except ValueError:
        return None


def split_tape(text):
    """Divide a tape into its TPID record and materials.

    Returns the TPID line (or None) and a list of materials, each a list
    of sections ``(mf, mt, lines)`` in the order of the file.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    tpid = None
    start = 0
    if lines:
        numbers = control_numbers(lines[0])
        if numbers is not None and numbers[0] >= 0 and numbers[1:] == (0, 0):
            tpid = lines[0]
            start = 1
    materials = []
    material = None
    section = None
    for lineno, line in enumerate(lines[start:], start=start + 1):
        numbers = control_numbers(line)
        if numbers is None:
            raise ValueError(f"line {lineno}: no MAT/MF/MT numbers")
        mat, mf, mt = numbers
        if mat > 0 and mf > 0 and mt > 0:
            if material is None:
                material = []
                materials.append((mat, material))
            if section is None or section[0] != mf or section[1] != mt:
                section = (mf, mt, [])
                material.append(section)
            section[2].append(line)
            continue
        section = None
        if mat <= 0 and mf == 0 and mt == 0:
            # MEND or TEND
            material = None
    return tpid, materials


def control_line(mat, mf, mt, ns):
    return " " * 66 + f"{mat:4d}{mf:2d}{mt:3d}{ns:5d}"


def section_tape(tpid, mat, mf, mt, lines):
    """Return a short tape holding one section."""
    return "\n".join(
        [tpid if tpid is not None else TPID_DEFAULT]
        + lines
        + [
            control_line(mat, mf, 0, 99999),
            control_line(mat, 0, 0, 0),
            control_line(0, 0, 0, 0),
            control_line(-1, 0, 0, 0),
        ]
    )


def written_section_lines(text, mf, mt):
    """Return the data lines of section MF/MT of a written tape."""
    if isinstance(text, (list, tuple)):
        lines = list(text)
    else:
        lines = text.split("\n")
    result = []
    for line in lines:
        numbers = control_numbers(line)
        if numbers is not None and numbers[1:] == (mf, mt):
            result.append(line)
    return result


def first_difference(written, original):
    for k, (a, b) in enumerate(zip(written, original)):
        if a != b:
            return f"line {k + 1} of the section: {a!r} instead of {b!r}"
    return f"{len(written)} lines written instead of {len(original)}"


def values_equal(a, b, path=""):
    """Compare two parsed sections; return None or the first difference."""
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None and (isinstance(a, np.ndarray) or isinstance(b, np.ndarray)):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)):
            return f"{path}: {type(a).__name__} and {type(b).__name__}"
        if a.shape != b.shape or a.dtype != b.dtype:
            return f"{path}: arrays of {a.shape}/{a.dtype} and {b.shape}/{b.dtype}"
        if not np.array_equal(a, b, equal_nan=a.dtype.kind == "f"):
            return f"{path}: array values differ"
        return None
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b):
            return f"{path}: keys {list(a)[:5]} and {list(b)[:5]}"
        for key in a:
            diff = values_equal(a[key], b[key], f"{path}/{key}")
            if diff:
                return diff
        return None
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return f"{path}: lengths {len(a)} and {len(b)}"
        for k, (x, y) in enumerate(zip(a, b)):
            diff = values_equal(x, y, f"{path}/{k}")
            if diff:
                return diff
        return None
    if type(a) is not type(b):
        return f"{path}: {type(a).__name__} and {type(b).__name__}"
    if isinstance(a, float) and math.isnan(a) and math.isnan(b):
        return None
    if a != b:
        return f"{path}: {a!r} and {b!r}"
    return None


def make_parsers(which, njoy_number_forms):
    """Return a dict name -> parser class of the parsers to check."""
    from endf_parserpy import EndfParserPy

    classes = {}
    notes = []
    if which in ("py", "both"):
        classes["py"] = EndfParserPy
    if which in ("cpp", "both"):
        try:
            from endf_parserpy import EndfParserCpp

            EndfParserCpp(endf_format="gendf")
            classes["cpp"] = EndfParserCpp
        except Exception as exc:  # module not built or not importable
            if which == "cpp":
                raise
            notes.append(f"EndfParserCpp not checked: {exc}")
    if njoy_number_forms:
        options = dict(prefer_noexp=True, standard_form_on_tie=True)
    else:
        options = dict(preserve_value_strings=True)
    parsers = {
        name: cls(endf_format="gendf", **options) for name, cls in classes.items()
    }
    return classes, parsers, notes


def check_file(path, classes, parsers, compare_parsers, array_types):
    """Check one file; return the summary line and the details."""
    with open(path, "r", encoding="latin-1", newline="") as fh:
        text = fh.read()
    tpid, materials = split_tape(text)
    counts = Counter()
    details = []
    nsections = sum(len(m[1]) for m in materials)
    for position, (mat, sections) in enumerate(materials):
        seen = Counter((mf, mt) for mf, mt, _ in sections)
        for (mf, mt), n in seen.items():
            if n > 1:
                counts["duplicate"] += n
                details.append(
                    f"note: material {position} (MAT {mat}): MF{mf}/MT{mt} "
                    f"appears {n} times (each checked on its own)"
                )
        for mf, mt, lines in sections:
            where = f"material {position} (MAT {mat}) MF{mf}/MT{mt}"
            tape = section_tape(tpid, mat, mf, mt, lines)
            for name, parser in parsers.items():
                try:
                    written = parser.write(parser.parse(tape))
                except Exception as exc:
                    counts[f"{name}:error"] += 1
                    msg = str(exc).strip().splitlines()
                    details.append(
                        f"{where} [{name}] {type(exc).__name__}: "
                        f"{msg[0] if msg else ''}"
                    )
                    continue
                out = written_section_lines(written, mf, mt)
                if out != lines:
                    counts[f"{name}:diff"] += 1
                    details.append(f"{where} [{name}] " + first_difference(out, lines))
            if compare_parsers and len(classes) == 2:
                for array_type in array_types:
                    try:
                        dicts = [
                            cls(endf_format="gendf", array_type=array_type).parse(tape)
                            for cls in classes.values()
                        ]
                        diff = values_equal(dicts[0], dicts[1])
                    except Exception as exc:
                        diff = f"{type(exc).__name__}: {exc}"
                    if diff:
                        counts[f"equal-{array_type}:diff"] += 1
                        details.append(f"{where} [py/cpp {array_type}] {diff}")
    # sections with the same MF/MT are checked one by one; they are
    # reported, but not counted as a failure of the round trip
    failed = sum(v for k, v in counts.items() if k != "duplicate")
    parts = [f"materials {len(materials)}", f"sections {nsections}"]
    for name in parsers:
        parts.append(
            f"{name}: errors {counts[name + ':error']}, "
            f"differing {counts[name + ':diff']}"
        )
    if compare_parsers and len(classes) == 2:
        for array_type in array_types:
            parts.append(
                f"py=cpp {array_type}: differing {counts['equal-' + array_type + ':diff']}"
            )
    if counts["duplicate"]:
        parts.append(f"duplicate MF/MT sections {counts['duplicate']}")
    status = "FAIL" if failed else "OK"
    return status, f"{status} {path}: " + "; ".join(parts), details


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check the round trip of GENDF tapes with the gendf flavor."
    )
    ap.add_argument("files", nargs="+", help="GENDF tapes")
    ap.add_argument("--parser", choices=("py", "cpp", "both"), default="both")
    ap.add_argument(
        "--no-compare-parsers",
        action="store_true",
        help="do not compare the dictionaries of EndfParserPy and EndfParserCpp",
    )
    ap.add_argument(
        "--njoy-number-forms",
        action="store_true",
        help="write from the values (prefer_noexp, standard_form_on_tie) "
        "instead of preserving the text of the numbers",
    )
    args = ap.parse_args(argv)
    classes, parsers, notes = make_parsers(args.parser, args.njoy_number_forms)
    array_types = ["dict", "list"]
    try:
        import numpy  # noqa: F401

        array_types.append("numpy")
    except ImportError:
        notes.append("numpy mode not compared: NumPy is not installed")
    for note in notes:
        print("note:", note)
    nfail = 0
    for path in args.files:
        try:
            status, line, details = check_file(
                path, classes, parsers, not args.no_compare_parsers, array_types
            )
        except Exception as exc:
            status, line, details = (
                "FAIL",
                f"FAIL {path}: {type(exc).__name__}: {exc}",
                [],
            )
        print(line)
        for detail in details[:MAX_DETAILS]:
            print("   ", detail)
        if len(details) > MAX_DETAILS:
            print(f"    ... and {len(details) - MAX_DETAILS} more")
        nfail += status != "OK"
    print(f"{len(args.files) - nfail} of {len(args.files)} files OK")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
