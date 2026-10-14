############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/10
# Last modified:   2026/10/10
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Regression tests for if-conditions with lookahead in write mode.

When writing, EndfParserPy evaluates an if-condition against the
variables present in the dictionary, and a comparison involving a
variable missing in the dictionary is false. The code generated for
EndfParserCpp emulates the lookahead in write mode by substituting
absent variables with placeholder values (-99999), but still marked them
as read, so that a comparison such as ``NX != 2`` with NX absent was
true. The writer then entered the wrong branch and failed with a
``KeyError``. This affected, for instance, the JENDL recipe for MF8/MT457
(also used by the default flavor endf6-ext), so that EndfParserCpp could
not write ENDF-6 conformant sections of stable nuclides.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.debugging_utils import compare_objects


PARSER_CLASSES = [EndfParserCpp, EndfParserPy]


# Stable nucleus (NST=1) as specified by ENDF-102, Section 8.4.1, taken
# from dec-001_H_001.endf (ENDF/B-VIII.0 decay sublibrary)
MF8_MT457_STABLE_ENDF6 = (
    " 1.001000+3 9.991673-1          0          0          1          0   2 8457    1\n"
    " 0.000000+0 0.000000+0          0          0          6          0   2 8457    2\n"
    " 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0   2 8457    3\n"
    " 5.000000-1 1.000000+0          0          0          6          0   2 8457    4\n"
    " 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0   2 8457    5\n"
    " 0.000000+0 0.000000+0          0          0          0          0   2 8  099999"
)

# Stable nucleus in the style of JENDL-5, where the second LIST record
# contains no values (NPL=0)
MF8_MT457_STABLE_JENDL = (
    " 1.001000+3 9.991673-1          0          0          1          0   2 8457    1\n"
    " 0.000000+0 0.000000+0          0          0          6          0   2 8457    2\n"
    " 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0 0.000000+0   2 8457    3\n"
    " 5.000000-1 1.000000+0          0          0          0          0   2 8457    4\n"
    " 0.000000+0 0.000000+0          0          0          0          0   2 8  099999"
)


def _make_parser(ParserCls, flavor):
    return ParserCls(
        endf_format=flavor, ignore_send_records=True, ignore_missing_tpid=True
    )


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize(
    "section, npl",
    [
        ({"Y": {1: 1.0, 2: 2.0}}, 2),
        ({"NX": 3, "X": {1: 1.0, 2: 2.0, 3: 3.0}}, 3),
    ],
    ids=["else_branch", "if_branch"],
)
def test_write_lookahead_condition_with_absent_variable(ParserCls, section, npl):
    # recipe MF1/MT4 of the test flavor: if NX != 2 [lookahead=1] ...
    parser = _make_parser(ParserCls, "test")
    endf_dict = {1: {4: {"MAT": 1, "MF": 1, "MT": 4, **section}}}
    lines = _lines(parser.write(endf_dict))
    # NPL field of the LIST record reveals the branch that was written
    assert int(lines[1][44:55]) == npl
    compare_objects(parser.parse("\n".join(lines)), endf_dict)


@pytest.mark.parametrize(
    "section",
    [
        {"Y": {1: 1.0, 2: 2.0}},
        {"NX": 3, "X": {1: 1.0, 2: 2.0, 3: 3.0}},
    ],
    ids=["else_branch", "if_branch"],
)
def test_write_lookahead_python_and_cpp_parser_agree(section):
    endf_dict = {1: {4: {"MAT": 1, "MF": 1, "MT": 4, **section}}}
    lines_py = _lines(_make_parser(EndfParserPy, "test").write(endf_dict))
    lines_cpp = _lines(_make_parser(EndfParserCpp, "test").write(endf_dict))
    assert lines_py == lines_cpp


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("flavor", ["endf6", "endf6-ext", "jendl"])
def test_write_mf8_mt457_stable_nucleus(ParserCls, flavor):
    parser = _make_parser(ParserCls, flavor)
    endf_dict = parser.parse(MF8_MT457_STABLE_ENDF6)
    lines = _lines(parser.write(endf_dict))
    data_lines = MF8_MT457_STABLE_ENDF6.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines


@pytest.mark.parametrize("ParserCls", PARSER_CLASSES)
@pytest.mark.parametrize("flavor", ["endf6-ext", "jendl"])
def test_write_mf8_mt457_stable_nucleus_jendl_style(ParserCls, flavor):
    parser = _make_parser(ParserCls, flavor)
    endf_dict = parser.parse(MF8_MT457_STABLE_JENDL)
    assert endf_dict[8][457]["JENDL_LIST_NPL"] == 0
    lines = _lines(parser.write(endf_dict))
    data_lines = MF8_MT457_STABLE_JENDL.splitlines()[:-1]
    assert lines[: len(data_lines)] == data_lines
