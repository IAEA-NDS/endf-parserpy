############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/13
# Last modified:   2026/10/13
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for the arithmetic of expressions in ENDF recipes.

Expressions are evaluated exactly by both parsers: integers and decimal
literals are exact, a division of exact numbers gives an exact fraction
(e.g. 13/6), and only where an integer is needed (an integer field, a loop
bound, an index) must the value be an integer. Values of float fields
are floats; arithmetic with a float gives a float. The result of a
modulo operation has the sign of the divisor.

The recipes of MF2 of the test flavor (endf_recipes/test/endf_recipe_mf2.py)
exercise the places of a recipe in which expressions are evaluated.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects
from endf_parserpy.utils.math_utils import EndfFloat


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]

# part of the error message of EndfParserPy for a non-integral value
# where an integer is needed
NOT_AN_INTEGER = "is not an integer|must evaluate to an integer"


def _make_parser(ParserCls, preserve_value_strings=False):
    return ParserCls(
        endf_format="test",
        ignore_send_records=True,
        ignore_missing_tpid=True,
        preserve_value_strings=preserve_value_strings,
    )


def _float_field(x):
    return f"{x:11.6e}".replace("e+0", "+").replace("e-0", "-").rjust(11)


def _record(mt, seq, c1=0.0, c2=0.0, l1=0, l2=0, n1=0, n2=0):
    ints = "".join(f"{v:11d}" for v in (l1, l2, n1, n2))
    return _float_field(c1) + _float_field(c2) + ints + f"   1 2{mt:3d}{seq:5d}"


def _section(mt, *records):
    lines = [_record(mt, 1)]
    lines += [_record(mt, seq, **rec) for seq, rec in enumerate(records, start=2)]
    lines.append(_record(0, 99999))
    return "\n".join(lines)


def _section_dict(mt, **variables):
    return {2: {mt: {"MAT": 1, "MF": 2, "MT": mt, **variables}}}


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _plain(values):
    # EndfFloat (with preserve_value_strings=True) to float for comparisons
    def conv(v):
        if isinstance(v, EndfFloat):
            return float(v)
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        return v

    return conv(values)


# (MT, records after the HEAD record, expected variables)
VALID_CASES = {
    "solve_6*NX": (1, [dict(n1=12)], {"NX": 2}),
    "field_N/6": (2, [dict(l1=12, l2=2)], {"N": 12}),
    "loop_bound_N/6": (
        3,
        [dict(l1=12), dict(c1=1.0), dict(c1=2.0)],
        {"N": 12, "X": {1: 1.0, 2: 2.0}},
    ),
    "abbreviation_N/6": (4, [dict(l1=12), dict(l1=2)], {"N": 12}),
    "modulo_negative_operand": (5, [dict(l1=7), dict(l1=4)], {"N": 7}),
    "negative_numerator": (6, [dict(l1=6), dict(l1=-1)], {"N": 6}),
    "condition_division": (7, [dict(l1=12), dict(l1=1)], {"N": 12}),
    "condition_modulo": (7, [dict(l1=6), dict(l1=1)], {"N": 6}),
    "condition_false": (7, [dict(l1=13), dict(l1=2)], {"N": 13}),
    "condition_add_sub_mul": (8, [dict(l1=7), dict(l1=1)], {"N": 7}),
    "condition_add_sub_mul_false": (8, [dict(l1=8), dict(l1=2)], {"N": 8}),
    "lookahead_branch_applies": (9, [dict(l1=1, n1=6, n2=3)], {"L": 1, "NP": 3}),
    "lookahead_other_branch": (9, [dict(l1=2, n1=7)], {"L": 2, "NT": 7}),
    "solve_N/6": (10, [dict(l1=2)], {"N": 12}),
    "solve_2*N/3": (11, [dict(l1=4)], {"N": 6}),
    "solve_(2*N+1)/3": (12, [dict(l1=3)], {"N": 4}),
    "solve_2*(N/4)_fraction": (13, [dict(l1=3)], {"N": 6}),
    "solve_2*(N/4)": (13, [dict(l1=4)], {"N": 8}),
    "lookahead_2*NP/3_applies": (14, [dict(l1=1, n1=4)], {"L": 1, "NP": 6}),
    "lookahead_2*NP/3_other": (14, [dict(l1=2, n1=5)], {"L": 2, "NT": 5}),
    "array_elements": (15, [dict(l1=2), dict(l1=4)], {"M": {1: 3, 2: 6}}),
    "decimal_literals": (16, [dict(l1=2, l2=3)], {"N": 19, "K": 6}),
    "float_field_N/4": (17, [dict(l1=6), dict(c1=1.5)], {"N": 6}),
    "float_variable_X/2": (18, [dict(c1=3.0, c2=1.5)], {"X": 3.0}),
    "solve_float_field": (19, [dict(c1=3.0)], {"X": 1.5}),
    "int_field_from_float": (20, [dict(c1=6.0), dict(l1=3)], {"X": 6.0}),
    "compare_float_with_fraction": (
        21,
        [dict(c1=1.6, l1=6), dict(l1=1)],
        {"X": 1.6, "N": 6},
    ),
    "compare_float_with_fraction_false": (
        21,
        [dict(c1=1.5, l1=6), dict(l1=2)],
        {"X": 1.5, "N": 6},
    ),
}

