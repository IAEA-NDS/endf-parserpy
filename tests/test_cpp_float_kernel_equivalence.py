############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Equivalence of the conversion of float fields with its previous version.

The function cpp_fast_field_to_double of the C++ templates converts the 11
characters of a float field; a first stage handles the two most common
layouts of float fields with integer operations. The C++ program
tests/cpp/float_kernel_equivalence.cpp compares the function as it ships,
extracted from the template, with a frozen copy of the function before the
first stage was added: the decision whether a field is converted or left to
the general path and the bits of the double must agree for every field.

test_float_kernel_sampled runs by default on a sample of fields (every byte
value at every position of a few hundred valid fields, a few million random
fields and special cases). test_float_kernel_exhaustive enumerates all
strings of both layouts, every byte value at every position of 20,000
fields and 10**9 random fields; it takes minutes and only runs with the
option --run-exhaustive. Both tests are skipped if no C++ compiler is
found (environment variable CXX, otherwise c++, g++ or clang++).
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import pytest
import endf_parserpy.compiler.cpp_templates as cpp_templates


TEST_SOURCE = Path(__file__).parent / "cpp" / "float_kernel_equivalence.cpp"
TEMPLATE = Path(cpp_templates.__file__).parent / "module_header_reading.hpp"

KERNEL_START = "#if defined(__BYTE_ORDER__) && defined(__ORDER_LITTLE_ENDIAN__)"
KERNEL_FUNCTION = "inline bool cpp_fast_field_to_double("


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


def _extract_kernel():
    # the code from the endianness check before the first stage to the end
    # of cpp_fast_field_to_double, as it is in the template
    text = TEMPLATE.read_text()
    start = text.find(KERNEL_START)
    func = text.find(KERNEL_FUNCTION)
    assert start != -1 and func > start, (
        "conversion kernel not found in module_header_reading.hpp; "
        "update the markers in this test"
    )
    end = text.find("\n}\n", func)
    assert end != -1
    return text[start : end + 3]


@pytest.fixture(scope="module")
def kernel_test_program(tmp_path_factory):
    compiler = _find_compiler()
    if compiler is None:
        pytest.skip("no C++ compiler found (set CXX or install c++, g++ or clang++)")
    workdir = tmp_path_factory.mktemp("float_kernel")
    header = workdir / "float_kernel_under_test.hpp"
    header.write_text(
        "// extracted from module_header_reading.hpp by the test\n"
        "#include <cstdint>\n#include <cstring>\n\n" + _extract_kernel()
    )
    exe = workdir / "float_kernel_equivalence"
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


def test_float_kernel_sampled(kernel_test_program):
    rc, out = _run(kernel_test_program, "sampled")
    assert rc == 0 and "mismatches=0" in out, out


@pytest.mark.exhaustive
def test_float_kernel_exhaustive(kernel_test_program):
    jobs = [("exhaustive", str(i)) for i in range(3)]
    jobs += [("boundary", "20000")]
    jobs += [("random", "250000000", str(seed)) for seed in range(1, 5)]
    if hasattr(os, "sched_getaffinity"):
        ncpu = len(os.sched_getaffinity(0))
    else:
        ncpu = os.cpu_count() or 1
    workers = max(1, min(len(jobs), ncpu))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda job: _run(kernel_test_program, *job), jobs))
    failed = [out for rc, out in results if rc != 0 or "mismatches=0" not in out]
    assert failed == [], "\n".join(failed)
