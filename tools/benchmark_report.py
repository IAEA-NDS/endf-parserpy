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

"""Measure the parsing and writing speed and the peak memory of
endf-parserpy on the sublibraries of ENDF/B-VIII.1, and render the
results for the Performance page of the documentation.

usage:
  python tools/benchmark_report.py measure <library dir> --out results.json
      [--rounds 5] [--sample-per-group 3] [--sample results.json]
      [--check-manifest results.json] [--pin-cpu N] [--no-memory]
      [--sublibraries neutrons,decay,...] [--parsers cpp,py]
      [--modes dict,list,numpy] [--max-py-seconds-per-file S]
  python tools/benchmark_report.py render results.json --out-dir docs/source/performance/
  python tools/benchmark_report.py readme-sentence results.json
  python tools/benchmark_report.py strip-ignored old.json --out new.json

``measure`` takes the directory that contains the sublibraries as
distributed by the NNDC (``neutrons-version.VIII.1``, ...), and measures
``EndfParserCpp`` on all their ENDF files and ``EndfParserPy`` on a
fixed sample, with ``array_type`` ``dict``, ``list`` and ``numpy``, each
for ``parsefile`` and ``write`` (the text in memory), in one fresh
worker process per parser and mode, with interleaved rounds and a warm
file cache, and then the peak memory in a separate pass. The results
file holds every time, the machine and software record, the manifest
of the files used (path, size, sha256) and the sample, so that another
person can check their data against it (``--check-manifest``) and reuse
the sample (``--sample``). The other entries of the directory are
skipped and only counted on the terminal; their names are not recorded.

``render`` writes the tables of the page as RST include files, the chart
(it needs matplotlib, ``measure`` does not) and a copy of the results
file. ``readme-sentence`` prints the sentence of the Performance section
of the README from the same results file. Both read the results files of
format 1 and 2.

``strip-ignored`` converts a results file of format 1, which listed the
ignored entries of the directory by name, to format 2: it removes the
list ``ignored`` and sets ``format_version`` to 2, and changes nothing
else, also not the layout of the file.

For reproducible numbers: an idle machine on AC power, the CPU pinned
(``--pin-cpu``), and the package installed, not a source tree in the
current directory, which would shadow it. The file cache is warm, so
disk speed is not measured.
"""

import argparse
import base64
import datetime
import gc
import hashlib
import json
import math
import os
import platform
import re
import shutil
import site
import subprocess
import sys
import sysconfig
import time
import urllib.parse
import urllib.request
import warnings


FORMAT = "endf-parserpy-benchmark"
# 2: no list of the ignored entries of the library directory (format 1
# had ``ignored``, a list of their paths and reasons)
FORMAT_VERSION = 2

PARSERS = ("cpp", "py")
PARSER_CLASSES = {"cpp": "EndfParserCpp", "py": "EndfParserPy"}
MODES = ("dict", "list", "numpy")

# the sublibraries of ENDF/B-VIII.1 as distributed by the NNDC, in the
# order of the page, with their names on the page
SUBLIBRARIES = (
    ("neutrons", "Neutrons"),
    ("thermal_scatt", "Thermal neutron scattering"),
    ("gammas", "Photonuclear"),
    ("decay", "Decay data"),
    ("photoat", "Photo-atomic"),
    ("standards", "Standards"),
    ("protons", "Protons"),
    ("electrons", "Electro-atomic"),
    ("atomic_relax", "Atomic relaxation"),
    ("nfy", "Neutron-induced fission yields"),
    ("sfy", "Spontaneous fission yields"),
    ("deuterons", "Deuterons"),
    ("tritons", "Tritons"),
    ("helium3s", "Helium-3"),
    ("alphas", "Alphas"),
)
SUBLIBRARY_LABELS = dict(SUBLIBRARIES)
# the small sublibraries of charged particles, one group on the page
LIGHT_CHARGED = ("deuterons", "tritons", "helium3s", "alphas")
LIGHT_CHARGED_LABEL = "Light charged particles"

SUBLIBRARY_DIR = re.compile(r"^([a-z0-9_]+)-version\.(.+)$")

# the bounds of the size groups in bytes (1 kB = 1000 bytes)
DEFAULT_SIZE_BOUNDS = (100e3, 1e6, 10e6)
MB = 1e6


# --- the machine ------------------------------------------------------


def cpu_model():
    """Marketing name of the CPU, e.g. "Apple M1" or "Intel(R) Core(TM) ...".

    Linux: /proc/cpuinfo; macOS: sysctl machdep.cpu.brand_string;
    Windows: ProcessorNameString in the registry (the name shown by the
    Task Manager). Falls back to platform.processor().
    """
    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    elif system == "Darwin":
        try:
            name = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if name:
                return name
        except (OSError, subprocess.CalledProcessError):
            pass
    elif system == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            if name:
                return name.strip()
        except (ImportError, OSError):
            pass
    return platform.processor() or platform.machine()


def short_cpu_name(model):
    """The CPU model without trademarks, generation and clock, e.g.
    "Intel Core i7-1165G7" for "11th Gen Intel(R) Core(TM) i7-1165G7 @
    2.80GHz"."""
    name = re.sub(r"\((R|TM|tm|r)\)", "", model)
    name = re.sub(r"\b\d+(st|nd|rd|th) Gen\b", "", name)
    name = re.sub(r"@.*$", "", name)
    name = re.sub(r"\b(CPU|Processor)\b", "", name)
    return " ".join(name.split())


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _cpufreq_mhz(cpu, name):
    value = _read(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/{name}")
    try:
        return round(int(value) / 1000)
    except (TypeError, ValueError):
        return "unknown"


def _boost():
    no_turbo = _read("/sys/devices/system/cpu/intel_pstate/no_turbo")
    if no_turbo in ("0", "1"):
        return no_turbo == "0"
    boost = _read("/sys/devices/system/cpu/cpufreq/boost")
    if boost in ("0", "1"):
        return boost == "1"
    return "unknown"


def _power_supply():
    """("AC" or "battery" or "unknown", whether there is a battery)."""
    base = "/sys/class/power_supply"
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return "unknown", "unknown"
    mains = []
    battery = False
    for name in names:
        kind = _read(os.path.join(base, name, "type"))
        if kind == "Mains":
            mains.append(_read(os.path.join(base, name, "online")) == "1")
        elif kind == "Battery":
            battery = True
    if mains:
        return ("AC" if any(mains) else "battery"), battery
    return "unknown", battery


def _os_name():
    if platform.system() == "Linux":
        text = _read("/etc/os-release") or ""
        for line in text.splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    if platform.system() == "Darwin":
        return "macOS " + platform.mac_ver()[0]
    return f"{platform.system()} {platform.release()}"


def _ram_bytes():
    text = _read("/proc/meminfo") or ""
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) * 1024
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return "unknown"


