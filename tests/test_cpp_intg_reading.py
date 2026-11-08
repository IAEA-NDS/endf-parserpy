############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Reading the integer fields of INTG records with EndfParserCpp.

The fields II, JJ and KIJ of INTG records (and the MAT, MF and MT numbers)
are read as EndfParserPy reads them (read_fort_int): a blank field is 0,
otherwise the field must hold an integer with an optional sign, preceded
and followed by blanks only; anything else is an error. They were
converted like the C function atoi before, which reads non-numeric text
as 0 and stops at the first other character. The conversion of a field
must not depend on its width or on its position in the line, and short
lines are padded with blanks.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


# R-Matrix Limited compact covariance (LCOMP=2) with INTG records; the
# CONT record in line 18 holds NDIGIT, NNN and NM (see
# test_cpp_intg_writing.py)
HEADER = (
    " 2.605600+4 5.545400+1          0          0          1          0263132151\n"
    " 2.605600+4 1.000000+0          0          0          1          0263132151\n"
    " 1.000000-5 1.000000+6          1          7          0          0263132151\n"
    " 0.000000+0 0.000000+0          0          2          1          1263132151\n"
    " 0.000000+0 0.000000+0          0          0          2          1263132151\n"
    " 1.000000-2 2.000000-2                                            263132151\n"
    " 0.000000+0 0.000000+0          2          1         24          4263132151\n"
    " 0.000000+0 5.545400+1 0.000000+0 2.600000+1 1.000000+0 0.000000+0263132151\n"
    " 0.000000+0 0.000000+0 0.000000+0 1.020000+2 0.000000+0 0.000000+0263132151\n"
    " 1.000000+0 5.545400+1 0.000000+0 2.600000+1 5.000000-1 0.000000+0263132151\n"
    " 0.000000+0 1.000000+0 0.000000+0 2.000000+0 0.000000+0 0.000000+0263132151\n"
    " 5.000000-1 1.000000+0          0          0         12          2263132151\n"
    " 1.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0263132151\n"
    " 2.000000+0 0.000000+0 5.000000-1 0.000000+0 5.400000-1 5.400000-1263132151\n"
    " 0.000000+0 0.000000+0          0          1         12          1263132151\n"
    " 1.000000+4 1.000000+0 5.000000-1 0.000000+0 0.000000+0 0.000000+0263132151\n"
    " 1.000000+1 1.000000-2 5.000000-3 0.000000+0 0.000000+0 0.000000+0263132151\n"
)
TRAILER = (
    " 0.000000+0 0.000000+0          0          0          0          0263132  0\n"
)

NUM_VALUES = {2: 18, 3: 13, 4: 11, 5: 9, 6: 8}


def _int(field):
    # the value of a field accepted by both parsers (read_fort_int)
    return int(field) if field.strip() != "" else 0


def _is_valid(field):
    # blanks, or blanks, an optional sign, digits and blanks
    body = field.strip(" ")
    if body[:1] in "+-":
        body = body[1:]
    return field.strip(" ") == "" or (body.isdigit() and body.isascii())


def _text(ndigit, rows):
    # rows: list of (II field, JJ field, list of KIJ fields) as strings of
    # the field widths, or a complete line (str)
    lines = HEADER
    lines += " 0.000000+0 0.000000+0{:>11}{:>11}{:>11}{:>11}263132151\n".format(
        ndigit, 12, len(rows), 0
    )
    width = ndigit + 1
    start = 11 if ndigit <= 5 else 10
    for row in rows:
        if isinstance(row, str):
            lines += row + "\n"
            continue
        ii, jj, kij = row
        assert len(ii) == 5 and len(jj) == 5
        assert all(len(f) == width for f in kij)
        line = (ii + jj).ljust(start) + "".join(kij)
        lines += line.ljust(66) + "263132151\n"
    return lines + TRAILER


def _parse(text, array_type):
    parser = EndfParserCpp(
        ignore_send_records=True, ignore_missing_tpid=True, array_type=array_type
    )
    sec = parser.parse(text)[32][151]
    isotope = sec["isotope"]
    rng = (isotope[1] if isinstance(isotope, dict) else isotope[0])["range"]
    rng = rng[1] if isinstance(rng, dict) else rng[0]
    return rng


def _as_lists(rng, array_type):
    def tolist(x):
        if array_type == "dict":
            return [tolist(x[k]) for k in sorted(x)] if isinstance(x, dict) else x
        if hasattr(x, "tolist"):
            return x.tolist()
        return [tolist(v) for v in x] if isinstance(x, list) else x

    return tolist(rng["II"]), tolist(rng["JJ"]), tolist(rng["KIJ"])


