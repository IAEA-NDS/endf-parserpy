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

"""The conformance of the readers of the framing of a tape.

The framing of a tape (the SEND, FEND, MEND and TEND records, the order
of the sections and their repetition) is checked by several
implementations: the splitting of ``EndfParserPy``, the reading loop of
``EndfParserCpp`` and ``check_framing`` of the tape layer. This test set
runs the same valid and damaged inputs through all of them, with the
filters ``include``/``exclude`` (which read sections verbatim) and with
and without ``ignore_send_records``:

- the verdicts of the two parsers agree, except for the differences
  listed in ``KNOWN_DIFFERENCES``;
- the implementations that name the offending line (counting from 1)
  name the same line;
- the exact messages of every implementation, which give the offending
  line in its own convention, are those of the golden file
  ``conformance_goldens/framing_endf6.json``. Run with the environment
  variable ``ENDF_CONFORMANCE_CAPTURE=1`` to write it anew.

The damaged inputs are those of ``test_validate_framing_records.py``
(``PU_CASES``) and ``test_section_order.py`` (``CASES``), built from the
decay file of Pu-244, and tapes of two materials.
``tools/snapshot_framing_messages.py`` writes the same results for the
installed package, to compare two versions.
"""

import contextlib
import hashlib
import io
import json
import re
import os
import tempfile
from pathlib import Path

import pytest

from endf_parserpy import EndfParserPy
from endf_parserpy.tape import check_framing
from endf_parserpy.utils.debugging_utils import compare_objects
from test_section_order import CASES as ORDER_CASES, _file as _order_file
from endf_parserpy.endf_recipes import get_tape_structure
from test_validate_framing_records import CU, PU, PU_CASES, ZN, _lines, _tape

GOLDEN = Path(__file__).resolve().parent / "conformance_goldens" / "framing_endf6.json"

FILTERS = {
    "full": {},
    "include": {"include": [8]},
    "exclude": {"exclude": [1]},
    "exclude_mt": {"exclude": [(1, 451)]},
}

OPTIONS = {
    "strict": {},
    "ignore_send_records": {"ignore_send_records": True},
}


def _cases():
    """The inputs as lists of lines (bytes, without line endings)."""
    cases = {f"pu:{name}": lines for name, lines in PU_CASES.items()}
    for name, (parts, *_) in ORDER_CASES.items():
        cases[f"order:{name}"] = _order_file(*parts)
    cases["tape:pu_twice"] = _tape([PU, PU])
    cases["tape:cu_zn"] = _tape([CU, ZN])
    return cases


CASES = _cases()

GENDF_TESTDATA = Path(__file__).resolve().parent / "testdata" / "gendf"


def _gendf_blocks():
    """The records of a GENDF test file (MF1/MT451, MF3/MT221 and
    MF6/MT221 of H-1): tape head, MF1/MT451 (without SEND record), the
    FEND record after it, the other sections with their SEND records,
    MEND and TEND records."""
    L = _lines(GENDF_TESTDATA / "h1_thermal_freegas.gendf")
    ctrl = [line[66:75] for line in L]
    fend = [i for i, c in enumerate(ctrl) if c == b" 125 0  0"][0]
    sends = [i for i, c in enumerate(ctrl) if c[6:9] == b"  0" and c[4:6] != b" 0"]
    return {
        "tpid": L[:1],
        "451": L[1:fend],
        "fend1": [L[fend]],
        "s1": L[fend + 1 : sends[0] + 1],
        "s2": L[sends[0] + 1 : sends[1] + 1],
        "mend": [L[-2]],
        "tend": [L[-1]],
    }


