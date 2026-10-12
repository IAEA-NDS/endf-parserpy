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

"""Regression tests for the C++ code generator and fields that it solves.

The C++ code generator recursed endlessly (RecursionError) on a field
containing a sum of numbers, e.g. (1+1)*N, because factoring the number 1
out of 1+1 gives 1*(1+1) again. The same happened for a field in which
the unknown appears more than once, e.g. N+N, which is solved via
N*(1+1). Other fields with a repeated unknown, e.g. 2*N-N, were solved by
EndfParserCpp, whereas EndfParserPy rejects them.

The code generator now completes for these fields. A field in which the
unknown appears more than once cannot be solved for it, as in
EndfParserPy: the generated code raises an error if no other field
provides the value of the variable.

These tests check the generated code, so they do not need a compiled
module.
"""

import pytest
from endf_parserpy import EndfParserPy
from endf_parserpy.compiler.endf2cpp import generate_cpp_module_code


NOT_ISOLATED = "cannot be solved for N because this variable could not be isolated"


def _recipe(field):
    return (
        "[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD\n"
        + f"[MAT,MF,MT/ 0.0, 0.0, {field}, 0, 0, 0] CONT\n"
        + "SEND\n"
    )


def _cont(l1, mt, seq):
    ints = "".join(f"{v:11d}" for v in (l1, 0, 0, 0))
    return " 0.000000+0 0.000000+0" + ints + f"   1 1{mt:3d}{seq:5d}"


def _section(n1):
    return "\n".join([_cont(0, 1, 1), _cont(n1, 1, 2), _cont(0, 0, 99999)])


def _parse_py(field, n1):
    parser = EndfParserPy(
        recipes={1: {1: _recipe(field)}},
        cache_dir=False,
        print_cache_info=False,
        ignore_missing_tpid=True,
        ignore_send_records=True,
    )
    return parser.parse(_section(n1))[1][1]


@pytest.mark.parametrize("field", ["(1+1)*N", "(1+1)*(N+1)", "N*(2+3)"])
def test_codegen_for_sum_of_numbers(field):
    code = generate_cpp_module_code({1: {1: _recipe(field)}}, "codegen_test")
    assert NOT_ISOLATED not in code


@pytest.mark.parametrize("field", ["N+N", "2*N-N", "N-N", "2*N+N", "N/2+N/2"])
def test_codegen_for_repeated_unknown(field):
    code = generate_cpp_module_code({1: {1: _recipe(field)}}, "codegen_test")
    assert NOT_ISOLATED in code


@pytest.mark.parametrize("field", ["N+N", "2*N-N", "N-N", "2*N+N"])
def test_python_parser_rejects_repeated_unknown(field):
    # the behavior of EndfParserPy that the generated code follows
    with pytest.raises(Exception):
        _parse_py(field, 4)


def test_python_parser_solves_sum_of_numbers():
    assert _parse_py("(1+1)*N", 4)["N"] == 2
