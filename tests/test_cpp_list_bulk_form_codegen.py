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
the per-field form and in the bulk form (see ListBulkForm in
compiler/endf2cpp_aux.py), chosen at runtime by
``if (! cpp_list_bulk(cont, parse_opts, strided))``, where ``strided``
tells whether the generator has found a regular layout. The per-field form must be
exactly the code generated without the bulk form (apart from the comment
with the hash of the function definition), for all recipes of all
flavors. The bulk form must decode the body first (CppListBody) and take
every float value of the body from it, either by strided copies (for a
regular layout, see the rule in ListBulkForm._strided_plan) or by the
code of the per-field form with the readings of fields and lines
replaced. Writing code has no bulk form. The equivalence of the results
of both forms is tested in test_cpp_float_row_kernel.py and
test_cpp_list_bulk_form.py.
"""

import re
import pytest
from endf_parserpy.compiler import code_generator_core, code_generator_parsing
from endf_parserpy.compiler.endf2cpp_aux import ListBulkForm
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.endf_recipes.catalogue import list_endf_flavors


COND_RE = re.compile(r"if \(! cpp_list_bulk\(cont, parse_opts, (true|false)\)\) \{\n")
STRIDED = "// LIST body: strided copies from the buffer"
LOOPED_RE = re.compile(r"// LIST body: code of the per-field form \((.*)\)")
FIELD_RE = re.compile(r"cpp_read_field<\w+>\(cpp_line\.data\(\), cpp_j")


def _recipes(flavor):
    for mf, value in get_recipe_dict(flavor).items():
        if isinstance(value, dict):
            for mt, recipe in value.items():
                yield (mf, mt), recipe
        else:
            yield (mf, None), value


def _split_forms(code):
    # the code with every two-form block replaced by its per-field branch
    # (with the indentation of the block), and the bulk-form branches
    out = []
    bulks = []
    i = 0
    while True:
        m = COND_RE.search(code, i)
        if m is None:
            out.append(code[i:])
            break
        k = m.start()
        start = code.rfind("\n", 0, k) + 1
        ind = code[start:k]
        out.append(code[i:start])
        else_mark = "\n" + ind + "} else {\n"
        end_mark = "\n" + ind + "}\n"
        e = code.index(else_mark, k)
        e2 = code.index(end_mark, e + len(else_mark) - 1)
        per_field = code[m.end() : e + 1]
        bulks.append((m.group(1) == "true", code[e + len(else_mark) : e2 + 1]))
        out.append(
            "".join(
                s[2:] if s.startswith(ind + "  ") else s
                for s in per_field.splitlines(True)
            )
        )
        i = e2 + len(end_mark)
    return "".join(out), bulks


def _without_hash(code):
    # the comment with the hash of the function definition differs
    return "".join(
        s
        for s in code.splitlines(True)
        if "MD5 hash of the following function definition" not in s
    )


def _without_bulk_form(monkeypatch, func, *args):
    with monkeypatch.context() as m:
        m.setattr(code_generator_parsing, "register_list_bulk_form", lambda *a: None)
        return func(*args)


@pytest.mark.parametrize("flavor", list_endf_flavors())
def test_per_field_form_unchanged(flavor, monkeypatch):
    nbulk = 0
    nstrided = 0
    for key, recipe in _recipes(flavor):
        code = generate_cpp_parsefun("f", recipe)
        ref = _without_bulk_form(monkeypatch, generate_cpp_parsefun, "f", recipe)
        assert "cpp_body" not in ref
        per_field, bulks = _split_forms(code)
        assert _without_hash(per_field) == _without_hash(ref), f"MF/MT {key}"
        for strided_flag, bulk in bulks:
            # the body is decoded first and every float value of the body
            # taken from it; every line of the body is read by it
            assert bulk.count("CppListBody cpp_body(") == 1
            assert not FIELD_RE.search(bulk)
            assert "cpp_read_line(" not in bulk
            assert "cpp_body.field<" in bulk
            assert bulk.count("cpp_body.next_line(") >= 2
            # the delivery by the code of the per-field form repositions
            # the stream for errors
            assert "cpp_body.reposition(cpp_i," in bulk
            # strided copies, or the reason why there are none
            strided = bulk.count(STRIDED)
            assert strided + len(LOOPED_RE.findall(bulk)) == 1
            assert strided_flag == (strided == 1)
            nstrided += strided
        nbulk += len(bulks)
    if flavor != "errorr":
        assert nbulk > nstrided > 0


def _generation_counts(flavor):
    # Counts of the bulk form in the parse functions of all recipes of a
    # flavor (each recipe once): LIST bodies in the bulk form, bodies with
    # strided copies, strided sites by kind (list copies, block copies,
    # single values outside of loops, checks of literals), the reasons of
    # the bodies without strided copies, and the type checks removed by
    # remove_redundant_type_checks and kept
    counts = {
        "bulk": 0,
        "strided": 0,
        "list": 0,
        "block": 0,
        "single": 0,
        "check": 0,
        "reasons": {},
        "type_checks_removed": 0,
        "type_checks_kept": 0,
    }
    orig_plan = ListBulkForm.plan.__func__
    orig_remove = code_generator_core.remove_redundant_type_checks
    check = "validate_vartype_consistency("

    def plan(cls, *args):
        items, reason = orig_plan(cls, *args)
        counts["bulk"] += 1
        if items is None:
            reasons = counts["reasons"]
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
        else:
            counts["strided"] += 1
            for site in cls._sites(items):
                if site.kind == "literal":
                    counts["check"] += 1
                elif len(site.loops) == 0:
                    counts["single"] += 1
                else:
                    counts[site.copy[0]] += 1
        return items, reason

    def remove(code):
        new_code = orig_remove(code)
        counts["type_checks_removed"] += code.count(check) - new_code.count(check)
        counts["type_checks_kept"] += new_code.count(check)
        return new_code

    with pytest.MonkeyPatch.context() as m:
        m.setattr(ListBulkForm, "plan", classmethod(plan))
        m.setattr(code_generator_core, "remove_redundant_type_checks", remove)
        for _, recipe in _recipes(flavor):
            generate_cpp_parsefun("f", recipe)
    return counts


# The expected counts per flavor. A change of the generator that changes
# them (e.g. a body that loses its strided copies) must be confirmed here.
GOLDEN_COUNTS = {
    "endf6-ext": {
        "bulk": 98,
        "strided": 80,
        "list": 265,
        "block": 14,
        "single": 17,
        "check": 22,
        "reasons": {
            "assignment code": 3,
            "index expression": 1,
            "loop bounds depend on a loop of the body": 12,
            "variable assigned or checked": 2,
        },
        "type_checks_removed": 2588,
        "type_checks_kept": 29,
    },
    "endf6": {
        "bulk": 96,
        "strided": 78,
        "list": 264,
        "block": 14,
        "single": 17,
        "check": 21,
        "reasons": {
            "assignment code": 3,
            "index expression": 1,
            "loop bounds depend on a loop of the body": 12,
            "variable assigned or checked": 2,
        },
        "type_checks_removed": 2540,
        "type_checks_kept": 29,
    },
    "jendl": {
        "bulk": 97,
        "strided": 79,
        "list": 264,
        "block": 14,
        "single": 17,
        "check": 22,
        "reasons": {
            "assignment code": 3,
            "index expression": 1,
            "loop bounds depend on a loop of the body": 12,
            "variable assigned or checked": 2,
        },
        "type_checks_removed": 2572,
        "type_checks_kept": 29,
    },
    "pendf": {
        "bulk": 100,
        "strided": 81,
        "list": 269,
        "block": 26,
        "single": 17,
        "check": 21,
        "reasons": {
            "assignment code": 3,
            "index expression": 1,
            "loop bounds depend on a loop of the body": 12,
            "variable assigned or checked": 3,
        },
        "type_checks_removed": 2649,
        "type_checks_kept": 29,
    },
    "errorr": {
        "bulk": 3,
        "strided": 3,
        "list": 3,
        "block": 0,
        "single": 0,
        "check": 0,
        "reasons": {},
        "type_checks_removed": 43,
        "type_checks_kept": 0,
    },
    "test": {
        "bulk": 11,
        "strided": 8,
        "list": 5,
        "block": 5,
        "single": 2,
        "check": 2,
        "reasons": {
            "assignment code": 1,
            "loop bounds depend on a loop of the body": 1,
            "variable assigned or checked": 1,
        },
        "type_checks_removed": 426,
        "type_checks_kept": 15,
    },
}


@pytest.mark.parametrize("flavor", list_endf_flavors())
def test_golden_counts(flavor):
    assert _generation_counts(flavor) == GOLDEN_COUNTS[flavor]


def test_no_bulk_form_in_writing_code():
    for _, recipe in _recipes("endf6-ext"):
        code = generate_cpp_writefun("f", recipe)
        assert "cpp_body" not in code and "cpp_list_bulk" not in code


_HEAD = "[MAT,MF,MT/ 0.0, 0.0, N, M, 0, 0] HEAD\n"


def _list_recipe(body):
    return _HEAD + f"[MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL, 0/ {body}] LIST\nSEND\n"


def _bulk_code(body):
    _, bulks = _split_forms(generate_cpp_parsefun("f", _list_recipe(body)))
    return bulks


def _form(bulks):
    # "strided", or the reason of the delivery by the per-field code
    assert len(bulks) == 1
    if STRIDED in bulks[0][1]:
        return "strided"
    return LOOPED_RE.search(bulks[0][1]).group(1)


def test_bulk_form_only_for_bodies_with_loops():
    assert _bulk_code("A, B, C") == []
    assert len(_bulk_code("{X[i]}{i=1 to N}")) == 1


@pytest.mark.parametrize(
    "recipe, form",
    [
        # a list (S) and scalars before it (S1)
        (_list_recipe("A, B, {X[i]}{i=1 to N}"), "strided"),
        # list and block in one loop, a checked literal (Cs)
        (_list_recipe("{E[k], 0.0, {F[k,m]}{m=1 to M}}{k=1 to N}"), "strided"),
        # a block filled with its indices in another order
        (_list_recipe("{{G[m,n]}{m=1 to M}}{n=1 to N}"), "strided"),
        # literals only
        (_list_recipe("{0.0}{m=1 to 6}"), "strided"),
        # a list for each iteration of a loop around the LIST
        (
            _HEAD
            + "for j=1 to N:\n"
            + "    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL[j], 0/ {W[j,k]}{k=1 to M}] LIST\n"
            + "endfor\nSEND\n",
            "strided",
        ),
        # triangular ranges: one copy per row (R), not implemented
        (
            _list_recipe("{{F[k,l]}{l=k to N}}{k=1 to N}"),
            "loop bounds depend on a loop of the body",
        ),
        # a variable read before: assigned or checked at runtime (L)
        (_list_recipe("{N, X[k]}{k=1 to N}"), "variable assigned or checked"),
        # an index that is an expression of the loop variable (L)
        (_list_recipe("{X[k+1]}{k=1 to N}"), "index expression"),
        # a scalar in a loop (L)
        (_list_recipe("{S}{k=1 to N}"), "scalar read in a loop"),
        # an expression of a variable (L)
        (_list_recipe("{2*X[k]}{k=1 to N}"), "expression"),
    ],
)
def test_generator_rule(recipe, form):
    _, bulks = _split_forms(generate_cpp_parsefun("f", recipe))
    assert _form(bulks) == form


def test_rows_of_a_list_in_two_loops():
    # a list of 1-D arrays, one per iteration of the outer loop of the body
    # (the list form of F, as F is also assigned elsewhere): one copy per
    # row would be needed (R)
    recipe = _HEAD
    recipe += (
        "[MAT,MF,MT/ 0.0, 0.0, 0, 0, NPL, 0/ {{F[k,l]}{l=1 to M}}{k=1 to N}] LIST\n"
    )
    recipe += "[MAT,MF,MT/ F[1,1], 0.0, 0, 0, 0, 0] CONT\nSEND\n"
    _, bulks = _split_forms(generate_cpp_parsefun("f", recipe))
    assert _form(bulks) == "rows"


def test_strided_copies_and_checks():
    # the copies of list and block and the check of the literal
    bulks = _bulk_code("{E[k], 0.0, {F[k,m]}{m=1 to M}}{k=1 to N}")
    code = bulks[0][1]
    assert code.count("set_strided(") == 1
    assert code.count("cpp_copy_strided(") == 1
    # the check runs over all positions of the literal before the delivery
    check = code.index("cpp_validate_field(0.0, cpp_body.field<")
    assert check < code.index("set_strided(")
    # the number of values of the layout is compared with NPL
    assert "if (cpp_npl != " in code
