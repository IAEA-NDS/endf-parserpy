############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/07
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Measure the read/write throughput of endf-parserpy on a directory of
ENDF-6 files.

The script measures what a user gets from the installed package:
sequential wall-clock time of ``parsefile`` over all files and of
``write`` back to ENDF-6 text, in one process, with a warm file cache
(one untimed warm-up pass reads every file first), reporting the best
of ``--rounds`` timed rounds. The numbers of the Performance section of
the README are produced with this script; it prints the sentence
ready to paste.

This is deliberately different from ``tools/benchmark_bulk_bodies.py``,
which is a development harness: it builds two refs into separate
environments and times them interleaved to give reliable *ratios*.
This script times only the installed package and gives *absolute*
throughput.

Usage:
    python tools/benchmark_throughput.py <directory-with-endf-files> [--rounds N]

Example (ENDF/B-VIII.1 neutron sublibrary):
    python tools/benchmark_throughput.py ~/data/endfb8.1/neutrons-version.VIII.1

For reproducible numbers: run on an idle machine on AC power. The file
cache is deliberately warm, so the result measures parsing and writing,
not disk speed. Report the endf-parserpy version, the Python version
and the CPU model together with the numbers; the script prints all of
them, including which installation of ``endf_parserpy`` it imported
(run it from a directory that does not contain an ``endf_parserpy``
source tree, which would shadow the installed package).
"""

import argparse
import os
import platform
import sys
import time


def cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def main():
    cli = argparse.ArgumentParser(
        description="Measure endf-parserpy read/write throughput."
    )
    cli.add_argument("datadir", help="directory containing .endf files")
    cli.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="timed rounds; the best is reported (default 2)",
    )
    args = cli.parse_args()

    import endf_parserpy
    from endf_parserpy import EndfParserCpp

    files = sorted(
        os.path.join(args.datadir, f)
        for f in os.listdir(args.datadir)
        if f.endswith(".endf")
    )
    if not files:
        sys.exit(f"no .endf files found in {args.datadir}")
    total_bytes = sum(os.path.getsize(f) for f in files)
    mb = total_bytes / 1e6

    parser = EndfParserCpp(array_type="numpy")

    print(
        f"endf-parserpy {endf_parserpy.__version__} "
        f"(from {os.path.dirname(endf_parserpy.__file__)}), "
        f"Python {platform.python_version()}, {platform.system()}"
    )
    print(f"CPU: {cpu_model()}")
    print(f"files: {len(files)}, size: {mb:.0f} MB (1 MB = 1e6 bytes)")
    print(
        f"parser: EndfParserCpp(array_type='numpy'), "
        f"{args.rounds} timed round(s) after one warm-up pass"
    )

    # warm-up: warms the file cache and the parser; results discarded
    for f in files:
        parser.parsefile(f)

    best_parse = best_write = float("inf")
    for rnd in range(1, args.rounds + 1):
        t0 = time.perf_counter()
        dicts = [parser.parsefile(f) for f in files]
        parse_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        for d in dicts:
            parser.write(d)
        write_s = time.perf_counter() - t0
        del dicts

        print(
            f"round {rnd}: parse {parse_s:6.2f} s ({mb / parse_s:5.0f} MB/s)"
            f" | write {write_s:6.2f} s ({mb / write_s:5.0f} MB/s)"
        )
        best_parse = min(best_parse, parse_s)
        best_write = min(best_write, write_s)

    print()
    print(
        f"best: parse {best_parse:.2f} s = {mb / best_parse:.0f} MB/s, "
        f"write {best_write:.2f} s = {mb / best_write:.0f} MB/s"
    )
    print()
    print("README sentence:")
    print(
        f"  reads {len(files)} files ({mb / 1000:.1f} GB) in about "
        f"{best_parse:.1f} seconds and writes them back to ENDF-6 text "
        f"in about {best_write:.0f} seconds "
        f"(single core, {cpu_model()}, warm file cache, "
        f"version {endf_parserpy.__version__})."
    )


if __name__ == "__main__":
    main()
