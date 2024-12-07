############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/12/07
# Last modified:   2024/12/07
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark import Lark, Tree, Token
from endf_parserpy import EndfPath, EndfDict
from endf_parserpy.utils.math_utils import EndfFloat
from itertools import product
from collections.abc import MutableMapping, MutableSequence


def print_assignment(endf_path, endf_dict, prefix=""):
    if endf_path.exists(endf_dict):
        value = endf_path.get(endf_dict)
        if isinstance(value, (int, float)):
            print(f"{prefix}{endf_path} = {value}")
        else:
            typename = type(value).__name__
            print(f"{prefix}{endf_path} has type `{typename}`")
    else:
        print(f"{prefix}{endf_path} does not exist")


def endf_path_generator(endf_path, trail_dict, lead_path=EndfPath()):
    endf_path = EndfPath(endf_path)
    try:
        first_star_pos = endf_path.index(EndfPath("*"))
    except ValueError:
        first_star_pos = None

    if first_star_pos is not None:
        new_lead_path = endf_path[:first_star_pos]
        try:
            curdict = new_lead_path.get(trail_dict)
        except (KeyError, ValueError, TypeError):
            return

        if not isinstance(curdict, (MutableMapping, MutableSequence)):
            return

        results = []
        new_lead_paths = []
        # construct appropriate iterator
        # for either dict-like or list-like datatypes
        if isinstance(curdict, MutableMapping):
            it = curdict.keys()
        else:
            it = range(len(curdict))

        for k in it:
            trail_path = k + endf_path[first_star_pos + 1 :]
            new_lead_path = lead_path + new_lead_path
            yield from endf_path_generator(trail_path, curdict, new_lead_path)
    else:
        curpath = lead_path + endf_path
        yield lead_path + endf_path


logical_expr_grammar = """
    // logical expression evaluation

    ?start: logical_or

    ?logical_or: logical_and
        | logical_or "|" logical_and   -> logical_or

    ?logical_and: atom
        | logical_and "&" atom  -> logical_and

    ?atom: relation
         | "!" atom      -> logical_not
         | "(" logical_or ")"
         | endfpath "(" logical_or ")" -> prefixed_logical_expr
         | "exists" "(" endfpath ")" -> exists

    ?relation : expr "==" expr -> eq
          | expr "<" expr   -> lt
          | expr ">" expr   -> gt
          | expr "<=" expr  -> le
          | expr ">=" expr  -> ge
          | expr "!=" expr  -> neq

    ?expr : NUMBER
          | endfpath

    NUMBER : ("+" | "-")? NON_NEG_NUMBER

    endfpath : "/" PATH_ELEMENT ("/"+ PATH_ELEMENT)* "/"*
    PATH_ELEMENT : LETTER (LETTER | NUMBER)* | NUMBER | "*"

    %import common.LETTER
    %import common.NUMBER -> NON_NEG_NUMBER
    %import common.WS_INLINE

    %ignore WS_INLINE
"""


expr_parser = Lark(logical_expr_grammar, parser="lalr")


def make_robust_relation(func):
    def wrapper(x):
        cx = tuple(float(a) if isinstance(a, EndfFloat) else a for a in x)
        if not all(isinstance(v, (int, float)) for v in cx):
            return False
        return func(cx)

    return wrapper


node_fun_map = {
    # logical operators
    "logical_or": lambda x: x[0] or x[1],
    "logical_and": lambda x: x[0] and x[1],
    "logical_not": lambda x: not x[0],
    # relations
    "eq": make_robust_relation(lambda x: x[0] == x[1]),
    "lt": make_robust_relation(lambda x: x[0] < x[1]),
    "gt": make_robust_relation(lambda x: x[0] > x[1]),
    "le": make_robust_relation(lambda x: x[0] <= x[1]),
    "ge": make_robust_relation(lambda x: x[0] >= x[1]),
    "neq": make_robust_relation(lambda x: x[0] != x[1]),
    # evaluation of expr
    "NUMBER": lambda x, _: float(x[0]),
}


special_tree_handlers = {
    "endfpath": lambda n, d, o: eval_endfpath_tree(n, d, o),
    "prefixed_logical_expr": lambda n, d, o: eval_prefixed_logical_expr_tree(n, d, o),
    "exists": lambda n, d, o: eval_exists_tree(n, d, o),
}


def eval_exists_tree(node, endf_dict, opts):
    endfpath_tree = node.children[0]
    endfpath = EndfPath(endfpath_tree.children)
    endfpath_gen = endf_path_generator(endfpath, endf_dict)
    for p in endfpath_gen:
        retval = p.exists(endf_dict)
        yield retval, [p]


def eval_endfpath_tree(node, endf_dict, opts):
    path = EndfPath(node.children)
    path_gen = endf_path_generator(path, endf_dict)
    for p in path_gen:
        try:
            value = p.get(endf_dict)
            yield value, [p]
        except (KeyError, IndexError, TypeError):
            yield None, [p]


def _eval_prefixed_logical_expr(endf_path, expr, endf_dict, opts):
    if not endf_path.exists(endf_dict):
        yield None, [endf_path]
        return
    newdict = endf_path.get(endf_dict)
    eval_tree_gen = eval_tree(expr, newdict, opts)
    for retval, relpaths in eval_tree_gen:
        abspaths = [endf_path + p for p in relpaths]
        yield retval, abspaths


def eval_prefixed_logical_expr_tree(node, endf_dict, opts):
    wild_prefix = EndfPath(node.children[0].children)
    expr = node.children[1]
    path_gen = endf_path_generator(wild_prefix, endf_dict)
    for p in path_gen:
        yield from _eval_prefixed_logical_expr(p, expr, endf_dict, opts)


def eval_tree(node, endf_dict, opts):
    if isinstance(node, Tree):
        name = node.data
        if name in special_tree_handlers:
            yield from special_tree_handlers[name](node, endf_dict, opts)
            return
        results = product(*(eval_tree(c, endf_dict, opts) for c in node.children))
        for cur_results in results:
            retval = node_fun_map[name](list(r[0] for r in cur_results))
            paths_list = (r[1] for r in cur_results)
            paths = sum(paths_list, [])
            yield retval, paths
        return
    retval = node_fun_map[node.type]([node.value], endf_dict)
    paths = []
    yield retval, paths


def eval_tree_print(tree, endf_dict, opts=None):
    opts = {} if opts is None else opts
    eval_tree_gen = eval_tree(tree, endf_dict, opts)
    retval = False
    paths = []
    for retval, paths in eval_tree_gen:
        if retval:
            break
    print_policy = opts.get("print", "match")
    filename = opts.get("filename", None)
    prefix = "  "
    if print_policy == "always" or (print_policy == "match" and retval):
        if retval and filename is not None:
            print(f"match: {filename}")
        for p in paths:
            print_assignment(p, endf_dict, prefix)
    return retval


def eval_expr(expr, endf_dict, opts=None):
    opts = {} if opts is None else opts
    tree = expr_parser.parse(expr)
    return eval_tree_print(tree, endf_dict, opts)
