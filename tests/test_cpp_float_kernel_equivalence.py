############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/24
# Last modified:   2026/10/25
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
The exception are fields with a decimal exponent below -22, which the
previous version left to std::strtod and which are now converted exactly
(cpp_decimal_to_double_negexp): for the fields the previous version does
not convert, the field must be converted if and only if the previous
version accepts its form and the decimal exponent is below -22, with the
bits of the std::strtod result. cpp_decimal_to_double_negexp is also
compared with std::strtod directly, for all decimal exponents from -360
to 30, and on near-halfway cases (decimal
numbers next to the midpoint between two adjacent doubles) generated here
with exact integer arithmetic, also as fields; for these, the bits must
also agree with the conversion of Python.

test_float_kernel_sampled runs by default on a sample of fields (every byte
value at every position of a few hundred valid fields, a few million random
fields and special cases, and about 1.5 million significands for the
direct comparison). test_float_kernel_halfway runs by default on the
near-halfway cases. test_float_kernel_exhaustive enumerates all strings of
both layouts of the first stage and of the layout d.dddd+ddd with
three-digit exponents, every byte value at every position of 20,000
fields, 10**9 random fields and about 10**9 significands for the direct
comparison; it takes minutes and only runs with the option
--run-exhaustive. The tests are skipped if no C++ compiler is found
(environment variable CXX, otherwise c++, g++ or clang++).
"""

from concurrent.futures import ThreadPoolExecutor
import math
import os
import random
import struct
from pathlib import Path
import shlex
import shutil
import subprocess
import pytest
import endf_parserpy.compiler.cpp_templates as cpp_templates


TEST_SOURCE = Path(__file__).parent / "cpp" / "float_kernel_equivalence.cpp"
TEMPLATE = Path(cpp_templates.__file__).parent / "module_header_reading.hpp"

KERNEL_START = (
    "// Exact conversion of mant * 10^k for decimal exponents k below -22, the"
)
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
    # the code from cpp_decimal_to_double_negexp (with its table and helpers)
    # to the end of cpp_fast_field_to_double, as it is in the template
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


def _bits(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def _halfway_doubles(rng):
    # pairs of adjacent non-negative doubles below 1e-14 (as integers of
    # their bits): around the limits of the subnormal range, at powers of
    # ten and at random exponents
    starts = [0, 1, 2, 0x000FFFFFFFFFFFFE, 0x000FFFFFFFFFFFFF, 0x0010000000000000]
    starts += [_bits(10.0**e) for e in range(-323, -14)]
    starts += [rng.randrange(0, _bits(1e-14)) for _ in range(2500)]
    starts += [rng.randrange(0, 0x0010000000000000) for _ in range(500)]
    return starts


def _fraction_of_bits(b):
    # exact value of the double with bits b (b < 2**63) as numerator and
    # power of two
    e, m = b >> 52, b & ((1 << 52) - 1)
    if e == 0:
        return m, -1074
    return m | (1 << 52), e - 1075


def _halfway_lines(seed=1):
    # decimal numbers with 1 to 19 digits next to the midpoint of two
    # adjacent doubles: the two neighbours of the midpoint with n digits,
    # as "W <significand> <k> <bits of the correctly rounded value>" lines
    # and, with 5 and 6 digits, as fields in the layouts d.dddd+ddd and
    # d.ddddd+dd
    rng = random.Random(seed)
    lines = []
    for b in _halfway_doubles(rng):
        m, e = _fraction_of_bits(b)
        # midpoint (2m+1) * 2^(e-1) as num / den
        num, den = 2 * m + 1, 1
        if e - 1 >= 0:
            num <<= e - 1
        else:
            den <<= 1 - e
        mag = math.floor(math.log10(num) - math.log10(den))
        for n in range(1, 20):
            k = mag - n + 1
            for kk in (k - 1, k, k + 1):
                # floor(midpoint / 10^kk)
                if kk >= 0:
                    lo = num // (den * 10**kk)
                else:
                    lo = num * 10 ** (-kk) // den
                for mant in (lo, lo + 1):
                    if not 0 < mant < 2**64 or len(str(mant)) != n:
                        continue
                    value = float("%de%d" % (mant, kk))
                    lines.append("W %d %d %x" % (mant, kk, _bits(value)))
                    s = str(mant)
                    x = kk + n - 1
                    for sign in (" ", "-"):
                        if n == 5 and abs(x) <= 999:
                            lines.append(
                                "F %s%s.%s%s%03d"
                                % (sign, s[0], s[1:], "-" if x < 0 else "+", abs(x))
                            )
                        if n == 6 and abs(x) <= 99:
                            lines.append(
                                "F %s%s.%s%s%02d"
                                % (sign, s[0], s[1:], "-" if x < 0 else "+", abs(x))
                            )
    return lines


def test_float_kernel_halfway(kernel_test_program, tmp_path):
    lines = _halfway_lines()
    path = tmp_path / "halfway_cases.txt"
    path.write_text("\n".join(lines) + "\n")
    rc, out = _run(kernel_test_program, "list", str(path))
    assert rc == 0 and "mismatches=0" in out, out


@pytest.mark.exhaustive
def test_float_kernel_exhaustive(kernel_test_program):
    jobs = [("exhaustive", str(i)) for i in range(3)]
    jobs += [("exhaustive3", str(i)) for i in range(3)]
    jobs += [("boundary", "20000")]
    jobs += [("random", "250000000", str(seed)) for seed in range(1, 5)]
    jobs += [("negexp", "400000", str(seed)) for seed in range(1, 5)]
    if hasattr(os, "sched_getaffinity"):
        ncpu = len(os.sched_getaffinity(0))
    else:
        ncpu = os.cpu_count() or 1
    workers = max(1, min(len(jobs), ncpu))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda job: _run(kernel_test_program, *job), jobs))
    failed = [out for rc, out in results if rc != 0 or "mismatches=0" not in out]
    assert failed == [], "\n".join(failed)
