############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/03
# Last modified:   2026/11/07
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Interleaved parse timing of two builds and of the row kernel tiers.

usage:
  python tools/benchmark_bulk_bodies.py prepare --data-dir <checkout> \\
      --out-dir <dir>
  python tools/benchmark_bulk_bodies.py run --base-python <python> \\
      --new-python <python> --files <file>... --out <results.json> \\
      [--rounds 11] [--reps 3] [--summary <summary.md>]
  python tools/benchmark_bulk_bodies.py merge --out <merged.json> \\
      [--summary <summary.md>] <results.json>...
  python tools/benchmark_bulk_bodies.py equivalence --tests <tests dir> \\
      --work-dir <dir> [--mode sampled] [--summary <summary.md>]

``prepare`` checks the zip archives of ``DATA_FILES`` in a checkout of the
data repository IAEA-NDS/ENDF-PENDF-File (each must be a zip archive, not
a Git LFS pointer, with exactly one ENDF file) and writes their ENDF files
to ``<dir>/<name>.endf``, e.g. ``Fe56.endf``.

``run`` parses each file in the array types numpy, list and dict with
EndfParserCpp, in fresh processes of the two Python interpreters (e.g. of
two virtual environments, one with the base build of the package and one
with the build under test):

- ``base``: the base build, ENDF_PARSERPY_CPP_BULK_BODIES unset;
- ``new``: the build under test, ENDF_PARSERPY_CPP_BULK_BODIES unset;
- ``new:<tier>``: the build under test with ENDF_PARSERPY_CPP_BULK_BODIES
  set to each tier the CPU supports there (``off``, ``scalar`` and the
  vector tiers that are built and supported).

The variants are run one after the other in each round, in an order that
is rotated from round to round (interleaved, so that a drift of the
machine affects all variants alike). Each process parses the file once
(warm-up) and then ``--reps`` times; its time is the minimum of these
(``time.thread_time``, the CPU time of the parsing thread only; on
Windows ``time.perf_counter``, because the resolution of the CPU clocks
there is about 15.6 ms, which measures a fast parse as zero). The CPU
time of the whole process is not used: importing numpy starts the thread
pool of its BLAS library, whose idle threads spin for a while, and their
CPU time would be added to fast parses (seen on many-core runners). The
workers also run with one BLAS/OpenMP thread. The result per variant is the median over the
rounds of the ratio of its time to the time of ``base`` in the same
round; with ``base`` against itself (``base:aa``, a second process of the
base build) as the noise floor. The JSON file contains the CPU
information of the machine, the selected tiers and all times; the summary
is a Markdown table (for ``$GITHUB_STEP_SUMMARY``).

``merge`` combines the JSON files of several machines into one file and
one summary table.

``equivalence`` compiles the C++ test of the conversion kernels
(tests/cpp/float_kernel_equivalence.cpp with the header extracted from the
installed template, see tests/test_cpp_float_kernel_equivalence.py) with
the compiler of the machine and runs it (mode ``sampled`` by default):
every row kernel tier built and supported there must give the mask and
the bits of the conversion field by field. The compiler is the one of the
wheels: MSVC on Windows (found by setuptools, which must be installed),
otherwise CXX or c++, g++, clang++. Exits with status 1 on a mismatch.
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time


ENV_VAR = "ENDF_PARSERPY_CPP_BULK_BODIES"
MODES = ("numpy", "list", "dict")

# The ENDF files of the benchmark: short name -> zip archive in the data
# repository IAEA-NDS/ENDF-PENDF-File (.enf: ENDF, .pen: PENDF). The sparse
# checkout of .github/workflows/benchmark_bulk_bodies.yml must list the same
# archives. U233 is the covariance-heavy file (the repository has no U238).
# TODO: add a thermal scattering file (e.g. H in H2O) once the data
# repository has one.
DATA_FILES = {
    "Fe56": "ENDF-B-VIII.1/n/n-Fe56-2631.enf.zip",
    "H1": "ENDF-B-VIII.1/n/n-H1-0125.enf.zip",
    "U233": "ENDF-B-VIII.1/n/n-U233-9222.enf.zip",
    "Pu238": "ENDF-B-VIII.1/n/n-Pu238-9434.enf.zip",
}
ENDF_SUFFIXES = (".enf", ".endf")
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"

