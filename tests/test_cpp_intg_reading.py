############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Reading the integer fields of INTG records with EndfParserCpp.

The fields II, JJ and KIJ of INTG records (and the MAT, MF and MT numbers)
are converted like the C function atoi: leading whitespace is skipped,
then an optional sign and the digits up to the first other character are
read; a field without digits is 0. The conversion of a field must not
depend on its width or on its position in the line, and short lines are
padded with blanks.
"""

import re
import pytest
from endf_parserpy import EndfParserCpp


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


def _atoi(field):
    # the conversion of the C function atoi for the values that fit
    m = re.match(r"[ \t\n\v\f\r]*([+-]?[0-9]+)", field)
    return int(m.group(1)) if m else 0


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


@pytest.mark.parametrize("atype", ["numpy", "list", "dict"])
@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
def test_intg_fields_like_atoi(ndigit, atype):
    n = NUM_VALUES[ndigit]
    cands = _fields(ndigit)
    rows = []
    for k in range(12):
        kij = [cands[(k * n + m) % len(cands)] for m in range(n)]
        ii = ["    5", "   -1", "99999", "  +12", "-9999", "1    "][k % 6]
        jj = ["    1", "    0", "     ", " -  3", "  7x ", "00042"][k % 6]
        rows.append((ii, jj, kij))
    rng = _parse(_text(ndigit, rows), atype)
    ii, jj, kij = _as_lists(rng, atype)
    assert ii == [_atoi(r[0]) for r in rows]
    assert jj == [_atoi(r[1]) for r in rows]
    assert kij == [[_atoi(f) for f in r[2]] for r in rows]


@pytest.mark.parametrize("ndigit", sorted(NUM_VALUES))
def test_intg_fields_with_other_characters(ndigit):
    # tabs are whitespace for atoi; other characters end the number
    n = NUM_VALUES[ndigit]
    w = ndigit + 1
    cands = ["\t5".rjust(w), "\xe95".rjust(w), "5\xe9".rjust(w), "\t-2".rjust(w)]
    cands = [c for c in cands if len(c) == w]
    rows = []
    for k in range(4):
        kij = [cands[(k + m) % len(cands)] for m in range(n)]
        rows.append(("\t  -3", " \xe9  4", kij))
    parser = EndfParserCpp(
        ignore_send_records=True,
        ignore_missing_tpid=True,
        array_type="list",
        accept_non_ascii=True,
    )
    sec = parser.parse(_text(ndigit, rows))[32][151]
    rng = sec["isotope"][0]["range"][0]
    assert rng["II"] == [-3] * 4
    assert rng["JJ"] == [0] * 4
    assert rng["KIJ"] == [[_atoi(f) for f in r[2]] for r in rows]
