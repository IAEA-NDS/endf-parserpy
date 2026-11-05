############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/05
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""DIAGNOSTIC ONLY (branch diag/bulk-bodies-u233, never merged): the
measurements of .github/workflows/diag_bulk_bodies.yml for the slow parse
of U233 in numpy mode with the bulk form on ubuntu-latest.

usage:
  python tools/diag_bulk_bodies.py fileinfo --files <file>... --out <json>
  python tools/diag_bulk_bodies.py cut --file <file> --out-dir <dir> [--min-lines 1]
  python tools/diag_bulk_bodies.py counters --spec <spec>... --files <file>...
      --modes numpy [...] --out <json>
  python tools/diag_bulk_bodies.py timing --spec <spec>... --files <file>...
      --modes numpy [...] --rounds 7 --reps 5 --out <json> [--title <text>]
  python tools/diag_bulk_bodies.py digest --spec <spec>... --files <file>...
      --modes numpy list dict --out <json>
  python tools/diag_bulk_bodies.py tiers --python <python>
  python tools/diag_bulk_bodies.py loop --file <file> --mode numpy --seconds 20
  python tools/diag_bulk_bodies.py collapse --file <py-spy raw output> [--top 60]
  python tools/diag_bulk_bodies.py summary --results-dir <dir> --out <md>

A spec is ``name|python`` or ``name|python|VAR=value;VAR=value``: the
variant ``name`` runs in fresh processes of the interpreter ``python``
(e.g. of the virtual environment of one build) with these environment
variables set (ENDF_PARSERPY_CPP_BULK_BODIES and
ENDF_PARSERPY_DIAG_BULK_DISABLE are removed otherwise). The first spec is
the reference of the ratios (``timing``) and of the comparison
(``digest``).

``timing``: in each round, every variant runs one process per mode that
parses each file once (warm-up) and then ``--reps`` times, in an order
rotated from round to round; per file the minimum of ``time.process_time``
(and of the wall clock), and the medians of the user and system times and
of the page faults and context switches of a parse (getrusage). The result
per variant is the median over the rounds of the ratio of its time to the
time of the first variant in the same round. The worker is that of
tools/benchmark_bulk_bodies.py with these additions.

``counters``: one fresh process per variant, file and mode that parses
the file once; then the full ``_bulk_body_info()`` of the module (including
the diagnostic counters of this branch).

``digest``: one process per variant and mode; a digest of each result
(values with their bits, types, numpy dtypes and shapes; errors: type and
message), compared with the first variant.

``cut``: per-MF tapes of one file (TPID line, the lines of the MF, its FEND
line, MEND and TEND), as earlier studies did
(benchmarks/vm_study_2026-11/tools/cut_minitapes.py), named
``<name>_MF<mf>.endf``.

``tiers``: prints the tiers built and supported with the interpreter
``python`` (space-separated, e.g. ``scalar avx2 avx512``).

``collapse``: the functions with the most samples (self and total) in
the collapsed stacks of ``py-spy record -f raw``.

``loop``: parses one file repeatedly for about ``--seconds`` (the program
profiled by perf or py-spy).
"""

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

ENV_VARS = ("ENDF_PARSERPY_CPP_BULK_BODIES", "ENDF_PARSERPY_DIAG_BULK_DISABLE")

WORKER = r"""
import hashlib, importlib, json, os, sys, time
cfg = json.loads(sys.argv[1])
from endf_parserpy import EndfParserCpp
try:
    import resource
except ImportError:
    resource = None
p = EndfParserCpp(array_type=cfg["mode"])
mod = importlib.import_module(p._parse_endf.__module__)
info_load = mod._bulk_body_info() if hasattr(mod, "_bulk_body_info") else None
timer = time.perf_counter if sys.platform == "win32" else time.process_time
FIELDS = ("ru_utime", "ru_stime", "ru_minflt", "ru_majflt", "ru_nvcsw", "ru_nivcsw")

