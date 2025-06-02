import pytest
from endf_parserpy import EndfParser
from endf_parserpy.utils.matching import eval_expr


RELATIONS = ("==", ">", ">=", "<", "<=", "!=")
UNARY_LOGICAL_OPS = ("!",)
UNARY_LOGICAL_OPS_PY = {"!": "not"}
BINARY_LOGICAL_OPS = ("&", "|")
BINARY_LOGICAL_OPS_PY = {"&": "and", "|": "or"}


@pytest.fixture(scope="module")
def test_endf_dict():
    parser = EndfParserPy()
    endf_file = Path(__file__).parent.joinpath("testdata", "n_2925_29-Cu-63.endf")
    endf_dict = parser.parsefile(endf_dict)
    return endf_dict


def test_relation_with_different_number_types():
    exprs = (
        "5 == 5",
        "-5 <= -5",
        "3.3 >= 3.7",
        "1.3e5 < 2.7",
        "1.3 > 2.7e-3",
        "5.1 >= 5.1",
    )
    for expr in exprs:
        assert eval_expr(expr, {}) == eval(expr)


@pytest.mark.parametrize("relation", RELATIONS)
def test_relations_with_numbers(relation):
    r = relation
    d = {}
    numbers = (-5, 0, 5)
    for n1 in numbers:
        for n2 in numbers:
            expr = f"{n1} {r} {n2}"
            py_res = eval(expr)
            my_res = eval_expr(expr, d)
            assert py_res == my_res


@pytest.mark.parametrize("relation", RELATIONS)
def test_relations_with_paths(relation):
    r = relation
    d = {"a": -5, "b": {"c": 0, "d": 5.1}}
    relations = ("==", ">", ">=", "<", "<=")
    els = ((None, -5), (None, 0), (None, 5))
    els = els + (("/a", -5), ("/b/c", 0), ("/b/d/", 5.1))
    for v1 in els:
        n1 = v1[1]
        m1 = v1[1] if v1[0] is None else v1[0]
        for v2 in els:
            n2 = v2[1]
            m2 = v2[1] if v2[0] is None else v2[0]
            py_expr = f"{n1} {r} {n2}"
            my_expr = f"{m1} {r} {m2}"
            py_res = eval(py_expr)
            my_res = eval_expr(my_expr, d)
            assert py_res == my_res, f"{py_res} != {my_res} for {my_expr}"


@pytest.mark.parametrize("relation", RELATIONS)
def test_relation_with_missing_path(relation):
    r = relation
    d = {}
    assert not eval_expr(f"/a {r} 1", d)


@pytest.mark.parametrize("relation", RELATIONS)
def test_relation_with_type_mismatch(relation):
    r = relation
    d = {"a": {"b": 1}}
    expr = f"/a {r} 1"
    assert not eval_expr(expr, d), expr


@pytest.mark.parametrize("relation", RELATIONS)
def test_relation_with_starred_path(relation):
    r = relation
    d = {"a": 1, "b": {"c": 2, "d": 3}, "c": 3}
    expr1 = "/b/* == 2"
    expr2 = "/b/* == 3"
    expr3 = "/b/* == 4"
    assert eval_expr(expr1, d)
    assert eval_expr(expr2, d)
    assert not eval_expr(expr3, d)
    expr4 = "/*/c == 2"
    expr5 = "/*/c == 5"
    assert eval_expr(expr4, d)
    assert not eval_expr(expr5, d)


@pytest.mark.parametrize("lop", UNARY_LOGICAL_OPS)
def test_unary_logical_ops(lop):
    py_lop = UNARY_LOGICAL_OPS_PY[lop]
    false = "0==1"
    true = "0==0"
    for v in (false, true):
        py_expr = f"{py_lop} {v}"
        my_expr = f"{lop} {v}"
        py_res = eval(py_expr)
        my_res = eval_expr(my_expr, {})
        assert py_res == my_res


@pytest.mark.parametrize("lop", BINARY_LOGICAL_OPS)
def test_binary_logical_ops(lop):
    py_lop = BINARY_LOGICAL_OPS_PY[lop]
    false = "0==1"
    true = "0==0"
    for v1 in (false, true):
        for v2 in (false, true):
            py_expr = f"{v1} {py_lop} {v2}"
            my_expr = f"{v1} {lop} {v2}"
            py_res = eval(py_expr)
            my_res = eval_expr(my_expr, {})
            assert py_res == my_res
