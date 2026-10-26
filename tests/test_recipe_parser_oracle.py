"""Equivalence of the recipe parser with Lark (oracle tests).

The recipe parser in ``endf_parserpy.recipe_parser`` must produce the
same parse trees as Lark does from the grammar in
``endf_parserpy.endf_recipes.endf_lark_ebnf`` (Earley parser,
``keep_all_tokens=True``). Two trees are considered identical if they
have, recursively, the same node kinds (tree or token), the same rule
names and numbers and order of children (trees), and the same terminal
types and string values (tokens); token positions are ignored.

Compared are:
- all recipes of all ENDF flavors (taken dynamically from the recipe
  catalogue, so newly added recipes are covered automatically);
- a synthetic corpus exercising every rule and terminal of the grammar.

Where the grammar is ambiguous, Lark's choice is an artifact of its
Earley implementation and, in some cases, differs between Lark versions.
The cases the recipe parser reproduces deterministically are tested
with explicit expectations (the behavior of Lark 1.2), as are the cases
in which it deliberately makes a fixed choice.
"""

import pytest
from endf_parserpy.endf_recipes.catalogue import list_endf_flavors, get_recipe_dict
from endf_parserpy.endf_recipes.endf_lark_ebnf import endf_recipe_grammar
from endf_parserpy.recipe_parser import (
    parse_recipe,
    get_recipe_parser,
    RecipeSyntaxError,
    Tree,
    Token,
)

lark = pytest.importorskip("lark")


def _lark_version():
    return tuple(int(x) for x in lark.__version__.split(".")[:2])


# Lark 1.0 attributes part of the indentation preceding a comment to the
# ignored whitespace, which changes the values of COMMENT tokens
pytestmark = pytest.mark.skipif(
    _lark_version() < (1, 1), reason="oracle tests require lark>=1.1"
)


@pytest.fixture(scope="module")
def lark_parser():
    return lark.Lark(endf_recipe_grammar, start="endf_recipe", keep_all_tokens=True)


def tree_difference(ref, test, path="endf_recipe"):
    """Return a description of the first difference, or None."""
    if isinstance(ref, lark.Token):
        if not isinstance(test, Token):
            return f"{path}: expected token, got {type(test).__name__}"
        if ref.type != test.type or str(ref) != str(test):
            return f"{path}: expected {ref.type} {str(ref)!r}, got {test!r}"
        return None
    if not isinstance(test, Tree):
        return f"{path}: expected tree {ref.data}, got {test!r}"
    if str(ref.data) != str(test.data):
        return f"{path}: expected rule {ref.data}, got {test.data}"
    if len(ref.children) != len(test.children):
        return (
            f"{path}: {len(ref.children)} children expected, "
            f"got {len(test.children)}"
        )
    for i, (r, t) in enumerate(zip(ref.children, test.children)):
        diff = tree_difference(r, t, f"{path}/{i}:{getattr(r, 'data', '')}")
        if diff is not None:
            return diff
    return None


def _collect_recipes():
    recipes = {}

    def walk(dic, key):
        for k, v in dic.items():
            if isinstance(v, str):
                recipes.setdefault(v, key + (k,))
            else:
                walk(v, key + (k,))

    for flavor in list_endf_flavors():
        walk(get_recipe_dict(flavor), (flavor,))
    return [(key, recipe) for recipe, key in recipes.items()]


PACKAGE_RECIPES = _collect_recipes()


@pytest.mark.parametrize(
    "key,recipe",
    PACKAGE_RECIPES,
    ids=["-".join(map(str, k)) for k, _ in PACKAGE_RECIPES],
)
def test_package_recipes_identical_to_lark(lark_parser, key, recipe):
    ref = lark_parser.parse(recipe)
    test = parse_recipe(recipe)
    assert tree_difference(ref, test) is None


def test_all_flavors_covered():
    # recipes shared by several flavors are compared once
    tested = {recipe for _, recipe in PACKAGE_RECIPES}
    for flavor in list_endf_flavors():
        recipes = []
        for v in get_recipe_dict(flavor).values():
            recipes.extend([v] if isinstance(v, str) else v.values())
        assert len(recipes) > 0
        assert all(r in tested for r in recipes if isinstance(r, str))


