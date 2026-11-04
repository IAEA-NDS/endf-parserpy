############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The bulk form of the bodies of LIST records gives the results and
errors of the per-field form.

The bodies of the test recipes MF10 (endf_recipes/test/endf_recipe_mf10.py)
are read in the bulk form by default and in the per-field form with
ENDF_PARSERPY_CPP_BULK_BODIES=off; each runs in a subprocess (the variable
is read when the module is loaded, see test_cpp_float_row_kernel.py, whose
script the subprocesses run), also with the scalar row kernel forced,
which reads all bodies with a loop in the bulk form, not only those with
a regular layout. The inputs are valid bodies and bodies with
errors at chosen places, in particular:

- a check that fails before a field that cannot be converted, in one
  body (the check must be reported, for its line);
- a field that cannot be converted in the middle of a body delivered by
  strided copies;
- NPL different from the number of values of the layout, and NPL=0;
- short, blank, too long and non-ASCII lines, lines of another material
  and the end of the data within a body;
- for the reading of a body as one byte range (CppListBody::fast_body):
  CRLF line endings, mixed line endings, a tab, a byte of 127 or more,
  lines of 80 columns, MAT/MF/MT in another form, the end of the data
  within a body and a body of one line, which is not read as a range.

The results (values with their bits, types and array layouts) and the
errors (type and message, which names the line) must be identical, and
the counters of the module must show that the strided delivery, the
delivery by the code of the per-field form and a stopped conversion all
occurred, and which bodies were read as one byte range and which line by
line.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


ENV_VAR = "ENDF_PARSERPY_CPP_BULK_BODIES"
WORKER = Path(__file__).parent / "test_cpp_float_row_kernel.py"
ARRAY_TYPES = ("numpy", "list", "dict")
BASE_OPTIONS = {
    "endf_format": "test",
    "ignore_missing_tpid": True,
}
OPTION_SETS = (
    {},
    {"ignore_zero_mismatch": False, "ignore_varspec_mismatch": False},
    {"ignore_number_mismatch": True},
    {"validate_control_records": True, "accept_non_ascii": False},
    {"ignore_blank_lines": True},
    {"accept_d_exponent": False, "accept_spaces": False},
)


def _float(x):
    # an 11-character float field as written in ENDF-6 files
    if x == 0:
        return " 0.000000+0"
    s = f"{x:.6e}"
    mant, exp = s.split("e")
    e = int(exp)
    return f"{mant:>8}{'+' if e >= 0 else '-'}{abs(e)}".rjust(11)[-11:]


def _int(n):
    return f"{n:11d}"


def _line(fields, mf, mt, mat=1):
    text = "".join(fields).ljust(66)
    return f"{text}{mat:4d}{mf:2d}{mt:3d}"


def _body_lines(values, mf, mt):
    fields = [v if isinstance(v, str) else _float(v) for v in values]
    return [_line(fields[i : i + 6], mf, mt) for i in range(0, len(fields), 6)]


def _send(mf, mt):
    # SEND, FEND, MEND and TEND records
    zeros = [_float(0)] * 2 + [_int(0)] * 4
    return [
        _line(zeros, mf, 0),
        _line(zeros, 0, 0),
        _line(zeros, 0, 0, mat=0),
        _line(zeros, 0, 0, mat=-1),
    ]


def _list(head_ints, values, mf, mt, npl=None):
    npl = len(values) if npl is None else npl
    n1, n2 = head_ints
    head = _line([_float(0), _float(0), _int(n1), _int(n2), _int(npl), _int(0)], mf, mt)
    return [head] + _body_lines(values, mf, mt)


def _mt1_values(n, m):
    # A, B, {X[k], 0.0, {Y[k,m]}{m=1 to M}}{k=1 to N}
    values = [1.5, -2.25]
    for k in range(1, n + 1):
        values.append(float(k) + 0.125)
        values.append(0.0)
        values.extend(100.0 * k + mm + 0.5 for mm in range(1, m + 1))
    return values


def _mt1(values, n=3, m=4, npl=None):
    return _list((n, m), values, 10, 1, npl) + _send(10, 1)


def _mt2(n, npl=None, values=None):
    if values is None:
        values = [10.0 * k + l for k in range(1, n + 1) for l in range(k, n + 1)]
    return _list((n, 0), values, 10, 2, npl) + _send(10, 2)