def machine_record(pin_cpu=None):
    """The parts of the machine that matter for single-threaded speed;
    no host name, user or disk details."""
    cpu = pin_cpu if pin_cpu is not None else 0
    power, battery = _power_supply()
    return {
        "cpu": cpu_model(),
        "architecture": platform.machine(),
        "base_clock_mhz": _cpufreq_mhz(cpu, "base_frequency"),
        "max_clock_mhz": _cpufreq_mhz(cpu, "cpuinfo_max_freq"),
        "boost": _boost(),
        "governor": _read(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
        or "unknown",
        "platform_profile": _read("/sys/firmware/acpi/platform_profile") or "unknown",
        "power": power,
        "battery": battery,
        "ram_bytes": _ram_bytes(),
        "os": _os_name(),
        "kernel": platform.release(),
        "pin_cpu": pin_cpu,
    }


def _load_average():
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except (OSError, AttributeError):
        return None


# --- the software -----------------------------------------------------


def _is_under(path, directory):
    path = os.path.normcase(os.path.realpath(path))
    directory = os.path.normcase(os.path.realpath(directory))
    try:
        return os.path.commonpath([path, directory]) == directory
    except ValueError:
        return False


def _git(checkout, *args, strip=True):
    try:
        out = subprocess.run(
            ["git", "-C", checkout, *args],
            capture_output=True,
            text=True,
            errors="surrogateescape",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() if strip else out.stdout


# what is recorded as ``dirty_ignored`` if only such files changed
GENERATED_SOURCES_NOTE = "generated C++ sources"


def _generated_tu_matcher():
    """``is_generated_tu_filename`` of the imported endf_parserpy, which
    the build of this package used; None if it has none."""
    try:
        from endf_parserpy.compiler.compiler import is_generated_tu_filename
    except ImportError:
        return None
    return is_generated_tu_filename


def _status_entries(checkout):
    """The changes to tracked files in ``checkout`` from ``git status
    --porcelain -z``: a list of ``(XY, paths)``, the paths relative to
    the top level of the repository, two of them (new, old) for a rename
    or copy; None if git fails."""
    out = _git(
        checkout, "status", "--porcelain", "-z", "--untracked-files=no", strip=False
    )
    if out is None:
        return None
    fields = out.split("\0")
    entries = []
    i = 0
    while i < len(fields):
        field = fields[i]
        i += 1
        if len(field) < 4:
            continue
        xy, paths = field[:2], [field[3:]]
        if ("R" in xy or "C" in xy) and i < len(fields):
            paths.append(fields[i])
            i += 1
        entries.append((xy, paths))
    return entries


def _checkout_changes(checkout):
    """Whether tracked files in ``checkout`` changed, as ``(dirty,
    ignored)``: changes to the translation units that a build of the C++
    module writes into ``endf_parserpy/cpp_parsers/`` (and removes before
    writing new ones) are build output; they set ``ignored``, not
    ``dirty``. Every other change, and a conflict, sets ``dirty``."""
    entries = _status_entries(checkout)
    if not entries:
        return False, False
    is_generated = _generated_tu_matcher()
    prefix = _git(checkout, "rev-parse", "--show-prefix")
    if is_generated is None or prefix is None:
        return True, False
    prefix += "endf_parserpy/cpp_parsers/"

    def generated(path):
        if not path.startswith(prefix):
            return False
        name = path[len(prefix) :]
        return "/" not in name and is_generated(name)

    dirty = ignored = False
    for xy, paths in entries:
        conflict = "U" in xy or xy in ("AA", "DD")
        if not conflict and all(generated(path) for path in paths):
            ignored = True
        else:
            dirty = True
    return dirty, ignored


def _package_dir():
    import endf_parserpy

    return os.path.dirname(os.path.abspath(endf_parserpy.__file__))


def _distribution():
    """The installed distribution of endf-parserpy, None if there is none."""
    from importlib import metadata

    try:
        return metadata.distribution("endf-parserpy")
    except metadata.PackageNotFoundError:
        return None


def _record_sha256(path):
    """The sha256 of a file in the form of the ``RECORD`` of a wheel:
    urlsafe base64 without padding."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return base64.urlsafe_b64encode(h.digest()).rstrip(b"=").decode("ascii")


def _installed_py_differs(dist, checkout):
    """Whether the ``.py`` files of the package installed as ``dist``
    differ from those in ``checkout``: a hash in ``RECORD`` that differs
    from the file in the checkout, a file missing in the checkout, or a
    ``.py`` file tracked in the checkout that is not installed."""
    installed = set()
    for entry in dist.files or ():
        path = str(entry).replace("\\", "/")
        if not (path.startswith("endf_parserpy/") and path.endswith(".py")):
            continue
        installed.add(path)
        if entry.hash is None or entry.hash.mode != "sha256":
            return True
        local = os.path.join(checkout, *path.split("/"))
        if not os.path.isfile(local) or _record_sha256(local) != entry.hash.value:
            return True
    if not installed:
        return True
    tracked = _git(checkout, "ls-files", "--", "endf_parserpy")
    if tracked is None:
        return True
    return any(p.endswith(".py") and p not in installed for p in tracked.splitlines())


def _installed_location(package_dir):
    """The origin of an installed package from the ``direct_url.json``
    (PEP 610) of its distribution: a dictionary with ``kind``,
    ``checkout``, ``commit`` and ``warnings``. The URL itself is not
    returned, so that no local path reaches the results."""
    location = {"kind": "installed", "checkout": None, "commit": None, "warnings": []}
    dist = _distribution()
    if dist is None:
        return location
    # only the distribution of the imported package counts
    init = dist.locate_file("endf_parserpy/__init__.py")
    try:
        if not os.path.samefile(init, os.path.join(package_dir, "__init__.py")):
            return location
    except OSError:
        return location
    try:
        text = dist.read_text("direct_url.json")
        direct_url = json.loads(text) if text else None
    except (OSError, ValueError):
        direct_url = None
    if not isinstance(direct_url, dict):
        return location
    url = direct_url.get("url", "")
    vcs_info = direct_url.get("vcs_info")
    dir_info = direct_url.get("dir_info")
    if isinstance(vcs_info, dict):
        location["kind"] = "installed from a repository"
        commit = vcs_info.get("commit_id")
        if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{7,64}", commit):
            location["commit"] = commit
    elif isinstance(dir_info, dict) and not dir_info.get("editable"):
        if not url.startswith("file:"):
            return location
        directory = urllib.request.url2pathname(urllib.parse.urlparse(url).path)
        location["kind"] = "installed from a directory"
        if _git(directory, "rev-parse", "--show-toplevel") is None:
            return location
        location["kind"] = "installed from a checkout"
        location["checkout"] = directory
        if _installed_py_differs(dist, directory):
            location["modified"] = True
            location["warnings"].append(
                "the installed .py files of endf_parserpy differ from those "
                "of the checkout it was installed from; the commit is marked "
                "+modified"
            )
    return location


def _tool_checkout():
    """The checkout of this tool, if it is one."""
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return parent if os.path.exists(os.path.join(parent, ".git")) else None


def _same_dir(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(
        os.path.realpath(b)
    )


def _install_dirs():
    """The directories into which this interpreter installs packages: the
    ``purelib`` and ``platlib`` of its install scheme (those of the venv
    in a venv), the site-packages directories and the user site-packages
    directory."""
    dirs = []
    paths = sysconfig.get_paths()
    dirs.extend(paths[key] for key in ("purelib", "platlib") if paths.get(key))
    for get in ("getsitepackages", "getusersitepackages"):
        try:
            found = getattr(site, get)()
        except Exception:
            continue
        dirs.extend([found] if isinstance(found, str) else found)
    return [d for d in dirs if d]


def _shadows_installed(package_dir):
    """Whether the package in ``package_dir`` is one that is imported
    instead of an installed package: it is not in an install directory
    of the interpreter (``_install_dirs``), and it is under the current
    directory or in the first entry of ``sys.path``, the directory of
    the script (or the current directory for ``python -m`` and ``-c``).
    A venv under the current directory is not such a package."""
    parent = os.path.dirname(package_dir)
    if any(_same_dir(parent, d) for d in _install_dirs()):
        return False
    if _is_under(package_dir, os.getcwd()):
        return True
    first = sys.path[0] if sys.path else None
    return first is not None and _same_dir(parent, first or os.getcwd())


def package_location():
    """Where the imported endf_parserpy is, as ``kind``: ``"source tree"``
    (a checkout, e.g. by ``PYTHONPATH`` or an editable install),
    ``"installed from a checkout"``, ``"installed from a directory"``
    (not a git checkout), ``"installed from a repository"`` (a VCS URL)
    or ``"installed"`` (e.g. a wheel from PyPI), the latter four from the
    ``direct_url.json`` of the distribution; whether it ``shadows`` an
    installed package (see ``_shadows_installed``); the checkout
    for the git commit; the commit of a VCS URL; whether the installed
    files differ from the checkout (``modified``); and warnings."""
    package_dir = _package_dir()
    parent = os.path.dirname(package_dir)
    if os.path.exists(os.path.join(parent, ".git")):
        location = {
            "kind": "source tree",
            "checkout": parent,
            "commit": None,
            "warnings": [],
        }
    else:
        location = _installed_location(package_dir)
    location["shadows"] = _shadows_installed(package_dir)
    location.setdefault("modified", False)
    return location


def cpp_module_info():
    """``_build_info()`` and the parts of ``_bulk_body_info()`` of the C++
    module that matter for speed, "unknown" for a module without them."""
    import importlib

    try:
        module = importlib.import_module("endf_parserpy.cpp_parsers._flavors")
    except ImportError as exc:
        return {"available": False, "error": str(exc)}
    info = {"available": True}
    build = getattr(module, "_build_info", None)
    info["build_info"] = dict(build()) if build is not None else "unknown"
    bulk = getattr(module, "_bulk_body_info", None)
    if bulk is not None:
        b = bulk()
        info["simd_tier"] = b.get("selected", "unknown")
        info["compiler_family"] = b.get("compiler", "unknown")
    else:
        info["simd_tier"] = info["compiler_family"] = "unknown"
    origin = None
    if isinstance(info["build_info"], dict):
        origin = info["build_info"].get("origin")
    info["origin"] = {
        "cibuildwheel": "wheel",
        "setup.py": "source build",
        "cmake": "source build (CMake)",
    }.get(origin, "unknown")
    return info


def software_record(location=None):
    import endf_parserpy

    if location is None:
        location = package_location()
    record = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "endf_parserpy": endf_parserpy.__version__,
        "package_location": location["kind"],
        "git_commit": None,
        "git_describe": None,
    }
    try:
        import numpy

        record["numpy"] = numpy.__version__
    except ImportError:
        record["numpy"] = None
    if location["checkout"]:
        commit = _git(location["checkout"], "rev-parse", "HEAD")
        if commit:
            dirty, ignored = _checkout_changes(location["checkout"])
            record["git_commit"] = commit + ("+dirty" if dirty else "")
            if ignored:
                record["dirty_ignored"] = GENERATED_SOURCES_NOTE
            record["git_describe"] = _git(location["checkout"], "describe", "--tags")
    elif location["commit"]:
        record["git_commit"] = location["commit"]
        # a describe only if the checkout of this tool has the commit
        tool_checkout = _tool_checkout()
        if (
            tool_checkout
            and _git(tool_checkout, "cat-file", "-e", location["commit"] + "^{commit}")
            is not None
        ):
            record["git_describe"] = _git(
                tool_checkout, "describe", "--tags", location["commit"]
            )
    if record["git_commit"] and location["modified"]:
        record["git_commit"] += "+modified"
    if location["warnings"]:
        record["warnings"] = list(location["warnings"])
    record["cpp_module"] = cpp_module_info()
    return record


# --- the data ---------------------------------------------------------


def endf_file_reason(path):
    """None for an ENDF file, otherwise why the file is ignored: an ENDF
    file has the extension ``.endf`` and a tape head (TPID) as its first
    line, with MF=0 and MT=0 in columns 71-75 (the MAT number in columns
    67-70 may be blank, as in ENDF/B-VIII.1)."""
    if not path.lower().endswith(".endf"):
        return "not an .endf file"
    try:
        with open(path, "rb") as f:
            first = f.readline(200).decode("latin-1").rstrip("\r\n")
    except OSError as exc:
        return f"cannot be read: {exc.strerror}"
    try:
        mf, mt = int(first[70:72]), int(first[72:75])
        if first[66:70].strip():
            int(first[66:70])
    except ValueError:
        return "the first line is not a tape head"
    if mf != 0 or mt != 0:
        return "the first line is not a tape head"
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def discover(root, sublibraries=None):
    """The ENDF files of the sublibraries in ``root`` and the ignored
    entries.

    A sublibrary is a directory ``<name>-version.<version>`` with a
    known name (see ``SUBLIBRARIES``). Returns ``(files, ignored,
    library)``: the files as dictionaries with ``path`` (relative to
    ``root``, with ``/``), ``sublibrary`` and ``size``, sorted by path;
    the ignored entries with their path and reason; and the library
    name (e.g. "ENDF/B-VIII.1"), from the versions of the directories.
    """
    files, ignored, versions = [], [], set()
    wanted = None if sublibraries is None else set(sublibraries)
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        match = SUBLIBRARY_DIR.match(name)
        if not os.path.isdir(full):
            ignored.append({"path": name, "reason": "not a sublibrary directory"})
            continue
        if not match or match.group(1) not in SUBLIBRARY_LABELS:
            ignored.append({"path": name, "reason": "not a known sublibrary"})
            continue
        sublibrary = match.group(1)
        if wanted is not None and sublibrary not in wanted:
            continue
        versions.add(match.group(2))
        for entry in sorted(os.listdir(full)):
            relpath = f"{name}/{entry}"
            path = os.path.join(full, entry)
            if not os.path.isfile(path):
                ignored.append({"path": relpath, "reason": "not a file"})
                continue
            reason = endf_file_reason(path)
            if reason is not None:
                ignored.append({"path": relpath, "reason": reason})
                continue
            files.append(
                {
                    "path": relpath,
                    "sublibrary": sublibrary,
                    "size": os.path.getsize(path),
                }
            )
    if wanted is not None:
        missing = wanted - set(f["sublibrary"] for f in files)
        for sublibrary in sorted(missing):
            ignored.append({"path": sublibrary, "reason": "sublibrary not found"})
    library = None
    if len(versions) == 1:
        library = "ENDF/B-" + versions.pop()
    elif versions:
        library = "ENDF/B (" + ", ".join(sorted(versions)) + ")"
    return files, ignored, library


def size_group(size, bounds=DEFAULT_SIZE_BOUNDS):
    """The index of the size group of a file of ``size`` bytes."""
    for i, bound in enumerate(bounds):
        if size < bound:
            return i
    return len(bounds)


def _format_size(nbytes):
    for unit, factor in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if nbytes >= factor:
            value = nbytes / factor
            return f"{value:g} {unit}" if value == int(value) else f"{value:.3g} {unit}"
    return f"{nbytes:g} B"


def size_group_labels(bounds=DEFAULT_SIZE_BOUNDS):
    """E.g. ["< 100 kB", "100 kB – 1 MB", "1 MB – 10 MB", "≥ 10 MB"]."""
    labels = [f"< {_format_size(bounds[0])}"]
    for low, high in zip(bounds, bounds[1:]):
        labels.append(f"{_format_size(low)} – {_format_size(high)}")
    labels.append(f"≥ {_format_size(bounds[-1])}")
    return labels


def select_sample(files, per_group=3, bounds=DEFAULT_SIZE_BOUNDS):
    """The sample for ``EndfParserPy``: per sublibrary and size group, up
    to ``per_group`` files at the quantiles 1/(2k), 3/(2k), ... of the
    files of the group sorted by size and then by path. No randomness:
    the same files give the same sample, in any order. Returns the paths,
    sorted."""
    groups = {}
    for f in files:
        key = (f["sublibrary"], size_group(f["size"], bounds))
        groups.setdefault(key, []).append(f)
    sample = []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda f: (f["size"], f["path"]))
        n, k = len(members), per_group
        if n <= k:
            chosen = members
        else:
            chosen = [members[int((2 * i + 1) * n / (2 * k))] for i in range(k)]
        sample.extend(f["path"] for f in chosen)
    return sorted(sample)


def check_manifest(manifest, reference):
    """Compare the manifest of the data with a published one: the files
    that are missing, that differ (size or sha256) and that are extra."""
    ours = {f["path"]: f for f in manifest}
    theirs = {f["path"]: f for f in reference}
    missing = sorted(set(theirs) - set(ours))
    extra = sorted(set(ours) - set(theirs))
    different = sorted(
        p
        for p in set(ours) & set(theirs)
        if (ours[p]["size"], ours[p]["sha256"])
        != (theirs[p]["size"], theirs[p]["sha256"])
    )
    return {
        "missing": missing,
        "different": different,
        "extra": extra,
        "identical": not (missing or different or extra),
    }


# --- the worker -------------------------------------------------------


def _short_error(exc):
    text = str(exc).strip().splitlines()
    text = text[0] if text else ""
    return f"{type(exc).__name__}: {text}"[:300]


def _warning_kind(w, root):
    message = str(w.message).strip().splitlines()
    message = message[0] if message else ""
    message = message.replace(root, "<data>")
    message = re.sub(r"\d+", "#", message)
    return f"{w.category.__name__}: {message}"[:160]


def _proc_status_kb(field):
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith(field + ":"):
                return int(line.split()[1])
    raise RuntimeError(f"no {field} in /proc/self/status")


def _malloc_trim():
    # return the free memory of the C heap to the system (glibc), so that
    # the resident memory before a measurement is that in use
    try:
        import ctypes

        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


def _reset_hwm():
    with open("/proc/self/clear_refs", "w") as f:
        f.write("5")


def clear_refs_works():
    """Whether the peak resident memory of this process can be reset
    (Linux: ``/proc/self/clear_refs``)."""
    if platform.system() != "Linux":
        return False
    try:
        _reset_hwm()
        return _proc_status_kb("VmHWM") <= _proc_status_kb("VmRSS") + 64
    except (OSError, RuntimeError, ValueError):
        return False


def _maxrss_bytes():
    import resource

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if platform.system() == "Darwin" else rss * 1024


def _make_parser(parser, mode):
    if parser == "cpp":
        from endf_parserpy import EndfParserCpp

        return EndfParserCpp(array_type=mode)
    from endf_parserpy import EndfParserPy

    return EndfParserPy(array_type=mode)


def worker_main(args):
    """A worker process for one parser and mode: reads one command per
    line from stdin and answers with one JSON line on its stdout (the
    package's own output goes to the null device)."""
    proto = os.fdopen(os.dup(1), "w")
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    sys.stdout = open(os.devnull, "w")
    root = args.root
    parser = _make_parser(args.parser, args.mode)
    # the warnings are recorded, not printed, every one of them
    catcher = warnings.catch_warnings(record=True)
    recorded = catcher.__enter__()
    warnings.simplefilter("always")
    proto.write(json.dumps({"ready": True}) + "\n")
    proto.flush()
    for line in sys.stdin:
        cmd = json.loads(line)
        if cmd["cmd"] == "quit":
            break
        path = os.path.join(root, cmd["path"])
        answer = {}
        del recorded[:]
        gc.collect()
        if cmd["cmd"] == "time":
            answer = _time_file(parser, path)
        elif cmd["cmd"] == "memory":
            answer = _memory_file(parser, path, cmd.get("fresh", False))
        if cmd.get("count_warnings"):
            kinds = {}
            for w in recorded:
                kind = _warning_kind(w, root)
                kinds[kind] = kinds.get(kind, 0) + 1
            answer["warnings"] = kinds
        del recorded[:]
        gc.collect()
        proto.write(json.dumps(answer) + "\n")
        proto.flush()
    catcher.__exit__(None, None, None)


def _time_file(parser, path):
    try:
        t0 = time.perf_counter_ns()
        obj = parser.parsefile(path)
        t1 = time.perf_counter_ns()
    except Exception as exc:
        return {"error": _short_error(exc), "operation": "parse"}
    try:
        t2 = time.perf_counter_ns()
        lines = parser.write(obj)
        t3 = time.perf_counter_ns()
    except Exception as exc:
        return {"error": _short_error(exc), "operation": "write"}
    nbytes = sum(len(x) for x in lines) + len(lines)
    del obj, lines
    return {"parse_ns": t1 - t0, "write_ns": t3 - t2, "bytes_written": nbytes}


def _memory_file(parser, path, fresh):
    # the increase of the peak resident memory while parsing and while
    # writing; with the reset of the peak (Linux), the increase over the
    # resident memory before; in a fresh process (no reset), the increase
    # of the peak, for writing over the peak of parsing (a lower bound)
    try:
        _malloc_trim()
        if fresh:
            base = _maxrss_bytes()
        else:
            _reset_hwm()
            base = _proc_status_kb("VmRSS") * 1024
        obj = parser.parsefile(path)
        if fresh:
            after_parse = _maxrss_bytes()
            parse_peak = after_parse - base
            base = after_parse
        else:
            parse_peak = _proc_status_kb("VmHWM") * 1024 - base
            _reset_hwm()
            base = _proc_status_kb("VmRSS") * 1024
        lines = parser.write(obj)
        if fresh:
            write_peak = _maxrss_bytes() - base
        else:
            write_peak = _proc_status_kb("VmHWM") * 1024 - base
        del obj, lines
    except Exception as exc:
        return {"error": _short_error(exc), "operation": "memory"}
    return {"parse_peak": max(parse_peak, 0), "write_peak": max(write_peak, 0)}


class Worker:
    """The coordinator's handle of a worker process."""

    def __init__(self, parser, mode, root):
        self.parser, self.mode, self.root = parser, mode, root
        self.proc = None

    @property
    def key(self):
        return f"{self.parser}/{self.mode}"

    def start(self):
        cmd = [
            sys.executable,
            os.path.abspath(__file__),
            "_worker",
            self.parser,
            self.mode,
            self.root,
        ]
        env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env
        )
        ready = self.proc.stdout.readline()
        if not ready:
            raise RuntimeError(f"the worker {self.key} did not start")

    def request(self, cmd):
        """The answer of the worker; if the worker ends (e.g. killed for
        lack of memory), an error, and the worker is started anew."""
        try:
            self.proc.stdin.write(json.dumps(cmd) + "\n")
            self.proc.stdin.flush()
            answer = self.proc.stdout.readline()
        except (BrokenPipeError, OSError):
            answer = ""
        if answer:
            return json.loads(answer)
        code = self.proc.wait()
        self.start()
        return {
            "error": f"the worker process ended (exit status {code})",
            "operation": cmd["cmd"],
        }

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=60)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
        self.proc = None


# --- measure ----------------------------------------------------------


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _split_list(text, allowed, what):
    values = [v.strip() for v in text.split(",") if v.strip()]
    unknown = [v for v in values if v not in allowed]
    if unknown:
        raise SystemExit(f"unknown {what}: {', '.join(unknown)}")
    return values


def _human_seconds(seconds):
    if seconds < 120:
        return f"{seconds:.0f} s"
    if seconds < 7200:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"


def _estimation_file(files):
    # the file for the estimate of the time: the smallest of at least
    # 100 kB, otherwise the largest
    large = [f for f in files if f["size"] >= 100e3]
    if large:
        return min(large, key=lambda f: (f["size"], f["path"]))
    return max(files, key=lambda f: (f["size"], f["path"]))


def measure(args):
    root = os.path.abspath(args.datadir)
    sublibraries = (
        _split_list(args.sublibraries, SUBLIBRARY_LABELS, "sublibraries")
        if args.sublibraries
        else None
    )
    parsers = _split_list(args.parsers, PARSERS, "parsers")
    modes = _split_list(args.modes, MODES, "modes")
    bounds = tuple(float(b) for b in args.size_bounds.split(","))
    if list(bounds) != sorted(bounds):
        raise SystemExit("--size-bounds must be ascending")

    load_start = _load_average()
    if load_start is not None and load_start[0] > 0.5:
        print(
            f"warning: the load average is {load_start[0]} (above 0.5); "
            "the machine is not idle",
            file=sys.stderr,
        )
    if args.pin_cpu is not None:
        if not hasattr(os, "sched_setaffinity"):
            raise SystemExit("--pin-cpu needs os.sched_setaffinity (Linux)")
        os.sched_setaffinity(0, {args.pin_cpu})

    location = package_location()
    if location["shadows"] or location["kind"] == "source tree":
        print(
            "warning: endf_parserpy is imported from a source tree, not the "
            "installed package",
            file=sys.stderr,
        )
    for text in location["warnings"]:
        print(f"warning: {text}", file=sys.stderr)

    started = _now()
    files, ignored, library = discover(root, sublibraries)
    if not files:
        raise SystemExit(f"no ENDF files of known sublibraries in {args.datadir}")
    # the manifest; reading every file also warms the file cache
    for f in files:
        f["sha256"] = sha256_file(os.path.join(root, f["path"]))
    manifest = [
        {k: f[k] for k in ("path", "sublibrary", "size", "sha256")} for f in files
    ]
    total = sum(f["size"] for f in files)
    # the ignored entries are only counted here: their names (the user's
    # own files next to the data, for example) are not recorded
    reasons = {}
    for entry in ignored:
        reasons[entry["reason"]] = reasons.get(entry["reason"], 0) + 1
    print(
        f"{len(files)} ENDF files ({total / MB:.1f} MB) in "
        f"{len(set(f['sublibrary'] for f in files))} sublibraries, "
        f"{len(ignored)} entries ignored"
        + (
            " (" + ", ".join(f"{r}: {n}" for r, n in sorted(reasons.items())) + ")"
            if reasons
            else ""
        )
    )

    manifest_check = None
    if args.check_manifest:
        reference = load_results(args.check_manifest)["manifest"]
        if sublibraries is not None:
            reference = [f for f in reference if f["sublibrary"] in sublibraries]
        manifest_check = check_manifest(manifest, reference)
        if manifest_check["identical"]:
            print("the data are identical to the published manifest")
        else:
            for key in ("missing", "different", "extra"):
                for path in manifest_check[key]:
                    print(f"manifest: {key}: {path}", file=sys.stderr)

    by_path = {f["path"]: f for f in files}
    if args.sample:
        published = load_results(args.sample)["sample"]
        sample_paths = []
        for entry in published["files"]:
            f = by_path.get(entry["path"])
            if f is None:
                if sublibraries is None or entry["path"].split("-version.")[0] in (
                    sublibraries
                ):
                    print(f"sample: missing: {entry['path']}", file=sys.stderr)
                continue
            if f["sha256"] != entry["sha256"]:
                print(f"sample: different: {entry['path']}", file=sys.stderr)
            sample_paths.append(entry["path"])
        sample = {
            "source": "reused",
            "per_group": published.get("per_group"),
            "paths": sorted(sample_paths),
        }
    else:
        sample = {
            "source": "selected",
            "per_group": args.sample_per_group,
            "paths": select_sample(files, args.sample_per_group, bounds),
        }

    configs = [(p, m) for p in PARSERS if p in parsers for m in MODES if m in modes]
    cell_files = {}
    for parser, mode in configs:
        paths = [f["path"] for f in files] if parser == "cpp" else sample["paths"]
        cell_files[f"{parser}/{mode}"] = paths

    results = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "placeholder": bool(args.placeholder),
        "library": library,
        "started": started,
        "finished": None,
        "rounds_completed": 0,
        "settings": {
            "rounds": args.rounds,
            "sample_per_group": sample["per_group"],
            "size_bounds": list(bounds),
            "parsers": parsers,
            "modes": modes,
            "sublibraries": sublibraries,
            "memory": not args.no_memory,
            "max_py_seconds_per_file": args.max_py_seconds_per_file,
        },
        "machine": machine_record(args.pin_cpu),
        "software": software_record(location),
        "load_average": {"start": load_start, "end": None},
        "manifest": manifest,
        "manifest_check": manifest_check,
        "sample": {
            "source": sample["source"],
            "per_group": sample["per_group"],
            "files": [
                {"path": p, "sha256": by_path[p]["sha256"]} for p in sample["paths"]
            ],
        },
        "excluded": [],
        "memory_method": None,
        "warnings": {},
        "cells": {
            key: {"parser": key.split("/")[0], "mode": key.split("/")[1], "files": {}}
            for key in cell_files
        },
    }
    errors = {}  # path -> list of errors

    def save():
        results["excluded"] = [
            {
                "path": path,
                "sublibrary": by_path[path]["sublibrary"],
                "errors": errors[path],
            }
            for path in sorted(errors)
        ]
        write_results(args.out, results)

    workers = [Worker(p, m, root) for p, m in configs]
    try:
        for w in workers:
            w.start()
        # the warm-up and the estimate of the time
        est_file = _estimation_file([by_path[p] for p in sample["paths"]] or files)
        print(f"warm-up with {est_file['path']} ({est_file['size'] / MB:.2f} MB)")
        estimate = {}
        for w in workers:
            answer = w.request({"cmd": "time", "path": est_file["path"]})
            if "error" in answer:
                estimate[w.key] = None
                continue
            per_byte = (
                (answer["parse_ns"] + answer["write_ns"]) / 1e9 / est_file["size"]
            )
            nbytes = sum(by_path[p]["size"] for p in cell_files[w.key])
            estimate[w.key] = per_byte * nbytes * args.rounds
        for parser in parsers:
            total_s = sum(v for k, v in estimate.items() if k.startswith(parser) and v)
            print(
                f"expected time of the {PARSER_CLASSES[parser]} cells: "
                f"about {_human_seconds(total_s)} for {args.rounds} round(s)"
            )

        limited = {key: set() for key in cell_files}
        for rnd in range(1, args.rounds + 1):
            shift = (rnd - 1) % len(workers)
            for w in workers[shift:] + workers[:shift]:
                cell = results["cells"][w.key]["files"]
                cell_warnings = results["warnings"].setdefault(w.key, {})
                t_start = time.perf_counter()
                parse_ns = write_ns = 0
                for path in cell_files[w.key]:
                    if path in errors or (rnd > 1 and path in limited[w.key]):
                        continue
                    answer = w.request(
                        {"cmd": "time", "path": path, "count_warnings": rnd == 1}
                    )
                    for kind, count in answer.pop("warnings", {}).items():
                        entry = cell_warnings.setdefault(
                            kind, {"count": 0, "files": 0, "examples": []}
                        )
                        entry["count"] += count
                        entry["files"] += 1
                        if len(entry["examples"]) < 3:
                            entry["examples"].append(path)
                    if "error" in answer:
                        errors.setdefault(path, []).append(
                            {
                                "cell": w.key,
                                "operation": answer["operation"],
                                "error": answer["error"],
                            }
                        )
                        cell.pop(path, None)
                        continue
                    entry = cell.setdefault(
                        path, {"parse_ns": [], "write_ns": [], "bytes_written": None}
                    )
                    entry["parse_ns"].append(answer["parse_ns"])
                    entry["write_ns"].append(answer["write_ns"])
                    entry["bytes_written"] = answer["bytes_written"]
                    parse_ns += answer["parse_ns"]
                    write_ns += answer["write_ns"]
                    limit = args.max_py_seconds_per_file
                    if (
                        w.parser == "py"
                        and rnd == 1
                        and limit is not None
                        and (answer["parse_ns"] + answer["write_ns"]) / 1e9 > limit
                    ):
                        limited[w.key].add(path)
                        entry["limited"] = True
                print(
                    f"round {rnd}/{args.rounds} {w.key}: parse {parse_ns / 1e9:.2f} s,"
                    f" write {write_ns / 1e9:.2f} s"
                    f" (wall {time.perf_counter() - t_start:.1f} s)"
                )
            results["rounds_completed"] = rnd
            save()
    finally:
        for w in workers:
            w.stop()

    if not args.no_memory:
        fresh = not clear_refs_works()
        if fresh and platform.system() == "Windows":
            print("memory: not measured on Windows", file=sys.stderr)
        else:
            results["memory_method"] = "fresh_process" if fresh else "clear_refs"
            print(f"memory pass ({results['memory_method']})")
            for parser, mode in configs:
                w = Worker(parser, mode, root)
                cell = results["cells"][w.key]["files"]
                w.start()
                try:
                    for path in cell_files[w.key]:
                        if path in errors:
                            continue
                        if fresh:
                            w.stop()
                            w.start()
                        answer = w.request(
                            {"cmd": "memory", "path": path, "fresh": fresh}
                        )
                        if "error" in answer:
                            errors.setdefault(path, []).append(
                                {
                                    "cell": w.key,
                                    "operation": "memory",
                                    "error": answer["error"],
                                }
                            )
                            continue
                        cell[path]["parse_peak"] = answer["parse_peak"]
                        cell[path]["write_peak"] = answer["write_peak"]
                finally:
                    w.stop()
                print(f"memory {w.key}: done")

    # files failing in any cell are dropped from all cells
    for cell in results["cells"].values():
        for path in errors:
            cell["files"].pop(path, None)
    results["load_average"]["end"] = _load_average()
    results["finished"] = _now()
    save()
    print(f"results written to {args.out}")
    if errors:
        print(f"{len(errors)} file(s) excluded (see 'excluded' in the results)")


