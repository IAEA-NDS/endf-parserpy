############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token


def is_code_token(node):
    return isinstance(node, Tree) and node.data == "code_token"


def is_expr(node):
    return isinstance(node, Tree) and node.data == "expr"


def is_send(node):
    return isinstance(node, Tree) and node.data == "send_line"


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


def is_intg(node):
    return isinstance(node, Tree) and node.data == "intg_line"


def is_section(node):
    return isinstance(node, Tree) and node.data == "section"


def is_stop(node):
    return isinstance(node, Tree) and node.data == "stop_line"


def is_extvar(node):
    return isinstance(node, Tree) and node.data == "extvarname"


def is_textplaceholder(node):
    return isinstance(node, Tree) and node.data == "textplaceholder"


def is_for_loop(node):
    return isinstance(node, Tree) and node.data == "for_loop"


def is_repeat_loop(node):
    return isinstance(node, Tree) and node.data == "repeat_loop"


def is_loop(node):
    return isinstance(node, Tree) and node.data in (
        "for_loop",
        "list_loop",
        "repeat_loop",
    )


def is_loop_head(node):
    return isinstance(node, Tree) and node.data in ("for_head", "list_for_head")


def is_if_clause(node):
    return isinstance(node, Tree) and node.data == "if_clause"


def is_if_condition(node):
    return isinstance(node, Tree) and node.data == "if_condition"


def is_abbreviation(node):
    return isinstance(node, Tree) and node.data == "abbreviation"