def _mt3(values, n, npl=None):
    return _list((n, 0), values, 10, 3, npl) + _send(10, 3)


def _mt4(ni, nk, values_of=None):
    lines = [_line([_float(0), _float(0), _int(ni), _int(nk), _int(0), _int(0)], 10, 4)]
    for i in range(1, ni + 1):
        values = [1000.0 * i + k for k in range(1, nk + 1)] + [0.0]
        if values_of is not None:
            values = values_of(i, values)
        lines += _list((0, 0), values, 10, 4)
    return lines + _send(10, 4)


def _mt5(n, npl=None):
    values = [7.0 + k for k in range(1, n + 1)]
    return _list((n, 0), values, 10, 5, npl) + _send(10, 5)


def _replace(lines, lineno, field, text):
    # field `field` (0..5) of line `lineno` replaced by text
    line = lines[lineno]
    lines = list(lines)
    lines[lineno] = line[: 11 * field] + text.ljust(11)[:11] + line[11 * field + 11 :]
    return lines


def _cases():
    cases = {}
    valid1 = _mt1(_mt1_values(3, 4))
    cases["mt1_valid"] = valid1
    cases["mt1_large"] = _mt1(_mt1_values(40, 9), n=40, m=9)
    # a field that cannot be converted in the middle of the body
    cases["mt1_malformed_mid"] = _replace(valid1, 2, 3, "1.23x456+00")
    # the conversion stops at a field of another form (D exponent), which
    # the general path converts (or not, with accept_d_exponent=False)
    cases["mt1_dexp_mid"] = _replace(valid1, 2, 1, "1.234567D+1")
    # a failing check (0.0 of k=1, value 3) before a malformed field
    chk = _replace(valid1, 1, 3, " 5.000000+0")
    cases["mt1_check_then_malformed"] = _replace(chk, 3, 0, "abcdefghijk")
    cases["mt1_check_only"] = chk
    # a failing check in the last iteration
    cases["mt1_check_last"] = _replace(valid1, 3, 3, " 2.000000+0")
    # NPL larger and smaller than the number of values of the layout
    cases["mt1_npl_large"] = _mt1(_mt1_values(3, 4) + [9.0], npl=21)
    cases["mt1_npl_small"] = _mt1(_mt1_values(3, 4)[:19], npl=19)
    cases["mt1_npl_small_line"] = _mt1(_mt1_values(3, 4)[:18], npl=18)
    cases["mt1_npl_zero"] = _mt1([], npl=0)
    cases["mt1_n_zero"] = _mt1(_mt1_values(0, 4), n=0)
    # a short line (the missing columns are blanks) and a cut line
    short = list(valid1)
    short[2] = short[2][:40]
    cases["mt1_short_line"] = short
    cut = list(valid1)
    cut[3] = cut[3][:12]
    cases["mt1_cut_last_line"] = cut
    # a blank line, a line too long, a non-ASCII byte, another MAT
    blank = list(valid1)
    blank.insert(3, "")
    cases["mt1_blank_line"] = blank
    long_line = list(valid1)
    long_line[2] = long_line[2] + "    1  extra"
    cases["mt1_long_line"] = long_line
    nonascii = list(valid1)
    nonascii[3] = nonascii[3][:20] + "é" + nonascii[3][21:]
    cases["mt1_non_ascii"] = nonascii
    other_mat = list(valid1)
    other_mat[2] = other_mat[2][:66] + "   2" + other_mat[2][70:]
    cases["mt1_other_mat"] = other_mat
    # a check that fails before a line of another material
    cases["mt1_check_then_mat"] = _replace(other_mat, 1, 3, " 5.000000+0")
    # the end of the data within the body
    cases["mt1_truncated"] = valid1[:3]
    # lines with CR LF endings and a line with fewer columns before it
    crlf = [s + "\r" for s in valid1]
    cases["mt1_crlf"] = crlf
    # triangular matrix: code of the per-field form
    cases["mt2_valid"] = _mt2(5)
    cases["mt2_npl_zero"] = _mt2(0, npl=0)
    cases["mt2_malformed"] = _replace(_mt2(5), 2, 2, "1.23x456+00")
    cases["mt2_npl_mismatch"] = _mt2(5, npl=14, values=[1.0] * 14)
    # a variable checked in each iteration, before a malformed field
    vals3 = [v for k in range(1, 6) for v in (5.0, 10.0 + k)]
    cases["mt3_valid"] = _mt3(vals3, 5)
    bad3 = list(vals3)
    bad3[4] = 4.0
    bad3[9] = "1.0.0.0.0.0"
    cases["mt3_check_then_malformed"] = _mt3(bad3, 5)
    # a list per iteration of the loop around the LIST, and a check after
    cases["mt4_valid"] = _mt4(3, 7)
    cases["mt4_nk_zero"] = _mt4(2, 0)
    cases["mt4_check"] = _mt4(3, 7, lambda i, v: v[:-1] + [1.0] if i == 2 else v)
    cases["mt5_valid"] = _mt5(8)
    cases["mt5_npl_zero"] = _mt5(0)
    cases["mt5_npl_zero_n"] = _mt5(2, npl=0)[:1] + _send(10, 5)
    # the body as one byte range, or line by line for anything unusual
    one_cr = list(valid1)
    one_cr[2] = one_cr[2] + "\r"
    cases["range_mixed_line_endings"] = one_cr
    crlf_but_one = [s + "\r" for s in valid1]
    crlf_but_one[3] = valid1[3]
    cases["range_crlf_but_one"] = crlf_but_one

    # a character after column 75 of one body line, all body lines of 76
    # columns (only the check of the characters refuses the range)
    def _col76(char, lineno):
        lines = [s + " " if 1 <= i <= 4 else s for i, s in enumerate(valid1)]
        lines[lineno] = valid1[lineno] + char
        return lines

    cases["range_tab"] = _col76("\t", 2)
    cases["range_byte_127"] = _col76("\x7f", 1)
    cases["range_byte_255"] = _col76("\xff", 4)
    tab_field = list(valid1)
    tab_field[3] = "\t" + tab_field[3][1:]
    cases["range_tab_in_field"] = tab_field
    col80 = list(valid1)
    col80[2] = col80[2] + "    3"
    cases["range_one_line_80_columns"] = col80
    cases["range_all_80_columns"] = [s + f"{i + 1:5d}" for i, s in enumerate(valid1)]
    cases["range_all_80_columns_crlf"] = [
        s + f"{i + 1:5d}\r" for i, s in enumerate(valid1)
    ]
    form = list(valid1)
    form[2] = form[2][:66] + "0001" + form[2][70:]
    cases["range_mat_form"] = form
    form_mt = list(valid1)
    form_mt[3] = form_mt[3][:72] + "1  "
    cases["range_mt_form"] = form_mt
    # the end of the data within the body (no line ending after the last
    # line, or in the middle of a line)
    cases["range_end_of_data"] = valid1[:5]
    cut_end = valid1[:4] + [valid1[4][:30]]
    cases["range_end_of_data_mid_line"] = cut_end
    # a body of one line (not read as a range) and of two lines
    cases["range_one_line_body"] = _mt5(4)
    cases["range_two_line_body"] = _mt5(7)
    return cases