def usage():
    if resource is None:
        return None
    r = resource.getrusage(resource.RUSAGE_SELF)
    return [getattr(r, f) for f in FIELDS]

def digest(obj, h):
    t = type(obj)
    h.update(t.__name__.encode())
    if isinstance(obj, dict):
        h.update(str(len(obj)).encode())
        for k in obj:
            digest(k, h)
            digest(obj[k], h)
    elif isinstance(obj, (list, tuple)):
        h.update(str(len(obj)).encode())
        for v in obj:
            digest(v, h)
    elif isinstance(obj, float):
        import struct
        h.update(struct.pack("<d", obj))
    elif isinstance(obj, (int, str, bool)) or obj is None:
        h.update(repr(obj).encode())
    elif t.__module__ == "numpy" and t.__name__ == "ndarray":
        h.update(str(obj.dtype).encode() + str(obj.shape).encode())
        if obj.dtype == object:
            for v in obj.ravel():
                digest(v, h)
        else:
            import numpy
            h.update(numpy.ascontiguousarray(obj).tobytes())
    else:
        h.update(repr(obj).encode())

out = {"info_load": info_load, "files": {}}
for path in cfg["files"]:
    if cfg.get("digest"):
        try:
            d = p.parsefile(path)
            h = hashlib.sha256()
            digest(d, h)
            out["files"][path] = {"digest": h.hexdigest()}
        except Exception as exc:
            out["files"][path] = {"error": type(exc).__name__ + ": " + str(exc)}
        continue
    p.parsefile(path)
    rec = {"t": [], "wall": [], "ru": []}
    for _ in range(cfg["reps"]):
        u0 = usage(); w0 = time.perf_counter(); t0 = timer()
        d = p.parsefile(path)
        t1 = timer(); w1 = time.perf_counter(); u1 = usage()
        del d
        rec["t"].append(t1 - t0)
        rec["wall"].append(w1 - w0)
        if u0 is not None:
            rec["ru"].append([b - a for a, b in zip(u0, u1)])
    out["files"][path] = rec
out["info"] = mod._bulk_body_info() if hasattr(mod, "_bulk_body_info") else None
try:
    with open("/proc/self/status") as f:
        out["threads"] = int([s for s in f if s.startswith("Threads:")][0].split()[1])
except (OSError, IndexError, ValueError):
    out["threads"] = None
