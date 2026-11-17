############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Tests of the generated C++ code: the assignment of the shared parse
and write functions to the shared translation units, the functions of a
flavor, and the translation units of the module with all flavors.

The shared functions were assigned to the chunks round-robin by recipe
hash, which put the two largest recipes (parse and write function each)
into one chunk with three to four times the source of the others. They
are now assigned by size, largest first, each into the chunk with the
smallest total so far, which gives chunks of about equal size and the
same chunks on every run.
"""

import random
import re

import pytest

from endf_parserpy.compiler.endf2cpp import (
    balanced_chunk_assignment,
    generate_cpp_flavor_code,
    generate_cpp_flavors_module_code,
    generate_cpp_module_code,
    generate_shared_cpp_code,
)


def _totals(assignment, sizes):
    return [sum(sizes[key] for key in keys) for keys in assignment]


def test_assignment_of_synthetic_sizes():
    sizes = {"a": 7, "b": 5, "c": 4, "d": 3, "e": 3, "f": 1}
    assignment = balanced_chunk_assignment(sizes.items(), 3)
    assert assignment == [["a", "f"], ["b", "e"], ["c", "d"]]
    assert _totals(assignment, sizes) == [8, 8, 7]


def test_ties_broken_by_key_and_chunk_number():
    sizes = {"z": 2, "y": 2, "x": 2, "w": 2}
    assert balanced_chunk_assignment(sizes.items(), 2) == [["w", "y"], ["x", "z"]]


def test_fewer_items_than_chunks_leaves_the_last_chunks_empty():
    assignment = balanced_chunk_assignment([("a", 1), ("b", 3)], 4)
    assert assignment == [["b"], ["a"], [], []]


def test_single_chunk_takes_everything():
    assignment = balanced_chunk_assignment([("a", 1), ("b", 3), ("c", 2)], 1)
    assert assignment == [["b", "c", "a"]]


def test_duplicate_keys_rejected():
    with pytest.raises(ValueError):
        balanced_chunk_assignment([("a", 1), ("a", 2)], 2)


def _shaped_sizes(seed):
    # shaped like the shared functions of the package: two large parse
    # functions, two large write functions and many small ones
    rng = random.Random(seed)
    sizes = {("parse", "big1"): 700, ("parse", "big2"): 604}
    sizes[("write", "big1")] = 391
    sizes[("write", "big2")] = 384
    for i in range(210):
        sizes[("parse" if i % 2 else "write", f"r{i:03d}")] = rng.randint(1, 190)
    return sizes


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_independent_of_input_order(seed):
    sizes = _shaped_sizes(seed)
    items = list(sizes.items())
    expected = balanced_chunk_assignment(items, 8)
    rng = random.Random(seed + 100)
    for _ in range(5):
        rng.shuffle(items)
        assert balanced_chunk_assignment(items, 8) == expected
    assert balanced_chunk_assignment(reversed(items), 8) == expected


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("num_chunks", [2, 3, 8])
def test_balance_bounds(seed, num_chunks):
    sizes = _shaped_sizes(seed)
    assignment = balanced_chunk_assignment(sizes.items(), num_chunks)
    # every item exactly once
    assigned = [key for keys in assignment for key in keys]
    assert sorted(assigned) == sorted(sizes)
    totals = _totals(assignment, sizes)
    # the largest total exceeds the smallest by at most the largest item
    assert max(totals) - min(totals) <= max(sizes.values())
    # here the many small items even out the large ones
    assert max(totals) / min(totals) < 1.05
    # the four large functions are in different chunks
    big = [k for k in sizes if k[1].startswith("big")]
    chunk_of = {key: i for i, keys in enumerate(assignment) for key in keys}
    assert len({chunk_of[k] for k in big}) == min(4, num_chunks)


# two recipe texts of different sizes; the MF number is given literally
RECIPE_SMALL = """
[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
SEND
"""

RECIPE_LARGE = """
[MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
[MAT, 3, MT/ QM, QI, 0, LR, NR, NP/ E / xs] TAB1
[MAT, 3, MT/ 0.0, 0.0, 0, 0, NR2, NP2/ E2 / xs2] TAB1
SEND
"""


def _shared_registry(order):
    recipes = {3: {1: RECIPE_SMALL, 2: RECIPE_LARGE}}
    if order == "reversed":
        recipes = {3: {2: RECIPE_LARGE, 1: RECIPE_SMALL}}
    registry = {}
    generate_cpp_module_code(recipes, "x", shared_registry=registry)
    return registry


@pytest.mark.parametrize("num_chunks", [1, 2, 3, 4, 8])
def test_shared_code_independent_of_registry_order(num_chunks):
    chunks = generate_shared_cpp_code(_shared_registry("given"), num_chunks)
    chunks2 = generate_shared_cpp_code(_shared_registry("reversed"), num_chunks)
    assert chunks == chunks2


@pytest.mark.parametrize("num_chunks", [1, 2, 3, 4, 8])
def test_each_shared_function_defined_once(num_chunks):
    registry = _shared_registry("given")
    chunks = generate_shared_cpp_code(registry, num_chunks)
    names = [
        canonical + suffix
        for side, suffix in (("parse", "_istream"), ("write", "_ostream"))
        for canonical, _code in registry[side].values()
    ]
    assert len(names) == 4
    if num_chunks == 1:
        assert [basename for basename, _ in chunks] == ["_shared.cpp"]
    else:
        # chunks without functions are left out, the others are numbered
        # from 0
        expected = [f"_shared_part_{i:02d}.cpp" for i in range(min(num_chunks, 4))]
        assert [basename for basename, _ in chunks] == expected
    for name in names:
        definition = re.compile(r"^\S.*\b" + name + r"\(", re.MULTILINE)
        assert sum(len(definition.findall(code)) for _, code in chunks) == 1


def test_large_parse_and_write_functions_in_different_chunks():
    registry = _shared_registry("given")
    chunks = generate_shared_cpp_code(registry, 2)
    largest = {
        side: max(registry[side].values(), key=lambda it: len(it[1]))[0]
        for side in ("parse", "write")
    }
    holder = {
        side: [i for i, (_, code) in enumerate(chunks) if name + "_" in code]
        for side, name in largest.items()
    }
    assert holder["parse"] != holder["write"]


@pytest.mark.parametrize("dedup", [False, True])
def test_module_without_per_section_wrappers(dedup):
    # only the functions registered with pybind11 are generated as
    # wrappers; the per-section functions are called by the dispatchers
    registry = {} if dedup else None
    code = generate_cpp_module_code(
        {3: {1: RECIPE_SMALL, 2: RECIPE_LARGE}}, "x", shared_registry=registry
    )
    for mt in (1, 2):
        for side in ("parse", "write"):
            assert re.search(rf"\b{side}_mf3mt{mt}(_file)?\(", code) is None
            assert (f"{side}_mf3mt{mt}_" in code) is not dedup
    registered = re.findall(r'm\.def\("(\w+)", &\w+, "([^"]*)"', code)
    assert registered == [
        ("parse_endf", "parsing function"),
        ("parse_endf_file", "parsing function"),
        ("write_endf", "writing function"),
        ("write_endf_file", "writing function"),
    ]


# --- the module with all flavors ---------------------------------------


def test_flavor_code_in_namespace():
    # the code of a flavor, whose functions have the same names in every
    # flavor, is in a namespace of its own; the declarations of the shared
    # functions, which are defined in the shared chunks, are outside it
    registry = {}
    code = generate_cpp_flavor_code(
        {3: {1: RECIPE_SMALL, 2: RECIPE_LARGE}}, "my_flavor", shared_registry=registry
    )
    head, sep, rest = code.partition("\nnamespace endf_flavor_my_flavor {\n")
    assert sep
    body, sep, tail = rest.partition("\n}  // namespace endf_flavor_my_flavor\n")
    assert sep and tail.strip() == ""
    for side, suffix in (("parse", "_istream"), ("write", "_ostream")):
        for canonical, _code in registry[side].values():
            declaration = re.compile(
                r"^\S.*\b" + canonical + suffix + r"\(.*\);$", re.M
            )
            assert len(declaration.findall(head)) == 1
            assert canonical + suffix + "(" in body
    assert "void register_functions(py::module_& m) {" in body
    registered = re.findall(r'm\.def\("(\w+)", &\w+, "([^"]*)"', body)
    assert [name for name, _ in registered] == [
        "parse_endf",
        "parse_endf_file",
        "write_endf",
        "write_endf_file",
    ]
    assert "PYBIND11_MODULE" not in code


def test_flavors_module_init():
    code = generate_cpp_flavors_module_code("_flavors", ["a", "b_0_20"])
    assert code.count("PYBIND11_MODULE(_flavors, m) {") == 1
    for entry in ("a", "b_0_20"):
        assert (
            f"namespace endf_flavor_{entry} {{\n"
            "  void register_functions(py::module_& m);\n}"
        ) in code
        assert (
            f'cpp_register_flavor(m, sys_modules, "{entry}", '
            f"&endf_flavor_{entry}::register_functions);"
        ) in code
    assert 'm.attr("_entries") = py::make_tuple("a", "b_0_20");' in code
