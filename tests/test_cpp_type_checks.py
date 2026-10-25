############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Checks of the types of variables in the code generated for EndfParserCpp.

The generated code checks, when a variable is assigned, that its value has
the same type as the value assigned before (an integer or a float, a
scalar or an array). The code generator omits the checks of the variables
that are assigned values of a single type in a function, as these checks
cannot fail (see ``remove_redundant_type_checks``). The recipes of MF8 of
the test flavor (endf_recipes/test/endf_recipe_mf8.py) assign values of
different types to a variable, so that their checks are kept and fail.
"""

import os
import re
import subprocess
import sys
import json
from pathlib import Path
import pytest
import endf_parserpy
from endf_parserpy import EndfParserCpp
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.compiler.cpp_types.cpp_vartype_handling import (
    remove_redundant_type_checks,
)
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.endf_recipes.test import endf_recipe_mf8 as mf8


_CHECK_RE = re.compile(r'validate_vartype_consistency\("(\w+)", (\w+), ')


def _checks(code):
    return sorted(_CHECK_RE.findall(code))


def _make_parser():
    return EndfParserCpp(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )


def _record(mt, seq, floats=(0.0, 0.0), ints=(0, 0, 0, 0)):
    fstr = "".join(_float_str(v) for v in floats)
    istr = "".join(f"{v:11d}" for v in ints)
    return fstr + istr + f"   1 8{mt:3d}{seq:5d}"


def _float_str(v):
    return f"{v:.6e}".replace("e", "")[:11].rjust(11)


def _section(mt, s, n, xvals=()):
    lines = [_record(mt, 1, ints=(s, n, 0, 0))]
    order = [] if mt == 3 else ["scalar", "array"] if mt == 1 else ["array", "scalar"]
    seq = 2
    for kind in order:
        if kind == "scalar" and s == 1:
            lines.append(_record(mt, seq, floats=(9.0, 0.0)))
            seq += 1
        elif kind == "array":
            for x in xvals:
                lines.append(_record(mt, seq, floats=(x, 0.0)))
                seq += 1
    lines.append(_record(0, 99999))
    return "\n".join(lines)


def _mt3_section(s, z):
    floats, ints = ((0.0, 0.0), (z, 0, 0, 0)) if s == 1 else ((z, 0.0), (0, 0, 0, 0))
    lines = [_record(3, 1, ints=(s, 0, 0, 0)), _record(3, 2, floats, ints)]
    lines.append(_record(0, 99999))
    return "\n".join(lines)


def _type_error_message(var, current, previous):
    return (
        f"variable `{var}` is now encountered with type `{current}` but was "
        f"previously encountered with type `{previous}. "
    )


# The messages are obtained in a separate process: in some builds, a C++
# exception raised by a flavor module other than the first one loaded in
# the process loses its message.
_MESSAGE_SCRIPT = """
import json, sys
from endf_parserpy import EndfParserCpp
parser = EndfParserCpp(
    endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
)
try:
    parser.parse(sys.stdin.read())
    print(json.dumps(None))
except RuntimeError as exc:
    print(json.dumps(str(exc)))
"""


def _parse_error_message(text):
    # the package imported by the test, also in the separate process
    env = dict(os.environ)
    pkgdir = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (pkgdir, env.get("PYTHONPATH")) if p)
    res = subprocess.run(
        [sys.executable, "-c", _MESSAGE_SCRIPT],
        input=text,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return json.loads(res.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    "mt, current, previous",
    [
        (1, "NESTEDARRAY_DOUBLE", "SCALAR_DOUBLE"),
        (2, "SCALAR_DOUBLE", "NESTEDARRAY_DOUBLE"),
    ],
)
def test_conflicting_types_raise(mt, current, previous):
    message = _parse_error_message(_section(mt, 1, 2, (1.0, 2.0)))
    assert message is not None
    assert _type_error_message("X", current, previous) in message


@pytest.mark.parametrize("mt", [1, 2])
def test_single_type_executed(mt):
    parser = _make_parser()
    # only the array
    res = parser.parse(_section(mt, 0, 2, (1.0, 2.0)))
    assert list(res[8][mt]["X"].values()) == [1.0, 2.0]
    # only the scalar
    res = parser.parse(_section(mt, 1, 0))
    assert res[8][mt]["X"] == 9.0


@pytest.mark.parametrize("s, z", [(1, 7), (0, 2.5)])
def test_types_in_exclusive_branches(s, z):
    parser = _make_parser()
    res = parser.parse(_mt3_section(s, z))
    assert res[8][3]["Z"] == z
    assert isinstance(res[8][3]["Z"], int if s == 1 else float)


@pytest.mark.parametrize("genfun", [generate_cpp_parsefun, generate_cpp_writefun])
@pytest.mark.parametrize(
    "recipe, expected",
    [
        (
            mf8.ENDF_RECIPE_MF8_MT1,
            [("X", "NESTEDARRAY_DOUBLE"), ("X", "SCALAR_DOUBLE")],
        ),
        (
            mf8.ENDF_RECIPE_MF8_MT2,
            [("X", "NESTEDARRAY_DOUBLE"), ("X", "SCALAR_DOUBLE")],
        ),
        (mf8.ENDF_RECIPE_MF8_MT3, [("Z", "SCALAR_DOUBLE"), ("Z", "SCALAR_INT")]),
    ],
)
def test_checks_kept_for_variables_with_several_types(genfun, recipe, expected):
    assert _checks(genfun("f", recipe)) == expected


@pytest.mark.parametrize("genfun", [generate_cpp_parsefun, generate_cpp_writefun])
def test_no_checks_for_variables_with_one_type(genfun):
    # all variables of the recipe of MF3 have a single type
    recipe = get_recipe_dict("endf6")[3]
    code = genfun("f", recipe)
    assert _checks(code) == []
    # the type of the last value is still recorded
    assert "aux_last_type_read_for_QI = SCALAR_DOUBLE;" in code


def test_remove_redundant_type_checks():
    code = (
        "aux_last_type_read_for_A = SCALAR_INT;\n"
        '  validate_vartype_consistency("A", SCALAR_INT, aux_last_type_read_for_A);\n'
        "  aux_last_type_read_for_A = SCALAR_INT;\n"
        'validate_vartype_consistency("B", SCALAR_INT, aux_last_type_read_for_B);\n'
        "aux_last_type_read_for_B = SCALAR_INT;\n"
        "{\n"
        '  validate_vartype_consistency("B", SCALAR_DOUBLE, aux_last_type_read_for_B);\n'
        "  aux_last_type_read_for_B = SCALAR_DOUBLE;\n"
        "}\n"
    )
    expected = (
        "aux_last_type_read_for_A = SCALAR_INT;\n"
        "  aux_last_type_read_for_A = SCALAR_INT;\n"
        'validate_vartype_consistency("B", SCALAR_INT, aux_last_type_read_for_B);\n'
        "aux_last_type_read_for_B = SCALAR_INT;\n"
        "{\n"
        '  validate_vartype_consistency("B", SCALAR_DOUBLE, aux_last_type_read_for_B);\n'
        "  aux_last_type_read_for_B = SCALAR_DOUBLE;\n"
        "}\n"
    )
    assert remove_redundant_type_checks(code) == expected
