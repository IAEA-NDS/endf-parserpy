############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import re
from fractions import Fraction
from endf_parserpy.recipe_parser.tree import Tree
from endf_parserpy.recipe_parser.tree import Token
from .tree_walkers import transform_nodes
from .node_checks import (
    is_expr,
    is_addition,
    is_subtraction,
    is_multiplication,
    is_division,
    is_modulo,
    is_minusexpr,
    is_number,
    is_variable,
    has_factor,
    is_desired_number,
    is_inconsistent_variable,
)


# All the following node transformation functions
# are based on the assumption that the children
# of each untransformed node have already been
# transformed by the same transformation function.
# Effecting all transformations in this so-called
# postorder traversal order is done by `transform_nodes`
# in the `tree_walkers` module.


def replace_node(node, old, new):
    if node == old:
        return new
    return node


def eliminate_subtraction(node):
    if isinstance(node, Tree) and node.data == "subtraction":
        term1 = node.children[0]
        term2 = Tree("minusexpr", [node.children[1]])
        return Tree("addition", [term1, term2])
    return node


def eliminate_minusexpr(node):
    if not isinstance(node, Tree):
        return node
    if node.data == "minusexpr":
        term1 = Token("NUMBER", "-1")
        term2 = node.children[0]
        return Tree("multiplication", [term1, term2])
    return node


def factorout_division(node):
    if not isinstance(node, Tree):
        return node
    if node.data != "division":
        return node
    numerator = Token("NUMBER", "1")
    # 1/6 is an exact fraction in the generated code (see `cpp_div`),
    # so integer denominators need no conversion to floats
    denominator = node.children[1]
    factor1 = node.children[0]
    factor2 = Tree("division", [numerator, denominator])
    return Tree("multiplication", [factor1, factor2])


def flatten_multiplication(node):
    if not is_multiplication(node):
        return node
    new_children = []
    for child in node.children:
        if is_multiplication(child):
            new_children.extend(child.children)
        else:
            new_children.append(child)
    new_node = Tree("multiplication", new_children)
    return new_node


def flatten_addition(node):
    if not is_addition(node):
        return node
    new_children = []
    for child in node.children:
        if is_addition(child):
            new_children.extend(child.children)
        else:
            new_children.append(child)
    new_node = Tree("addition", new_children)
    return new_node


def convert_negnums_to_minusexpr(node):
    if not is_number(node):
        return node
    if float(node.value) >= 0:
        return node
    new_valstr = node.value.strip().lstrip("-")
    new_num = Token("NUMBER", new_valstr)
    return Tree("minusexpr", [new_num])


def evaluate_int_multiplication(node):
    if not is_multiplication(node):
        return node
    int_prod = 1
    new_factors = []
    for fact in node.children:
        if is_number(fact):
            try:
                int_prod *= int(fact.value)
            except ValueError:
                new_factors.append(fact)
        else:
            new_factors.append(fact)
    if int_prod != 1 or len(new_factors) == 0:
        new_factors.append(Token("NUMBER", str(int_prod)))
    if len(new_factors) == 1:
        return new_factors[0]
    else:
        return Tree("multiplication", new_factors)


def evaluate_int_addition(node):
    if not is_addition(node):
        return node
    int_sum = 0
    new_terms = []
    for term in node.children:
        if is_number(term):
            try:
                int_sum += int(term.value)
            except ValueError:
                new_terms.append(term)
        else:
            new_terms.append(term)
    if int_sum != 0:
        new_terms.append(Token("NUMBER", str(int_sum)))
    if len(new_terms) == 1:
        return new_terms[0]
    else:
        return Tree("addition", new_terms)


def evaluate_int_ops(node):
    if is_addition(node):
        return evaluate_int_addition(node)
    elif is_multiplication(node):
        return evaluate_int_multiplication(node)
    else:
        return node


