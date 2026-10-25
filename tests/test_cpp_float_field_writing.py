############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Equivalence of the float fields written by EndfParserCpp with the
iostream based conversion.

The function cpp_write_field_double_at of the C++ templates writes the 11
characters of a float field into a line; most values are written by
cpp_float_field_fast, which composes the characters directly, the others
by the general conversion. The C++ program
tests/cpp/float_field_writing_equivalence.cpp compares the characters
written into the line, extracted from the template as it ships, with a
frozen copy of the iostream based conversion that the writer used before,
for all combinations of the options abuse_signpos, keep_E, skip_intzero
and prefer_noexp.

test_float_field_writing_sampled runs by default on a sample of values
(values close to rounding ties and to a carry into the next decade at
every precision and decimal exponent, decade boundaries, special values,
random decimal numbers and random bit patterns).
test_float_field_writing_exhaustive checks 2 * 10**7 random values; it
takes minutes and only runs with the option --run-exhaustive. Both tests
are skipped if no C++ compiler is found (environment variable CXX,
otherwise c++, g++ or clang++).
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import pytest
import endf_parserpy.compiler.cpp_templates as cpp_templates


TEST_SOURCE = Path(__file__).parent / "cpp" / "float_field_writing_equivalence.cpp"
TEMPLATE = Path(cpp_templates.__file__).parent / "module_header_writing.hpp"

INCLUDES = """#include <algorithm>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
"""


def _find_compiler():
    cxx = os.environ.get("CXX")
    if cxx:
        cmd = shlex.split(cxx)
        if cmd and shutil.which(cmd[0]):
            return cmd
    for name in ("c++", "g++", "clang++"):
        path = shutil.which(name)
        if path:
            return [path]
    return None


def _extract(text, start, end="\n}\n", after=None):
    i = text.find(start)
    assert i != -1, (
        f"`{start}` not found in module_header_writing.hpp; "
        "update the markers in this test"
    )
    j = text.find(after, i) if after else i
    assert j != -1, f"`{after}` not found in module_header_writing.hpp"
    k = text.find(end, j)
    assert k != -1
    return text[i : k + len(end)]


def _extract_writer():
    # the options, the integer formatting and the code from the float
    # formatting functions to the end of cpp_write_field_double_at, as
    # they are in the template
    text = TEMPLATE.read_text()
    parts = [
        _extract(text, "struct WritingOptions {", end="\n};\n"),
        _extract(text, "inline int cpp_int_to_padded_chars("),
        _extract(
            text,
            "inline void normalize_exponent(",
            after="inline void cpp_write_field_double_at(",
        ),
    ]
    return "\n\n".join(parts)


@pytest.fixture(scope="module")
def field_test_program(tmp_path_factory):
    compiler = _find_compiler()
    if compiler is None:
        pytest.skip("no C++ compiler found (set CXX or install c++, g++ or clang++)")
    workdir = tmp_path_factory.mktemp("float_field_writing")
    header = workdir / "float_field_under_test.hpp"
    header.write_text(
        "// extracted from module_header_writing.hpp by the test\n"
        + INCLUDES
        + "\n"
        + _extract_writer()
    )
    exe = workdir / "float_field_writing_equivalence"
    cmd = compiler + [
        "-O2",
        "-std=c++11",
        "-I",
        str(workdir),
        str(TEST_SOURCE),
        "-o",
        str(exe),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, "compilation failed:\n" + res.stdout + res.stderr
    return exe


def _run(exe, *args):
    res = subprocess.run([str(exe), *args], capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def test_float_field_writing_sampled(field_test_program):
    rc, out = _run(field_test_program, "sampled")
    assert rc == 0 and "mismatches=0" in out, out
    # the fast path must handle a good part of the values, which include
    # many values close to rounding ties and carries that it leaves to the
    # general conversion
    m = re.search(r"finite=(\d+) fast=(\d+)", out)
    assert m is not None, out
    assert int(m.group(2)) * 10 > int(m.group(1)), out


@pytest.mark.exhaustive
def test_float_field_writing_exhaustive(field_test_program):
    jobs = [("random", "5000000", str(seed)) for seed in range(1, 5)]
    if hasattr(os, "sched_getaffinity"):
        ncpu = len(os.sched_getaffinity(0))
    else:
        ncpu = os.cpu_count() or 1
    workers = max(1, min(len(jobs), ncpu))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda job: _run(field_test_program, *job), jobs))
    failed = [out for rc, out in results if rc != 0 or "mismatches=0" not in out]
    assert failed == [], "\n".join(failed)