def _fields(ndigit):
    w = ndigit + 1
    digits = "9" * ndigit
    cands = [
        " " * w,
        "1".rjust(w),
        "1".ljust(w),
        ("-" + digits)[-w:].rjust(w),
        digits.rjust(w),
        "+7".rjust(w),
        "-0".rjust(w),
        "+-3"[-w:].rjust(w),
        "- 5"[-w:].rjust(w),
        "4x".rjust(w),
        "x4".rjust(w),
        "-".rjust(w),
        "+".ljust(w),
        "0" * w,
        ("1" + " " * (w - 2) + "2"),
    ]
    return [c for c in cands if len(c) == w]


def _split(cands):
    valid = [c for c in cands if _is_valid(c)]
    invalid = [c for c in cands if not _is_valid(c)]
    return valid, invalid


II_FIELDS = ["    5", "   -1", "99999", "  +12", "-9999", "1    ", "00042", "     "]
II_INVALID = [" -  3", "  7x ", "1\t2  ", "1 2  ", "  +-1"]


def _py_parse(text):
    # (the text ends without a TEND record, after which EndfParserPy
    # would accept the empty line after the last line ending)
    parser = EndfParserPy(
        ignore_send_records=True, ignore_missing_tpid=True, ignore_blank_lines=True
    )
    return parser.parse(text)[32][151]


def test_field_candidates():
    for ndigit in NUM_VALUES:
        valid, invalid = _split(_fields(ndigit))
        assert len(valid) >= 7 and len(invalid) >= 5
    assert all(_is_valid(f) for f in II_FIELDS)
    assert not any(_is_valid(f) for f in II_INVALID)


@pytest.mark.parametrize("atype", ["numpy", "list", "dict"])
@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
def test_intg_fields_like_python(ndigit, atype):
    n = NUM_VALUES[ndigit]
    cands, _ = _split(_fields(ndigit))
    rows = []
    for k in range(12):
        kij = [cands[(k * n + m) % len(cands)] for m in range(n)]
        ii = II_FIELDS[k % len(II_FIELDS)]
        jj = II_FIELDS[(k + 3) % len(II_FIELDS)]
        rows.append((ii, jj, kij))
    text = _text(ndigit, rows)
    rng = _parse(text, atype)
    ii, jj, kij = _as_lists(rng, atype)
    assert ii == [_int(r[0]) for r in rows]
    assert jj == [_int(r[1]) for r in rows]
    assert kij == [[_int(f) for f in r[2]] for r in rows]
    # the same values as EndfParserPy
    rng_py = _py_parse(text)["isotope"][1]["range"][1]
    assert ii == [rng_py["II"][k] for k in sorted(rng_py["II"])]
    assert jj == [rng_py["JJ"][k] for k in sorted(rng_py["JJ"])]


def _rejected(text):
    parser = EndfParserCpp(ignore_send_records=True, ignore_missing_tpid=True)
    with pytest.raises(RuntimeError) as excinfo:
        parser.parse(text)
    with pytest.raises(Exception):
        _py_parse(text)
    return str(excinfo.value)


@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
def test_intg_invalid_kij_field_rejected(ndigit):
    n = NUM_VALUES[ndigit]
    w = ndigit + 1
    start = 11 if ndigit <= 5 else 10
    valid, invalid = _split(_fields(ndigit))
    for field in invalid:
        for pos in (0, n - 1):
            kij = [valid[1]] * n
            kij[pos] = field
            msg = _rejected(_text(ndigit, [("    1", "    1", kij)]))
            col = start + pos * w + 1
            assert (
                f'invalid integer field: "{field}" (columns {col}-{col + w - 1})' in msg
            )
            assert "INTG" in msg


@pytest.mark.parametrize("field", II_INVALID)
@pytest.mark.parametrize("which", ["II", "JJ"])
def test_intg_invalid_ii_jj_field_rejected(field, which):
    ndigit = 3
    kij = [" " * (ndigit + 1)] * NUM_VALUES[ndigit]
    row = (field, "    1", kij) if which == "II" else ("    1", field, kij)
    msg = _rejected(_text(ndigit, [row]))
    cols = "1-5" if which == "II" else "6-10"
    assert (
        f'invalid integer field: "{field}" (columns {cols})'.replace("\t", "\\t") in msg
    )


@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
def test_intg_fields_with_other_characters(ndigit):
    # tabs and characters outside ASCII are not part of a number (int() of
    # EndfParserPy accepts a tab before or after the number, which is not
    # printable ASCII; see test_strict_control_fields.py)
    n = NUM_VALUES[ndigit]
    w = ndigit + 1
    cands = ["\t5".rjust(w), "\xe95".rjust(w), "5\xe9".rjust(w), "\t-2".rjust(w)]
    cands = [c for c in cands if len(c) == w]
    parser = EndfParserCpp(
        ignore_send_records=True,
        ignore_missing_tpid=True,
        array_type="list",
        accept_non_ascii=True,
    )
    for field in cands:
        kij = ["  1".rjust(w)] * n
        kij[1] = field
        with pytest.raises(RuntimeError, match="invalid integer field"):
            parser.parse(_text(ndigit, [("    1", "    2", kij)]))
