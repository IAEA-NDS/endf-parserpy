############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/05
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""A LIST record whose body, as laid out by the recipe, has more elements
than the NPL given in the record.

The number of elements of a body is given by the loops of the recipe with
the values read so far, NPL is a field of the first line of the record,
e.g. NT in MF35 (``{E[i]}{i=1 to NE}, {{F[i,j]}{j=i to NE-1}}{i=1 to
NE-1}``), which the recipe does not tie to NE. The NPL elements occupy
the first NPL fields of the body lines. EndfParserCpp reads the next line
of the body only as long as fewer than NPL elements have been read, and
it used to read the elements after the NPL-th one from the following
fields of the last line read, i.e. from the line after its sixth field,
the next line and beyond the end of the data, before it raised the error
"not exactly NPL elements consumed" (or another error for the bytes read
there). It now raises the error before such an element is read, with
NPL in the message. EndfParserPy raises MoreListElementsExpectedError
before it takes an element after the NPL values. A body with fewer
elements than NPL raises the error of EndfParserCpp with the message
as before, and a valid body (with a last line of fewer than six
values) is read as before by both parsers.

The data are minimal tapes with an MF35/MT18 section (NE=4, i.e. 10
elements), whose lines end after column 75, so that the eleven
characters of a seventh field of a line are the MAT/MF/MT columns, the
line ending and the first character of the next line, which do not form
a number; a field read beyond the line therefore gave a "malformed
number field" error instead of the NPL error.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes import get_recipe_dict, list_endf_flavors
from endf_parserpy.interpreter.custom_exceptions import (
    MoreListElementsExpectedError,
    UnconsumedListElementsError,
)


NE = 4
NUM_ELEMENTS = 10
E_VALUES = [1.0e-5, 1.0e5, 1.0e6, 2.0e7]
F_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
OVERRUN = "not exactly NPL elements consumed: all NPL={} elements of the LIST body"
TEMPLATE = "\nTemplate: [ MAT , 35 , MT / E1 , E2 , LS , LB , NT , NE / "
# lines of the tape (counting from 1): the HEAD and LIST records and the
# two lines of the body
LIST_LINE = 3
BODY_LINES = (4, 5)


def _float(x):
    mant, exp = f"{x:.6e}".split("e")
    return (mant + exp[0] + str(int(exp[1:]))).rjust(11)


def _int(n):
    return str(n).rjust(11)


def _line(fields, mf=35, mt=18, mat=9228):
    return "".join(fields).ljust(66) + f"{mat:4d}{mf:2d}{mt:3d}"