# ---------------------------------------------------------------------
# synthetic corpus
# ---------------------------------------------------------------------

REC = "[MAT,3,MT/ a, b, c, d, e, f] CONT\n"

SYNTHETIC_CORPUS = {
    "empty_recipe": "",
    "only_newlines": "\n\n\n",
    "spaces_and_newlines": "  \n \n",
    "cont_and_head": "[MAT, 1, 451/ ZA, AWR, 0, 0, 0, 0] HEAD\n" + REC,
    "numeric_ctrl_spec": "[125,3,1/ 0.0, 0.0, 0, 0, 0, 0]CONT\n",
    "blank_lines_between": REC + "\n\n" + REC + "\n \n\n" + REC,
    "crlf_newlines": REC.replace("\n", "\r\n") + "\r\n\r\n" + REC,
    "trailing_spaces": "[MAT,3,MT/ a,b,c,d,e,f] CONT   \n   \n",
    "text_record": "[MAT, 1, 451/ HL] TEXT\n",
    "text_record_lengths": "[MAT,1,451/ ZSYMAM{11}, ALAB{11}, EDATE{10},"
    " {1}, AUTH{33}] TEXT\n",
    "text_record_several_lengths": "[MAT,1,451/ A{1 2 3}, {4 5}] TEXT\n",
    "text_record_newlines": "[MAT,1,451/ A{11}\n, B{11},\n C\n] TEXT\n",
    "text_record_indexed": "[MAT,1,451/ DESCRIPTION[i]{66}] TEXT\n",
    "text_record_empty": "[MAT,1,451/ ] TEXT\n",
    "text_record_empty_placeholders": "[MAT,1,451/ , A, , ] TEXT\n",
    "dir_record": "[MAT,1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]] DIR\n",
    "intg_record": "[MAT,32,151/ II[q], JJ[q], KIJ[q,k]{NDIGIT}] INTG\n",
    "intg_record_expr": "[MAT,32,151/ II, JJ, KIJ[k] {2*N+1}] INTG\n",
    "tab1_record": "[MAT,3,MT/ QM, QI, 0, LR, NR, NP/ E / xs] TAB1\n",
    "tab1_record_named": "[MAT,3,MT/ QM, QI, 0, LR, NR, NP/ E / xs] TAB1 (xstable)\n",
    "tab1_record_indexed": "[MAT,6,MT/ 0.0, E[i], 0, 0, NR, NP/ Ep[i] / f[i]]"
    " TAB1 (tbl[i])\n",
    "tab1_division_in_last_field": "[MAT,3,MT/ a,b,c,d,e,f/2/X/Y] TAB1\n",
    "tab2_record": "[MAT,6,MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint] TAB2\n",
    "tab2_record_named": "[MAT,6,MT/ 0.0, 0.0, 0, 0, NR, NE/ Eint] TAB2 (t2)\n",
    "tab2_division_in_last_field": "[MAT,6,MT/ a,b,c,d,e,f/2/X] TAB2\n",
    "list_record": "[MAT,1,452/ 0.0, 0.0, 0, 0, NC, 0/ C[1], C[2]] LIST\n",
    "list_record_named": "[MAT,1,452/ 0.0, 0.0, 0, 0, NC, 0/ C] LIST (lst)\n",
    "list_record_empty_body": "[MAT,1,452/ 0.0, 0.0, 0, 0, 0, 0/ ] LIST\n",
    "list_record_loop": "[MAT,1,452/ 0.0, 0.0, 0, 0, NC, 0/ {C[k]}{k=1 to NC}] LIST\n",
    "list_record_nested_loops": "[MAT,32,151/ 0.0, 0.0, 0, 0, N, NP/\n"
    "  {{X[i,j], Y[i,j]}{j=1 to i}\n  }{i=1 to NP}\n  ] LIST\n",
    "list_record_newlines_commas": "[MAT,1,452/ 0.0, 0.0, 0, 0, NC, 0/\n"
    "    A, B,\n\n    C\n ,, D\n] LIST\n",
    "list_record_empty_loop": "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ {}{k=1 to N}] LIST\n",
    "list_record_division_before_loop": "[MAT,1,452/ 0, 0, 0, 0, NPL, NW/2/"
    " {X[k]}{k=1 to NW/2}] LIST\n",
    "list_record_padline_expression": "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ PADLINE-1, X]"
    " LIST\n",
    "send_record": "SEND\n",
    "stop_without_message": "stop()\n",
    "stop_with_message": 'stop("This option is not supported")\n',
    "stop_message_with_spaces": 'stop(  "  spaces around  "  )\n',
    "stop_message_multiline": 'stop("first line\nsecond line")\n',
    "abbreviation": "NS := NS1 + NS2*2\n" + REC,
    "abbreviation_keyword_prefix": "format := 3\nifx := 1\nSENDER := 2\n",
    "comment_block": "# comment\n" + REC,
    "comment_block_multiline": "# line 1\n#line 2\n   # line 3\n#\n" + REC,
    "comment_block_indented": "for i=1 to N:\n    # comment\n      # more\n"
    "    " + REC + "endfor\n",
    "comment_blocks_separated": "# a\n\n# b\n  \n  # c\n",
    "comment_crlf": "# a\r\n# b\r\n" + REC,
    "comment_after_statement_line": "x := 1\n   # x\n",
    "section": "(sec)\n" + REC + "(/sec)\n",
    "section_indexed": "(sub[i])\n" + REC + "(/sub[i])\n",
    "section_nested": "(a)\n(b[k])\n" + REC + "(/b[k])\n(/a)\n",
    "section_empty": "(sec)\n(/sec)\n",
    "for_loop": "for i=1 to N:\n" + REC + "endfor\n",
    "for_loop_glued_keywords": "fori=1toN:\n" + REC + "endfor\n",
    "for_loop_expressions": "for k = 2*j-1 to NS[j] + (1):\n" + REC + "endfor\n",
    "for_loop_empty": "for i=1 to N:endfor\n",
    "for_loop_nested": "for i=1 to N:\n  for j=1 to M[i]:\n    "
    + REC
    + "  endfor\nendfor\n",
    "repeat_loop": "repeat:\n" + REC + "until a > 0\n",
    "repeat_loop_varassign": "repeat [i=1]:\n" + REC + "until i==N or x<0\n",
    "repeat_loop_empty": "repeat:until x>1\n",
    "if_clause": "if LRP == 1:\n" + REC + "endif\n",
    "if_elif_else": "if a > 1:\n"
    + REC
    + "elif a < 1:\n"
    + REC
    + "elif a != 0:\n"
    + REC
    + "else:\n"
    + REC
    + "endif\n",
    "if_all_relations": "if a>1 and b<1 and c!=1 and d==1 and e>=1 and f<=1:\n"
    + REC
    + "endif\n",
    "if_and_or_precedence": "if a>1 or b>1 and c>1 or d>1:\n" + REC + "endif\n",
    "if_parenthesized_conditions": "if (a>1 or b>1) and (c>1 and (d>1 or e>1)):\n"
    + REC
    + "endif\n",
    "if_parenthesized_expression": "if (a+b)*2 > c and ((x)) == 1:\n" + REC + "endif\n",
    "if_lookahead": "if MT==2 [lookahead=1]:\n"
    + REC
    + "elif MT==3 [lookahead=N+1]:\n"
    + REC
    + "endif\n",
    "if_lookahead_after_index": "if x > A[1] [lookahead=1]:\n" + REC + "endif\n",
    "if_lookahead_after_name": "if x > A [lookahead=1]:\n" + REC + "endif\n",
    "if_empty_bodies": "if x>1: elif x<1: else: endif\n",
    "if_glued_keywords": "if x>1and y<2or z==3:\n" + REC + "endif\n",
    "if_endif_without_newline": "if x>1:\n" + REC + "endif",
    "expressions_arithmetic": "[MAT,3,MT/ a+b-c, a*b/c%d, -a, a-(-b), -(a+b)*c,"
    " a-b-c-d] CONT\n",
    "expressions_precedence": "[MAT,3,MT/ a+b*c, a*b+c, a/b/c, a-b+c, (a+b)*(c-d),"
    " a%b*c] CONT\n",
    "expressions_minus": "[MAT,3,MT/ -1, --a, a--b, a*-b, a - -b, -a*-b] CONT\n",
    "numbers": "[MAT,3,MT/ 0, 12, 1.5, 1., .5, 1e5] CONT\n",
    "numbers_exponents": "[MAT,3,MT/ 2E-3, 1.5e+2, 1.e3, .5E1, 0.0, 007] CONT\n",
    "desired_numbers": "[MAT,3,MT/ 0.0?, 1?, 1.5e3?, .5?, a, b] CONT\n",
    "inconsistent_varspec": "[MAT,3,MT/ a?, b[i]?, c ?, d, e, f] CONT\n",
    "indices": "[MAT,3,MT/ a[i], b[i,j], c[i, j, k], d[i+1], e[f[i]], g[2*i-1]]"
    " CONT\n",
    "keywords_as_names": "[MAT,3,MT/ to, lookahead, blank, andy, orb, endfor]"
    " CONT\n",
    "spacing_variants": "[ MAT , 3 , MT /a,b ,c , d,e,  f ]   CONT\n",
    "nested_everything": "(outer)\nfor i=1 to N:\n  (inner[i])\n  if a[i] > 0:\n"
    "    repeat [k=0]:\n      [MAT,3,MT/ 0, 0, 0, 0, NR, NP/ E[i] / xs[i,k]] TAB1\n"
    "    until k > 2\n  else:\n    stop()\n  endif\n  (/inner[i])\nendfor\n"
    "(/outer)\nSEND\n",
}


