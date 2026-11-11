############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/11
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The write option standard_form_on_tie of both writers.

The standard form of a float is the field of the default writer
(prefer_noexp, abuse_signpos and skip_intzero False, the other options as
given). With standard_form_on_tie=True, the field written with the
options as given is replaced by the standard form if the standard form
reads back at least as close to the value; the special forms of these
three options (the decimal form, the sign column and the skipped integer
zero) are then only used where they are strictly closer. Without any of
the three options, the option has no effect.

The comparison of both writers for all combinations of the options is in
tests/test_cpp_float_writing_edge_cases.py.
"""

import itertools
import json
import os
import subprocess
import sys
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


PARSERS = [EndfParserPy, EndfParserCpp]


def _section(xs):
    return {
        3: {
            1: {
                "MAT": 125,
                "MF": 3,
                "MT": 1,
                "ZA": 1001.0,
                "AWR": 0.9991673,
                "QM": 0.0,
                "QI": 0.0,
                "LR": 0,
                "xstable": {
                    "NBT": [len(xs)],
                    "INT": [2],
                    "E": [float(i + 1) for i in range(len(xs))],
                    "xs": xs,
                },
            }
        }
    }


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _fields(ParserCls, values, **options):
    # the float fields of the values, written as cross sections of a TAB1
    # record (the second field of each pair)
    parser = ParserCls(ignore_missing_tpid=True, **options)
    lines = _lines(parser.write(_section(values)))
    body = [line[:66] for line in lines[3:]]
    fields = [line[11 * i : 11 * (i + 1)] for line in body for i in range(6)]
    return fields[1 : 2 * len(values) : 2]


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize(
    "value, options, without, standard",
    [
        # exact in the decimal and in the standard form
        (3007.0, {}, "       3007", " 3.007000+3"),
        (-3007.0, {}, "      -3007", "-3.007000+3"),
        (6.955732, {}, "   6.955732", " 6.955732+0"),
        (1.0e-5, {}, "    0.00001", " 1.000000-5"),
        (0.0, {}, "          0", " 0.000000+0"),
        (3007.0, {"abuse_signpos": True}, "       3007", " 3.007000+3"),
        (3007.0, {"keep_E": True}, "       3007", " 3.00700e+3"),
        (3.007e-5, {"abuse_signpos": True}, " 0.00003007", " 3.007000-5"),
        (
            0.0,
            {"abuse_signpos": True, "skip_intzero": True, "keep_E": True},
            "          0",
            " 0.00000e+0",
        ),
        # equally inexact: both are read back as 0.001018483
        (0.0010184826, {"skip_intzero": True}, " .001018483", " 1.018483-3"),
        # or as 1
        (0.99999999999, {}, "          1", " 1.000000+0"),
        (-0.99999999999, {}, "         -1", "-1.000000+0"),
        (
            0.99999999999,
            {"abuse_signpos": True, "skip_intzero": True},
            "          1",
            " 1.000000+0",
        ),
    ],
)
def test_tie_gives_standard_form_with_prefer_noexp(
    ParserCls, value, options, without, standard
):
    opts = {"prefer_noexp": True, **options}
    assert _fields(ParserCls, [value], **opts) == [without]
    assert _fields(ParserCls, [value], standard_form_on_tie=True, **opts) == [standard]


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize(
    "value, options, expected",
    [
        # only the decimal form is exact
        (13.7740142, {}, " 13.7740142"),
        (13.7740142, {"abuse_signpos": True, "skip_intzero": True}, " 13.7740142"),
        (0.0010184826, {"skip_intzero": True, "keep_E": True}, " .001018483"),
        (10203954.97, {"abuse_signpos": True}, "10203954.97"),
        (0.1090507741, {"abuse_signpos": True, "skip_intzero": True}, ".1090507741"),
        # exact in the decimal form (here without the integer zero) and in
        # the sign column, not in the standard form: the decimal form, as
        # without the option
        (
            0.0010184826,
            {"abuse_signpos": True, "skip_intzero": True},
            ".0010184826",
        ),
        (1062199.8, {"abuse_signpos": True}, "  1062199.8"),
        # neither is exact, the decimal form is closer
        (0.0120463068, {"skip_intzero": True}, " .012046307"),
        (1.23456789, {}, " 1.23456789"),
        # the exponent form is closer
        (0.0010184826, {}, " 1.018483-3"),
        (1.234567891e-5, {"skip_intzero": True}, " 1.234568-5"),
        # the exponent form in the sign column is closer (exact)
        (1.0621998e-5, {"abuse_signpos": True}, "1.0621998-5"),
        (
            1.0621998e-5,
            {"abuse_signpos": True, "skip_intzero": True},
            "1.0621998-5",
        ),
    ],
)
def test_special_form_if_closer_with_prefer_noexp(ParserCls, value, options, expected):
    opts = {"prefer_noexp": True, **options}
    assert _fields(ParserCls, [value], **opts) == [expected]
    assert _fields(ParserCls, [value], standard_form_on_tie=True, **opts) == [expected]


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("with_e", [False, True])
@pytest.mark.parametrize(
    "value, without, standard",
    [
        # exact in the standard form: the sign column only without the option
        (3007.0, ("3.0070000+3", "3.007000e+3"), (" 3.007000+3", " 3.00700e+3")),
        (0.0, ("0.0000000+0", "0.000000e+0"), (" 0.000000+0", " 0.00000e+0")),
        (1.0e-5, ("1.0000000-5", "1.000000e-5"), (" 1.000000-5", " 1.00000e-5")),
        # equally inexact: both are read back as 1
        (0.99999999999, ("1.0000000+0", "1.000000e+0"), (" 1.000000+0", " 1.00000e+0")),
    ],
)
def test_sign_column_only_if_closer(ParserCls, with_e, value, without, standard):
    opts = {"abuse_signpos": True, "keep_E": with_e}
    assert _fields(ParserCls, [value], **opts) == [without[with_e]]
    assert _fields(ParserCls, [value], standard_form_on_tie=True, **opts) == [
        standard[with_e]
    ]


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize("intzero", [False, True])
@pytest.mark.parametrize(
    "value, expected",
    [
        # the 8th digit of the sign column is needed to be exact
        (1062199.8, "1.0621998+6"),
        (1.0621998e-5, "1.0621998-5"),
        # closer with it, neither is exact
        (1.23456789, "1.2345679+0"),
        # negative values are written as without the sign column
        (-3007.0, "-3.007000+3"),
        (-1062199.8, "-1.062200+6"),
        (-0.0, " 0.000000+0"),
    ],
)
def test_sign_column_if_closer(ParserCls, intzero, value, expected):
    if expected == " 0.000000+0":
        # -0.0 is written as zero: the standard form with the option
        without = "0.0000000+0"
    else:
        without = expected
    opts = {"abuse_signpos": True, "skip_intzero": intzero}
    assert _fields(ParserCls, [value], **opts) == [without]
    assert _fields(ParserCls, [value], standard_form_on_tie=True, **opts) == [expected]


VALUES = [
    3007.0,
    -3007.0,
    0.0,
    6.955732,
    13.7740142,
    0.0010184826,
    0.99999999999,
    1.0e-5,
    1.0e11,
    -2.5e-300,
    123456789.0,
]


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize(
    "options",
    [
        {},
        {"keep_E": True},
        {"skip_intzero": True},
        {"keep_E": True, "skip_intzero": True},
    ],
    ids=lambda o: "+".join(k for k, v in o.items() if v) or "default",
)
def test_no_effect_without_special_forms(ParserCls, options):
    # without prefer_noexp and abuse_signpos (skip_intzero only has an
    # effect with prefer_noexp), the field is the standard form
    parser = ParserCls(ignore_missing_tpid=True, **options)
    parser_opt = ParserCls(
        ignore_missing_tpid=True, standard_form_on_tie=True, **options
    )
    section = _section(VALUES)
    assert _lines(parser_opt.write(section)) == _lines(parser.write(section))
    parser_std = ParserCls(
        ignore_missing_tpid=True, keep_E=options.get("keep_E", False)
    )
    assert _lines(parser_opt.write(section)) == _lines(parser_std.write(section))


@pytest.mark.parametrize("ParserCls", PARSERS)
@pytest.mark.parametrize(
    "options",
    [
        dict(zip(("abuse_signpos", "keep_E", "skip_intzero", "prefer_noexp"), values))
        for values in itertools.product([False, True], repeat=4)
    ],
    ids=lambda o: "+".join(k for k, v in o.items() if v) or "default",
)
def test_values_exact_in_standard_form_keep_it(ParserCls, options):
    # every value that the standard form represents exactly (also with
    # keep_E, with one digit less) is written in the standard form with
    # the option, whatever the other options
    values = [3007.0, -3007.0, 0.0, 6.95573, 1.0e-5, -2.5e-300, 1.0e11, 123456.0]
    expected = _fields(ParserCls, values, keep_E=options["keep_E"])
    assert _fields(ParserCls, values, standard_form_on_tie=True, **options) == expected


@pytest.mark.parametrize("ParserCls", PARSERS)
def test_option_in_write_opts_and_pickle(ParserCls):
    import pickle

    assert ParserCls().write_opts["standard_form_on_tie"] is False
    parser = ParserCls(prefer_noexp=True, standard_form_on_tie=True)
    assert parser.write_opts["standard_form_on_tie"] is True
    restored = pickle.loads(pickle.dumps(parser))
    assert restored.write_opts["standard_form_on_tie"] is True


@pytest.mark.parametrize("select", ["python", "cpp"])
def test_option_through_parser_factory(select):
    from endf_parserpy import EndfParserFactory

    parser = EndfParserFactory.create(
        select=select, prefer_noexp=True, standard_form_on_tie=True
    )
    assert parser.write_opts["standard_form_on_tie"] is True


def _cli_convert_to_endf(tmp_path, name, *flags):
    destfile = tmp_path / name
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    proc = subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", "convert"]
        + ["--ignore_missing_tpid", "--to", "endf", *flags]
        + [str(tmp_path / "source.json"), str(destfile)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return destfile.read_text().splitlines()


@pytest.mark.parametrize("no_cpp", [False, True])
def test_cli_flag(tmp_path, no_cpp):
    section = _section([3007.0, 13.7740142])
    jsondict = {
        str(mf): {str(mt): sec for mt, sec in mts.items()}
        for mf, mts in section.items()
    }
    (tmp_path / "source.json").write_text(json.dumps(jsondict))
    cpp = ["--no-cpp"] if no_cpp else []
    lines = _cli_convert_to_endf(tmp_path, "noexp.endf", "--prefer_noexp", *cpp)
    lines_std = _cli_convert_to_endf(
        tmp_path, "std.endf", "--prefer_noexp", "--standard_form_on_tie", *cpp
    )
    lines_sign = _cli_convert_to_endf(
        tmp_path, "sign.endf", "--abuse_signpos", "--standard_form_on_tie", *cpp
    )
    # after the tape head: the HEAD record (ZA 1001 and AWR exact in the
    # standard form) and the first line of the pairs (3007 exact in the
    # standard form, 13.7740142 only in the decimal form, and closer in
    # the sign column than in the standard form)
    assert lines[1][:22] == "       1001  0.9991673"
    assert lines_std[1][:22] == " 1.001000+3 9.991673-1"
    assert lines_sign[1][:22] == " 1.001000+3 9.991673-1"
    assert lines[4][:44] == "          1       3007          2 13.7740142"
    assert lines_std[4][:44] == " 1.000000+0 3.007000+3 2.000000+0 13.7740142"
    assert lines_sign[4][:44] == " 1.000000+0 3.007000+3 2.000000+01.3774014+1"