def _expand_twofactor_product(node1, node2):
    if isinstance(node1, Tree):
        nc1 = node1.children
    if isinstance(node2, Tree):
        nc2 = node2.children
    if is_addition(node1) and is_addition(node2):
        new_terms = [Tree("multiplication", [t1, t2]) for t1 in nc1 for t2 in nc2]
        return Tree("addition", new_terms)
    elif is_addition(node1):
        new_terms = [Tree("multiplication", [node2, t]) for t in nc1]
        return Tree("addition", new_terms)
    elif is_addition(node2):
        new_terms = [Tree("multiplication", [node1, t]) for t in nc2]
        return Tree("addition", new_terms)
    else:
        return Tree("multiplication", [node1, node2])


def expand_product(node):
    if not is_multiplication(node):
        return node
    children = node.children
    worknode = children[0]
    for child in children[1:]:
        worknode = _expand_twofactor_product(worknode, child)
    worknode = transform_nodes(worknode, flatten_multiplication)
    return worknode


def remove_factor_from_product(node, factor):
    if not is_multiplication(node):
        if factor == node:
            return Token("NUMBER", "1")
        else:
            raise TypeError("node must contain factor")
    new_children = []
    found_factor = False
    for child in node.children:
        if child == factor and not found_factor:
            found_factor = True
        else:
            new_children.append(child)
    if not found_factor:
        raise TypeError("node must contain factor")
    if len(new_children) == 0:
        if node.children[0] != factor:
            raise NotImplementedError("who implemented this stupid routine??")
        new_children.append(factor)
    return Tree("multiplication", new_children)


def extract_factor(node, factor):
    if is_addition(node):
        terms = node.children
    elif is_multiplication(node):
        terms = [node]
    else:
        raise TypeError("expect addition or multiplication node")
    new_terms = []
    for term in terms:
        new_product = remove_factor_from_product(term, factor)
        new_terms.append(new_product)
    if len(new_terms) == 1:
        new_node = new_terms[0]
    else:
        new_node = Tree("addition", new_terms)
    return Tree("multiplication", [factor, new_node])


def _get_term_factor_sets(terms):
    """Determine the factors contributing to each term"""
    term_els = {}
    for term in terms:
        # use dict instead of set for stable ordering
        # to ensure reproducible code generation
        curset = term_els.setdefault(term, dict())
        if is_multiplication(term):
            for c in term.children:
                curset[c] = None
        else:
            curset[term] = None
    return term_els


def _count_factor_appearance(term_factors):
    """Count how many terms have each factor"""
    factor_counts = {}
    for term, factorset in term_factors.items():
        for factor in factorset:
            factor_counts.setdefault(factor, 0)
            factor_counts[factor] += 1
    return factor_counts


def get_most_common_factor(node):
    term_factors = _get_term_factor_sets(node.children)
    factor_counts = _count_factor_appearance(term_factors)
    maxcount = max(c for c in factor_counts.values())
    elmax = tuple(el for el, c in factor_counts.items() if c == maxcount)[0]
    return elmax


def factorout_common(node):
    if not is_addition(node):
        return node
    if len(node.children) == 1:
        return node.children[0]

    factor = get_most_common_factor(node)
    # factoring out the number 1, e.g. 1+1 == 1*(1+1), does not simplify
    # the expression and would be repeated endlessly
    if is_number(factor) and float(factor.value) == 1:
        return node
    terms1 = []
    terms2 = []
    for child in node.children:
        if has_factor(child, factor):
            terms1.append(child)
        else:
            terms2.append(child)

    # return if no common factors
    if len(terms1) <= 1:
        return node

    new_node = Tree("addition", terms1)
    new_node = extract_factor(new_node, factor)
    new_node = transform_nodes(new_node, factorout_common)
    final_terms = [new_node]

    if len(terms2) >= 2:
        other_addition = Tree("addition", terms2)
        other_addition = factorout_common(other_addition)
        final_terms.append(other_addition)
    elif len(terms2) == 1:
        final_terms.append(terms2[0])

    if len(final_terms) == 1:
        return final_terms[0]
    else:
        return Tree("addition", final_terms)