# recipes for which Lark's tree depends on the Lark version; they are
# tested with explicit expectations below
VERSION_DEPENDENT_CORPUS = {
    "list_record_linepadding_first": "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ PADLINE\n"
    " A, B] LIST\n",
    "text_record_newline_before_empty_placeholder": "[MAT,1,451/ A,\n, B] TEXT\n",
}


@pytest.mark.parametrize("name", sorted(SYNTHETIC_CORPUS))
def test_synthetic_corpus_identical_to_lark(lark_parser, name):
    recipe = SYNTHETIC_CORPUS[name]
    ref = lark_parser.parse(recipe)
    test = parse_recipe(recipe)
    assert tree_difference(ref, test) is None


def _rule_and_terminal_names(tree, rules, terminals):
    rules.add(str(tree.data))
    for child in tree.children:
        if isinstance(child, Tree):
            _rule_and_terminal_names(child, rules, terminals)
        else:
            terminals.add(child.type)


def test_synthetic_corpus_covers_grammar(lark_parser):
    grammar_rules = {
        r.origin.name for r in lark_parser.rules if not r.origin.name.startswith("_")
    }
    grammar_terminals = {
        t.name for t in lark_parser.terminals if not t.name.startswith("__IGNORE")
    }
    rules, terminals = set(), set()
    corpus = list(SYNTHETIC_CORPUS.values()) + list(VERSION_DEPENDENT_CORPUS.values())
    for recipe in corpus:
        _rule_and_terminal_names(parse_recipe(recipe), rules, terminals)
    assert grammar_rules - rules == set()
    assert grammar_terminals - terminals == set()