WORKER = r"""
import importlib, json, sys, time
from endf_parserpy import EndfParserCpp
path, mode, reps = sys.argv[1], sys.argv[2], int(sys.argv[3])
p = EndfParserCpp(array_type=mode)
mod = importlib.import_module(p._parse_endf.__module__)
# None for a build without _bulk_body_info (e.g. a base build before it)
info = mod._bulk_body_info() if hasattr(mod, "_bulk_body_info") else None
# CPU time of this thread only: the idle threads of numpy's BLAS thread
# pool spin for a while after numpy is imported, and the CPU time of the
# whole process (process_time) would include them. The resolution of the
# CPU clocks on Windows is about 15.6 ms, which measures a fast parse as
# zero; there the interleaved rounds and the median of the ratios absorb
# the noise of the wall clock
timer = time.perf_counter if sys.platform == "win32" else time.thread_time
p.parsefile(path)
ts = []
for _ in range(reps):
    t0 = timer()
    d = p.parsefile(path)
    ts.append(timer() - t0)
    del d
print(json.dumps({"times": ts, "info": info}))
"""


def _run_worker(python, value, path, mode, reps):
    env = dict(os.environ)
    # one thread for the BLAS and OpenMP libraries numpy may load, so that
    # no idle thread pool runs next to the parse
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        env[name] = "1"
    env.pop(ENV_VAR, None)
    if value is not None:
        env[ENV_VAR] = value
    res = subprocess.run(
        [python, "-c", WORKER, path, mode, str(reps)],
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"worker failed ({python}, {value}):\n{res.stderr}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def _check_endf_text(name, member, data):
    # the first lines of an ENDF file: at least 75 columns, MAT, MF and MT
    # in columns 67-75
    lines = data[:2000].decode("ascii", errors="replace").splitlines()[:3]
    for line in lines:
        try:
            ok = len(line) >= 75 and all(
                s.strip() and int(s) >= -1
                for s in (line[66:70], line[70:72], line[72:75])
            )
        except ValueError:
            ok = False
        if not ok:
            raise SystemExit(
                f"{name}: {member} does not look like an ENDF file "
                f"(line {line[:80]!r})"
            )


def cmd_prepare(args):
    import io
    import zipfile

    os.makedirs(args.out_dir, exist_ok=True)
    for name, rel in DATA_FILES.items():
        path = os.path.join(args.data_dir, rel)
        if not os.path.isfile(path):
            raise SystemExit(f"{rel}: not found in the checkout of the data repository")
        with open(path, "rb") as f:
            raw = f.read()
        if raw.startswith(LFS_POINTER):
            raise SystemExit(
                f"{rel}: is a Git LFS pointer, not the archive "
                f"(LFS object not fetched; check lfs: true of the checkout)"
            )
        if not raw.startswith(b"PK"):
            raise SystemExit(f"{rel}: not a zip archive (starts with {raw[:40]!r})")
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                members = [i for i in z.infolist() if not i.is_dir()]
                if len(members) != 1:
                    raise SystemExit(
                        f"{rel}: expected exactly one ENDF file in the archive, "
                        f"found {len(members)}: {[i.filename for i in members]}"
                    )
                member = members[0].filename
                if not member.lower().endswith(ENDF_SUFFIXES):
                    raise SystemExit(
                        f"{rel}: the file in the archive, {member}, "
                        f"is not an ENDF file (.enf or .endf)"
                    )
                data = z.read(members[0])
        except zipfile.BadZipFile as exc:
            raise SystemExit(f"{rel}: not a valid zip archive ({exc})")
        _check_endf_text(rel, member, data)
        out = os.path.join(args.out_dir, name + ".endf")
        with open(out, "wb") as f:
            f.write(data)
        print(f"{rel}: {member} -> {out} ({len(data)} bytes)")


def _label(path):
    # the name of a file in the tables: Fe56 for .../Fe56.endf
    base = os.path.basename(path)
    return base[: -len(".endf")] if base.endswith(".endf") else base


def _cpu_info():
    info = {"platform": platform.platform(), "machine": platform.machine()}
    try:
        if sys.platform.startswith("linux"):
            info["lscpu"] = subprocess.run(
                ["lscpu"], capture_output=True, text=True
            ).stdout
        elif sys.platform == "darwin":
            info["sysctl"] = subprocess.run(
                ["sysctl", "-a"], capture_output=True, text=True
            ).stdout
            info["sysctl"] = "\n".join(
                s
                for s in info["sysctl"].splitlines()
                if s.startswith("machdep.cpu")
                or s.startswith("hw.optional")
                or s.startswith("hw.ncpu")
            )
        elif sys.platform == "win32":
            info["processor"] = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-CimInstance Win32_Processor | Format-List Name,"
                    "Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed",
                ],
                capture_output=True,
                text=True,
            ).stdout
    except OSError as exc:
        info["error"] = str(exc)
    return info


