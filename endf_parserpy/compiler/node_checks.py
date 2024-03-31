from lark.tree import Tree
from lark.lexer import Token


def is_code_token(node):
    return isinstance(node, Tree) and node.data == "code_token"


def is_expr(node):
    return isinstance(node, Tree) and node.data == "expr"


def is_head_or_cont(node):
    return isinstance(node, Tree) and node.data == "head_or_cont_line"


def is_dir(node):
    return isinstance(node, Tree) and node.data == "dir_line"


def is_tab1(node):
    return isinstance(node, Tree) and node.data == "tab1_line"


def is_tab2(node):
    return isinstance(node, Tree) and node.data == "tab2_line"


def is_list(node):
    return isinstance(node, Tree) and node.data == "list_line"


def is_text(node):
    return isinstance(node, Tree) and node.data == "text_line"


def is_section(node):
    return isinstance(node, Tree) and node.data == "section"


def is_extvar(node):
    return isinstance(node, Tree) and node.data == "extvarname"


def is_textplaceholder(node):
    return isinstance(node, Tree) and node.data == "textplaceholder"


def is_for_loop(node):
    return isinstance(node, Tree) and node.data == "for_loop"


def is_if_clause(node):
    return isinstance(node, Tree) and node.data == "if_clause"


def is_abbreviation(node):
    return isinstance(node, Tree) and node.data == "abbreviation"