def _gendf_cases():
    b = _gendf_blocks()

    def tape(*parts):
        return [line for part in parts for line in b[part]]

    send_451 = b["s1"][-1][:66] + b" 125 1  0" + b["s1"][-1][75:]
    fend3 = b["fend1"][0]
    return {
        "valid": tape("tpid", "451", "fend1", "s1", "s2", "mend", "tend"),
        # the order of the sections is free, and a section may repeat
        "sections_reversed": tape("tpid", "451", "fend1", "s2", "s1", "mend", "tend"),
        "section_twice": tape("tpid", "451", "fend1", "s1", "s1", "s2", "mend", "tend"),
        # a SEND record after MF1/MT451, which the structure has without one
        "send_after_451": tape("tpid", "451")
        + [send_451]
        + tape("fend1", "s1", "s2", "mend", "tend"),
        # the FEND record after MF1 missing, a FEND record after MF3
        "fend_missing": tape("tpid", "451", "s1", "s2", "mend", "tend"),
        "fend_extra": tape("tpid", "451", "fend1", "s1")
        + [fend3]
        + tape("s2", "mend", "tend"),
        # the SEND record of the MF3 section missing
        "send_missing": tape("tpid", "451", "fend1")
        + b["s1"][:-1]
        + tape("s2", "mend", "tend"),
        "mend_missing": tape("tpid", "451", "fend1", "s1", "s2", "tend"),
    }


GENDF_CASES = _gendf_cases()
GENDF_FILTERS = {
    "full": {},
    "include": {"include": [3]},
    "exclude": {"exclude": [1]},
    "exclude_mt": {"exclude": [(1, 451)]},
}
GENDF_GOLDEN = GOLDEN.parent / "framing_gendf.json"

# The differences of the verdicts of the two parsers, by case: the filters
# and options with which one parser accepts an input that the other
# rejects. There are none: the strict-mode gaps of the C++ reader (a
# missing, second or misplaced FEND, MEND or TEND record, the MAT and MF
# numbers of the SEND records, the fields of a SEND record after a
# section read verbatim) are closed.
KNOWN_DIFFERENCES = {}

# the tapes of several materials, which are valid tapes (check_framing)
# but not a single material for a parse
_TAPES = ("tape:pu_twice", "tape:cu_zn")


def _text(lines):
    return b"".join(line + b"\n" for line in lines).decode("latin-1")


def _outcome(parse, path, kwargs):
    try:
        return parse(str(path), **kwargs), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}".replace(str(path), "<file>")


def run_case(name, cpp_class=None, flavor=None):
    """The results of the case ``name`` (of ``GENDF_CASES`` for the flavor
    ``gendf``, otherwise of ``CASES``): for every filter and option the
    messages of both parsers (``None`` for a successful parse), whether
    their results agree, and the problems found by ``check_framing``."""
    result = {}
    cases = GENDF_CASES if flavor == "gendf" else CASES
    filters = GENDF_FILTERS if flavor == "gendf" else FILTERS
    flavor_opts = {} if flavor is None else {"endf_format": flavor}
    tape_structure = None if flavor is None else get_tape_structure(flavor)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.endf"
        path.write_bytes(_text(cases[name]).encode("latin-1"))
        for option, opts in OPTIONS.items():
            py = EndfParserPy(**opts, **flavor_opts)
            cpp = cpp_class(**opts, **flavor_opts) if cpp_class is not None else None
            for filt, kwargs in filters.items():
                res_py, msg_py = _outcome(py.parsefile, path, kwargs)
                entry = {"py": msg_py}
                if cpp is not None:
                    res_cpp, msg_cpp = _outcome(cpp.parsefile, path, kwargs)
                    entry["cpp"] = msg_cpp
                    if msg_py is None and msg_cpp is None:
                        # (compare_objects prints the differences)
                        with contextlib.redirect_stdout(io.StringIO()):
                            same = compare_objects(res_py, res_cpp, fail_on_diff=False)
                        entry["same_result"] = same
                result[f"{filt}/{option}"] = entry
        result["framing"] = {
            option: [
                [p.line, p.message]
                for p in check_framing(path, tape_structure=tape_structure, **opts)
            ]
            for option, opts in OPTIONS.items()
        }
    return result