# ---------------------------------------------------------------------
# ambiguous constructs
# ---------------------------------------------------------------------


def _types(nodes):
    return [str(n.data) if isinstance(n, Tree) else n.type for n in nodes]


def _list_body(recipe):
    tree = parse_recipe(recipe)
    list_line = tree.children[0].children[0].children[0]
    assert list_line.data == "list_line"
    return list_line.children[5]


def _expr_text(node):
    if isinstance(node, Token):
        return str(node)
    return "".join(_expr_text(c) for c in node.children)


def test_empty_bodies_have_empty_code_token():
    # the empty alternative of code_token represents an empty sequence
    tree = parse_recipe("")
    assert _types(tree.children) == ["code_token"]
    assert tree.children[0].children == []
    tree = parse_recipe("for i=1 to N:endfor\n")
    for_body = tree.children[0].children[0].children[1]
    assert for_body.data == "for_body"
    assert _types(for_body.children) == ["code_token"]
    assert for_body.children[0].children == []


def test_comment_keeps_indentation():
    tree = parse_recipe("x := 1\n    # comment\n")
    comment = tree.children[1].children[0].children[0]
    assert comment.type == "COMMENT"
    assert comment == "    # comment\n"


def test_text_fields_newline_after_empty_placeholder():
    # Lark 1.2 attributes a newline between a comma and an empty
    # placeholder to the slot after the placeholder (Lark 1.3 to the
    # slot before it)
    tree = parse_recipe("[MAT,1,451/ A,\n, B] TEXT\n")
    text_fields = tree.children[0].children[0].children[0].children[3]
    assert _types(text_fields.children) == [
        "textplaceholder",
        "COMMA",
        "textplaceholder",
        "NEWLINE",
        "COMMA",
        "textplaceholder",
    ]
    tree = parse_recipe("[MAT,1,451/ A,\nB] TEXT\n")
    text_fields = tree.children[0].children[0].children[0].children[3]
    assert _types(text_fields.children) == [
        "textplaceholder",
        "COMMA",
        "NEWLINE",
        "textplaceholder",
    ]