# cases whose body is not read as a whole without trailing line ending
NO_FINAL_NEWLINE = ("range_end_of_data", "range_end_of_data_mid_line")


@pytest.fixture(scope="module")
def jobs_spec(tmp_path_factory):
    pytest.importorskip("numpy")
    try:
        from endf_parserpy import EndfParserCpp

        EndfParserCpp(endf_format="test")
    except ImportError:
        pytest.skip("the C++ modules are not available")
    tmpdir = tmp_path_factory.mktemp("list_bulk_form")
    jobs = []
    for name, lines in _cases().items():
        path = tmpdir / f"{name}.endf"
        end = b"" if name in NO_FINAL_NEWLINE else b"\n"
        path.write_bytes("\n".join(lines).encode("latin-1") + end)
        for array_type in ARRAY_TYPES:
            for k, opts in enumerate(OPTION_SETS):
                options = dict(BASE_OPTIONS)
                options.update(opts)
                jobs.append(
                    {
                        "key": f"{name}|{array_type}|{k}",
                        "file": str(path),
                        "array_type": array_type,
                        "options": options,
                    }
                )
    spec = tmpdir / "jobs.json"
    spec.write_text(json.dumps(jobs))
    return spec, tmpdir


def _run(spec, tmpdir, value):
    env = dict(os.environ)
    if value is None:
        env.pop(ENV_VAR, None)
    else:
        env[ENV_VAR] = value
    out = tmpdir / f"results_{value}.jsonl"
    res = subprocess.run(
        [sys.executable, str(WORKER), str(spec), str(out)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    records = [json.loads(s) for s in out.read_text().splitlines()]
    info = records[0]["info"]
    final_info = records[-1]["final_info"]
    results = {r["job"]: r.get("digest", r.get("error")) for r in records[1:-1]}
    bodies = {r["job"]: r["bodies"] for r in records[1:-1]}
    return info, final_info, results, bodies


@pytest.fixture(scope="module")
def per_field_form(jobs_spec):
    spec, tmpdir = jobs_spec
    return _run(spec, tmpdir, "off")


@pytest.fixture(scope="module", params=[None, "scalar"])
def both_forms(request, jobs_spec, per_field_form):
    # the default (bulk form for the bodies with a regular layout) and the
    # scalar tier forced (bulk form for all bodies)
    spec, tmpdir = jobs_spec
    return per_field_form, _run(spec, tmpdir, request.param)


def _is_digest(value):
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def test_bulk_form_equals_per_field_form(both_forms):
    (info_off, final_off, off, _), (info, final, bulk, _) = both_forms
    assert info_off["selected"] == "off"
    assert info["selected"] != "off"
    # the default reads only the bodies with a regular layout in the bulk
    # form unless a vector tier is selected; a forced tier reads all
    all_bodies = (
        info["requested"] is not None or info["tiers"][info["selected"]]["vector"]
    )
    assert info["bulk_all_list_bodies"] == all_bodies
    assert set(final_off["bulk_list_bodies"].values()) == {0}
    assert bulk.keys() == off.keys()
    mismatches = [k for k in bulk if bulk[k] != off[k]]
    assert mismatches == [], "\n".join(
        f"{k}:\n  off: {off[k]}\n  bulk: {bulk[k]}" for k in mismatches[:10]
    )
    # all ways of the delivery occurred
    counts = final["bulk_list_bodies"]
    assert counts["strided"] > 0 and counts["looped"] > 0 and counts["stopped"] > 0
    assert counts["byte_range"] > 0 and counts["line_by_line"] > 0


def _result(results, case, array_type="numpy", optset=0):
    return results[f"{case}|{array_type}|{optset}"]


def test_cases_give_the_intended_errors(both_forms):
    # the inputs exercise what they are meant to (in both forms, which
    # are equal by the test above)
    _, (_, _, res, _) = both_forms
    for case in ("mt1_valid", "mt1_large", "mt1_n_zero", "mt1_short_line"):
        assert _is_digest(_result(res, case)), case
    for case in ("mt2_valid", "mt2_npl_zero", "mt3_valid", "mt4_valid"):
        assert _is_digest(_result(res, case)), case
    for case in ("mt4_nk_zero", "mt5_valid", "mt5_npl_zero", "mt1_crlf"):
        assert _is_digest(_result(res, case)), case
    assert "1.23x456+00" in _result(res, "mt1_malformed_mid")
    assert "Line 3" in _result(res, "mt1_malformed_mid")
    # the check fails before the malformed field (only if zero mismatches
    # are not ignored), and the message names the line of the check
    msg = _result(res, "mt1_check_then_malformed", optset=1)
    assert "Expected a field to contain the value 0" in msg and "Line 2" in msg
    assert "abcdefghijk" in _result(res, "mt1_check_then_malformed", optset=0)
    assert "Line 4" in _result(res, "mt1_check_last", optset=1)
    assert _is_digest(_result(res, "mt1_check_last", optset=0))
    assert "Line 2" in _result(res, "mt1_check_then_mat", optset=1)
    assert "MAT" in _result(res, "mt1_check_then_mat", optset=3)
    # NPL larger than the layout: the NPL error after the body
    msg = _result(res, "mt1_npl_large")
    assert msg.startswith("RuntimeError: not exactly NPL elements consumed\n"), msg
    # more elements in the layout than NPL (also NPL=0): the NPL error
    # before the first element after the NPL elements, which is not read;
    # the line is the last line of the NPL elements (for NPL=0 the line of
    # the LIST record)
    for case, npl, line in (
        ("mt1_npl_small", 19, 5),
        ("mt1_npl_small_line", 18, 4),
        ("mt1_npl_zero", 0, 1),
        ("mt2_npl_mismatch", 14, 4),
        ("mt5_npl_zero_n", 0, 1),
    ):
        msg = _result(res, case)
        assert msg.startswith(
            "RuntimeError: not exactly NPL elements consumed: "
            f"all NPL={npl} elements of the LIST body have been consumed, "
            "but the recipe requires more elements\n"
        ), (case, msg)
        assert f"\nLine {line}: " in msg, (case, msg)
        assert "malformed" not in msg, (case, msg)
    assert "Blank line" in _result(res, "mt1_blank_line")
    assert _is_digest(_result(res, "mt1_blank_line", optset=4))
    assert not _is_digest(_result(res, "mt1_non_ascii", optset=3))
    assert not _is_digest(_result(res, "mt1_truncated"))
    assert not _is_digest(_result(res, "mt1_dexp_mid", optset=5))
    msg = _result(res, "mt3_check_then_malformed")
    assert "Invalid N" in msg and "Line 2" in msg
    assert _is_digest(_result(res, "mt1_dexp_mid"))
    assert "1.23x456+00" in _result(res, "mt2_malformed")
    assert "Line 3" in _result(res, "mt2_malformed")
    assert "Line 7" in _result(res, "mt4_check", optset=1)


# the bodies of the cases read as one byte range (the others: line by
# line), with the default options and the options of OPTION_SETS[3]
# (validate_control_records, accept_non_ascii=False)
BYTE_RANGE_CASES = {
    "mt1_valid": True,
    "mt1_large": True,
    "mt1_crlf": True,
    "mt1_malformed_mid": True,
    "mt1_dexp_mid": True,
    "mt1_npl_small": True,
    "range_all_80_columns": True,
    "range_all_80_columns_crlf": True,
    "range_two_line_body": True,
    "mt1_short_line": False,
    "mt1_cut_last_line": False,
    "mt1_blank_line": False,
    "mt1_long_line": False,
    "mt1_non_ascii": False,
    "mt1_other_mat": False,
    "mt1_truncated": False,
    "range_mixed_line_endings": False,
    "range_crlf_but_one": False,
    "range_tab": False,
    "range_tab_in_field": False,
    "range_byte_127": False,
    "range_byte_255": False,
    "range_one_line_80_columns": False,
    "range_mat_form": False,
    "range_mt_form": False,
    "range_end_of_data": False,
    "range_end_of_data_mid_line": False,
}


def test_bodies_read_as_byte_range(both_forms):
    # which bodies are read as one byte range, which line by line, and
    # that a body of one line is read by neither path (the results equal
    # those of the per-field form, see test_bulk_form_equals_per_field_form)
    (_, _, _, bodies_off), (_, _, _, bodies) = both_forms
    for key, counts in bodies_off.items():
        assert set(counts.values()) == {0}, key
    for case, as_range in BYTE_RANGE_CASES.items():
        for array_type in ARRAY_TYPES:
            for optset in (0, 3):
                counts = bodies[f"{case}|{array_type}|{optset}"]
                key = (case, array_type, optset)
                if as_range:
                    assert counts["byte_range"] == 1, key
                    assert counts["line_by_line"] == 0, key
                else:
                    assert counts["byte_range"] == 0, key
                    assert counts["line_by_line"] == 1, key
    for array_type in ARRAY_TYPES:
        counts = bodies[f"range_one_line_body|{array_type}|0"]
        assert counts["byte_range"] == 0 and counts["line_by_line"] == 0
        assert counts["strided"] + counts["looped"] == 1


def test_byte_range_cases_give_the_intended_results(both_forms):
    # the variants of the lines are read as by the per-field form: valid
    # where its line reading accepts them, errors where it does not
    _, (_, _, res, _) = both_forms
    for case in (
        "range_mixed_line_endings",
        "range_crlf_but_one",
        "range_tab",
        "range_byte_127",
        "range_byte_255",
        "range_one_line_80_columns",
        "range_all_80_columns",
        "range_all_80_columns_crlf",
        "range_mat_form",
        "range_mt_form",
        "range_one_line_body",
        "range_two_line_body",
    ):
        assert _is_digest(_result(res, case)), case
    for case in ("range_tab", "range_byte_127", "range_byte_255"):
        assert not _is_digest(_result(res, case, optset=3)), case
    assert _is_digest(_result(res, "range_mat_form", optset=3))
    assert not _is_digest(_result(res, "range_end_of_data"))
    assert not _is_digest(_result(res, "range_end_of_data_mid_line"))