def _lines(nt, truncate=False):
    # the tape with NT in the LIST record; with truncate=True, the data end
    # after the body lines of NT elements, i.e. the body is the last data
    vals = [_float(v) for v in E_VALUES + F_VALUES]
    lines = [_line([" minimal tape"], 0, 0, 1)]
    lines.append(
        _line([_float(92235.0), _float(233.0), _int(0), _int(0), _int(1), _int(0)])
    )
    lines.append(
        _line([_float(1.0e-5), _float(2.0e7), _int(1), _int(7), _int(nt), _int(NE)])
    )
    body = [_line(vals[i : i + 6]) for i in range(0, NUM_ELEMENTS, 6)]
    if truncate:
        return lines + body[: max(0, -(-nt // 6))]
    lines += body
    lines += [
        _line([], 35, 0),
        _line([], 0, 0),
        _line([], 0, 0, 0),
        _line([], 0, 0, -1),
    ]
    return lines


def _text(lines):
    return "\n".join(lines) + "\n"


def _cpp_error(lines, tmp_path=None, **kwargs):
    parser = EndfParserCpp(**kwargs)
    with pytest.raises(RuntimeError) as excinfo:
        if tmp_path is None:
            parser.parse(_text(lines))
        else:
            path = tmp_path / "tape.endf"
            path.write_text(_text(lines), encoding="ascii")
            parser.parsefile(str(path))
    return str(excinfo.value)


def _line_part(lines, lineno):
    return f'\nLine {lineno}: "{lines[lineno - 1]}"'


def test_valid_body_unchanged():
    # the last body line has four values; both parsers read the body as
    # given by the recipe
    lines = _lines(NUM_ELEMENTS)
    for parser in (EndfParserCpp(), EndfParserPy()):
        sec = parser.parse(_text(lines))[35][18]["subsection"][1]
        assert sec["NT"] == NUM_ELEMENTS
        assert [sec["E"][i] for i in range(1, NE + 1)] == E_VALUES
        F = [sec["F"][i][j] for i in range(1, NE) for j in range(i, NE)]
        assert F == F_VALUES


# NT and the line of the last element of NT (counting from 1 in the tape):
# an element after the NPL-th one in the same line (9), at the end of a
# full line (6), after the first field of the first body line (1) and
# without a body line, i.e. in the line of the LIST record (0 and a
# negative NT)
OVERRUN_CASES = [(9, BODY_LINES[1]), (6, BODY_LINES[0]), (1, BODY_LINES[0])]
OVERRUN_CASES += [(0, LIST_LINE), (-1, LIST_LINE)]


@pytest.mark.parametrize("nt, lineno", OVERRUN_CASES)
def test_more_elements_than_npl(nt, lineno):
    lines = _lines(nt)
    msg = _cpp_error(lines)
    assert msg.startswith(OVERRUN.format(nt) + " have been consumed, but the recipe ")
    assert TEMPLATE in msg
    # the last line read is the last line of the NPL elements, no line or
    # field after it was read
    assert msg.endswith(_line_part(lines, lineno))
    assert "malformed" not in msg
    with pytest.raises(MoreListElementsExpectedError):
        EndfParserPy().parse(_text(lines))


@pytest.mark.parametrize("load_file_into_memory", [True, False])
@pytest.mark.parametrize("nt, lineno", OVERRUN_CASES[1:4])
@pytest.mark.parametrize("from_file", [False, True])
def test_more_elements_than_npl_at_end_of_data(
    nt, lineno, load_file_into_memory, from_file, tmp_path
):
    # the data end after the NPL elements: nothing after them is read, so
    # that the error is the NPL error and not one for the end of the data
    # (or for the bytes after it)
    lines = _lines(nt, truncate=True)
    assert len(lines) == lineno
    msg = _cpp_error(
        lines,
        tmp_path if from_file else None,
        load_file_into_memory=load_file_into_memory,
    )
    assert msg.startswith(OVERRUN.format(nt))
    assert msg.endswith(_line_part(lines, lineno))


@pytest.mark.parametrize("nt", [NUM_ELEMENTS + 1, 12])
def test_fewer_elements_than_npl(nt):
    # the message without details, as before
    lines = _lines(nt)
    msg = _cpp_error(lines)
    assert msg.startswith("not exactly NPL elements consumed\n")
    assert msg.endswith(_line_part(lines, BODY_LINES[1]))
    with pytest.raises(UnconsumedListElementsError):
        EndfParserPy().parse(_text(lines))


@pytest.mark.parametrize("nt", [9, 6, 0])
def test_write_more_elements_than_npl(nt):
    # writing raises the error before the element after the NPL-th one is
    # written (previously, after it had been written beyond the six fields
    # of the line)
    endf_dict = EndfParserCpp().parse(_text(_lines(NUM_ELEMENTS)))
    endf_dict[35][18]["subsection"][1]["NT"] = nt
    with pytest.raises(RuntimeError) as excinfo:
        EndfParserCpp().write(endf_dict)
    assert str(excinfo.value).startswith(OVERRUN.format(nt))
    with pytest.raises(UnconsumedListElementsError):
        EndfParserPy().write(endf_dict)


def _recipes():
    seen = set()
    for flavor in list_endf_flavors():
        for mf, value in get_recipe_dict(flavor).items():
            items = value.items() if isinstance(value, dict) else [(None, value)]
            for mt, recipe in items:
                if recipe not in seen:
                    seen.add(recipe)
                    yield (flavor, mf, mt), recipe


def _unchecked_accesses(code, access):
    # the lines of code that access a field of a LIST body (at cpp_j) after
    # the start of the body or the count of an element (cpp_i++) without
    # the check of the count against NPL in between; an element may be
    # accessed in several branches of the code
    out = []
    checked = False
    for line in code.splitlines():
        if "int cpp_i = 0;" in line or "cpp_i++;" in line:
            checked = False
        elif "cpp_throw_list_body_overrun(cpp_npl);" in line:
            checked = True
        elif access in line and not checked:
            out.append(line)
    return out


def test_every_element_access_is_checked():
    num_reads = 0
    num_writes = 0
    for key, recipe in _recipes():
        code = generate_cpp_parsefun("f", recipe)
        assert not _unchecked_accesses(code, "cpp_line.data(), cpp_j"), key
        num_reads += code.count("cpp_line.data(), cpp_j")
        code = generate_cpp_writefun("f", recipe)
        assert not _unchecked_accesses(code, "cpp_draft_line, cpp_j"), key
        num_writes += code.count("cpp_draft_line, cpp_j")
    assert num_reads > 100 and num_writes > 100