def test_linepadding_versus_variable_name():
    # Lark 1.2: the bare word PADLINE is LINEPADDING only as the first
    # element of the body of a LIST record
    prefix = "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ "
    body = _list_body(prefix + "PADLINE] LIST\n")
    assert _types(body.children) == ["LINEPADDING"]
    body = _list_body(prefix + "PADLINE PADLINE] LIST\n")
    assert _types(body.children) == ["LINEPADDING", "expr"]
    body = _list_body(prefix + "PADLINE (1)] LIST\n")
    assert _types(body.children) == ["LINEPADDING", "expr"]
    body = _list_body(prefix + "x, PADLINE] LIST\n")
    assert _types(body.children) == ["expr", "COMMA", "expr"]
    body = _list_body(prefix + "\nPADLINE] LIST\n")
    assert _types(body.children) == ["NEWLINE", "expr"]
    body = _list_body(prefix + "{PADLINE}{i=1 to N}] LIST\n")
    assert _types(body.children[0].children[1].children) == ["expr"]
    for text in ("PADLINE-1", "PADLINE[1]", "PADLINE?", "PADLINE2"):
        body = _list_body(prefix + text + "] LIST\n")
        assert _types(body.children) == ["expr"]


def test_linepadding_matches_lark_where_stable(lark_parser):
    prefix = "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ "
    for text in ("PADLINE-1", "PADLINE[1]", "PADLINE?", "x, PADLINE[1]"):
        recipe = prefix + text + "] LIST\n"
        assert tree_difference(lark_parser.parse(recipe), parse_recipe(recipe)) is None


def test_list_record_last_field_division():
    # the slash after the six fields of a LIST record can also be read
    # as a division in the last field; the last field is chosen as long
    # as possible (Lark's choice depends on the remainder of the record)
    prefix = "[MAT,1,452/ a, b, c, d, e, "
    tree = parse_recipe(prefix + "f/X/Y] LIST\n")
    fields = tree.children[0].children[0].children[0].children[3]
    assert _expr_text(fields.children[-1]) == "f/X"
    tree = parse_recipe(prefix + "f/X/Y/Z, x] LIST\n")
    fields = tree.children[0].children[0].children[0].children[3]
    assert _expr_text(fields.children[-1]) == "f/X/Y"


def test_juxtaposed_list_elements_maximal():
    # list elements need not be separated by commas; an expression
    # always extends as far as possible (`y -z` is one element)
    prefix = "[MAT,1,452/ 0, 0, 0, 0, 0, 0/ "
    body = _list_body(prefix + "x -y] LIST\n")
    assert _types(body.children) == ["expr"]
    body = _list_body(prefix + "x, y -z*w] LIST\n")
    assert _types(body.children) == ["expr", "COMMA", "expr"]
    body = _list_body(prefix + "x y (z)] LIST\n")
    assert _types(body.children) == ["expr", "expr", "expr"]


# ---------------------------------------------------------------------
# malformed recipes
# ---------------------------------------------------------------------