def node2str(node):
    if is_expr(node):
        assert len(node.children) == 1
        return node.children[0]
    elif is_number(node):
        if node.value.strip().startswith("-"):
            return "(" + str(node.value) + ")"
        else:
            return str(node.value)
    elif is_variable(node):
        return str(node.value)

    if is_addition(node):
        exprstr = "+".join(node.children)
    elif is_subtraction(node):
        exprstr = "-".join(node.children)
    elif is_multiplication(node):
        exprstr = "*".join(node.children)
    elif is_division(node):
        assert len(node.children) == 2
        exprstr = "/".join(node.children)
    elif is_modulo(node):
        assert len(node.children) == 2
        exprstr = "%".join(node.children)
    elif is_minusexpr(node):
        assert len(node.children) == 1
        exprstr = "-" + node.children[0]
    else:
        node_name = node.type if isinstance(node, Token) else node.data
        raise TypeError(f"unknown node type `{node_name}`")

    return "(" + exprstr + ")"


class CppFloatValue(str):
    """C++ code of a value of a float field (of type EndfFloatCpp).

    Such a value enters arithmetic as a double (see `cpp_operand`).
    """


_DECIMAL_LITERAL = re.compile(
    r"^([0-9]*\.[0-9]*([eE][-+]?[0-9]+)?|[0-9]+[eE][-+]?[0-9]+)$"
)


def _exact_decimal_literal(code):
    # recognizes decimal literals, also negated and in parentheses,
    # e.g. 0.5, (-0.5), -(0.5), and returns their exact value
    s = code.strip()
    negative = False
    while True:
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
        elif s.startswith("-"):
            negative = not negative
            s = s[1:].strip()
        else:
            break
    if _DECIMAL_LITERAL.match(s) is None:
        return None
    value = Fraction(s)
    return -value if negative else value


def cpp_operand(code):
    """Convert the C++ code of an operand of an arithmetic operation.

    - A value of a float field becomes a double.
    - A decimal literal becomes its exact value (choice of the recipe
      language: decimal literals are exact, e.g. 0.1 is 1/10), i.e. an
      integer literal or an EndfRational.
    Other operands are returned unchanged.
    """
    if isinstance(code, CppFloatValue):
        return f"static_cast<double>({code})"
    value = _exact_decimal_literal(code)
    if value is None:
        return code
    if value.denominator == 1:
        num = value.numerator
        return f"({num})" if num < 0 else str(num)
    return f"EndfRational({value.numerator}, {value.denominator})"


_CPP_OPERATORS = {
    "addition": "+",
    "subtraction": "-",
    "multiplication": "*",
}


def node2cppstr(node):
    # Like node2str but for C++ code: divisions and modulo operations
    # are mapped to the functions `cpp_div` and `cpp_mod` (see
    # `cpp_templates/module_header.hpp`), and the operands of arithmetic
    # operations are converted by `cpp_operand`, so that the arithmetic
    # gives the same results as in the Python parser.
    if is_division(node) or is_modulo(node):
        assert len(node.children) == 2
        func = "cpp_div" if is_division(node) else "cpp_mod"
        ops = [cpp_operand(c) for c in node.children]
        return f"{func}({ops[0]}, {ops[1]})"
    if isinstance(node, Tree) and node.data in _CPP_OPERATORS:
        op = _CPP_OPERATORS[node.data]
        return "(" + op.join(cpp_operand(c) for c in node.children) + ")"
    if is_minusexpr(node):
        assert len(node.children) == 1
        return "(-" + cpp_operand(node.children[0]) + ")"
    return node2str(node)


def node_contains_modulo(tree):
    if is_modulo(tree):
        return True
    if not isinstance(tree, Tree):
        return False
    return any(tree.children)


def node_contains_variable(node):
    if is_variable(node):
        return True
    if not isinstance(node, Tree):
        return False
    return any(node.children)


def node_contains_desired_number(node):
    if is_desired_number(node):
        return True
    if not isinstance(node, Tree):
        return False
    return any(node.children)


def node_contains_potentially_inconsistent_variable(node):
    if is_inconsistent_variable(node):
        return True
    if not isinstance(node, Tree):
        return False
    return any(node.children)
