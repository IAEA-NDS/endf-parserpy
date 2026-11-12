############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/10
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""``ignore_zero_mismatch`` applies only to the fixed zeros of a recipe.

The option tolerates a non-zero value in a field that is zero according to
the recipe, i.e. a literal ``0`` or ``0.0``. EndfParserPy also applied it
to a field with a variable that had been read before as 0: a variable
appearing in several records (e.g. AWR in the HEAD and CONT records of
MF4) read as 0 first and with another value in a later record gave only a
warning, the parser kept the first value and wrote the later records with
it. With the values in the other order, it raised a NumberMismatchError.
EndfParserCpp rejects both. Now both parsers decide as cpp_validate_field
does:

- a field without variables: a mismatch is tolerated if the expected value
  is zero and ``ignore_zero_mismatch``, or if the field contains a desired
  number (e.g. ``0.0?``) and ``ignore_number_mismatch``;
- a field with a variable (also an expression, an abbreviation standing
  for one, or a variable with indices): a mismatch is tolerated only if a
  variable is marked by ``?`` and ``ignore_varspec_mismatch``.

The tapes are synthetic: MF4 (AWR twice, literal zeros) of the endf6
flavor, the same with ``AWR?`` of the endf6-ext flavor, MF3 of the errorr
flavor (``0.0?``), and recipes of the test flavor with an expression and an
abbreviation of a variable read before. The last test rebuilds the case of
MF6 LAW=2 with LANG 0 and then 12 (MF6/MT50-55 of p-004_Be_009 of the
ENDF/B-VIII.1 proton sublibrary) with the recipe that had a single LANG for
all incident energies.
"""

import itertools
import warnings
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy, EndfToleratedMismatchWarning
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.interpreter.custom_exceptions import NumberMismatchError
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserPy, EndfParserCpp]
OPTION_NAMES = (
    "ignore_zero_mismatch",
    "ignore_number_mismatch",
    "ignore_varspec_mismatch",
)
OPTION_COMBINATIONS = [
    dict(zip(OPTION_NAMES, values))
    for values in itertools.product([True, False], repeat=3)
]


def _opts_id(opts):
    return "-".join(
        name.split("_")[1] + ("1" if val else "0") for name, val in opts.items()
    )


def _field(value):
    if isinstance(value, int):
        return f"{value:11d}"
    assert value == 0 or 1e-9 < abs(value) < 1e9
    mantissa, exponent = f"{value:.6e}".split("e")
    exponent = int(exponent)
    sign = "+" if exponent >= 0 else "-"
    return f"{mantissa}{sign}{abs(exponent)}".rjust(11)


def _line(fields, mat, mf, mt, seq):
    text = "".join(_field(v) for v in fields).ljust(66)
    return text + f"{mat:4d}{mf:2d}{mt:3d}{seq:5d}\n"


def _tape(mat, mf, mt, records, tpid=True):
    zeros = [0.0, 0.0, 0, 0, 0, 0]
    lines = [" synthetic tape".ljust(66) + "   1 0  0    0\n"] if tpid else []
    lines += [_line(rec, mat, mf, mt, i) for i, rec in enumerate(records, start=1)]
    lines.append(_line(zeros, mat, mf, 0, 99999))
    lines.append(_line(zeros, mat, 0, 0, 0))
    lines.append(_line(zeros, 0, 0, 0, 0))
    lines.append(_line(zeros, -1, 0, 0, 0))
    return "".join(lines)


def _mf4(awr_head, awr_cont, l1=0, c1=0.0):
    # MF4/MT2 with LTT=0, LI=1 (isotropic): HEAD and CONT record, both
    # with AWR; the HEAD has literal zeros in L1, N1, N2 and the CONT in C1
    return _tape(
        125,
        4,
        2,
        [[1001.0, awr_head, l1, 0, 0, 0], [c1, awr_cont, 1, 1, 0, 0]],
    )


def _errorr_mf3(c2):
    # MF3 of the errorr flavor, [MAT, 3, MT/ ZA, 0.0?, 0, 0, NG, 0 / SIG]
    return _tape(125, 3, 1, [[1001.0, c2, 0, 0, 2, 0], [1.5, 2.5]])


def _test_mf2(mt, n, value):
    # recipes of the test flavor, MF2: a CONT record with N, then a field
    # with N/6 (MT2, in the same record), M := N/6 (MT4) or (5-N)%6 (MT5)
    head = [0.0, 0.0, 0, 0, 0, 0]
    if mt == 2:
        records = [head, [0.0, 0.0, n, value, 0, 0]]
    else:
        records = [head, [0.0, 0.0, n, 0, 0, 0], [0.0, 0.0, value, 0, 0, 0]]
    # (the recipes of the test flavor have no tape head)
    return _tape(1, 2, mt, records, tpid=False)


VARIABLE = "variable"
LITERAL_ZERO = "zero"
DESIRED_NUMBER = "desired"
VARSPEC = "varspec"
CONSISTENT = "consistent"

# name: (endf_format, tape, kind of the mismatch)
CASES = {
    # AWR of the HEAD record checked in the CONT record
    "awr_zero_then_nonzero": ("endf6", _mf4(0.0, 5.0), VARIABLE),
    "awr_nonzero_then_zero": ("endf6", _mf4(5.0, 0.0), VARIABLE),
    "awr_nonzero_then_other": ("endf6", _mf4(5.0, 7.0), VARIABLE),
    "awr_zero_twice": ("endf6", _mf4(0.0, 0.0), CONSISTENT),
    "awr_nonzero_twice": ("endf6", _mf4(5.0, 5.0), CONSISTENT),
    # literal zeros of the recipe with a non-zero value
    "literal_int_zero": ("endf6", _mf4(5.0, 5.0, l1=3), LITERAL_ZERO),
    "literal_float_zero": ("endf6", _mf4(5.0, 5.0, c1=1.5), LITERAL_ZERO),
    "literal_zero_with_awr_zero": ("endf6", _mf4(0.0, 0.0, l1=3), LITERAL_ZERO),
    # AWR? in the CONT record of the endf6-ext flavor
    "varspec_zero_then_nonzero": ("endf6-ext", _mf4(0.0, 5.0), VARSPEC),
    "varspec_nonzero_then_zero": ("endf6-ext", _mf4(5.0, 0.0), VARSPEC),
    # 0.0? of the errorr flavor
    "desired_zero": ("errorr", _errorr_mf3(2.0), DESIRED_NUMBER),
    "desired_zero_matched": ("errorr", _errorr_mf3(0.0), CONSISTENT),
    # an expression of N, read before in the same or an earlier record
    "expression_zero_then_nonzero": ("test", _test_mf2(2, 0, 1), VARIABLE),
    "expression_nonzero_then_zero": ("test", _test_mf2(2, 12, 0), VARIABLE),
    "expression_consistent": ("test", _test_mf2(2, 12, 2), CONSISTENT),
    "modulo_zero_then_nonzero": ("test", _test_mf2(5, 5, 3), VARIABLE),
    # an abbreviation, M := N/6
    "abbreviation_zero_then_nonzero": ("test", _test_mf2(4, 0, 1), VARIABLE),
    "abbreviation_consistent": ("test", _test_mf2(4, 6, 1), CONSISTENT),
}


def _accepted(kind, opts):
    if kind == CONSISTENT:
        return True
    if kind == VARIABLE:
        return False
    if kind == LITERAL_ZERO:
        return opts["ignore_zero_mismatch"]
    if kind == DESIRED_NUMBER:
        # 0.0? is a zero and a desired number
        return opts["ignore_zero_mismatch"] or opts["ignore_number_mismatch"]
    if kind == VARSPEC:
        return opts["ignore_varspec_mismatch"]
    raise ValueError(kind)


def _parser(ParserCls, endf_format, **opts):
    kwargs = dict(endf_format=endf_format, **opts)
    if endf_format == "test":
        kwargs["ignore_missing_tpid"] = True
        kwargs["ignore_send_records"] = True
    return ParserCls(**kwargs)


def _text(written):
    if isinstance(written, str):
        return written
    return "".join(line if line.endswith("\n") else line + "\n" for line in written)


def _tolerated_warnings(caught):
    return [w for w in caught if issubclass(w.category, EndfToleratedMismatchWarning)]


@pytest.mark.parametrize("opts", OPTION_COMBINATIONS, ids=_opts_id)
@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_mismatch_accepted_or_rejected(ParserCls, case, opts):
    endf_format, tape, kind = CASES[case]
    parser = _parser(ParserCls, endf_format, **opts)
    if _accepted(kind, opts):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(tape)
        # a tolerated mismatch gives one summary warning in both parsers
        # (EndfParserPy logged each mismatch at WARNING level before; the
        # details are now logged at DEBUG level)
        tolerated = _tolerated_warnings(caught)
        assert len(tolerated) == (0 if kind == CONSISTENT else 1)
        if tolerated:
            assert len(tolerated[0].message.mismatches) == 1
    else:
        # EndfParserCpp reports a mismatch as a RuntimeError
        exc_type = NumberMismatchError if ParserCls is EndfParserPy else RuntimeError
        with pytest.raises(exc_type):
            parser.parse(tape)


@pytest.mark.parametrize("case", sorted(CASES))
def test_python_and_cpp_parser_agree(case):
    endf_format, tape, kind = CASES[case]
    if kind == VARIABLE:
        pytest.skip("rejected by both parsers")
    dict_py = _parser(EndfParserPy, endf_format).parse(tape)
    dict_cpp = _parser(EndfParserCpp, endf_format).parse(tape)
    compare_objects(dict_py, dict_cpp)


@pytest.mark.parametrize(
    "case",
    [c for c in sorted(CASES) if CASES[c][2] == CONSISTENT and CASES[c][0] != "test"],
)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_write_reproduces_consistent_input(ParserCls, case):
    endf_format, tape, kind = CASES[case]
    parser = _parser(ParserCls, endf_format)
    assert _text(parser.write(parser.parse(tape))) == tape


def test_python_error_message_names_variable():
    # the message of EndfParserCpp is "Invalid AWR encountered! Expected
    # AWR=0 but found AWR=5"; it is not checked here because with several
    # C++ modules in one process, the message of an error of the second
    # module may get lost in some builds
    _, tape, _ = CASES["awr_zero_then_nonzero"]
    with pytest.raises(NumberMismatchError) as excinfo:
        _parser(EndfParserPy, "endf6").parse(tape)
    msg = str(excinfo.value)
    assert "Expected 0.0 in the ENDF file but got 5.0" in msg
    assert "This is not the case for AWR which previously was determined" in msg
    assert "to be 0.0 but in the present record would be determined" in msg


def test_python_error_message_for_expression():
    _, tape, _ = CASES["expression_zero_then_nonzero"]
    with pytest.raises(NumberMismatchError) as excinfo:
        _parser(EndfParserPy, "test").parse(tape)
    assert "The expression N/6 in the ENDF recipe evaluates to 0" in str(excinfo.value)


# MF6/MT50 of a proton sublibrary file (like p-004_Be_009) with one LAW=2
# subsection: Legendre coefficients (LANG=0) at 1 MeV, a tabulated
# distribution (LANG=12) at 100 MeV
MF6_LAW2_TAPE = _tape(
    425,
    6,
    50,
    [
        [4009.0, 8.93478, 0, 2, 1, 0],
        [1001.0, 0.9986235, 0, 2, 1, 2],
        [2, 2],
        [1.0e6, 1.0, 1.0e8, 1.0],
        [0.0, 0.0, 0, 0, 1, 2],
        [2, 2],
        [0.0, 1.0e6, 0, 0, 2, 2],
        [0.1, -0.05],
        [0.0, 1.0e8, 12, 0, 4, 2],
        [-1.0, 0.25, 1.0, 0.75],
    ],
)


def _single_lang_recipes():
    # the endf6 recipes with the MF6 recipe as it was with a single LANG for
    # all incident energies of a LAW=2 subsection
    recipes = get_recipe_dict("endf6")
    recipe = recipes[6]
    new_recipe = recipe.replace("E[j], LANG[j], 0, NLW[j]", "E[j], LANG, 0, NLW[j]")
    assert new_recipe != recipe
    return {**recipes, 6: new_recipe}


@pytest.mark.parametrize("opts", OPTION_COMBINATIONS, ids=_opts_id)
def test_variable_read_as_zero_first_with_single_lang_recipe(opts):
    # EndfParserPy gave only a warning for LANG=12 after LANG=0 and wrote
    # the second LIST record with LANG=0
    parser = EndfParserPy(endf_format="endf6", recipes=_single_lang_recipes(), **opts)
    with pytest.raises(NumberMismatchError, match="LANG"):
        parser.parse(MF6_LAW2_TAPE)


@pytest.mark.parametrize("opts", OPTION_COMBINATIONS, ids=_opts_id)
@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
def test_lang_per_energy_accepted(ParserCls, opts):
    parser = ParserCls(endf_format="endf6", **opts)
    endf_dict = parser.parse(MF6_LAW2_TAPE)
    lang = endf_dict[6][50]["subsection"][1]["LANG"]
    assert [lang[1], lang[2]] == [0, 12]
    assert _text(parser.write(endf_dict)) == MF6_LAW2_TAPE


# A recipe with an abbreviation for a number and a loop counter in a
# field. These are not in the recipes of the compiled flavors, so
# EndfParserPy reads them with the recipe as custom recipe, and for
# EndfParserCpp the generated code is checked (contains_variable, the
# third argument of cpp_validate_field).
EDGE_RECIPE = (
    "[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD\n"
    "Z := 0\n"
    "[MAT,MF,MT/ 0.0, 0.0, Z, 0, 0, 0] CONT\n"
    "for i=0 to 1:\n"
    "    [MAT,MF,MT/ 0.0, 0.0, i, 0, 0, 0] CONT\n"
    "endfor\n"
    "SEND\n"
)


def _edge_tape(z, i0):
    head = [0.0, 0.0, 0, 0, 0, 0]
    records = [head, [0.0, 0.0, z, 0, 0, 0]]
    records += [[0.0, 0.0, i0, 0, 0, 0], [0.0, 0.0, 1, 0, 0, 0]]
    return _tape(1, 1, 1, records, tpid=False)


def _edge_parser(**opts):
    return EndfParserPy(
        recipes={1: {1: EDGE_RECIPE}},
        ignore_missing_tpid=True,
        ignore_send_records=True,
        **opts,
    )


def test_cpp_codegen_for_abbreviated_number_and_loop_counter():
    from endf_parserpy.compiler.endf2cpp import generate_cpp_module_code

    code = " ".join(generate_cpp_module_code({1: {1: EDGE_RECIPE}}, "x").split())
    # Z is expanded to the number 0 (no variable), i is a variable
    assert (
        'cpp_read_field<int>(cpp_line.data(), 2, parse_opts), false, false, false, "0", 2,'
        in code
    )
    assert (
        'cpp_read_field<int>(cpp_line.data(), 2, parse_opts), true, false, false, "i", 2,'
        in code
    )


@pytest.mark.parametrize("opts", OPTION_COMBINATIONS, ids=_opts_id)
def test_abbreviated_number_is_a_fixed_zero(opts):
    _edge_parser(**opts).parse(_edge_tape(0, 0))
    if opts["ignore_zero_mismatch"]:
        _edge_parser(**opts).parse(_edge_tape(3, 0))
    else:
        with pytest.raises(NumberMismatchError):
            _edge_parser(**opts).parse(_edge_tape(3, 0))


@pytest.mark.parametrize("opts", OPTION_COMBINATIONS, ids=_opts_id)
def test_loop_counter_is_a_variable(opts):
    # the loop counter is 0 in the first iteration
    with pytest.raises(NumberMismatchError, match="This is not the case for i "):
        _edge_parser(**opts).parse(_edge_tape(0, 3))