def _cpp_class():
    try:
        import importlib

        importlib.import_module("endf_parserpy.cpp_parsers._flavors")
    except ImportError:
        return None
    from endf_parserpy import EndfParserCpp

    return EndfParserCpp


def _golden():
    if not GOLDEN.exists():
        return None
    return json.loads(GOLDEN.read_text())


@pytest.fixture(scope="module")
def cpp_class():
    cls = _cpp_class()
    if cls is None:
        pytest.skip("the C++ module is not available")
    return cls


def _write_outcome(write, data, kwargs):
    try:
        text = "\n".join(write(data, **kwargs))
        if len(text) > 2000:
            text = "sha256:" + hashlib.sha256(text.encode("latin-1")).hexdigest()
        return text, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def run_writes(cpp_class=None):
    """The output of both writers (as text) or their messages for the
    material of Pu-244, the tape head alone and damaged dictionaries."""
    parsed = EndfParserPy().parsefile(str(PU))
    tpid = parsed[0][0]
    wrong_mf = {0: {0: tpid}, 1: {451: dict(parsed[1][451], MF=2)}}
    inputs = {
        "pu": (parsed, {}),
        "pu_include_8": (parsed, {"include": [8]}),
        "pu_exclude_1": (parsed, {"exclude": [1]}),
        "tpid_only": ({0: {0: tpid}}, {}),
        "nothing_included": (parsed, {"include": [3]}),
        "wrong_mf_key": (wrong_mf, {}),
    }
    result = {}
    writers = {"py": EndfParserPy()}
    if cpp_class is not None:
        writers["cpp"] = cpp_class()
    for name, (data, kwargs) in inputs.items():
        result[name] = {
            kind: dict(zip(("text", "error"), _write_outcome(w.write, data, kwargs)))
            for kind, w in writers.items()
        }
    return result


@pytest.fixture(scope="module")
def results(cpp_class):
    results = {name: run_case(name, cpp_class) for name in CASES}
    results["write"] = run_writes(cpp_class)
    return results