def _variants(args):
    # the tiers available with the build under test
    probe = _run_worker(args.new_python, None, args.files[0], "numpy", 1)["info"]
    variants = [("base", args.base_python, None), ("base:aa", args.base_python, None)]
    variants.append(("new", args.new_python, None))
    if probe is not None:
        variants.append(("new:off", args.new_python, "off"))
        for name, tier in probe["tiers"].items():
            if tier["built"] and tier["supported"]:
                variants.append((f"new:{name}", args.new_python, name))
    return variants, probe


def _median_ratios(records, variants):
    table = {}
    for rec in records:
        key = (rec["file"], rec["mode"])
        table.setdefault(key, []).append(rec)
    result = {}
    for key, recs in table.items():
        result[key] = {}
        for name, _, _ in variants:
            # a base time of zero (a timer too coarse for the file)
            # cannot give a ratio
            ratios = [
                r["t"][name] / r["t"]["base"]
                for r in recs
                if name in r["t"] and r["t"]["base"] > 0
            ]
            if ratios:
                result[key][name] = (
                    statistics.median(ratios),
                    min(ratios),
                    max(ratios),
                )
    return result


def _summary(machine, variants, ratios, probe):
    names = [v[0] for v in variants if v[0] != "base"]
    lines = [f"### {machine}", ""]
    if probe is not None:
        lines.append(
            f"default row kernel of the build under test: `{probe['selected']}`; "
            f"tiers: "
            + ", ".join(
                f"{n} ({'built' if t['built'] else 'not built'}, "
                f"{'supported' if t['supported'] else 'not supported'})"
                for n, t in probe["tiers"].items()
            )
        )
        lines.append("")
    lines.append(
        "Median over rounds of the time ratio to `base` "
        "(lower is faster; `base:aa` is the noise floor):"
    )
    lines.append("")
    lines.append("| file | mode | " + " | ".join(names) + " |")
    lines.append("|---|---|" + "---|" * len(names))
    for (f, mode), r in sorted(ratios.items()):
        cells = [
            f"{r[n][0]:.3f} [{r[n][1]:.2f}..{r[n][2]:.2f}]" if n in r else ""
            for n in names
        ]
        lines.append(f"| {f} | {mode} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def cmd_run(args):
    variants, probe = _variants(args)
    records = []
    for rnd in range(args.rounds):
        for path in args.files:
            for mode in MODES:
                k = rnd % len(variants)
                order = variants[k:] + variants[:k]
                t = {}
                for name, python, value in order:
                    out = _run_worker(python, value, path, mode, args.reps)
                    t[name] = min(out["times"])
                records.append(
                    {"round": rnd, "file": _label(path), "mode": mode, "t": t}
                )
        print(f"round {rnd + 1}/{args.rounds} done", flush=True)
    ratios = _median_ratios(records, variants)
    machine = args.machine or platform.platform()
    result = {
        "machine": machine,
        "cpu": _cpu_info(),
        "bulk_body_info": probe,
        "variants": [v[0] for v in variants],
        "records": records,
        "ratios": {f"{f}|{m}": r for (f, m), r in ratios.items()},
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
    text = _summary(machine, variants, ratios, probe)
    print(text)
    if args.summary:
        with open(args.summary, "a") as f:
            f.write(text + "\n")


def cmd_merge(args):
    merged = []
    texts = []
    for path in args.inputs:
        with open(path) as f:
            res = json.load(f)
        merged.append(res)
        variants = [(n, None, None) for n in res["variants"]]
        ratios = {tuple(k.split("|")): v for k, v in res["ratios"].items()}
        texts.append(_summary(res["machine"], variants, ratios, res["bulk_body_info"]))
    with open(args.out, "w") as f:
        json.dump(merged, f, indent=1)
    text = "\n".join(texts)
    print(text)
    if args.summary:
        with open(args.summary, "a") as f:
            f.write(text + "\n")


def _compile_equivalence(tests, workdir):
    # the test program, with the compiler of the wheels of this platform
    source = os.path.join(tests, "cpp", "float_kernel_equivalence.cpp")
    sys.path.insert(0, tests)
    try:
        import test_cpp_float_kernel_equivalence as t
    finally:
        sys.path.pop(0)
    t.write_test_header(workdir)
    if sys.platform == "win32":
        from setuptools._distutils.ccompiler import new_compiler

        cc = new_compiler()
        cc.initialize()
        objs = cc.compile(
            [source],
            output_dir=workdir,
            include_dirs=[workdir],
            extra_postargs=["/O2", "/EHsc", "/std:c++14"],
        )
        cc.link_executable(objs, "float_kernel_equivalence", output_dir=workdir)
        name = "MSVC"
        exe = os.path.join(workdir, "float_kernel_equivalence.exe")
    else:
        cmd = t._find_compiler()
        if cmd is None:
            raise SystemExit("no C++ compiler found (set CXX)")
        exe = os.path.join(workdir, "float_kernel_equivalence")
        res = subprocess.run(
            cmd + ["-O2", "-std=c++11", "-I", workdir, source, "-o", exe],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise SystemExit("compilation failed:\n" + res.stdout + res.stderr)
        name = " ".join(cmd)
    version = ""
    if sys.platform != "win32":
        res = subprocess.run(cmd + ["--version"], capture_output=True, text=True)
        version = res.stdout.splitlines()[0] if res.stdout else ""
    return exe, f"{name} {version}".strip()


def cmd_equivalence(args):
    workdir = os.path.abspath(args.work_dir)
    os.makedirs(workdir, exist_ok=True)
    exe, compiler = _compile_equivalence(os.path.abspath(args.tests), workdir)
    t0 = time.perf_counter()
    res = subprocess.run([exe, args.mode], capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    out = (res.stdout + res.stderr).strip()
    ok = res.returncode == 0 and "mismatches=0" in out
    lines = [
        f"C++ kernel equivalence ({args.mode}, {compiler}, {elapsed:.0f} s, "
        f"{platform.machine()}): {'passed' if ok else 'FAILED'}",
        "",
        "```",
        *out.splitlines()[-25:],
        "```",
        "",
    ]
    text = "\n".join(lines)
    print(text)
    if args.summary:
        with open(args.summary, "a") as f:
            f.write(text + "\n")
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--data-dir", required=True)
    prepare.add_argument("--out-dir", required=True)
    run = sub.add_parser("run")
    run.add_argument("--base-python", required=True)
    run.add_argument("--new-python", required=True)
    run.add_argument("--files", nargs="+", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--rounds", type=int, default=11)
    run.add_argument("--reps", type=int, default=3)
    run.add_argument("--machine", default=None)
    run.add_argument("--summary", default=None)
    merge = sub.add_parser("merge")
    merge.add_argument("--out", required=True)
    merge.add_argument("--summary", default=None)
    merge.add_argument("inputs", nargs="+")
    equiv = sub.add_parser("equivalence")
    equiv.add_argument("--tests", required=True)
    equiv.add_argument("--work-dir", required=True)
    equiv.add_argument("--mode", default="sampled")
    equiv.add_argument("--summary", default=None)
    args = ap.parse_args()
    if args.cmd == "prepare":
        cmd_prepare(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "equivalence":
        cmd_equivalence(args)
    else:
        cmd_merge(args)


if __name__ == "__main__":
    main()
