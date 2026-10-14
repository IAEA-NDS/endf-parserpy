############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/12
# Last modified:   2026/10/12
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for variables on the right-hand side of if-conditions.

A comparison in an if-condition involving a variable that has not been
read is false in EndfParserPy, whichever side of the relation the
variable is on. The code generated for EndfParserCpp guards each
comparison with checks that its variables have been read, but collected
these variables from the left-hand side only. A comparison with an unread
variable on the right-hand side therefore used an undefined value, and a
comparison with a constant on the left-hand side (e.g. `2 != NX`) gave
code that did not compile.

The recipes of MF3 of the test flavor (endf_recipes/test/endf_recipe_mf3.py)
reproduce these cases.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


def _make_parser(ParserCls):
    return ParserCls(
        endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
    )


def _cont(ints, mt, seq):
    intstr = "".join(f"{v:11d}" for v in ints)
    return " 0.000000+0 0.000000+0" + intstr + f"   1 3{mt:3d}{seq:5d}"


def _section(mt, *records):
    lines = [_cont((0, 0, 0, 0), mt, 1)]
    lines += [_cont(rec, mt, seq) for seq, rec in enumerate(records, start=2)]
    lines.append(_cont((0, 0, 0, 0), 0, 99999))
    return "\n".join(lines)


def _section_dict(mt, **variables):
    return {3: {mt: {"MAT": 1, "MF": 3, "MT": mt, **variables}}}


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


# records after the HEAD record, expected variables;
# the last record reveals the branch: 1 if B != A, else 2
CONDITION_CASES = {
    "B_read_equal": (
        [(5, 1, 0, 0), (5, 0, 0, 0), (2, 0, 0, 0)],
        {"A": 5, "S": 1, "B": 5},
    ),
    "B_read_different": (
        [(5, 1, 0, 0), (4, 0, 0, 0), (1, 0, 0, 0)],
        {"A": 5, "S": 1, "B": 4},
    ),
    "B_not_read": ([(5, 0, 0, 0), (2, 0, 0, 0)], {"A": 5, "S": 0}),
}


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("mt", [1, 2], ids=["variable_left", "variable_right"])
@pytest.mark.parametrize("case", CONDITION_CASES.keys())
def test_comparison_with_variable_not_read(ParserCls, mt, case):
    records, variables = CONDITION_CASES[case]
    text = _section(mt, *records)
    parser = _make_parser(ParserCls)
    endf_dict = parser.parse(text)
    compare_objects(endf_dict, _section_dict(mt, **variables))
    data_lines = text.splitlines()[:-1]
    lines = _lines(parser.write(endf_dict))
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("mt", [1, 2], ids=["variable_left", "variable_right"])
def test_write_comparison_with_variable_absent(ParserCls, mt):
    # B is absent from the dictionary, so B != A is false
    parser = _make_parser(ParserCls)
    lines = _lines(parser.write(_section_dict(mt, A=5, S=0)))
    assert int(lines[2][22:33]) == 2


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "section, npl",
    [
        ({"NX": 3, "X": {1: 1.0, 2: 2.0, 3: 3.0}}, 3),
        ({"NX": 2, "Y": {1: 1.0, 2: 2.0}}, 2),
    ],
    ids=["if_branch", "else_branch"],
)
def test_constant_left_of_relation(ParserCls, section, npl):
    # recipe MF3/MT3: if 2 != NX [lookahead=1] ...
    parser = _make_parser(ParserCls)
    endf_dict = _section_dict(3, **section)
    lines = _lines(parser.write(endf_dict))
    # NPL field of the LIST record reveals the branch that was written
    assert int(lines[1][44:55]) == npl
    parsed = parser.parse("\n".join(lines))
    expected = {k: v for k, v in section.items() if k != "NX" or npl != 2}
    compare_objects(parsed, _section_dict(3, **expected))


@pytest.mark.parametrize("mt", [1, 2], ids=["variable_left", "variable_right"])
@pytest.mark.parametrize("case", CONDITION_CASES.keys())
def test_python_and_cpp_parser_agree(mt, case):
    text = _section(mt, *CONDITION_CASES[case][0])
    parser_py = _make_parser(EndfParserPy)
    parser_cpp = _make_parser(EndfParserCpp)
    dict_py = parser_py.parse(text)
    dict_cpp = parser_cpp.parse(text)
    compare_objects(dict_py, dict_cpp)
    assert _lines(parser_py.write(dict_py)) == _lines(parser_cpp.write(dict_cpp))