def test_capture_or_compare(results):
    if os.environ.get("ENDF_CONFORMANCE_CAPTURE"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
        pytest.skip("captured the golden file")
    golden = _golden()
    assert golden is not None, "no golden file"
    assert sorted(results) == sorted(golden)
    for name in results:
        assert results[name] == golden[name], name


def _differences(results):
    found = {}
    for name, result in results.items():
        if name == "write":
            continue
        for key, entry in result.items():
            if key == "framing":
                continue
            if (entry["py"] is None) != (entry["cpp"] is None) or entry.get(
                "same_result"
            ) is False:
                found.setdefault(name, []).append(key)
    return {name: sorted(keys) for name, keys in found.items()}


def test_parsers_agree(results):
    expected = {name: sorted(keys) for name, keys in KNOWN_DIFFERENCES.items()}
    assert _differences(results) == expected


def test_parse_results_agree(results):
    for name, result in results.items():
        if name == "write":
            continue
        for key, entry in result.items():
            if key in KNOWN_DIFFERENCES.get(name, ()):
                continue
            if key != "framing" and "same_result" in entry:
                assert entry["same_result"], (name, key)


def test_framing_check_agrees_with_full_parse(results):
    """check_framing finds a problem if and only if a full parse fails
    with one of the parsers (as in test_validate_framing_records)."""
    for name, result in results.items():
        if name == "write":
            continue
        if name in _TAPES:
            # valid tapes; with ignore_send_records, materials with the
            # same MAT number are not separated (test_section_order)
            assert result["framing"]["strict"] == []
            continue
        for option in OPTIONS:
            entry = result[f"full/{option}"]
            failed = entry["py"] is not None or entry["cpp"] is not None
            assert (result["framing"][option] != []) == failed, (name, option)


# the inputs for which the writers give different output
KNOWN_WRITE_DIFFERENCES = set()


def test_writers_agree(results):
    differ = {
        name for name, entry in results["write"].items() if entry["py"] != entry["cpp"]
    }
    assert differ == KNOWN_WRITE_DIFFERENCES


# the number of the offending line in a message (counting from 1): of
# EndfParserPy (a control record, a blank line, the last record of the
# record log) and of EndfParserCpp (the line appended to the message);
# None if the message gives none
_LINE_PATTERNS = (
    re.compile(r"in control record of line (\d+)\."),
    re.compile(r"\bLine (\d+) is a blank line\."),
    re.compile(r"^Line (\d+): ", re.MULTILINE),
)
_RECORD_LOG_LINE = re.compile(r"^-------- Line (\d+) -", re.MULTILINE)


def _offending_line(message):
    if message is None:
        return None
    for pattern in _LINE_PATTERNS:
        m = pattern.search(message)
        if m is not None:
            return int(m.group(1))
    found = _RECORD_LOG_LINE.findall(message)
    return int(found[-1]) if found else None


def test_offending_lines_agree(results):
    """The implementations that name the offending line name the same one,
    and for a full parse it is the line of the first problem found by
    check_framing."""
    compared = 0
    for name, result in results.items():
        if name == "write":
            continue
        for key, entry in result.items():
            if key == "framing":
                continue
            lines = {kind: _offending_line(entry.get(kind)) for kind in ("py", "cpp")}
            filt, option = key.split("/")
            problems = result["framing"][option]
            if filt == "full" and problems:
                lines["framing"] = problems[0][0]
            named = {kind: line for kind, line in lines.items() if line is not None}
            assert len(set(named.values())) <= 1, (name, key, named)
            compared += len(named) > 1
    assert compared > 100


# --- the tape structure of gendf -------------------------------------------

# the differences of the verdicts of the parsers (see KNOWN_DIFFERENCES)
KNOWN_GENDF_DIFFERENCES = {}


@pytest.fixture(scope="module")
def gendf_results(cpp_class):
    return {name: run_case(name, cpp_class, "gendf") for name in GENDF_CASES}


def test_gendf_capture_or_compare(gendf_results):
    if os.environ.get("ENDF_CONFORMANCE_CAPTURE"):
        GENDF_GOLDEN.write_text(
            json.dumps(gendf_results, indent=1, sort_keys=True) + "\n"
        )
        pytest.skip("captured the golden file")
    golden = json.loads(GENDF_GOLDEN.read_text())
    assert sorted(gendf_results) == sorted(golden)
    for name in gendf_results:
        assert gendf_results[name] == golden[name], name


def test_gendf_parsers_agree(gendf_results):
    expected = {name: sorted(keys) for name, keys in KNOWN_GENDF_DIFFERENCES.items()}
    assert _differences(gendf_results) == expected


def test_gendf_valid_cases(gendf_results):
    for name in ("valid", "sections_reversed", "section_twice"):
        result = gendf_results[name]
        assert result["framing"]["strict"] == [], name
        for key, entry in result.items():
            if key != "framing":
                assert entry["py"] is None and entry["cpp"] is None, (name, key)


def test_gendf_framing_check_agrees_with_full_parse(gendf_results):
    for name, result in gendf_results.items():
        for option in OPTIONS:
            entry = result[f"full/{option}"]
            failed = entry["py"] is not None or entry["cpp"] is not None
            assert (result["framing"][option] != []) == failed, (name, option)


def test_gendf_offending_lines_agree(gendf_results):
    for name, result in gendf_results.items():
        for key, entry in result.items():
            if key == "framing":
                continue
            lines = {kind: _offending_line(entry.get(kind)) for kind in ("py", "cpp")}
            filt, option = key.split("/")
            problems = result["framing"][option]
            if filt == "full" and problems:
                lines["framing"] = problems[0][0]
            named = {kind: line for kind, line in lines.items() if line is not None}
            assert len(set(named.values())) <= 1, (name, key, named)