print(json.dumps(out))
"""

RU_FIELDS = ("utime", "stime", "minflt", "majflt", "nvcsw", "nivcsw")


def parse_spec(spec):
    parts = spec.split("|")
    if len(parts) not in (2, 3):
        raise SystemExit(f"bad spec {spec!r} (expected name|python[|VAR=value;...])")
    env = {}
    if len(parts) == 3 and parts[2]:
        for assign in parts[2].split(";"):
            var, val = assign.split("=", 1)
            if var not in ENV_VARS:
                raise SystemExit(f"spec {spec!r}: unknown variable {var}")
            env[var] = val
    python = parts[1]
    if os.sep in python or "/" in python:
        # the workers run in another directory (see run_worker)
        python = os.path.abspath(python)
    return {"name": parts[0], "python": python, "env": env}


def run_worker(spec, cfg):
    env = dict(os.environ)
    for var in ENV_VARS:
        env.pop(var, None)
    env.update(spec["env"])
    # absolute paths, and the worker runs in the temporary directory, so
    # that no endf_parserpy package in the current directory shadows the
    # one of the interpreter (python -c puts the current directory first)
    cfg = dict(cfg, files=[os.path.abspath(f) for f in cfg["files"]])
    res = subprocess.run(
        [spec["python"], "-c", WORKER, json.dumps(cfg)],
        env=env,
        capture_output=True,
        text=True,
        cwd=tempfile.gettempdir(),
    )
    if res.returncode != 0:
        raise RuntimeError(f"worker failed ({spec['name']}):\n{res.stderr}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def label(path):
    base = os.path.basename(path)
    for sfx in (".endf", ".enf"):
        if base.endswith(sfx):
            return base[: -len(sfx)]
    return base


def cmd_fileinfo(args):
    result = {}
    for path in args.files:
        with open(path, "rb") as f:
            raw = f.read()
        lines = raw.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        crlf = sum(1 for s in lines if s.endswith(b"\r"))
        lengths = {}
        mf_lines = {}
        nonascii = 0
        for s in lines:
            s = s[:-1] if s.endswith(b"\r") else s
            lengths[len(s)] = lengths.get(len(s), 0) + 1
            if any(c < 32 or c > 126 for c in s):
                nonascii += 1
            try:
                mf = int(s[70:72])
            except ValueError:
                mf = None
            mf_lines[str(mf)] = mf_lines.get(str(mf), 0) + 1
        result[label(path)] = {
            "path": path,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "lines": len(lines),
            "crlf_lines": crlf,
            "final_newline": raw.endswith(b"\n"),
            "line_lengths": {str(k): v for k, v in sorted(lengths.items())},
            "lines_with_control_or_nonascii": nonascii,
            "lines_per_mf": mf_lines,
        }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
    for name, r in result.items():
        print(
            f"{name}: {r['bytes']} bytes, sha256 {r['sha256']}, {r['lines']} lines, "
            f"CRLF {r['crlf_lines']}, lengths {r['line_lengths']}"
        )


def cmd_cut(args):
    with open(args.file, "rb") as f:
        lines = f.read().splitlines(keepends=True)
    name = label(args.file)
    os.makedirs(args.out_dir, exist_ok=True)
    tail = [s for s in lines[-4:] if s.strip()]
    mend, tend = tail[-2], tail[-1]
    assert int(mend[66:70]) == 0 and int(tend[66:70]) == -1, "no MEND/TEND at the end"
    by_mf = {}
    for i, s in enumerate(lines[1:], start=1):
        try:
            mat, mf = int(s[66:70]), int(s[70:72])
        except ValueError:
            continue
        if mat > 0 and mf > 0:
            by_mf.setdefault(mf, []).append(i)
    written = []
    for mf, idx in sorted(by_mf.items()):
        if len(idx) < args.min_lines:
            continue
        fend = lines[idx[-1] + 1]
        assert int(fend[70:72]) == 0 and int(fend[72:75]) == 0, f"MF{mf}: no FEND"
        out = [lines[0]] + [lines[i] for i in idx] + [fend, mend, tend]
        path = os.path.join(args.out_dir, f"{name}_MF{mf:02d}.endf")
        with open(path, "wb") as f:
            f.write(b"".join(out))
        written.append(path)
        print(f"{path}: {len(idx)} lines of MF{mf}")


def cmd_counters(args):
    specs = [parse_spec(s) for s in args.spec]
    result = []
    for spec in specs:
        for mode in args.modes:
            for path in args.files:
                out = run_worker(spec, {"mode": mode, "files": [path], "reps": 0})
                result.append(
                    {
                        "variant": spec["name"],
                        "env": spec["env"],
                        "mode": mode,
                        "file": label(path),
                        "info": out["info"],
                    }
                )
                info = out["info"] or {}
                print(
                    spec["name"],
                    mode,
                    label(path),
                    info.get("selected"),
                    json.dumps(info.get("bulk_list_bodies")),
                    json.dumps(
                        {
                            k: v
                            for k, v in (info.get("diag") or {}).items()
                            if k not in ("variable", "value_now")
                        }
                    ),
                    flush=True,
                )
    with open(args.out, "w") as f:
        json.dump(
            {"kind": "counters", "title": args.title, "records": result}, f, indent=1
        )


def cmd_timing(args):
    specs = [parse_spec(s) for s in args.spec]
    records = []
    infos = {}
    for rnd in range(args.round_offset, args.round_offset + args.rounds):
        k = rnd % len(specs)
        order = specs[k:] + specs[:k]
        if rnd % 2:
            order = order[::-1]
        for mode in args.modes:
            for spec in order:
                out = run_worker(
                    spec, {"mode": mode, "files": args.files, "reps": args.reps}
                )
                infos.setdefault(spec["name"], out["info_load"])
                for path, rec in out["files"].items():
                    ru = rec["ru"]
                    med = (
                        {
                            f: statistics.median(r[i] for r in ru)
                            for i, f in enumerate(RU_FIELDS)
                        }
                        if ru
                        else {}
                    )
                    records.append(
                        {
                            "round": rnd,
                            "variant": spec["name"],
                            "file": label(path),
                            "mode": mode,
                            "t": min(rec["t"]),
                            "wall": min(rec["wall"]),
                            "ru_median": med,
                            "threads": out["threads"],
                        }
                    )
        print(f"round {rnd + 1 - args.round_offset}/{args.rounds} done", flush=True)
    ratios = ratio_table(records, [s["name"] for s in specs])
    result = {
        "kind": "timing",
        "title": args.title,
        "variants": [s["name"] for s in specs],
        "specs": [{"name": s["name"], "env": s["env"]} for s in specs],
        "info_load": infos,
        "records": records,
        "ratios": ratios,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
    print(timing_markdown(result))


def ratio_table(records, names):
    ref = names[0]
    by_key = {}
    for r in records:
        by_key.setdefault((r["file"], r["mode"], r["round"]), {})[r["variant"]] = r
    table = {}
    for (f, mode, rnd), recs in by_key.items():
        row = table.setdefault(f"{f}|{mode}", {})
        if ref not in recs or recs[ref]["t"] <= 0:
            continue
        for name, r in recs.items():
            cell = row.setdefault(
                name,
                {"ratio": [], "t": [], "wall_ratio": [], "stime": [], "minflt": []},
            )
            cell["ratio"].append(r["t"] / recs[ref]["t"])
            cell["t"].append(r["t"])
            if recs[ref]["wall"] > 0:
                cell["wall_ratio"].append(r["wall"] / recs[ref]["wall"])
            cell["stime"].append(r["ru_median"].get("stime", 0.0))
            cell["minflt"].append(r["ru_median"].get("minflt", 0))
    out = {}
    for key, row in table.items():
        out[key] = {}
        for name, c in row.items():
            out[key][name] = {
                "median": statistics.median(c["ratio"]),
                "min": min(c["ratio"]),
                "max": max(c["ratio"]),
                "t_min_ms": 1e3 * min(c["t"]),
                "wall_ratio_median": (
                    statistics.median(c["wall_ratio"]) if c["wall_ratio"] else None
                ),
                "stime_median_ms": 1e3 * statistics.median(c["stime"]),
                "minflt_median": statistics.median(c["minflt"]),
                "rounds": len(c["ratio"]),
            }
    return out


def timing_markdown(res):
    names = res["variants"]
    lines = [f"#### {res.get('title') or 'timing'}", ""]
    for s in res["specs"]:
        env = ", ".join(f"{k}={v}" for k, v in s["env"].items()) or "no variables"
        info = (res["info_load"] or {}).get(s["name"])
        sel = info.get("selected") if info else "-"
        dis = ",".join(info.get("diag_disabled", [])) if info else "-"
        lines.append(
            f"- `{s['name']}`: {env}; selected tier `{sel}`; diag disabled `{dis or '-'}`"
        )
    lines += [
        "",
        f"Median over rounds of the process-time ratio to `{names[0]}` [min..max]; "
        "in parentheses the minimum time in ms. Second table: wall-clock ratio, "
        "system time per parse (ms) and minor page faults per parse (medians).",
        "",
        "| file | mode | " + " | ".join(names) + " |",
        "|---|---|" + "---|" * len(names),
    ]
    extra = [
        "",
        "| file | mode | " + " | ".join(names) + " |",
        "|---|---|" + "---|" * len(names),
    ]
    for key in sorted(res["ratios"]):
        f, mode = key.split("|")
        row = res["ratios"][key]
        cells, cells2 = [], []
        for n in names:
            c = row.get(n)
            if c is None:
                cells.append("")
                cells2.append("")
                continue
            cells.append(
                f"{c['median']:.3f} [{c['min']:.2f}..{c['max']:.2f}] ({c['t_min_ms']:.1f})"
            )
            w = c["wall_ratio_median"]
            cells2.append(
                f"{w:.3f} / {c['stime_median_ms']:.2f} / {c['minflt_median']:.0f}"
                if w is not None
                else ""
            )
        lines.append(f"| {f} | {mode} | " + " | ".join(cells) + " |")
        extra.append(f"| {f} | {mode} | " + " | ".join(cells2) + " |")
    return "\n".join(lines + extra) + "\n"


def cmd_digest(args):
    specs = [parse_spec(s) for s in args.spec]
    digests = {}
    for spec in specs:
        for mode in args.modes:
            out = run_worker(
                spec, {"mode": mode, "files": args.files, "reps": 0, "digest": True}
            )
            for path, rec in out["files"].items():
                digests.setdefault(f"{label(path)}|{mode}", {})[spec["name"]] = rec
    ref = specs[0]["name"]
    differing = []
    for key, row in sorted(digests.items()):
        for name, rec in row.items():
            if rec != row[ref]:
                differing.append((key, name))
    result = {
        "kind": "digest",
        "title": args.title,
        "reference": ref,
        "variants": [s["name"] for s in specs],
        "digests": digests,
        "differing": differing,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
    n = len(digests) * (len(specs) - 1)
    print(f"{n} comparisons with {ref}, {len(differing)} differing: {differing}")
    if differing and args.fail:
        raise SystemExit(1)


def cmd_tiers(args):
    spec = parse_spec(f"probe|{args.python}")
    info = run_worker(spec, {"mode": "numpy", "files": [], "reps": 0})["info_load"]
    names = []
    if info is not None:
        names = [n for n, t in info["tiers"].items() if t["built"] and t["supported"]]
    print(" ".join(names))


def cmd_loop(args):
    from endf_parserpy import EndfParserCpp

    p = EndfParserCpp(array_type=args.mode)
    p.parsefile(args.file)
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < args.seconds:
        d = p.parsefile(args.file)
        del d
        n += 1
    print(f"{n} parses in {time.perf_counter() - t0:.1f} s")


def cmd_collapse(args):
    self_n, total_n, n = {}, {}, 0
    with open(args.file) as f:
        for line in f:
            stack, _, count = line.rstrip("\n").rpartition(" ")
            try:
                c = int(count)
            except ValueError:
                continue
            frames = [fr.split(" (")[0][:160] for fr in stack.split(";") if fr]
            if not frames:
                continue
            n += c
            self_n[frames[-1]] = self_n.get(frames[-1], 0) + c
            for fr in set(frames):
                total_n[fr] = total_n.get(fr, 0) + c
    print(f"{n} samples")
    for title, table in (("self", self_n), ("total (inclusive)", total_n)):
        print(f"\n== {title}")
        for fr, c in sorted(table.items(), key=lambda kv: -kv[1])[: args.top]:
            print(f"{100.0 * c / max(n, 1):6.2f}%  {c:8d}  {fr}")


def counters_markdown(res):
    keys = (
        "strided",
        "looped",
        "stopped",
        "byte_range",
        "line_by_line",
        "row_bodies",
        "row_values",
        "row_rows",
    )
    dkeys = (
        "prepass_catches",
        "delivery_catches",
        "incomplete_bodies",
        "rowpf_bodies",
        "loop_off_bodies",
        "repositions",
        "grow_calls",
        "store_allocs",
        "private_allocs",
        "max_capacity",
        "tab1_bulk",
        "tab1_perfield",
    )
    lines = [
        f"#### {res.get('title') or 'counters'}",
        "",
        "One parse per fresh process; `_bulk_body_info()` afterwards.",
        "",
        "| variant | file | mode | tier | "
        + " | ".join(keys)
        + " | scalar_kernel_lines |",
        "|---|---|---|---|" + "---|" * (len(keys) + 1),
    ]
    lines2 = [
        "",
        "| variant | file | mode | disabled | " + " | ".join(dkeys) + " |",
        "|---|---|---|---|" + "---|" * len(dkeys),
    ]
    for r in res["records"]:
        info = r["info"] or {}
        b = info.get("bulk_list_bodies") or {}
        d = info.get("diag") or {}
        lines.append(
            f"| {r['variant']} | {r['file']} | {r['mode']} | {info.get('selected', '-')} | "
            + " | ".join(str(b.get(k, "")) for k in keys)
            + f" | {info.get('scalar_kernel_lines', '')} |"
        )
        lines2.append(
            f"| {r['variant']} | {r['file']} | {r['mode']} | {','.join(d.get('disabled', [])) or '-'} | "
            + " | ".join(str(d.get(k, "")) for k in dkeys)
            + " |"
        )
    return "\n".join(lines + lines2) + "\n"


def digest_markdown(res):
    n = len(res["digests"]) * (len(res["variants"]) - 1)
    lines = [
        f"#### {res.get('title') or 'digests'}",
        "",
        f"{n} comparisons of result digests with `{res['reference']}` "
        f"({', '.join(res['variants'][1:])}): **{len(res['differing'])} differing**",
    ]
    for key, name in res["differing"]:
        lines.append(f"- {key}: {name}")
    return "\n".join(lines) + "\n"


def cmd_summary(args):
    parts = []
    names = sorted(os.listdir(args.results_dir))
    for name in names:
        if not name.endswith(".json"):
            continue
        with open(os.path.join(args.results_dir, name)) as f:
            try:
                res = json.load(f)
            except ValueError:
                continue
        if not isinstance(res, dict):
            continue
        kind = res.get("kind")
        if kind == "timing":
            parts.append(timing_markdown(res))
        elif kind == "counters":
            parts.append(counters_markdown(res))
        elif kind == "digest":
            parts.append(digest_markdown(res))
    text = "\n".join(parts)
    with open(args.out, "w") as f:
        f.write(text)
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fileinfo")
    p.add_argument("--files", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("cut")
    p.add_argument("--file", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--min-lines", type=int, default=1)
    for name in ("counters", "timing", "digest"):
        p = sub.add_parser(name)
        p.add_argument("--spec", nargs="+", required=True)
        p.add_argument("--files", nargs="+", required=True)
        p.add_argument("--modes", nargs="+", default=["numpy"])
        p.add_argument("--out", required=True)
        p.add_argument("--title", default=None)
        if name == "timing":
            p.add_argument("--rounds", type=int, default=7)
            p.add_argument("--reps", type=int, default=5)
            # the first round number (the order of the variants is rotated
            # by the round number), for rounds run by separate calls
            p.add_argument("--round-offset", type=int, default=0)
        if name == "digest":
            p.add_argument("--fail", action="store_true")
    p = sub.add_parser("tiers")
    p.add_argument("--python", required=True)
    p = sub.add_parser("loop")
    p.add_argument("--file", required=True)
    p.add_argument("--mode", default="numpy")
    p.add_argument("--seconds", type=float, default=20.0)
    p = sub.add_parser("collapse")
    p.add_argument("--file", required=True)
    p.add_argument("--top", type=int, default=60)
    p = sub.add_parser("summary")
    p.add_argument("--results-dir", required=True)
    p.add_argument("--out", required=True)
    args = ap.parse_args()
    {
        "fileinfo": cmd_fileinfo,
        "cut": cmd_cut,
        "counters": cmd_counters,
        "timing": cmd_timing,
        "digest": cmd_digest,
        "tiers": cmd_tiers,
        "loop": cmd_loop,
        "collapse": cmd_collapse,
        "summary": cmd_summary,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