# (MT, records after the HEAD record, error message of EndfParserPy)
INVALID_CASES = {
    "solve_6*NX": (1, [dict(n1=13)], NOT_AN_INTEGER),
    "field_N/6": (2, [dict(l1=13, l2=2)], "13/6"),
    "loop_bound_N/6": (3, [dict(l1=13), dict(c1=1.0), dict(c1=2.0)], NOT_AN_INTEGER),
    "abbreviation_N/6": (4, [dict(l1=13), dict(l1=2)], "13/6"),
    "modulo_sign": (5, [dict(l1=7), dict(l1=-2)], "Expected 4"),
    "negative_numerator": (6, [dict(l1=7), dict(l1=-1)], "-5/6"),
    "lookahead_selected_branch": (9, [dict(l1=1, n1=7, n2=3)], NOT_AN_INTEGER),
    "solve_2*N/3": (11, [dict(l1=5)], NOT_AN_INTEGER),
    "solve_(2*N+1)/3": (12, [dict(l1=4)], NOT_AN_INTEGER),
    "lookahead_2*NP/3_selected": (14, [dict(l1=1, n1=5)], NOT_AN_INTEGER),
    "array_elements": (15, [dict(l1=2), dict(l1=5)], NOT_AN_INTEGER),
    "float_field_N/4": (17, [dict(l1=6), dict(c1=1.4)], "3/2"),
    "float_variable_X/2": (18, [dict(c1=3.0, c2=1.4)], "1.5"),
    "int_field_from_float": (20, [dict(c1=6.5), dict(l1=3)], "3.25"),
}


@pytest.mark.parametrize("keep_strings", [False, True])
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", VALID_CASES.keys())
def test_valid_data(ParserCls, case, keep_strings):
    # keep_strings: preserve_value_strings option of the parsers
    mt, records, variables = VALID_CASES[case]
    text = _section(mt, *records)
    parser = _make_parser(ParserCls, keep_strings)
    endf_dict = parser.parse(text)
    compare_objects(_plain(endf_dict), _section_dict(mt, **variables))
    data_lines = text.splitlines()[:-1]
    lines = _lines(parser.write(endf_dict))
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("case", INVALID_CASES.keys())
def test_invalid_data_rejected_when_reading(ParserCls, case):
    mt, records, message = INVALID_CASES[case]
    parser = _make_parser(ParserCls)
    if ParserCls is EndfParserPy:
        with pytest.raises(Exception, match=message):
            parser.parse(_section(mt, *records))
    else:
        with pytest.raises(RuntimeError):
            parser.parse(_section(mt, *records))


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "mt, variables, line_index, field, expected",
    [
        (13, {"N": 6}, 1, slice(22, 33), "3"),
        (17, {"N": 6}, 2, slice(0, 11), " 1.500000+0"),
        (18, {"X": 3.0}, 1, slice(11, 22), " 1.500000+0"),
        (19, {"X": 1.5}, 1, slice(0, 11), " 3.000000+0"),
        (20, {"X": 6.0}, 2, slice(22, 33), "3"),
        (16, {"N": 19, "K": 6}, 1, slice(22, 44), "2          3"),
    ],
    ids=["2*(N/4)", "N/4", "X/2", "2*X", "2*(X/4)", "decimal_literals"],
)
def test_writing_computed_fields(ParserCls, mt, variables, line_index, field, expected):
    parser = _make_parser(ParserCls)
    lines = _lines(parser.write(_section_dict(mt, **variables)))
    assert lines[line_index][field].strip() == expected.strip()


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "mt, variables",
    [
        (2, {"N": 13}),
        (3, {"N": 13, "X": {1: 1.0, 2: 2.0}}),
        (4, {"N": 13}),
        (6, {"N": 7}),
        (20, {"X": 6.5}),
    ],
    ids=["field_N/6", "loop_bound_N/6", "abbreviation_N/6", "(N-12)/6", "2*(X/4)"],
)
def test_writing_non_integer_into_integer_field_rejected(ParserCls, mt, variables):
    parser = _make_parser(ParserCls)
    with pytest.raises(Exception):
        parser.write(_section_dict(mt, **variables))


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_modulo_result_has_sign_of_divisor(ParserCls):
    # (5-7)%6 is 4, not -2
    parser = _make_parser(ParserCls)
    lines = _lines(parser.write(_section_dict(5, N=7)))
    assert int(lines[2][22:33]) == 4


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_preserved_value_string_of_pass_through_field(ParserCls):
    # C1 = X keeps the original string of X, C2 = X/2 is computed
    text = (
        " 0.000000+0 0.000000+0          0          0          0          0   1 2 18    1\n"
        " 3.00000+0  1.500000+0          0          0          0          0   1 2 18    2\n"
        " 0.000000+0 0.000000+0          0          0          0          0   1 2  099999"
    )
    parser = _make_parser(ParserCls, preserve_value_strings=True)
    endf_dict = parser.parse(text)
    assert endf_dict[2][18]["X"].get_original_string() == " 3.00000+0 "
    lines = _lines(parser.write(endf_dict))
    assert lines[1][:22] == " 3.00000+0  1.500000+0"


@pytest.mark.parametrize("case", VALID_CASES.keys())
def test_python_and_cpp_parser_agree(case):
    mt, records, _ = VALID_CASES[case]
    text = _section(mt, *records)
    parser_py = _make_parser(EndfParserPy)
    parser_cpp = _make_parser(EndfParserCpp)
    dict_py = parser_py.parse(text)
    dict_cpp = parser_cpp.parse(text)
    compare_objects(dict_py, dict_cpp)
    assert _lines(parser_py.write(dict_py)) == _lines(parser_cpp.write(dict_cpp))
