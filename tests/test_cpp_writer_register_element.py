############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/02
# Last modified:   2026/11/02
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Registration of the elements of nested arrays by the C++ writer.

With array_type="list" (and "numpy"), the writer registers the elements of
a nested array with the index bookkeeping where the parsing code creates
them (IndexShifterStore::register_element), so that the start index of
each level is the first index of the loop creating the elements, also if
an inner array is empty. The code generator

- omits the registration in the code of a field if the value of the field
  is retrieved with an element of the variable with these leading indices
  (outside a lookahead), as the retrieval has set the start indices of
  these levels already;
- registers the elements in a loop with a CppElementRegistrar declared
  before the outermost loop of the same scope (not in a loop containing a
  lookahead), which looks up the index bookkeeping of the variable once;
- registers the remaining elements with the store, without constructing
  a std::string or std::vector, so that nothing is done in dict mode.

The output must be the same as before, in particular for data with empty
inner arrays at the beginning, in the middle and at the end, on several
levels; it is compared with that of EndfParserPy.
"""

import re
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.compiler.code_generator_parsing import generate_cpp_parsefun
from endf_parserpy.compiler.code_generator_writing import generate_cpp_writefun
from endf_parserpy.endf_recipes import get_recipe_dict, list_endf_flavors
from endf_parserpy.endf_recipes.test import endf_recipe_mf7 as mf7


MODES = ("list", "numpy")


def _registrations(code):
    # (variable, number of indices, "registrar" or "store") of each
    # registration in the generated code, in the order of the code
    registrars = dict(
        re.findall(
            r'CppElementRegistrar (cpp_wreg_\d+)\(cpp_index_shifter_store, "(\w+)"\)',
            code,
        )
    )
    res = []
    pattern = (
        r"(cpp_wreg_\d+)\.register_element<(\d)>\(\{[^}]*\}\)"
        r'|cpp_index_shifter_store\.register_element<(\d)>\("(\w+)", \{[^}]*\}\)'
    )
    for m in re.finditer(pattern, code):
        if m.group(1) is not None:
            res.append((registrars[m.group(1)], int(m.group(2)), "registrar"))
        else:
            res.append((m.group(4), int(m.group(3)), "store"))
    return res


def _all_recipes():
    # each distinct recipe of all flavors once
    seen = set()
    for flavor in list_endf_flavors():
        for mf, mfdic in get_recipe_dict(flavor).items():
            items = [(None, mfdic)] if isinstance(mfdic, str) else mfdic.items()
            for mt, recipe in items:
                if recipe not in seen:
                    seen.add(recipe)
                    yield f"{flavor}:MF{mf}/MT{mt}", recipe


def test_no_std_containers_constructed_for_registration():
    # neither the variable name nor the indices are converted to a
    # std::string or std::vector, and the parsing code registers nothing
    num = 0
    for name, recipe in _all_recipes():
        write = generate_cpp_writefun("test_write", recipe)
        assert "register_element(" not in write, name
        num += len(_registrations(write))
        assert "register_element" not in generate_cpp_parsefun("test_parse", recipe)
    assert num > 0


def test_registrations_of_mt3():
    # B[i] and B[i,j] are registered before the loops of j and k, which
    # may have no iterations, but not at the assignment of B[i,j,k] after
    # its retrieval in the loop of k
    code = generate_cpp_writefun("test_write", mf7.ENDF_RECIPE_MF7_MT3)
    assert _registrations(code) == [
        ("C", 1, "registrar"),
        ("L", 1, "registrar"),
        ("NW", 1, "registrar"),
        ("B", 1, "registrar"),
        ("B", 2, "registrar"),
    ]
    # the registrars are declared before the outermost loop
    loop_i = code.index("for (int var_i_0d_int_Scalar")
    for decl in re.finditer(r"CppElementRegistrar cpp_wreg_\d+", code):
        assert decl.start() < loop_i


def test_registrations_of_mt6():
    # the first index of V[r,g,c] is that of the innermost loop, so that the
    # elements V[r] and V[r,g] are created at the assignment, after the
    # retrieval of V[r,g,c]: no registration is needed
    code = generate_cpp_writefun("test_write", mf7.ENDF_RECIPE_MF7_MT6)
    assert [r for r in _registrations(code) if r[0] == "V"] == []


_HEAD = "[MAT,MF,MT/ 0.0, 0.0, N, M, 0, 0] HEAD\n"


@pytest.mark.parametrize(
    "body, expected",
    [
        # created at the assignment, after the retrieval: omitted
        (
            "for i=1 to N:\n"
            "    for j=1 to M:\n"
            "        [MAT,MF,MT/ X[j,i], 0.0, 0, 0, 0, 0] CONT\n"
            "        [MAT,MF,MT/ X[j,i], 0.0, 0, 0, 0, 0] CONT\n"
            "    endfor\n"
            "endfor\n",
            [],
        ),
        # created before the loop of the next index: registrar
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ 0.0, 0.0, K[i], 0, 0, 0] CONT\n"
            "    for j=1 to K[i]:\n"
            "        [MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT\n"
            "    endfor\n"
            "endfor\n",
            [("X", 1, "registrar")],
        ),
        # no loop around the registration
        (
            "[MAT,MF,MT/ 0.0, 0.0, K, 0, 0, 0] CONT\n"
            "for j=1 to K:\n"
            "    [MAT,MF,MT/ X[1,j], 0.0, 0, 0, 0, 0] CONT\n"
            "endfor\n",
            [("X", 1, "store")],
        ),
        # in a lookahead, the value is retrieved with a default value, so
        # the registration remains (it is omitted after the lookahead)
        (
            "for i=1 to N:\n"
            "    for j=1 to M:\n"
            "        if Y[j,i] > 0.0 [lookahead=1]:\n"
            "            [MAT,MF,MT/ X[j,i], Y[j,i], 0, 0, 0, 0] CONT\n"
            "        endif\n"
            "    endfor\n"
            "endfor\n",
            [("X", 1, "store"), ("Y", 1, "store")],
        ),
        # a loop containing a lookahead gets no registrar
        (
            "for i=1 to N:\n"
            "    [MAT,MF,MT/ 0.0, 0.0, K[i], 0, 0, 0] CONT\n"
            "    for j=1 to K[i]:\n"
            "        [MAT,MF,MT/ X[i,j], 0.0, 0, 0, 0, 0] CONT\n"
            "        if X[i,j] > 0.0 [lookahead=1]:\n"
            "            [MAT,MF,MT/ 0.0, 0.0, 0, 0, 0, 0] CONT\n"
            "        endif\n"
            "    endfor\n"
            "endfor\n",
            [("X", 1, "store")],
        ),
    ],
)
def test_registration_rules(body, expected):
    code = generate_cpp_writefun("test_write", _HEAD + body + "SEND\n")
    assert sorted(_registrations(code)) == expected


def test_registrar_in_scope_of_section():
    # the registrar of a variable of a section is declared within the
    # section (with its IndexShifterStore), before the outermost loop there
    recipe = (
        _HEAD + "for i=1 to N:\n"
        "    (sub[i])\n"
        "    [MAT,MF,MT/ 0.0, 0.0, 0, 0, NX, 0] CONT\n"
        "    for j=1 to NX:\n"
        "        [MAT,MF,MT/ 0.0, 0.0, NY[j], 0, 0, 0] CONT\n"
        "        for k=1 to NY[j]:\n"
        "            [MAT,MF,MT/ X[j,k], 0.0, 0, 0, 0, 0] CONT\n"
        "        endfor\n"
        "    endfor\n"
        "    (/sub[i])\n"
        "endfor\n"
        "SEND\n"
    )
    code = generate_cpp_writefun("test_write", recipe)
    assert _registrations(code) == [("X", 1, "registrar")]
    decl = code.index("CppElementRegistrar")
    assert code.index("for (int var_i_0d_int_Scalar") < decl
    assert code.rindex("IndexShifterStore cpp_index_shifter_store", 0, decl) > (
        code.index("for (int var_i_0d_int_Scalar")
    )
    assert decl < code.index("for (int var_j_0d_int_Scalar")


# writing data with empty inner arrays


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


def _pywrite(sec):
    parser = EndfParserPy(
        endf_format="test",
        array_type="dict",
        print_cache_info=False,
        ignore_missing_tpid=True,
        ignore_send_records=True,
    )
    return _lines(parser.write({sec["MF"]: {sec["MT"]: sec}}))


def _cpp(mode):
    return EndfParserCpp(
        endf_format="test",
        array_type=mode,
        ignore_missing_tpid=True,
        ignore_send_records=True,
    )


def _roundtrip(sec, mode):
    if mode == "numpy":
        pytest.importorskip("numpy")
    text = _pywrite(sec)
    parser = _cpp(mode)
    assert _lines(parser.write(parser.parse(text))) == text
    # the dictionary given in dict mode gives the same output
    assert _lines(_cpp("dict").write({sec["MF"]: {sec["MT"]: sec}})) == text


# NW[i,j] of MF7/MT3 for each i: NJ[i] = 0 gives an empty C[i], NW[i,j] = 0
# an empty B[i,j]
MT3_SHAPES = {
    "leading": [[], [], [2, 1]],
    "middle": [[1], [], [2]],
    "trailing": [[2], [1], []],
    "leading inner": [[0, 0, 2], [0, 1]],
    "middle inner": [[1, 0, 2], [2, 0, 0, 1]],
    "trailing inner": [[2, 0], [1, 0, 0]],
    "both levels": [[], [0, 2], [], [1, 0], [0]],
    "all empty": [[0], [], [0, 0]],
}


def _mt3_section(shape, mt=3):
    sec = {"MAT": 1, "MF": 7, "MT": mt, "NI": len(shape)}
    sec.update({"NJ": {}, "NW": {}, "C": {}, "L": {}, "B": {}})
    for i, nws in enumerate(shape, start=1):
        sec["NJ"][i] = len(nws)
        for j, nw in enumerate(nws, start=1):
            sec["C"].setdefault(i, {})[j] = float(10 * i + j)
            sec["L"].setdefault(i, {})[j] = j
            sec["NW"].setdefault(i, {})[j] = nw
            for k in range(1, nw + 1):
                sec["B"].setdefault(i, {}).setdefault(j, {})[k] = float(
                    100 * i + 10 * j + k
                )
    return sec


@pytest.mark.parametrize("mt", [3, 4])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", sorted(MT3_SHAPES))
def test_mt3_empty_inner_arrays(name, mode, mt):
    _roundtrip(_mt3_section(MT3_SHAPES[name], mt), mode)


def _nested_lists(arr):
    # the dict arrays of a section as lists (keys starting at 1)
    if isinstance(arr, dict):
        return [_nested_lists(arr[k]) for k in sorted(arr)]
    return arr


@pytest.mark.parametrize("name", sorted(MT3_SHAPES))
def test_mt3_list_input(name):
    # the arrays given as nested lists (not obtained by parsing), with an
    # empty list for each empty inner array
    shape = MT3_SHAPES[name]
    sec = _mt3_section(shape)
    lsec = {k: _nested_lists(v) for k, v in sec.items()}
    for key in ("C", "L", "NW"):
        lsec[key] = [
            _nested_lists(sec[key].get(i, {})) for i in range(1, len(shape) + 1)
        ]
    lsec["B"] = [
        [_nested_lists(sec["B"].get(i, {}).get(j, {})) for j in range(1, len(nws) + 1)]
        for i, nws in enumerate(shape, start=1)
    ]
    assert _lines(_cpp("list").write({7: {3: lsec}})) == _pywrite(sec)


# NEP[j], NA[j] of MF7/MT5: NEP[j] = 0 gives empty Ep[j] and b[j],
# NA[j] = -1 empty b[j,k]
MT5_SHAPES = {
    "leading": [(0, 1), (0, 2), (2, 1)],
    "middle": [(2, 1), (0, 2), (1, 0)],
    "trailing": [(1, 1), (0, 0)],
    "leading inner": [(2, -1), (1, -1), (2, 1)],
    "mixed": [(0, 1), (2, -1), (0, 0), (3, 2), (1, -1)],
}


def _mt5_section(shape):
    sec = {"MAT": 1, "MF": 7, "MT": 5, "NE": len(shape)}
    sec.update({"E": {}, "NA": {}, "NEP": {}, "Ep": {}, "b": {}})
    for j, (nep, na) in enumerate(shape, start=1):
        sec["E"][j] = 1e6 * j
        sec["NEP"][j] = nep
        sec["NA"][j] = na
        for k in range(1, nep + 1):
            sec["Ep"].setdefault(j, {})[k] = 10.0 * j + k
            for m in range(na + 1):
                sec["b"].setdefault(j, {}).setdefault(k, {})[m] = j + k / 10 + m / 100
    return sec


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", sorted(MT5_SHAPES))
def test_mt5_empty_inner_arrays(name, mode):
    _roundtrip(_mt5_section(MT5_SHAPES[name]), mode)


# NC[g] of MF7/MT6 for each g and NK: the elements V[r] and V[r,g] are
# created in the innermost loop over r (a group without records in the
# middle cannot be parsed in list mode: its element V[r,g] is not created,
# so that the element of the next group would leave a gap in V[r])
MT6_SHAPES = {
    "leading": ([0, 0, 2], 2),
    "trailing": ([1, 2, 0], 1),
    "no values": ([2, 0, 1], 0),
}


def _mt6_section(ncs, nk):
    sec = {"MAT": 1, "MF": 7, "MT": 6, "NG": len(ncs), "NK": nk, "W0": 0.5}
    sec.update({"Y": {}, "NC": {}, "Z": {}, "M": {}, "V": {}, "V_table": {}})
    for g, nc in enumerate(ncs, start=1):
        sec["Y"][g] = 0.25 * g
        sec["NC"][g] = nc
        sec["V_table"][g] = {
            "NR": 1,
            "NP": 2,
            "NBT": [2],
            "INT": [2],
            "X": [1.0, 2.0],
            "V": [3.0 * g, 4.0 * g],
        }
        for c in range(1, nc + 1):
            sec["Z"][c] = 10.0 * c
            sec["M"][c] = c
            for r in range(1, nk + 1):
                sec["V"].setdefault(r, {}).setdefault(g, {})[c] = float(
                    100 * r + 10 * g + c
                )
    return sec


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", sorted(MT6_SHAPES))
def test_mt6_empty_inner_arrays(name, mode):
    _roundtrip(_mt6_section(*MT6_SHAPES[name]), mode)
