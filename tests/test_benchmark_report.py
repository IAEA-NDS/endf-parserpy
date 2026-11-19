############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/19
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests of ``tools/benchmark_report.py``, the benchmark tool of the
Performance page, on the test data and synthetic directories (without
the ENDF/B-VIII.1 data)."""

import copy
import datetime
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "benchmark_report.py"
TESTDATA = Path(__file__).resolve().parent / "testdata"
# the results of the page, and a placeholder from the test data (the
# first version of the page), on which the tests of the tables run
COMMITTED = REPO_ROOT / "docs" / "source" / "performance" / "results.json"
PLACEHOLDER = TESTDATA / "benchmark_placeholder_results.json"

if not TOOL.exists():
    pytest.skip("tools/benchmark_report.py is not available", allow_module_level=True)

_spec = importlib.util.spec_from_file_location("benchmark_report", TOOL)
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def _tool_env():
    """The environment of a process of the tool: it imports the same
    ``endf_parserpy`` as this test process. Not the checkout by force: in
    CI the package is installed with its C++ module, which the checkout
    lacks (see tests/test_cli_equivalence.py)."""
    env = dict(os.environ)
    spec = importlib.util.find_spec("endf_parserpy")
    if spec is not None and spec.origin:
        pkgdir = str(Path(spec.origin).parent.parent)
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (pkgdir, env.get("PYTHONPATH")) if p
        )
    return env


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
            # the same bytes on every platform
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
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
    # the placeholder is in format 1, with the list of ignored entries,
    # which is still read
    assert results["format_version"] == 1
    assert isinstance(results["ignored"], list)
    assert results["placeholder"] is True
    # no absolute paths
    text = PLACEHOLDER.read_text(encoding="utf-8")
    for f in results["manifest"]:
        assert not os.path.isabs(f["path"])
    assert str(REPO_ROOT) not in text
    assert "/tmp/" not in text and "/home/" not in text


def test_committed_results_schema():
    results = br.load_results(str(COMMITTED))
    assert results["format"] == br.FORMAT
    assert results["placeholder"] is False
    assert results["format_version"] == 2
    assert "ignored" not in results
    text = COMMITTED.read_text(encoding="utf-8")
    for f in results["manifest"]:
        assert not os.path.isabs(f["path"])
    assert str(REPO_ROOT) not in text
    assert "/tmp/" not in text and "/home/" not in text
    # the only file names are those of the measured files
    names = set(re.findall(r'"([a-z0-9_]+-version\.[^"/]+/[^"]+)"', text))
    assert names == {f["path"] for f in results["manifest"]}


def test_format_versions():
    old = _results()
    assert old["format_version"] == 1
    new = br.strip_ignored(copy.deepcopy(old))
    br.validate_results(new)
    # format 2 has no list of ignored entries, format 1 needs it
    with_list = dict(new, ignored=[])
    with pytest.raises(ValueError, match="not recorded from format 2 on"):
        br.validate_results(with_list)
    without = copy.deepcopy(old)
    del without["ignored"]
    with pytest.raises(ValueError, match="format 1"):
        br.validate_results(without)
    with pytest.raises(ValueError, match="newer"):
        br.validate_results(dict(new, format_version=br.FORMAT_VERSION + 1))
    # both formats give the same tables and README sentence
    for render in (
        br.render_summary,
        lambda r: br.render_method(r, "performance/"),
        br.render_machine,
        br.render_by_sublibrary,
        lambda r: br.render_by_size(r, "performance/"),
        br.render_memory,
        br.readme_sentence,
    ):
        assert render(old) == render(new)


def _strip_ignored(src, out):
    return subprocess.run(
        [sys.executable, str(TOOL), "strip-ignored", str(src), "--out", str(out)],
        capture_output=True,
        text=True,
        env=_tool_env(),
    )


def test_strip_ignored(tmp_path):
    src = tmp_path / "old.json"
    shutil.copyfile(PLACEHOLDER, src)
    old_text = src.read_text(encoding="utf-8")
    old = json.loads(old_text)
    assert old["ignored"]
    outputs = []
    for name in ("one.json", "two.json"):
        proc = _strip_ignored(src, tmp_path / name)
        assert proc.returncode == 0, proc.stderr
        outputs.append((tmp_path / name).read_bytes())
    # deterministic, and the input is not changed
    assert outputs[0] == outputs[1]
    assert src.read_text(encoding="utf-8") == old_text
    new_text = outputs[0].decode("utf-8")
    new = json.loads(new_text)
    # only the list of ignored entries is removed and the version set
    assert new["format_version"] == 2
    assert "ignored" not in new
    expected = {k: v for k, v in old.items() if k != "ignored"}
    expected["format_version"] = 2
    assert new == expected
    assert list(new) == list(expected)
    # the layout is kept: the text is that of the input without the lines
    # of the list and with the line of the version changed
    old_lines = old_text.split("\n")
    start = old_lines.index('  "ignored": [')
    end = old_lines.index("  ],", start)
    version = old_lines.index('  "format_version": 1,')
    old_lines[version] = '  "format_version": 2,'
    assert new_text.split("\n") == old_lines[:start] + old_lines[end + 1 :]
    # no names of ignored entries remain
    for entry in old["ignored"]:
        assert entry["path"] not in new_text
    # a file of format 2 is not converted again
    proc = _strip_ignored(tmp_path / "one.json", tmp_path / "three.json")
    assert proc.returncode != 0 and "format 2, not 1" in proc.stderr
    assert not (tmp_path / "three.json").exists()
    # nor a file in another layout, whose lines would change
    other = tmp_path / "other.json"
    other.write_text(json.dumps(old, indent=4), encoding="utf-8")
    proc = _strip_ignored(other, tmp_path / "four.json")
    assert proc.returncode != 0 and "layout" in proc.stderr
    assert not (tmp_path / "four.json").exists()


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
                str(COMMITTED),
                "--out-dir",
                str(out),
            ],
            check=True,
            capture_output=True,
            env=_tool_env(),
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
    committed = COMMITTED.parent
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
    # a development build installed from a checkout
    results["software"]["git_describe"] = "v0.18.0-42-g135ffaa"
    results["software"]["endf_parserpy"] = "0.18.0"
    date = datetime.date.fromisoformat(results["started"][:10])
    assert br.readme_sentence(results).endswith(
        f"measured on the development version of {date.strftime('%B %Y')})."
    )
    assert br._measurement_line(results).endswith(
        "with endf-parserpy 0.18.0 (development version v0.18.0-42-g135ffaa)."
    )


def test_short_cpu_name():
    assert br.short_cpu_name("11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz") == (
        "Intel Core i7-1165G7"
    )
    assert br.short_cpu_name("AMD Ryzen 7 5800X 8-Core Processor") == (
        "AMD Ryzen 7 5800X 8-Core"
    )
    assert br.short_cpu_name("Apple M1") == "Apple M1"


# --- the software -----------------------------------------------------

_PACKAGE_FILES = {
    "endf_parserpy/__init__.py": '__version__ = "0.18.0"\n',
    "endf_parserpy/sub/module.py": "x = 1\n",
}


def _run_git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=test"]
        + ["-c", "user.email=test@example.org", "-c", "commit.gpgsign=false"]
        + ["-c", "tag.gpgsign=false", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _git_checkout(path):
    """A git repository with the package files, a tag v0.18.0 and one
    commit after it."""
    _make_library(path, _PACKAGE_FILES)
    _run_git(path, "init", "-q")
    _run_git(path, "add", ".")
    _run_git(path, "commit", "-q", "-m", "first")
    _run_git(path, "tag", "v0.18.0")
    _make_library(path, {"README": "readme\n"})
    _run_git(path, "add", "README")
    _run_git(path, "commit", "-q", "-m", "second")
    return _run_git(path, "rev-parse", "HEAD")


def _fake_install(monkeypatch, site, source, direct_url):
    """Install the package files of ``source`` into ``site`` as pip
    would, with a ``RECORD`` and, unless None, a ``direct_url.json``,
    and make the tool see this installed package."""
    from importlib import metadata

    lines = []
    for relpath in _PACKAGE_FILES:
        target = Path(site) / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(source) / relpath, target)
        digest = br._record_sha256(target)
        lines.append(f"{relpath},sha256={digest},{target.stat().st_size}")
    dist_info = Path(site) / "endf_parserpy-0.18.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: endf-parserpy\nVersion: 0.18.0\n"
    )
    for name in ("METADATA", "RECORD"):
        lines.append(f"{dist_info.name}/{name},,")
    if direct_url is not None:
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url))
        lines.append(f"{dist_info.name}/direct_url.json,,")
    (dist_info / "RECORD").write_text("\n".join(lines) + "\n")
    dist = metadata.Distribution.at(dist_info)
    monkeypatch.setattr(br, "_distribution", lambda: dist)
    monkeypatch.setattr(br, "_package_dir", lambda: str(Path(site) / "endf_parserpy"))
    monkeypatch.setattr(br, "cpp_module_info", lambda: {"available": False})


def _software(tmp_path):
    record = br.software_record()
    # neither the URL nor a local path is recorded
    text = json.dumps(record)
    assert "file:" not in text and "https:" not in text
    assert str(tmp_path) not in text
    assert str(Path(tmp_path).resolve()) not in text
    return record


def test_installed_from_checkout(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    commit = _git_checkout(checkout)
    direct_url = {"dir_info": {}, "url": checkout.as_uri()}
    _fake_install(monkeypatch, tmp_path / "site", checkout, direct_url)
    record = _software(tmp_path)
    assert record["package_location"] == "installed from a checkout"
    assert record["git_commit"] == commit
    assert record["git_describe"] == "v0.18.0-1-g" + commit[:7]
    assert "warnings" not in record


def test_installed_from_modified_checkout(tmp_path, monkeypatch, capsys):
    checkout = tmp_path / "checkout"
    commit = _git_checkout(checkout)
    direct_url = {"dir_info": {}, "url": checkout.as_uri()}
    _fake_install(monkeypatch, tmp_path / "site", checkout, direct_url)
    # the checkout moves on after the install
    (checkout / "endf_parserpy" / "sub" / "module.py").write_text("x = 2\n")
    _run_git(checkout, "commit", "-q", "-a", "-m", "third")
    record = _software(tmp_path)
    new_commit = _run_git(checkout, "rev-parse", "HEAD")
    assert new_commit != commit
    assert record["git_commit"] == new_commit + "+modified"
    assert len(record["warnings"]) == 1
    assert "+modified" in record["warnings"][0]
    # the table of the page shows the marker
    results = _results()
    results["software"] = record
    assert f"commit {new_commit[:12]}+modified" in br.render_machine(results)
    # a .py file in the checkout that is not installed
    (checkout / "endf_parserpy" / "sub" / "module.py").write_text("x = 1\n")
    (checkout / "endf_parserpy" / "new.py").write_text("y = 1\n")
    _run_git(checkout, "add", ".")
    _run_git(checkout, "commit", "-q", "-m", "fourth")
    assert _software(tmp_path)["git_commit"].endswith("+modified")


def test_installed_from_directory_without_git(tmp_path, monkeypatch):
    directory = tmp_path / "directory"
    _make_library(directory, _PACKAGE_FILES)
    direct_url = {"dir_info": {}, "url": directory.as_uri()}
    _fake_install(monkeypatch, tmp_path / "site", directory, direct_url)
    record = _software(tmp_path)
    assert record["package_location"] == "installed from a directory"
    assert record["git_commit"] is None
    assert record["git_describe"] is None


def test_installed_from_vcs_url(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    commit = _git_checkout(checkout)
    direct_url = {
        "url": "https://example.org/endf-parserpy.git",
        "vcs_info": {"vcs": "git", "commit_id": commit, "requested_revision": "dev"},
    }
    _fake_install(monkeypatch, tmp_path / "site", checkout, direct_url)
    monkeypatch.setattr(br, "_tool_checkout", lambda: None)
    record = _software(tmp_path)
    assert record["package_location"] == "installed from a repository"
    assert record["git_commit"] == commit
    assert record["git_describe"] is None
    # with the commit in the checkout of the tool, also the describe
    monkeypatch.setattr(br, "_tool_checkout", lambda: str(checkout))
    record = _software(tmp_path)
    assert record["git_describe"] == "v0.18.0-1-g" + commit[:7]


@pytest.mark.parametrize(
    "direct_url",
    [None, {"dir_info": {"editable": True}, "url": "file:///somewhere"}],
)
def test_installed_without_direct_url(tmp_path, monkeypatch, direct_url):
    # a wheel from PyPI; an editable install is imported from its
    # source tree and not looked at here
    checkout = tmp_path / "checkout"
    _git_checkout(checkout)
    _fake_install(monkeypatch, tmp_path / "site", checkout, direct_url)
    record = _software(tmp_path)
    assert record["package_location"] == "installed"
    assert record["git_commit"] is None
    assert record["git_describe"] is None
    assert "warnings" not in record


def _checkout_with_shared_cpp(path):
    """A checkout as ``_git_checkout`` that also tracks a generated
    translation unit, a source file that is not generated and a file
    outside ``cpp_parsers/`` with the name of a generated one."""
    _git_checkout(path)
    _make_library(
        path,
        {
            "endf_parserpy/cpp_parsers/_shared.cpp": "// generated\n",
            "endf_parserpy/cpp_parsers/helper.cpp": "// not generated\n",
            "other/_shared.cpp": "// not in cpp_parsers\n",
            "README.md": "readme\n",
        },
    )
    _run_git(path, "add", ".")
    _run_git(path, "commit", "-q", "-m", "third")
    return _run_git(path, "rev-parse", "HEAD")


def _source_tree_record(checkout, monkeypatch):
    monkeypatch.setattr(br, "cpp_module_info", lambda: {"available": False})
    location = {
        "kind": "source tree",
        "checkout": str(checkout),
        "commit": None,
        "warnings": [],
        "modified": False,
    }
    return br.software_record(location)


def _change(checkout, change):
    shared = checkout / "endf_parserpy" / "cpp_parsers" / "_shared.cpp"
    if change == "delete":
        shared.unlink()
    elif change == "modify":
        shared.write_text("// generated anew\n")
    elif change == "stage":
        shared.write_text("// generated anew\n")
        _run_git(checkout, "add", str(shared))
    elif change == "rename":
        _run_git(
            checkout,
            "mv",
            "endf_parserpy/cpp_parsers/_shared.cpp",
            "endf_parserpy/cpp_parsers/_shared_part_00.cpp",
        )
    else:
        (checkout / change).write_text("changed\n")


@pytest.mark.parametrize("change", ["delete", "modify", "stage", "rename"])
def test_generated_sources_are_not_dirty(tmp_path, monkeypatch, change):
    # a build of the C++ module removes and writes the generated
    # translation units in cpp_parsers/, some of which are tracked
    checkout = tmp_path / "checkout"
    commit = _checkout_with_shared_cpp(checkout)
    _change(checkout, change)
    record = _source_tree_record(checkout, monkeypatch)
    assert record["git_commit"] == commit
    assert record["dirty_ignored"] == "generated C++ sources"
    assert str(tmp_path) not in json.dumps(record)


@pytest.mark.parametrize(
    "change",
    [
        "endf_parserpy/__init__.py",
        "README.md",
        "endf_parserpy/cpp_parsers/helper.cpp",
        "other/_shared.cpp",
    ],
)
def test_other_changes_are_dirty(tmp_path, monkeypatch, change):
    checkout = tmp_path / "checkout"
    commit = _checkout_with_shared_cpp(checkout)
    _change(checkout, change)
    record = _source_tree_record(checkout, monkeypatch)
    assert record["git_commit"] == commit + "+dirty"
    assert "dirty_ignored" not in record
    # also with a generated source changed; that is still recorded
    _change(checkout, "delete")
    record = _source_tree_record(checkout, monkeypatch)
    assert record["git_commit"] == commit + "+dirty"
    assert record["dirty_ignored"] == "generated C++ sources"


def test_renamed_out_of_generated_sources_is_dirty(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    commit = _checkout_with_shared_cpp(checkout)
    _run_git(checkout, "mv", "endf_parserpy/cpp_parsers/_shared.cpp", "other/moved.cpp")
    record = _source_tree_record(checkout, monkeypatch)
    assert record["git_commit"] == commit + "+dirty"
    assert "dirty_ignored" not in record


def test_clean_checkout_has_no_note(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    commit = _checkout_with_shared_cpp(checkout)
    # untracked files are not looked at, generated or not
    _make_library(checkout, {"endf_parserpy/cpp_parsers/_shared_part_00.cpp": "\n"})
    record = _source_tree_record(checkout, monkeypatch)
    assert record["git_commit"] == commit
    assert "dirty_ignored" not in record


def test_installed_from_checkout_after_build(tmp_path, monkeypatch):
    # pip builds in the checkout and removes the tracked _shared.cpp
    checkout = tmp_path / "checkout"
    commit = _checkout_with_shared_cpp(checkout)
    direct_url = {"dir_info": {}, "url": checkout.as_uri()}
    _fake_install(monkeypatch, tmp_path / "site", checkout, direct_url)
    _change(checkout, "delete")
    record = _software(tmp_path)
    assert record["package_location"] == "installed from a checkout"
    assert record["git_commit"] == commit
    assert record["dirty_ignored"] == "generated C++ sources"
    assert "warnings" not in record
    # the page shows the commit without a marker
    results = _results()
    results["software"] = record
    assert f"commit {commit[:12]}\n" in br.render_machine(results)


# --- where the package is imported from -------------------------------

SITE_PACKAGES = f"lib/python{sys.version_info[0]}.{sys.version_info[1]}/site-packages"
SOURCE_TREE_WARNING = "imported from a source tree, not the installed package"


def _locate(
    monkeypatch,
    cwd,
    package_dir,
    purelib=None,
    site_packages=(),
    user_site=None,
    path0=None,
    git=False,
):
    """Make the tool see the package in ``package_dir``, with ``cwd`` as
    the current directory, the given install directories of the
    interpreter and, unless None, ``path0`` as the first entry of
    ``sys.path``; with ``git``, a ``.git`` next to the package."""
    package_dir = Path(package_dir)
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("")
    if git:
        (package_dir.parent / ".git").mkdir()
    Path(cwd).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(br, "_package_dir", lambda: str(package_dir))
    monkeypatch.setattr(br, "_distribution", lambda: None)
    paths = {"purelib": str(purelib or "/nonexistent/purelib")}
    paths["platlib"] = paths["purelib"]
    monkeypatch.setattr(br.sysconfig, "get_paths", lambda: dict(paths))
    monkeypatch.setattr(
        br.site, "getsitepackages", lambda: [str(d) for d in site_packages]
    )
    monkeypatch.setattr(
        br.site, "getusersitepackages", lambda: str(user_site or "/nonexistent/user")
    )
    if path0 is not None:
        monkeypatch.setattr(sys, "path", [str(path0), *sys.path])


@pytest.mark.parametrize("path0", ["script in cwd", "-c", "script elsewhere"])
def test_venv_under_cwd_does_not_shadow(tmp_path, monkeypatch, path0):
    # a venv in the working directory, from which the tool is run as
    # python benchmark_report.py (sys.path[0] is the directory of the
    # script), python -m benchmark_report (the current directory), or
    # python -c (''), or as a script in another directory
    site = tmp_path / "venv" / SITE_PACKAGES
    path0 = {
        "script in cwd": tmp_path,
        "-c": "",
        "script elsewhere": tmp_path / "tools",
    }[path0]
    _locate(monkeypatch, tmp_path, site / "endf_parserpy", purelib=site, path0=path0)
    location = br.package_location()
    assert location["kind"] == "installed"
    assert location["shadows"] is False


@pytest.mark.parametrize("path0", [None, "script in cwd", "-c"])
def test_source_tree_in_cwd_shadows(tmp_path, monkeypatch, path0):
    # an endf_parserpy without a .git next to it (e.g. an unpacked
    # sdist) in the current directory, also with a venv there
    site = tmp_path / "venv" / SITE_PACKAGES
    path0 = {None: None, "script in cwd": tmp_path, "-c": ""}[path0]
    _locate(
        monkeypatch, tmp_path, tmp_path / "endf_parserpy", purelib=site, path0=path0
    )
    location = br.package_location()
    assert location["kind"] == "installed"
    assert location["shadows"] is True


def test_source_tree_in_script_dir_shadows(tmp_path, monkeypatch):
    # python <dir>/benchmark_report.py with <dir>/endf_parserpy, run from
    # another directory: sys.path[0] is <dir>
    _locate(
        monkeypatch,
        tmp_path / "work",
        tmp_path / "tools" / "endf_parserpy",
        path0=tmp_path / "tools",
    )
    assert br.package_location()["shadows"] is True


def test_package_outside_cwd_does_not_shadow(tmp_path, monkeypatch):
    _locate(
        monkeypatch,
        tmp_path / "work",
        tmp_path / "elsewhere" / "endf_parserpy",
        path0=tmp_path / "work",
    )
    location = br.package_location()
    assert location["kind"] == "installed"
    assert location["shadows"] is False


def test_user_and_system_site_under_cwd_do_not_shadow(tmp_path, monkeypatch):
    # pip install --user, and a system install, both under the cwd
    user_site = tmp_path / "home" / ".local" / SITE_PACKAGES
    _locate(monkeypatch, tmp_path, user_site / "endf_parserpy", user_site=user_site)
    assert br.package_location()["shadows"] is False
    system_site = tmp_path / "usr" / "lib" / "python3" / "dist-packages"
    _locate(
        monkeypatch,
        tmp_path,
        system_site / "endf_parserpy",
        site_packages=[tmp_path / "usr" / "local" / "lib", system_site],
    )
    assert br.package_location()["shadows"] is False


def test_cwd_is_site_packages(tmp_path, monkeypatch):
    # run from site-packages itself, e.g. python -m from there
    site = tmp_path / "venv" / SITE_PACKAGES
    _locate(monkeypatch, site, site / "endf_parserpy", purelib=site, path0=site)
    assert br.package_location()["shadows"] is False


@pytest.mark.parametrize("cwd", ["checkout", "elsewhere"])
def test_source_tree_with_git(tmp_path, monkeypatch, cwd):
    # a checkout, by PYTHONPATH or an editable install, in or outside
    # the current directory: a source tree, as before
    checkout = tmp_path / "checkout"
    _locate(monkeypatch, tmp_path / cwd, checkout / "endf_parserpy", git=True)
    location = br.package_location()
    assert location["kind"] == "source tree"
    assert location["shadows"] is (cwd == "checkout")


def _measure_stderr(tmp_path, capsys):
    """The stderr of ``measure`` until it stops on an empty directory,
    after the check of the package location."""
    empty = tmp_path / "empty-library"
    empty.mkdir()
    capsys.readouterr()
    with pytest.raises(SystemExit, match="no ENDF files"):
        br.main(["measure", str(empty), "--out", str(tmp_path / "out.json")])
    return capsys.readouterr().err


@pytest.mark.parametrize(
    "case", ["venv under cwd", "source tree in cwd", "outside cwd", "git"]
)
def test_measure_source_tree_warning(tmp_path, monkeypatch, capsys, case):
    site = tmp_path / "venv" / SITE_PACKAGES
    package_dir = {
        "venv under cwd": site / "endf_parserpy",
        "source tree in cwd": tmp_path / "endf_parserpy",
        "outside cwd": tmp_path / "elsewhere" / "endf_parserpy",
        "git": tmp_path / "elsewhere" / "checkout" / "endf_parserpy",
    }[case]
    cwd = tmp_path / "work" if case in ("outside cwd", "git") else tmp_path
    _locate(monkeypatch, cwd, package_dir, purelib=site, path0=cwd, git=case == "git")
    err = _measure_stderr(tmp_path, capsys)
    expected = case in ("source tree in cwd", "git")
    assert (SOURCE_TREE_WARNING in err) is expected, err


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
        env=_tool_env(),
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    return br.load_results(str(out)), proc


def _check_measured(results):
    assert results["rounds_completed"] == 1 and results["finished"]
    # the ignored README.txt is not recorded, not even its name
    assert results["format_version"] == 2
    assert "ignored" not in results
    assert "README" not in json.dumps(results)
    assert [f["path"] for f in results["manifest"]] == [
        "decay-version.VIII.1/dec-094_Pu_244.endf",
        "nfy-version.VIII.1/broken.endf",
        "nfy-version.VIII.1/dec-094_Pu_244.endf",
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
    results, proc = _measure(tmp_path, "--modes", "numpy")
    _check_measured(results)
    assert "1 entries ignored (not an .endf file: 1)" in proc.stdout
    assert "README" not in (tmp_path / "results.json").read_text(encoding="utf-8")
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
    # a published results file of format 1 is read as well
    old = json.loads(published.read_text(encoding="utf-8"))
    old["format_version"] = 1
    old["ignored"] = [
        {"path": "decay-version.VIII.1/README.txt", "reason": "not an .endf file"}
    ]
    published.write_text(br._dump(old) + "\n", encoding="utf-8")
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
    assert "ignored" not in results


@pytest.mark.exhaustive
def test_measure_all_cells(tmp_path):
    pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
    results, _ = _measure(tmp_path)
    _check_measured(results)
    assert sorted(results["cells"]) == sorted(
        f"{p}/{m}" for p in br.PARSERS for m in br.MODES
    )