# --- the results file -------------------------------------------------


def _dump(obj, indent=0):
    # nested objects one level per line down to small leaves, so that the
    # file is diffable: a file entry or manifest record is one line
    compact = json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
    if not isinstance(obj, (dict, list)) or len(compact) <= 100 or indent >= 8:
        return compact
    pad = " " * (indent + 2)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [
            f"{pad}{json.dumps(k, ensure_ascii=False)}: {_dump(v, indent + 2)}"
            for k, v in obj.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"
    items = [f"{pad}{_dump(v, indent + 2)}" for v in obj]
    return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"


def write_results(path, results):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(_dump(results) + "\n")
    os.replace(tmp, path)


def strip_ignored(results):
    """A results file of format 1 in format 2: without the list
    ``ignored`` of the entries of the directory that are not ENDF files
    of a sublibrary, and with ``format_version`` 2. Everything else,
    including the order of the keys, is unchanged."""
    validate_results(results)
    if results["format_version"] != 1:
        raise ValueError(
            f"the results are in format {results['format_version']}, not 1"
        )
    stripped = {k: v for k, v in results.items() if k != "ignored"}
    stripped["format_version"] = 2
    validate_results(stripped)
    return stripped


def strip_ignored_file(path, out):
    """``strip-ignored``: convert the results file ``path`` of format 1
    to format 2 in ``out``. The input must be in the layout that
    ``measure`` writes, so that the output differs from it only by the
    removed lines and the line of ``format_version``."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    results = json.loads(text)
    if _dump(results) + "\n" != text:
        raise ValueError(
            f"{path} is not in the layout that measure writes; "
            "it is not converted, so that its other lines stay unchanged"
        )
    write_results(out, strip_ignored(results))


def load_results(path):
    with open(path, encoding="utf-8") as f:
        results = json.load(f)
    validate_results(results)
    return results


_TOP_LEVEL = {
    "format": str,
    "format_version": int,
    "placeholder": bool,
    "started": str,
    "rounds_completed": int,
    "settings": dict,
    "machine": dict,
    "software": dict,
    "load_average": dict,
    "manifest": list,
    "sample": dict,
    "excluded": list,
    "warnings": dict,
    "cells": dict,
}


def validate_results(results):
    """Check the schema of a results file; raises ValueError naming the
    problems."""
    problems = []
    for key, kind in _TOP_LEVEL.items():
        if not isinstance(results.get(key), kind):
            problems.append(f"{key}: missing or not a {kind.__name__}")
    if problems:
        raise ValueError("invalid results file: " + "; ".join(problems))
    if results["format"] != FORMAT:
        problems.append(f"format is not {FORMAT!r}")
    if results["format_version"] > FORMAT_VERSION:
        problems.append(f"format_version {results['format_version']} is newer")
    elif results["format_version"] < 1:
        problems.append(f"format_version {results['format_version']} is unknown")
    elif results["format_version"] == 1:
        if not isinstance(results.get("ignored"), list):
            problems.append("ignored: missing or not a list (format 1)")
    elif "ignored" in results:
        problems.append("ignored: not recorded from format 2 on (see strip-ignored)")
    paths = set()
    for f in results["manifest"]:
        if set(f) != {"path", "sublibrary", "size", "sha256"}:
            problems.append(f"manifest entry {f.get('path')}: wrong keys")
        elif f["sublibrary"] not in SUBLIBRARY_LABELS:
            problems.append(f"manifest entry {f['path']}: unknown sublibrary")
        elif os.path.isabs(f["path"]) or "\\" in f["path"]:
            problems.append(f"manifest entry {f['path']}: not a relative path")
        paths.add(f.get("path"))
    for entry in results["sample"].get("files", []):
        if entry.get("path") not in paths:
            problems.append(f"sample file {entry.get('path')} not in the manifest")
    for key, cell in results["cells"].items():
        if cell.get("parser") not in PARSERS or cell.get("mode") not in MODES:
            problems.append(f"cell {key}: unknown parser or mode")
            continue
        if key != f"{cell['parser']}/{cell['mode']}":
            problems.append(f"cell {key}: key does not match")
        for path, entry in cell.get("files", {}).items():
            if path not in paths:
                problems.append(f"cell {key}: {path} not in the manifest")
                continue
            parse, write = entry.get("parse_ns"), entry.get("write_ns")
            if not parse or not write or len(parse) != len(write):
                problems.append(f"cell {key}: {path}: wrong times")
            if not isinstance(entry.get("bytes_written"), int):
                problems.append(f"cell {key}: {path}: no bytes_written")
    for entry in results["excluded"]:
        if not entry.get("errors"):
            problems.append(f"excluded {entry.get('path')}: no errors")
    if problems:
        raise ValueError("invalid results file: " + "; ".join(problems[:20]))


# --- aggregation ------------------------------------------------------


def _median(values):
    values = sorted(values)
    n = len(values)
    mid = n // 2
    return values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2


def excluded_paths(results):
    return set(e["path"] for e in results["excluded"])


def usable_manifest(results):
    """The manifest without the excluded files."""
    excluded = excluded_paths(results)
    return [f for f in results["manifest"] if f["path"] not in excluded]


def page_groups(results):
    """The groups of the page in its order: (key, label, sublibraries),
    with the light charged particles as one group; only groups with
    files."""
    present = set(f["sublibrary"] for f in results["manifest"])
    groups = []
    for name, label in SUBLIBRARIES:
        if name in LIGHT_CHARGED:
            continue
        if name in present:
            groups.append((name, label, (name,)))
    light = tuple(s for s in LIGHT_CHARGED if s in present)
    if light:
        groups.append(("light_charged", LIGHT_CHARGED_LABEL, light))
    return groups


def totals(results, cell_key, paths):
    """The sums over ``paths`` of the median, minimum and maximum times
    (s) of a cell, the input and output bytes and the number of files;
    None if the cell lacks one of the files."""
    cell = results["cells"].get(cell_key)
    if cell is None or not paths:
        return None
    sizes = {f["path"]: f["size"] for f in results["manifest"]}
    t = {
        "files": 0,
        "bytes_in": 0,
        "bytes_out": 0,
        "limited": 0,
    }
    for op in ("parse", "write"):
        t[op] = t[op + "_min"] = t[op + "_max"] = 0.0
    for path in paths:
        entry = cell["files"].get(path)
        if entry is None:
            return None
        t["files"] += 1
        t["bytes_in"] += sizes[path]
        t["bytes_out"] += entry["bytes_written"]
        t["limited"] += bool(entry.get("limited"))
        for op in ("parse", "write"):
            times = entry[op + "_ns"]
            t[op] += _median(times) / 1e9
            t[op + "_min"] += min(times) / 1e9
            t[op + "_max"] += max(times) / 1e9
    t["parse_mbs"] = t["bytes_in"] / MB / t["parse"] if t["parse"] else None
    t["write_mbs"] = t["bytes_out"] / MB / t["write"] if t["write"] else None
    return t


def cell_paths(results, parser, sublibraries=None, group=None):
    """The files of a parser's cells: all usable files for ``cpp``, the
    usable files of the sample for ``py``; optionally only those of the
    given sublibraries and size group."""
    bounds = results["settings"]["size_bounds"]
    sample = set(e["path"] for e in results["sample"]["files"])
    paths = []
    for f in usable_manifest(results):
        if sublibraries is not None and f["sublibrary"] not in sublibraries:
            continue
        if group is not None and size_group(f["size"], bounds) != group:
            continue
        if parser == "py" and f["path"] not in sample:
            continue
        paths.append(f["path"])
    return paths


def cell_keys(results):
    return [
        f"{p}/{m}" for p in PARSERS for m in MODES if f"{p}/{m}" in results["cells"]
    ]


# --- render -----------------------------------------------------------


def _mbs(value):
    if value is None:
        return "—"
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _seconds(value):
    if value < 0.01:
        return f"{value * 1000:.2f} ms"
    if value < 0.1:
        return f"{value * 1000:.1f} ms"
    if value < 1:
        return f"{value * 1000:.0f} ms"
    if value < 10:
        return f"{value:.2f} s"
    if value < 60:
        return f"{value:.1f} s"
    if value < 3600:
        return f"{value / 60:.1f} min"
    return f"{value / 3600:.2f} h"


def _spread(t, op):
    if not t[op]:
        return ""
    return f" ±{(t[op + '_max'] - t[op + '_min']) / 2 / t[op] * 100:.1f} %"


def _mb(nbytes):
    return f"{nbytes / MB:.1f} MB" if nbytes >= 10 * MB else f"{nbytes / MB:.2f} MB"


def _files(n):
    return f"{n} file" if n == 1 else f"{n} files"


def _cell_label(key):
    parser, mode = key.split("/")
    star = "\\ :sup:`*`" if parser == "py" else ""
    return f"``{PARSER_CLASSES[parser]}`` ``{mode}``{star}"


def _list_table(header, rows, widths=None, title=None):
    lines = [f".. list-table::{(' ' + title) if title else ''}", "   :header-rows: 1"]
    if widths:
        lines.append("   :widths: " + " ".join(str(w) for w in widths))
    lines.append("")
    for row in [header] + rows:
        first = True
        for value in row:
            prefix = "   * - " if first else "     - "
            lines.append(prefix + (str(value) if str(value) != "" else ".."))
            first = False
    lines.append("")
    return lines


def _placeholder_note(results):
    if not results.get("placeholder"):
        return []
    return [
        ".. warning::",
        "",
        "   **Placeholder.** These numbers come from a few small test files",
        "   of the repository, not from ENDF/B-VIII.1; they only show the",
        "   layout of the page. The measurement over the sublibraries of",
        "   ENDF/B-VIII.1 replaces them.",
        "",
    ]


def _measurement_line(results):
    software = results["software"]
    version = software["endf_parserpy"]
    describe = software.get("git_describe")
    if describe and describe.lstrip("v") != version:
        version = f"{version} (development version {describe})"
    date = results["started"][:10]
    return f"Measured on {date} with endf-parserpy {version}."


def render_summary(results):
    keys = cell_keys(results)
    header = ["Sublibrary"] + [_cell_label(k) for k in keys]
    rows = []
    groups = page_groups(results)
    for name, label, subs in groups + [("all", "All", None)]:
        if name == "all" and len(groups) < 2:
            continue
        row = [f"**{label}**" if name == "all" else label]
        if name == "light_charged":
            row[0] += "\\ :sup:`†`"
        for key in keys:
            t = totals(results, key, cell_paths(results, key.split("/")[0], subs))
            row.append(
                "—" if t is None else f"{_mbs(t['parse_mbs'])} / {_mbs(t['write_mbs'])}"
            )
        rows.append(row)
    lines = _placeholder_note(results)
    lines += _list_table(header, rows)
    lines += [
        "Throughput in MB/s (1 MB = 10\\ :sup:`6` bytes), parsing / writing:",
        "the bytes of the files over the time of ``parsefile``, and the bytes",
        "written over the time of ``write``, summed over the files of the",
        "sublibrary.",
        "",
        f"\\ :sup:`*` On the sample of {len(cell_paths(results, 'py'))} files"
        " (see below)."
        + (
            " \\ :sup:`†` Deuterons, tritons, helium-3 and alphas, which"
            " have only a few files each, as one group."
            if any(g[0] == "light_charged" for g in groups)
            else ""
        ),
        "",
        _measurement_line(results),
        "",
    ]
    return "\n".join(lines)


def render_method(results, prefix):
    settings = results["settings"]
    n_used = len(usable_manifest(results))
    n_sample = len(cell_paths(results, "py"))
    excluded = len(results["excluded"])
    library = results.get("library") or "the library"
    text = [
        f"The files are the {n_used} ENDF files of {library} that every cell",
        "parses and writes;",
        f"{_files(excluded)} that fail{'s' if excluded == 1 else ''} in a cell"
        f" {'is' if excluded == 1 else 'are'} excluded from all cells and listed",
        "with the errors in the results file",
        f"(:download:`results.json <{prefix}/results.json>`, key ``excluded``).",
        "Each file is measured in",
        f"{settings['rounds']} rounds; a time is the sum of the medians per",
        "file, its spread (±) half the difference of the sums of the maxima",
        "and minima, relative to it.",
        f"``EndfParserPy`` is measured on a sample of {n_sample} files: per",
        "sublibrary and size group, up to",
        f"{settings['sample_per_group']} files at fixed quantiles of the",
        "file size, chosen without randomness; ``EndfParserCpp`` is measured",
        "on all files, and so also on the sample.",
    ]
    limited = sum(
        bool(e.get("limited"))
        for c in results["cells"].values()
        for e in c["files"].values()
    )
    if limited:
        text.append(
            f"{limited} measurement(s) of ``EndfParserPy`` over the time"
            " limit per file have one round only."
        )
    return "\n".join(text) + "\n"


def render_machine(results):
    m, s = results["machine"], results["software"]
    cpp = s.get("cpp_module", {})
    build = cpp.get("build_info") if isinstance(cpp.get("build_info"), dict) else {}

    def mhz(value):
        return f"{value / 1000:.2f} GHz" if isinstance(value, (int, float)) else value

    def text(value):
        if value is True:
            return "yes"
        if value is False:
            return "no"
        return "unknown" if value is None else str(value)

    ram = m.get("ram_bytes")
    rows = [
        ["CPU", m.get("cpu")],
        [
            "Clock (base / maximum)",
            f"{mhz(m.get('base_clock_mhz'))} / " f"{mhz(m.get('max_clock_mhz'))}",
        ],
        ["Boost", text(m.get("boost"))],
        ["Frequency governor", text(m.get("governor"))],
        ["Platform power profile", text(m.get("platform_profile"))],
        ["Power", text(m.get("power"))],
        ["Memory", f"{ram / 2**30:.0f} GiB" if isinstance(ram, int) else text(ram)],
        ["Operating system", f"{m.get('os')}, kernel {m.get('kernel')}"],
        [
            "CPU pinning",
            "core " + str(m["pin_cpu"]) if m.get("pin_cpu") is not None else "none",
        ],
        ["Python", f"{s.get('python')} ({s.get('python_implementation')})"],
        ["numpy", text(s.get("numpy"))],
    ]
    version = s.get("endf_parserpy")
    if s.get("git_commit"):
        commit, plus, suffix = s["git_commit"].partition("+")
        version += f", commit {commit[:12]}{plus}{suffix}"
    rows.append(["endf-parserpy", version])
    rows.append(["C++ module", text(cpp.get("origin"))])
    if build:
        rows.append(
            ["Compiler", f"{build.get('compiler')} {build.get('compiler_version')}"]
        )
        rows.append(
            [
                "Optimization",
                f"{build.get('optimization')} "
                f"({build.get('build_type')}, {build.get('cpp_standard')})",
            ]
        )
    else:
        rows.append(["Compiler", text(cpp.get("compiler_family"))])
    rows.append(["Vector tier of the row kernels", text(cpp.get("simd_tier"))])
    rows = [[k, str(v).replace("*", "\\*")] for k, v in rows]
    lines = _placeholder_note(results)
    lines += _list_table(["Item", "Value"], rows, widths=[1, 2])
    return "\n".join(lines)


def render_by_sublibrary(results):
    keys = cell_keys(results)
    lines = []
    for name, label, subs in page_groups(results):
        cpp_paths = cell_paths(results, "cpp", subs)
        py_paths = cell_paths(results, "py", subs)
        sizes = {f["path"]: f["size"] for f in results["manifest"]}
        nbytes = sum(sizes[p] for p in cpp_paths)
        lines += [f".. rubric:: {label}", ""]
        if name == "light_charged":
            lines += [
                "The sublibraries "
                + ", ".join(f"``{s}``" for s in subs)
                + ", as one group.",
                "",
            ]
        lines += [
            f"{_files(len(cpp_paths))}, {_mb(nbytes)}; the sample: "
            f"{_files(len(py_paths))}, {_mb(sum(sizes[p] for p in py_paths))}.",
            "",
        ]
        rows = []
        for key in keys:
            parser = key.split("/")[0]
            t = totals(results, key, cpp_paths if parser == "cpp" else py_paths)
            if t is None:
                continue
            rows.append(
                [
                    _cell_label(key),
                    t["files"],
                    _seconds(t["parse"]) + _spread(t, "parse"),
                    _mbs(t["parse_mbs"]),
                    _seconds(t["write"]) + _spread(t, "write"),
                    _mbs(t["write_mbs"]),
                ]
            )
        header = ["Parser, ``array_type``", "Files", "Parse", "MB/s", "Write", "MB/s"]
        lines += _list_table(header, rows, widths=[4, 1, 3, 1, 3, 1])
        ratio_rows = []
        for mode in MODES:
            cpp = totals(results, f"cpp/{mode}", py_paths)
            py = totals(results, f"py/{mode}", py_paths)
            if cpp is None or py is None or not cpp["parse"] or not cpp["write"]:
                continue
            ratio_rows.append(
                [
                    f"``{mode}``",
                    f"{py['parse'] / cpp['parse']:.0f}",
                    f"{py['write'] / cpp['write']:.0f}",
                ]
            )
        if ratio_rows:
            lines += _list_table(
                ["``array_type``", "Parse", "Write"],
                ratio_rows,
                title="Time of EndfParserPy over EndfParserCpp, on the sample",
            )
    return "\n".join(lines)


def _size_rows(results):
    bounds = results["settings"]["size_bounds"]
    labels = size_group_labels(bounds)
    rows = []
    for i, label in enumerate(labels):
        cpp_paths = cell_paths(results, "cpp", group=i)
        if not cpp_paths:
            continue
        py_paths = cell_paths(results, "py", group=i)
        cells = {}
        for key in cell_keys(results):
            parser = key.split("/")[0]
            cells[key] = totals(
                results, key, cpp_paths if parser == "cpp" else py_paths
            )
        rows.append((i, label, cpp_paths, py_paths, cells))
    return rows


def render_by_size(results, prefix):
    keys = cell_keys(results)
    lines = _placeholder_note(results)
    lines += [
        f".. image:: {prefix}/throughput_by_size.svg",
        "   :alt: Throughput in MB/s over the size groups of the files,",
        "         parsing and writing, one line per parser and array_type",
        "   :width: 100%",
        "",
    ]
    header = ["File size", "Files (sample)"] + [_cell_label(k) for k in keys]
    rows = []
    for _, label, cpp_paths, py_paths, cells in _size_rows(results):
        row = [label, f"{len(cpp_paths)} ({len(py_paths)})"]
        for key in keys:
            t = cells[key]
            row.append(
                "—" if t is None else f"{_mbs(t['parse_mbs'])} / {_mbs(t['write_mbs'])}"
            )
        rows.append(row)
    lines += _list_table(header, rows)
    lines += [
        "Throughput in MB/s, parsing / writing, over all sublibraries.",
        "",
    ]
    return "\n".join(lines)


def render_memory(results):
    keys = [k for k in cell_keys(results)]
    sizes = {f["path"]: f for f in results["manifest"]}
    bounds = results["settings"]["size_bounds"]
    labels = size_group_labels(bounds)
    lines = _placeholder_note(results)
    if not results.get("memory_method"):
        lines += ["The peak memory was not measured.", ""]
        return "\n".join(lines)
    header = ["Sublibrary", "File size"] + [_cell_label(k) for k in keys]
    rows = []
    largest_rows = []
    for name, label, subs in page_groups(results):
        for i, group_label in enumerate(labels):
            row = [label, group_label]
            found = False
            for key in keys:
                parser = key.split("/")[0]
                paths = cell_paths(results, parser, subs, group=i)
                factors = [
                    results["cells"][key]["files"][p]["parse_peak"] / sizes[p]["size"]
                    for p in paths
                    if "parse_peak" in results["cells"][key]["files"].get(p, {})
                ]
                if factors:
                    found = True
                    row.append(f"{_median(factors):.1f}")
                else:
                    row.append("—")
            if found:
                rows.append(row)
        cpp_paths = cell_paths(results, "cpp", subs)
        if cpp_paths:
            largest = max(cpp_paths, key=lambda p: (sizes[p]["size"], p))
            row = [
                label,
                f"{os.path.basename(largest)} ({_mb(sizes[largest]['size'])})",
            ]
            for key in keys:
                entry = results["cells"][key]["files"].get(largest, {})
                row.append(_mb(entry["parse_peak"]) if "parse_peak" in entry else "—")
            largest_rows.append(row)
    lines += _list_table(header, rows)
    lines += [
        "The peak memory of parsing over the file size: the median per",
        "sublibrary and size group of the increase of the peak resident",
        "memory of the process while parsing a file, divided by the size of",
        "the file.",
        "",
    ]
    lines += _list_table(
        ["Sublibrary", "Largest file"] + [_cell_label(k) for k in keys],
        largest_rows,
    )
    lines += [
        "The increase of the peak resident memory while parsing the largest",
        "file of each sublibrary (— if it is not in the sample).",
        "",
    ]
    return "\n".join(lines)


# the colors of the modes (a validated categorical order), the line
# styles and markers of the parsers
_MODE_COLORS = {"dict": "#2a78d6", "list": "#eb6834", "numpy": "#1baf7a"}
_PARSER_STYLES = {"cpp": ("-", "o"), "py": ("--", "s")}


def render_chart(results, path):
    import matplotlib

    matplotlib.use("svg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker

    rc = {
        "svg.hashsalt": "endf-parserpy-benchmark",
        "svg.fonttype": "none",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": "#8a8984",
        "axes.labelcolor": "#0b0b0b",
        "xtick.color": "#52514e",
        "ytick.color": "#52514e",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
    rows = _size_rows(results)
    with matplotlib.rc_context(rc):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
        xs = list(range(len(rows)))
        for ax, op, title in zip(axes, ("parse", "write"), ("Parsing", "Writing")):
            for key in cell_keys(results):
                parser, mode = key.split("/")
                ys = [
                    r[4][key][op + "_mbs"] if r[4][key] is not None else None
                    for r in rows
                ]
                points = [(x, y) for x, y in zip(xs, ys) if y]
                if not points:
                    continue
                style, marker = _PARSER_STYLES[parser]
                ax.plot(
                    [p[0] for p in points],
                    [p[1] for p in points],
                    linestyle=style,
                    marker=marker,
                    markersize=5,
                    linewidth=2,
                    color=_MODE_COLORS[mode],
                    label=f"{PARSER_CLASSES[parser]} {mode}",
                )
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
            )
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_title(title, loc="left", fontsize=11)
            ax.set_xticks(xs)
            ax.set_xticklabels([r[1] for r in rows])
            ax.set_xlabel("File size")
            ax.grid(True, which="major", axis="y", color="#e4e3df", linewidth=0.8)
            ax.set_axisbelow(True)
        axes[0].set_ylabel("MB/s")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, -0.02),
        )
        fig.tight_layout(rect=(0, 0.14, 1, 1))
        fig.savefig(path, format="svg", metadata={"Date": None, "Creator": None})
        plt.close(fig)
    # without trailing spaces (which matplotlib writes in some lines), so
    # that the committed file is the rendered one
    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render(args):
    results = load_results(args.results)
    out = args.out_dir.rstrip("/\\")
    os.makedirs(out, exist_ok=True)
    prefix = os.path.basename(os.path.abspath(out))
    files = {
        "summary.rst": render_summary(results),
        "method.rst": render_method(results, prefix),
        "machine.rst": render_machine(results),
        "by_sublibrary.rst": render_by_sublibrary(results),
        "by_size.rst": render_by_size(results, prefix),
        "memory.rst": render_memory(results),
    }
    for name, content in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(content.rstrip("\n") + "\n")
    render_chart(results, os.path.join(out, "throughput_by_size.svg"))
    target = os.path.join(out, "results.json")
    if os.path.abspath(target) != os.path.abspath(args.results):
        shutil.copyfile(args.results, target)
    print(f"rendered into {out}")


# --- the README sentence ----------------------------------------------


def _in_about(seconds):
    if seconds < 0.75:
        return "in under a second"
    if seconds >= 120:
        return f"in about {round(seconds / 60)} minutes"
    value = round(seconds)
    return f"in about {value} second{'s' if value != 1 else ''}"


def readme_sentence(results):
    """The sentence of the Performance section of the README: the
    neutron sublibrary with ``EndfParserCpp`` and ``array_type="numpy"``."""
    paths = cell_paths(results, "cpp", ("neutrons",))
    t = totals(results, "cpp/numpy", paths)
    if t is None:
        raise ValueError("the results have no EndfParserCpp numpy cell for neutrons")
    m, s = results["machine"], results["software"]
    kind = "laptop" if m.get("battery") is True else "machine"
    describe = s.get("git_describe") or ""
    if re.search(r"-\d+-g[0-9a-f]+$", describe) or "dev" in s["endf_parserpy"]:
        date = datetime.date.fromisoformat(results["started"][:10])
        when = f"on the development version of {date.strftime('%B %Y')}"
    else:
        when = f"with version {s['endf_parserpy']}"
    library = results.get("library") or "ENDF/B-VIII.1"
    size = t["bytes_in"]
    size_text = f"{size / 1e9:.1f} GB" if size >= 1e9 else f"{size / MB:.0f} MB"
    return (
        f'With the C++ backend and `array_type="numpy"`, `endf-parserpy` reads '
        f"the complete neutron sublibrary of {library} — {t['files']} files, "
        f"{size_text} — {_in_about(t['parse'])} and writes it "
        f"back to ENDF-6 text {_in_about(t['write'])} (single "
        f"core of an {short_cpu_name(m['cpu'])} {kind}, warm file cache; "
        f"measured {when})."
    )


def _wrap(text, width=70):
    words, lines, line = text.split(" "), [], ""
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    lines.append(line)
    return "\n".join(lines)


# --- main -------------------------------------------------------------


def main(argv=None):
    cli = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0].replace("\n", " ")
    )
    sub = cli.add_subparsers(dest="command", required=True)

    p = sub.add_parser("measure", help="measure the files of a library")
    p.add_argument("datadir", help="the directory with the sublibraries")
    p.add_argument("--out", required=True, help="the results file (JSON)")
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--sample-per-group", type=int, default=3)
    p.add_argument("--sample", help="reuse the sample of this results file")
    p.add_argument("--check-manifest", help="check the data against this results file")
    p.add_argument("--pin-cpu", type=int, help="run on this CPU only (Linux)")
    p.add_argument("--no-memory", action="store_true")
    p.add_argument("--sublibraries", help="e.g. neutrons,decay (default: all)")
    p.add_argument("--parsers", default="cpp,py")
    p.add_argument("--modes", default="dict,list,numpy")
    p.add_argument(
        "--max-py-seconds-per-file",
        type=float,
        help="measure a file of EndfParserPy over this time in one round only",
    )
    p.add_argument(
        "--size-bounds",
        default=",".join(f"{b:g}" for b in DEFAULT_SIZE_BOUNDS),
        help="the bounds of the size groups in bytes (default 1e5,1e6,1e7)",
    )
    p.add_argument(
        "--placeholder",
        action="store_true",
        help="mark the results as a placeholder (not the library)",
    )

    p = sub.add_parser("render", help="render the tables and the chart")
    p.add_argument("results")
    p.add_argument("--out-dir", required=True)

    p = sub.add_parser("readme-sentence", help="print the sentence of the README")
    p.add_argument("results")

    p = sub.add_parser(
        "strip-ignored",
        help="convert a results file of format 1 to format 2 (without the "
        "names of the ignored entries)",
    )
    p.add_argument("results")
    p.add_argument("--out", required=True)

    p = sub.add_parser("_worker")
    p.add_argument("parser", choices=PARSERS)
    p.add_argument("mode", choices=MODES)
    p.add_argument("root")

    args = cli.parse_args(argv)
    if args.command == "measure":
        if args.rounds < 1:
            raise SystemExit("--rounds must be at least 1")
        measure(args)
    elif args.command == "render":
        render(args)
    elif args.command == "readme-sentence":
        results = load_results(args.results)
        if results.get("placeholder"):
            print("warning: the results are a placeholder", file=sys.stderr)
        print(_wrap(readme_sentence(results)))
    elif args.command == "strip-ignored":
        try:
            strip_ignored_file(args.results, args.out)
        except ValueError as exc:
            raise SystemExit(f"error: {exc}")
        print(f"written {args.out} (format 2)")
    elif args.command == "_worker":
        worker_main(args)


if __name__ == "__main__":
    main()