MALFORMED = {
    "too_few_fields": ("[MAT,3,MT/ a, b, c, d, e] CONT\n", 1, 27),
    "missing_newline": ("[MAT,3,MT/ a, b, c, d, e, f] CONT", 1, 34),
    "unknown_record_type": ("[MAT,3,MT/ a, b, c, d, e, f] FOO\n", 1, 30),
    "missing_endfor": ("for i=1 to N:\n" + REC, 3, 1),
    "wrong_terminator": ("if x > 1:\n" + REC + "endfor\n", 3, 1),
    "incomplete_expression": ("x := 1 +\n", 1, 9),
    "unbalanced_brackets": ("x := (a + b\n", 1, 12),
    "empty_stop_message": ('stop("")\n', 1, 7),
    "tab_character": ("x :=\t1\n", 1, 5),
    "comment_without_newline": ("# comment", 1, 1),
    "unterminated_section": ("(sec)\n" + REC + "(/sec\n", 3, 6),
    "two_brace_groups": ("[MAT,1,451/ A{10}{20}] TEXT\n", 1, 18),
    "missing_condition": ("if :\nendif\n", 1, 4),
    "bad_ctrl_spec": ("[MAT,3/ a, b, c, d, e, f] CONT\n", 1, 7),
    "garbage": ("x := 1\n$\n", 2, 1),
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_recipe_raises(lark_parser, name):
    recipe, line, column = MALFORMED[name]
    with pytest.raises(lark.exceptions.LarkError):
        lark_parser.parse(recipe)
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe(recipe)
    err = excinfo.value
    assert (err.line, err.column) == (line, column)
    assert f"line {line}, column {column}" in str(err)
    assert "Expected one of" in str(err)
    assert len(err.expected) > 0


def test_error_message_names_expected_tokens():
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe("[MAT,3,MT/ a b, c, d, e, f] CONT\n")
    assert "','" in excinfo.value.expected
    assert (excinfo.value.line, excinfo.value.column) == (1, 14)
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe("for i=1 to N:\n" + REC)
    assert "'endfor'" in excinfo.value.expected
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe("x := 1 +\n")
    assert {"NUMBER", "VARNAME", "'('", "'-'"} <= set(excinfo.value.expected)
    with pytest.raises(RecipeSyntaxError) as excinfo:
        parse_recipe("[MAT,3,MT/ a, b, c, d, e, f] FOO\n")
    assert {"CONT_SUBTYPE", "'TEXT'"} <= set(excinfo.value.expected)


# ---------------------------------------------------------------------
# node classes
# ---------------------------------------------------------------------


def _strip(node):
    if isinstance(node, lark.Token):
        return (node.type, str(node))
    return (str(node.data), [_strip(c) for c in node.children])


def test_iter_subtrees_order_as_lark(lark_parser):
    recipe = SYNTHETIC_CORPUS["nested_everything"]
    ref = [_strip(t) for t in lark_parser.parse(recipe).iter_subtrees()]
    test = parse_recipe(recipe)
    assert [str(t.data) for t in test.iter_subtrees()] == [r[0] for r in ref]
    assert [str(t.data) for t in test.iter_subtrees_topdown()] == [
        str(t.data) for t in lark_parser.parse(recipe).iter_subtrees_topdown()
    ]


def test_node_semantics():
    tree = parse_recipe("x := a + 1\n")
    assert isinstance(tree.data, Token) and tree.data.type == "RULE"
    assert tree.data == "endf_recipe"
    assert tree == parse_recipe("x := a + 1\n")
    assert hash(tree) == hash(parse_recipe("x := a + 1\n"))
    assert tree != parse_recipe("x := a + 2\n")
    tok = Token("VARNAME", "x")
    assert tok == "x" and tok == Token("VARNAME", "x")
    assert tok != Token("NUMBER", "x") or not (tok == Token("NUMBER", "x"))
    assert not (tok == Token("NUMBER", "x"))
    assert hash(tok) == hash("x")
    assert repr(tok) == "Token('VARNAME', 'x')"
    assert repr(Tree("a", [tok])) == "Tree('a', [Token('VARNAME', 'x')])"
    assert tok.update(value="y") == Token("VARNAME", "y")
    assert tok.update(type="NUMBER").type == "NUMBER"
    # free attribute assignment on tree nodes, copies are shallow
    tree.parent = None
    cp = tree.copy()
    assert cp == tree and cp is not tree and cp.children is tree.children
    # Token positions
    abbr = tree.children[0].children[0]
    var = abbr.children[0]
    assert (var.line, var.column, var.start_pos, var.end_pos) == (1, 1, 0, 1)


def test_recipe_parser_object():
    parser = get_recipe_parser()
    assert parser.parse("x := 1\n") == parse_recipe("x := 1\n")
