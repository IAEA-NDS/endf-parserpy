############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/05/08
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree
from lark.lexer import Token
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
