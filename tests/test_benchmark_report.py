############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests of ``tools/benchmark_report.py``, the benchmark tool of the
Performance page, on the test data and synthetic directories (without
the ENDF/B-VIII.1 data)."""

import copy
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "benchmark_report.py"
TESTDATA = Path(__file__).resolve().parent / "testdata"
PLACEHOLDER = REPO_ROOT / "docs" / "source" / "performance" / "results.json"

if not TOOL.exists():
    pytest.skip("tools/benchmark_report.py is not available", allow_module_level=True)

_spec = importlib.util.spec_from_file_location("benchmark_report", TOOL)
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def _tape_head():
    # a tape head (TPID) of 80 columns: MAT 1, MF 0, MT 0
    return " synthetic tape".ljust(66) + "   1 0  0    0\n"


def _make_library(root, layout):
    """Directories and files: ``layout`` maps a relative path to the
    content (str) or to a file of the test data (Path)."""
    for relpath, content in layout.items():
        path = Path(root) / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Path):
            shutil.copyfile(content, path)
        else:
            path.write_text(content)
    return str(root)


# --- the data ---------------------------------------------------------


def test_sublibrary_detection(tmp_path):
    root = _make_library(
        tmp_path,
        {
            "neutrons-version.VIII.1/n-001_H_001.endf": _tape_head(),
            "neutrons-version.VIII.1/README": "text\n",
            "neutrons-version.VIII.1/notes.endf": "not a tape head\n",
            "neutrons-version.VIII.1/sub/x.endf": _tape_head(),
            "decay-version.VIII.1/dec-001_H_003.endf": _tape_head(),
            # the tape head of ENDF/B-VIII.1: no MAT number, no sequence
            "alphas-version.VIII.1/a-002_He_004.endf": " ENDF/B-VIII.1".ljust(70)
            + " 0  0\n",
            "unknown-version.VIII.1/x.endf": _tape_head(),
            "checksums.txt": "abc\n",
        },
    )
    files, ignored, library = br.discover(root)
    assert library == "ENDF/B-VIII.1"
    assert [(f["path"], f["sublibrary"]) for f in files] == [
        ("alphas-version.VIII.1/a-002_He_004.endf", "alphas"),
        ("decay-version.VIII.1/dec-001_H_003.endf", "decay"),
        ("neutrons-version.VIII.1/n-001_H_001.endf", "neutrons"),
    ]
    reasons = {i["path"]: i["reason"] for i in ignored}
    assert reasons == {
        "checksums.txt": "not a sublibrary directory",
        "neutrons-version.VIII.1/README": "not an .endf file",
        "neutrons-version.VIII.1/notes.endf": "the first line is not a tape head",
        "neutrons-version.VIII.1/sub": "not a file",
        "unknown-version.VIII.1": "not a known sublibrary",
    }
    files, _, _ = br.discover(root, ["decay", "protons"])
    assert [f["sublibrary"] for f in files] == ["decay"]
    _, ignored, _ = br.discover(root, ["decay", "protons"])
    assert {"path": "protons", "reason": "sublibrary not found"} in ignored


def test_test_data_are_endf_files():
    for name in ("n_2925_29-Cu-63.endf", "tsl_Al.endf", "dec-094_Pu_244.endf"):
        assert br.endf_file_reason(str(TESTDATA / name)) is None


def test_size_groups():
    assert [br.size_group(s) for s in (0, 99_999, 100_000, 999_999)] == [0, 0, 1, 1]
    assert [br.size_group(s) for s in (1_000_000, 9_999_999, 10_000_000)] == [2, 2, 3]
    assert br.size_group_labels() == [
        "< 100 kB",
        "100 kB – 1 MB",
        "1 MB – 10 MB",
        "≥ 10 MB",
    ]
    assert br.size_group(5, (10,)) == 0 and br.size_group(10, (10,)) == 1
    assert br.size_group_labels((1e3, 2.5e6)) == ["< 1 kB", "1 kB – 2.5 MB", "≥ 2.5 MB"]


def _files(n, sublibrary="neutrons", size=lambda i: 1000 * (i + 1)):
    return [
        {
            "path": f"{sublibrary}-version.VIII.1/f{i:03d}.endf",
            "sublibrary": sublibrary,
            "size": size(i),
        }
        for i in range(n)
    ]


def test_sample_is_deterministic():
    files = _files(30) + _files(2, "decay") + _files(10, "gammas", lambda i: 5e6)
    sample = br.select_sample(files, 3)
    # the quantiles 1/6, 3/6, 5/6 of the 30 files sorted by size
    assert [p for p in sample if p.startswith("neutrons")] == [
        "neutrons-version.VIII.1/f005.endf",
        "neutrons-version.VIII.1/f015.endf",
        "neutrons-version.VIII.1/f025.endf",
    ]
    # a group with at most k files is taken whole
    assert [p for p in sample if p.startswith("decay")] == [
        "decay-version.VIII.1/f000.endf",
        "decay-version.VIII.1/f001.endf",
    ]
    # files of equal size are ordered by name
    assert [p for p in sample if p.startswith("gammas")] == [
        "gammas-version.VIII.1/f001.endf",
        "gammas-version.VIII.1/f005.endf",
        "gammas-version.VIII.1/f008.endf",
    ]
    # the same in any order of the files
    shuffled = list(files)
    random.Random(1).shuffle(shuffled)
    assert br.select_sample(shuffled, 3) == sample
    assert len(br.select_sample(files, 1)) == 3


def test_manifest_check():
    manifest = [
        {"path": "a", "sublibrary": "neutrons", "size": 1, "sha256": "x"},
        {"path": "b", "sublibrary": "neutrons", "size": 2, "sha256": "y"},
        {"path": "c", "sublibrary": "neutrons", "size": 3, "sha256": "z"},
    ]
    assert br.check_manifest(manifest, manifest)["identical"]
    reference = copy.deepcopy(manifest)
    reference[1]["sha256"] = "other"
    reference[2]["path"] = "d"
    check = br.check_manifest(manifest, reference)
    assert check == {
        "missing": ["d"],
        "different": ["b"],
        "extra": ["c"],
        "identical": False,
    }


# --- the results file -------------------------------------------------


def _results():
    with open(PLACEHOLDER, encoding="utf-8") as f:
        return json.load(f)


def test_placeholder_results_schema():
    results = br.load_results(str(PLACEHOLDER))
    assert results["format"] == br.FORMAT
    assert results["placeholder"] is True
    # no absolute paths
    text = PLACEHOLDER.read_text(encoding="utf-8")
    for f in results["manifest"]:
        assert not os.path.isabs(f["path"])
    assert str(REPO_ROOT) not in text
    assert "/tmp/" not in text and "/home/" not in text


def test_schema_errors():
    results = _results()
    del results["manifest"]
    with pytest.raises(ValueError, match="manifest"):
        br.validate_results(results)
    results = _results()
    cell = results["cells"]["cpp/numpy"]["files"]
    path = next(iter(cell))
    cell[path]["write_ns"] = []
    with pytest.raises(ValueError, match="wrong times"):
        br.validate_results(results)
    results = _results()
    results["manifest"][0]["path"] = "/abs/" + results["manifest"][0]["path"]
    with pytest.raises(ValueError, match="relative"):
        br.validate_results(results)


def test_excluded_file_is_dropped_from_all_cells():
    results = _results()
    neutron_paths = br.cell_paths(results, "cpp", ("neutrons",))
    assert len(neutron_paths) == 2
    before = {k: br.totals(results, k, neutron_paths) for k in results["cells"]}
    # a file failing in one cell: excluded from every cell
    failing = neutron_paths[0]
    results["excluded"].append(
        {
            "path": failing,
            "sublibrary": "neutrons",
            "errors": [{"cell": "py/list", "operation": "write", "error": "E"}],
        }
    )
    for cell in results["cells"].values():
        cell["files"].pop(failing, None)
    br.validate_results(results)
    for parser in ("cpp", "py"):
        assert failing not in br.cell_paths(results, parser)
    after_paths = br.cell_paths(results, "cpp", ("neutrons",))
    assert after_paths == neutron_paths[1:]
    for key in results["cells"]:
        t = br.totals(results, key, after_paths)
        assert t["files"] == 1
        assert t["bytes_in"] < before[key]["bytes_in"]
    # a cell that lacks a file of the set gives no total
    assert br.totals(results, "cpp/dict", neutron_paths) is None


def test_totals_use_medians():
    results = _results()
    path = br.cell_paths(results, "cpp", ("decay",))[0]
    results["cells"]["cpp/dict"]["files"][path]["parse_ns"] = [3e9, 1e9, 2e9]
    t = br.totals(results, "cpp/dict", [path])
    assert t["parse"] == 2 and t["parse_min"] == 1 and t["parse_max"] == 3


def test_dump_is_json():
    results = _results()
    assert json.loads(br._dump(results)) == results


# --- render and the README sentence -----------------------------------


def test_render_is_deterministic(tmp_path):
    pytest.importorskip("matplotlib")
    outputs = []
    for name in ("one", "two"):
        out = tmp_path / name / "performance"
        subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "render",
                str(PLACEHOLDER),
                "--out-dir",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
        outputs.append({p.name: p.read_bytes() for p in sorted(out.iterdir())})
    assert outputs[0] == outputs[1]
    assert set(outputs[0]) == {
        "summary.rst",
        "method.rst",
        "machine.rst",
        "by_sublibrary.rst",
        "by_size.rst",
        "memory.rst",
        "throughput_by_size.svg",
        "results.json",
    }
    svg = outputs[0]["throughput_by_size.svg"].decode()
    assert "<dc:date>" not in svg
    # the committed tables are those of the committed results (the chart
    # depends on the version of matplotlib)
    committed = PLACEHOLDER.parent
    for name, content in outputs[0].items():
        if name.endswith(".rst"):
            assert (committed / name).read_bytes() == content, name


def test_rendered_tables():
    results = _results()
    summary = br.render_summary(results)
    assert summary.startswith(".. warning::")
    assert "Placeholder" in summary
    assert "``EndfParserPy`` ``numpy``\\ :sup:`*`" in summary
    for label in ("Neutrons", "Thermal neutron scattering", "Decay data", "All"):
        assert label in summary
    results["placeholder"] = False
    assert "Placeholder" not in br.render_summary(results)
    by_sub = br.render_by_sublibrary(results)
    assert by_sub.count(".. rubric::") == 3
    assert "Time of EndfParserPy over EndfParserCpp, on the sample" in by_sub


def test_light_charged_particles_are_one_group():
    results = _results()
    for name in ("deuterons", "alphas"):
        path = f"{name}-version.VIII.1/x.endf"
        results["manifest"].append(
            {"path": path, "sublibrary": name, "size": 10, "sha256": "0"}
        )
    groups = br.page_groups(results)
    assert groups[-1] == (
        "light_charged",
        br.LIGHT_CHARGED_LABEL,
        ("deuterons", "alphas"),
    )
    assert [g[0] for g in groups[:-1]] == ["neutrons", "thermal_scatt", "decay"]


def test_readme_sentence():
    results = _results()
    sentence = br.readme_sentence(results)
    assert sentence.startswith(
        'With the C++ backend and `array_type="numpy"`, `endf-parserpy` reads '
        "the complete neutron sublibrary of ENDF/B-VIII.1 — 2 files, 4 MB — "
    )
    assert "warm file cache" in sentence
    results["software"]["git_describe"] = "v0.19.0"
    results["software"]["endf_parserpy"] = "0.19.0"
    results["machine"]["cpu"] = "11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz"
    results["machine"]["battery"] = True
    sentence = br.readme_sentence(results)
    assert sentence.endswith(
        "(single core of an Intel Core i7-1165G7 laptop, warm file cache; "
        "measured with version 0.19.0)."
    )


def test_short_cpu_name():
    assert br.short_cpu_name("11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz") == (
        "Intel Core i7-1165G7"
    )
    assert br.short_cpu_name("AMD Ryzen 7 5800X 8-Core Processor") == (
        "AMD Ryzen 7 5800X 8-Core"
    )
    assert br.short_cpu_name("Apple M1") == "Apple M1"


# --- measure ----------------------------------------------------------


def _measure(tmp_path, *options):
    root = _make_library(
        tmp_path / "lib",
        {
            "decay-version.VIII.1/dec-094_Pu_244.endf": TESTDATA
            / "dec-094_Pu_244.endf",
            "decay-version.VIII.1/README.txt": "not an ENDF file\n",
            # a file that every parser rejects (a blank line)
            "nfy-version.VIII.1/broken.endf": "".join(
                (TESTDATA / "dec-094_Pu_244.endf").read_text().splitlines(True)[:60]
            ),
            "nfy-version.VIII.1/dec-094_Pu_244.endf": TESTDATA / "dec-094_Pu_244.endf",
        },
    )
    out = tmp_path / "results.json"
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "measure",
            root,
            "--out",
            str(out),
            "--rounds",
            "1",
            *options,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    return br.load_results(str(out)), proc


def _check_measured(results):
    assert results["rounds_completed"] == 1 and results["finished"]
    assert [f["path"] for f in results["manifest"]] == [
        "decay-version.VIII.1/dec-094_Pu_244.endf",
        "nfy-version.VIII.1/broken.endf",
        "nfy-version.VIII.1/dec-094_Pu_244.endf",
    ]
    assert results["ignored"] == [
        {"path": "decay-version.VIII.1/README.txt", "reason": "not an .endf file"}
    ]
    assert [e["path"] for e in results["excluded"]] == [
        "nfy-version.VIII.1/broken.endf"
    ]
    for cell in results["cells"].values():
        assert sorted(cell["files"]) == [
            "decay-version.VIII.1/dec-094_Pu_244.endf",
            "nfy-version.VIII.1/dec-094_Pu_244.endf",
        ]
        for entry in cell["files"].values():
            assert len(entry["parse_ns"]) == 1 and entry["bytes_written"] > 8000
    assert results["library"] == "ENDF/B-VIII.1"


def test_measure_smoke(tmp_path):
    pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    results, _ = _measure(tmp_path, "--modes", "numpy")
    _check_measured(results)
    assert sorted(results["cells"]) == ["cpp/numpy", "py/numpy"]
    if results["memory_method"] is not None:
        for cell in results["cells"].values():
            for entry in cell["files"].values():
                assert entry["parse_peak"] >= 0 and entry["write_peak"] >= 0
    # the published manifest and sample are checked and reused
    published = tmp_path / "published.json"
    shutil.copyfile(tmp_path / "results.json", published)
    results, proc = _measure(
        tmp_path,
        "--modes",
        "numpy",
        "--parsers",
        "cpp",
        "--no-memory",
        "--check-manifest",
        str(published),
        "--sample",
        str(published),
    )
    assert results["manifest_check"]["identical"]
    assert results["sample"]["source"] == "reused"
    assert results["memory_method"] is None


@pytest.mark.exhaustive
def test_measure_all_cells(tmp_path):
    pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    results, _ = _measure(tmp_path)
    _check_measured(results)
    assert sorted(results["cells"]) == sorted(
        f"{p}/{m}" for p in br.PARSERS for m in br.MODES
    )
