############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/03
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Equivalence of the per-field and the bulk form of EndfParserCpp.

The float values of the bodies of TAB1 and LIST records are read either
field by field (the per-field form) or with a row kernel (the bulk form:
one kernel call per line of a TAB1 body; a LIST body decoded as a whole
before its values are delivered), depending on the row kernel selected
when the C++ module is loaded, which the environment variable
ENDF_PARSERPY_CPP_BULK_BODIES can force (see module_header_reading.hpp;
``off`` selects the per-field form).
The results must not depend on it: for every tier the CPU supports, the
parse results (values with their bits and types, the layout of the
arrays) and the errors (type and message) must be those of the
per-field form, in the array types numpy, list and dict and with the
options that matter for the conversion of float fields. Each tier runs
in a subprocess, as the environment variable is only read when the
module is loaded; this file is the script run by the subprocesses.

The inputs are the test data of the repository and variants of them in
a temporary directory: fields of the bodies replaced by fields of other
forms (D exponents, spaces, decimal exponents below -22, values that
overflow, blanks, malformed fields) and shortened lines.
"""

import hashlib
import importlib
import json
import os
import random
import struct
import subprocess
import sys
from pathlib import Path
import pytest


ENV_VAR = "ENDF_PARSERPY_CPP_BULK_BODIES"
VECTOR_TIERS = ("avx2", "avx512")
TESTDATA = Path(__file__).parent / "testdata"
FILES = [
    "n_2925_29-Cu-63.endf",
    "tsl_Al.endf",
    "dec-094_Pu_244.endf",
]
ARRAY_TYPES = ("numpy", "list", "dict")
OPTION_SETS = (
    {},
    {"preserve_value_strings": True},
    {"accept_d_exponent": False},
    {"accept_spaces": False, "accept_nan_inf": False},
)
# fields of other forms than the two most common layouts
FIELD_VARIANTS = (
    " 1.234567D+0",
    "1.234567d-1",
    " 1.234 56+0",
    "  1.234-  5",
    " 1.23456-30",
    "-4.3709-320",
    " 1.0000+400",
    "-1.0000+400",
    "        nan",
    "       -inf",
    "           ",
    "-0.000000+0",
    "12345678901",
    "1.2345678+0",
    "+1.23456+10",
    "1.0e+0005  ",
    "   1.E5    ",
    "1.23x456+00",
    "abcdefghijk",
    "  .        ",
    "1.234567+ 1",
)


# ---------------------------------------------------------------------
# the subprocess


def _feed(h, obj):
    # a canonical serialization of a parse result into the hash h: the
    # types, the bits of floats, numpy arrays with dtype, shape and bytes
    if isinstance(obj, dict):
        h.update(b"D%d;" % len(obj))
        for k, v in obj.items():
            _feed(h, k)
            _feed(h, v)
    elif isinstance(obj, (list, tuple)):
        h.update(b"L%d;" % len(obj) if isinstance(obj, list) else b"T%d;" % len(obj))
        for v in obj:
            _feed(h, v)
    elif isinstance(obj, bool):
        h.update(b"B1;" if obj else b"B0;")
    elif isinstance(obj, int):
        h.update(b"I%d;" % obj)
    elif isinstance(obj, float):
        h.update(b"F" + struct.pack("<d", obj))
    elif isinstance(obj, str):
        b = obj.encode("utf-8", "surrogatepass")
        h.update(b"S%d;" % len(b) + b)
    elif obj is None:
        h.update(b"N;")
    elif type(obj).__name__ == "ndarray":
        h.update(b"A" + obj.dtype.str.encode() + repr(obj.shape).encode())
        if obj.dtype.kind == "O":
            for v in obj.ravel():
                _feed(h, v)
        else:
            h.update(obj.tobytes())
    elif hasattr(obj, "get_original_string"):
        h.update(b"E" + type(obj).__name__.encode())
        _feed(h, float(obj))
        _feed(h, obj.get_original_string())
    else:
        h.update(b"O" + type(obj).__name__.encode() + repr(obj).encode())


def _digest(obj):
    h = hashlib.sha256()
    _feed(h, obj)
    return h.hexdigest()


def _worker(spec_path, out_path):
    from endf_parserpy import EndfParserCpp

    with open(spec_path) as f:
        jobs = json.load(f)
    module = None
    with open(out_path, "w") as out:
        for job in jobs:
            parser = EndfParserCpp(array_type=job["array_type"], **job["options"])
            if module is None:
                module = importlib.import_module(parser._parse_endf.__module__)
                info = module._bulk_body_info()
                out.write(json.dumps({"info": info}) + "\n")
            before = module._bulk_body_info()["bulk_list_bodies"]
            try:
                res = parser.parsefile(job["file"])
                rec = {"digest": _digest(res)}
            except Exception as exc:  # noqa: BLE001 (any error is compared)
                rec = {"error": type(exc).__name__ + ": " + str(exc)}
            rec["job"] = job["key"]
            # the LIST bodies of this job by the way they were read
            after = module._bulk_body_info()["bulk_list_bodies"]
            rec["bodies"] = {k: after[k] - before[k] for k in after}
            out.write(json.dumps(rec) + "\n")
            out.flush()
        info = module._bulk_body_info()
        out.write(json.dumps({"final_info": info}) + "\n")


# ---------------------------------------------------------------------
# the test


def _body_lines(lines):
    # lines that are not the first line of a section (often bodies of
    # records) and have six numeric fields; positions of these lines
    result = []
    for i, line in enumerate(lines):
        if len(line) < 75 or i == 0:
            continue
        if lines[i - 1][70:75] != line[70:75]:
            continue
        fields = [line[11 * j : 11 * j + 11] for j in range(6)]
        if all(("." in f) or f.strip().lstrip("+-").isdigit() for f in fields):
            if any("." in f for f in fields):
                result.append(i)
    return result


def _make_variants(tmpdir):
    # variants of the test files with fields of other forms, each in its
    # own file, and shortened lines
    rng = random.Random(20261103)
    variants = []
    for name in ("tsl_Al.endf", "dec-094_Pu_244.endf", "n_2925_29-Cu-63.endf"):
        text = (TESTDATA / name).read_text()
        lines = text.split("\n")
        body = _body_lines(lines)
        # lines of float values only (bodies of TAB1 and LIST records)
        float_body = [
            i
            for i in body
            if all("." in lines[i][11 * j : 11 * j + 11] for j in range(6))
        ]
        nvar = 6 if name.startswith("n_") else 30
        for k in range(nvar):
            new = list(lines)
            nmut = 1 if k % 3 else 3
            for _ in range(nmut):
                i = rng.choice(float_body if rng.random() < 0.75 else body)
                j = rng.randrange(6)
                field = rng.choice(FIELD_VARIANTS)
                line = new[i]
                new[i] = line[: 11 * j] + field[:11].ljust(11) + line[11 * j + 11 :]
            path = tmpdir / f"{Path(name).stem}_var{k:02d}.endf"
            path.write_text("\n".join(new))
            variants.append(path)
        # a body line cut after 40 columns, and one after 10 columns
        for cut in (40, 10):
            new = list(lines)
            i = body[len(body) // 2]
            new[i] = new[i][:cut]
            path = tmpdir / f"{Path(name).stem}_cut{cut}.endf"
            path.write_text("\n".join(new))
            variants.append(path)
    return variants


def _jobs(tmpdir):
    jobs = []
    for name in FILES:
        for array_type in ARRAY_TYPES:
            for k, opts in enumerate(OPTION_SETS):
                jobs.append(
                    {
                        "key": f"{name}|{array_type}|{k}",
                        "file": str(TESTDATA / name),
                        "array_type": array_type,
                        "options": opts,
                    }
                )
    for path in _make_variants(tmpdir):
        for array_type in ARRAY_TYPES:
            for k, opts in enumerate(OPTION_SETS):
                if array_type != "numpy" and k == 1:
                    continue
                jobs.append(
                    {
                        "key": f"{path.name}|{array_type}|{k}",
                        "file": str(path),
                        "array_type": array_type,
                        "options": opts,
                    }
                )
    return jobs


@pytest.fixture(scope="module")
def jobs_spec(tmp_path_factory):
    pytest.importorskip("numpy")
    try:
        from endf_parserpy import EndfParserCpp

        EndfParserCpp()
    except ImportError:
        pytest.skip("the C++ modules are not available")
    tmpdir = tmp_path_factory.mktemp("float_row_kernel")
    jobs = _jobs(tmpdir)
    spec = tmpdir / "jobs.json"
    spec.write_text(json.dumps(jobs))
    return spec, tmpdir


def _run(spec, tmpdir, value):
    env = dict(os.environ)
    env[ENV_VAR] = value
    out = tmpdir / f"results_{value}.jsonl"
    res = subprocess.run(
        [sys.executable, __file__, str(spec), str(out)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    records = [json.loads(s) for s in out.read_text().splitlines()]
    info = records[0]["info"]
    final_info = records[-1]["final_info"]
    results = {r["job"]: r.get("digest", r.get("error")) for r in records[1:-1]}
    return info, final_info, results


@pytest.fixture(scope="module")
def per_field_results(jobs_spec):
    spec, tmpdir = jobs_spec
    info, _, results = _run(spec, tmpdir, "off")
    assert info["selected"] == "off"
    return results


@pytest.mark.parametrize("tier", ("scalar",) + VECTOR_TIERS)
def test_bulk_form_equals_per_field_form(tier, jobs_spec, per_field_results):
    spec, tmpdir = jobs_spec
    info, final_info, results = _run(spec, tmpdir, tier)
    if info["selected"] != tier:
        pytest.skip(f"tier {tier} not available here: {info['warning']}")
    if tier == "scalar":
        # the bulk form was used
        assert final_info["scalar_kernel_lines"] > 0
    # LIST bodies delivered by strided copies and by the code of the
    # per-field form, and conversions that stopped before the end
    counts = final_info["bulk_list_bodies"]
    assert counts["strided"] > 0 and counts["looped"] > 0 and counts["stopped"] > 0
    assert results.keys() == per_field_results.keys()
    mismatches = [k for k in results if results[k] != per_field_results[k]]
    assert mismatches == [], "\n".join(
        f"{k}:\n  off: {per_field_results[k]}\n  {tier}: {results[k]}"
        for k in mismatches[:10]
    )
    # the variants exercise the errors and the values of the other forms
    errors = [k for k, v in results.items() if not _is_digest(v)]
    assert len(errors) > 10 and len(errors) < len(results) - 10


def _is_digest(value):
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _info_in_subprocess(value):
    env = dict(os.environ)
    if value is None:
        env.pop(ENV_VAR, None)
    else:
        env[ENV_VAR] = value
    code = (
        "import importlib, json, warnings\n"
        "with warnings.catch_warnings(record=True) as w:\n"
        "    warnings.simplefilter('always')\n"
        "    m = importlib.import_module('endf_parserpy.cpp_parsers.endf6_ext')\n"
        "print(json.dumps({'info': m._bulk_body_info(),"
        " 'warnings': [str(x.message) for x in w]}))\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return json.loads(res.stdout.splitlines()[-1])


@pytest.mark.parametrize(
    "value", [None, "", "auto", "AUTO", "off", "scalar", "avx2", "avx512", "bogus"]
)
def test_row_kernel_selection(value, jobs_spec):
    out = _info_in_subprocess(value)
    info, warnings = out["info"], out["warnings"]
    tiers = info["tiers"]
    assert info["variable"] == ENV_VAR
    assert info["requested"] == value
    assert set(tiers) == {"scalar", "avx2", "avx512"}
    assert tiers["scalar"] == {"built": True, "supported": True, "vector": False}
    # a tier is only selected if it is built and supported by the CPU
    selected = info["selected"]
    assert selected == "off" or (
        tiers[selected]["built"] and tiers[selected]["supported"]
    )
    auto = next(
        (
            name
            for name in ("avx512", "avx2")
            if tiers[name]["built"] and tiers[name]["supported"]
        ),
        "scalar",
    )
    # all LIST bodies in the bulk form with a vector tier or a forced tier
    forced = (
        value not in (None, "", "auto", "AUTO", "off", "bogus") and selected == value
    )
    assert info["bulk_all_list_bodies"] == (
        selected != "off" and (forced or tiers[selected]["vector"])
    )
    if value in (None, "", "auto", "AUTO"):
        assert selected == auto and info["warning"] is None and warnings == []
    elif value in ("off", "scalar"):
        assert selected == value and info["warning"] is None and warnings == []
    elif value in VECTOR_TIERS:
        if tiers[value]["built"] and tiers[value]["supported"]:
            assert selected == value and warnings == []
        else:
            assert selected == auto
            assert len(warnings) == 1 and info["warning"] in warnings[0]
    else:
        assert selected == auto
        assert len(warnings) == 1 and "unknown value" in warnings[0]
    # the CPU features are consistent with the support of the tiers
    cpu = info["cpu"]
    if tiers["avx512"]["supported"]:
        assert tiers["avx2"]["supported"]
    if tiers["avx2"]["supported"]:
        assert cpu["detected"] and cpu["avx2"] and cpu["fma"] and cpu["os_ymm"]


if __name__ == "__main__":
    _worker(sys.argv[1], sys.argv[2])
