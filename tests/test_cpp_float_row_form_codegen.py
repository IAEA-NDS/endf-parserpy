############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/03
# Last modified:   2026/11/05
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The two forms of the reading of LIST bodies in the generated code.

The code generator emits the loop reading the body of a LIST record in
the per-field form and in the row form (see FloatRowForm in
compiler/endf2cpp_aux.py), chosen at runtime by
``if (cpp_float_row_kernel() == nullptr)``. The per-field form must be
exactly the code generated without the row form (apart from the comment
with the hash of the function definition), for all recipes of all
flavors; the row form must read every float value of the body from the
converted fields of the line and convert each line it reads. Writing
code has no row form. The equivalence of the results of both forms is
tested in test_cpp_float_row_kernel.py.
"""

import re
import pytest
from endf_parserpy.compiler import code_generator_parsing
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.endf_recipes.catalogue import list_endf_flavors


COND = "if (cpp_float_row_kernel() == nullptr) {\n"


def _recipes(flavor):
    for mf, value in get_recipe_dict(flavor).items():
        if isinstance(value, dict):
            for mt, recipe in value.items():
                yield (mf, mt), recipe
        else:
            yield (mf, None), value


def _split_forms(code):
    # the code with every two-form block replaced by its per-field branch
    # (with the indentation of the block), and the row-form branches
    out = []
    rows = []
    i = 0
    while True:
        k = code.find(COND, i)
        if k < 0:
            out.append(code[i:])
            break
        start = code.rfind("\n", 0, k) + 1
        ind = code[start:k]
        out.append(code[i:start])
        else_mark = "\n" + ind + "} else {\n"
        end_mark = "\n" + ind + "}\n"
        e = code.index(else_mark, k)
        e2 = code.index(end_mark, e + len(else_mark) - 1)
        per_field = code[k + len(COND) : e + 1]
        rows.append(code[e + len(else_mark) : e2 + 1])
        out.append(
            "".join(
                s[2:] if s.startswith(ind + "  ") else s
                for s in per_field.splitlines(True)
            )
        )
        i = e2 + len(end_mark)
    return "".join(out), rows


def _without_hash(code):
    # the comment with the hash of the function definition differs
    return "".join(
        s
        for s in code.splitlines(True)
        if "MD5 hash of the following function definition" not in s
    )


def _without_row_form(monkeypatch, func, *args):
    with monkeypatch.context() as m:
        m.setattr(code_generator_parsing, "register_float_row_form", lambda *a: None)
        return func(*args)


@pytest.mark.parametrize("flavor", list_endf_flavors())
def test_per_field_form_unchanged(flavor, monkeypatch):
    nrows = 0
    for key, recipe in _recipes(flavor):
        code = generate_cpp_parsefun("f", recipe)
        ref = _without_row_form(monkeypatch, generate_cpp_parsefun, "f", recipe)
        assert "cpp_row" not in ref
        per_field, rows = _split_forms(code)
        assert _without_hash(per_field) == _without_hash(ref), f"MF/MT {key}"
        for row in rows:
            # every float value of the body from the converted fields
            assert "cpp_read_row_field<" in row
            assert not re.search(r"cpp_read_field<\w+>\(cpp_line\.data\(\), cpp_j", row)
            # every line read in the body is converted
            nread = row.count("cpp_read_line(cpp_line,")
            assert nread > 0
            assert (
                row.count("cpp_row.convert(cpp_line.data(), cpp_npl - cpp_i);") == nread
            )
        nrows += len(rows)
    if flavor != "errorr":
        assert nrows > 0


def test_no_row_form_in_writing_code():
    for _, recipe in _recipes("endf6-ext"):
        assert "cpp_row" not in generate_cpp_writefun("f", recipe)


def test_row_form_only_for_bodies_with_loops():
    head = "[MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] HEAD\n"
    fixed = head + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL, 0/ A, B, C] LIST\nSEND\n"
    looped = head + "[MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL, N/ {X[i]}{i=1 to N}] LIST\nSEND\n"
    assert COND not in generate_cpp_parsefun("f", fixed)
    assert generate_cpp_parsefun("f", looped).count(COND) == 1
