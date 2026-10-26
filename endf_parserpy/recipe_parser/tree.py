############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Node classes of ENDF recipe parse trees.

The classes :class:`Tree` and :class:`Token` mirror the interface of the
``lark.Tree`` and ``lark.Token`` classes (Lark 1.x) to the extent used by
endf-parserpy, so that parse trees produced by
:mod:`endf_parserpy.recipe_parser.parser` can be consumed by the
interpreter and the compiler in exactly the same way as the trees
previously produced by Lark:

- :class:`Token` is a ``str`` subclass with a ``type`` attribute and the
  same constructor signature, equality, hashing and ``repr`` as
  ``lark.Token``;
- :class:`Tree` has ``data`` and ``children`` attributes, accepts free
  attribute assignment, and provides the same equality, hashing,
  ``repr``, ``copy``, ``set``, ``pretty`` and ``iter_subtrees``
  (including its traversal order) as ``lark.Tree``.

There is no dependency on Lark.
"""

from copy import deepcopy
from typing import List, Optional, TypeVar, Union


class Meta:
    """Container for position information of a tree node."""

    def __init__(self):
        self.empty = True


_Leaf_T = TypeVar("_Leaf_T")
Branch = Union[_Leaf_T, "Tree"]


class Tree:
    """A node of a parse tree.

    Parameters
    ----------
    data : str
        The name of the grammar rule; in trees produced by the
        recipe parser, a :class:`Token` of type ``RULE``.
    children : list
        The child nodes (instances of :class:`Tree` or :class:`Token`).
    meta : Meta, optional
        Position information (not populated by the recipe parser).
    """

    def __init__(
        self, data: str, children: "List[Branch]", meta: Optional[Meta] = None
    ) -> None:
        self.data = data
        self.children = children
        self._meta = meta

    @property
    def meta(self) -> Meta:
        if self._meta is None:
            self._meta = Meta()
        return self._meta

    def __repr__(self):
        return "Tree(%r, %r)" % (self.data, self.children)

    def _pretty_label(self):
        return self.data

    def _pretty(self, level, indent_str):
        yield f"{indent_str*level}{self._pretty_label()}"
        if len(self.children) == 1 and not isinstance(self.children[0], Tree):
            yield f"\t{self.children[0]}\n"
        else:
            yield "\n"
            for n in self.children:
                if isinstance(n, Tree):
                    yield from n._pretty(level + 1, indent_str)
                else:
                    yield f"{indent_str*(level+1)}{n}\n"

    def pretty(self, indent_str: str = "  ") -> str:
        """Return an indented string representation of the tree."""
        return "".join(self._pretty(0, indent_str))

    def __eq__(self, other):
        try:
            return self.data == other.data and self.children == other.children
        except AttributeError:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self.data, tuple(self.children)))

    def iter_subtrees(self):
        """Depth-first iteration over all subtrees (bottom-up order).

        Each node is returned once, also if it appears several times
        in the tree. The order is identical to ``lark.Tree.iter_subtrees``.
        """
        queue = [self]
        subtrees = dict()
        for subtree in queue:
            subtrees[id(subtree)] = subtree
            queue += [
                c
                for c in reversed(subtree.children)
                if isinstance(c, Tree) and id(c) not in subtrees
            ]
        del queue
        return reversed(list(subtrees.values()))

    def iter_subtrees_topdown(self):
        """Iterate over all subtrees in the order of :meth:`pretty`."""
        stack = [self]
        stack_append = stack.append
        stack_pop = stack.pop
        while stack:
            node = stack_pop()
            if not isinstance(node, Tree):
                continue
            yield node
            for child in reversed(node.children):
                stack_append(child)

    def find_pred(self, pred):
        """Return all subtrees for which ``pred(subtree)`` is true."""
        return filter(pred, self.iter_subtrees())

    def find_data(self, data: str):
        """Return all subtrees whose ``data`` equals the given value."""
        return self.find_pred(lambda t: t.data == data)

    def scan_values(self, pred):
        """Return all leaves (tokens) for which ``pred(leaf)`` is true."""
        for c in self.children:
            if isinstance(c, Tree):
                for t in c.scan_values(pred):
                    yield t
            else:
                if pred(c):
                    yield c

    def __deepcopy__(self, memo):
        return type(self)(self.data, deepcopy(self.children, memo), meta=self._meta)

    def copy(self) -> "Tree":
        return type(self)(self.data, self.children)

    def set(self, data: str, children: "List[Branch]") -> None:
        self.data = data
        self.children = children


class Token(str):
    """A string with a type (the name of the terminal) and position info.

    Parameters
    ----------
    type : str
        The name of the terminal, e.g. ``VARNAME`` or ``NUMBER``.
    value : str
        The matched text.
    start_pos, line, column, end_line, end_column, end_pos : int, optional
        Position information (lines and columns counted from 1).
    """

    __slots__ = (
        "type",
        "start_pos",
        "value",
        "line",
        "column",
        "end_line",
        "end_column",
        "end_pos",
    )

    __match_args__ = ("type", "value")

    def __new__(
        cls,
        type,
        value,
        start_pos=None,
        line=None,
        column=None,
        end_line=None,
        end_column=None,
        end_pos=None,
    ):
        inst = super(Token, cls).__new__(cls, value)
        inst.type = type
        inst.start_pos = start_pos
        inst.value = value
        inst.line = line
        inst.column = column
        inst.end_line = end_line
        inst.end_column = end_column
        inst.end_pos = end_pos
        return inst

    def update(self, type=None, value=None):
        """Return a new token with updated type and/or value."""
        return Token.new_borrow_pos(
            type if type is not None else self.type,
            value if value is not None else self.value,
            self,
        )

    @classmethod
    def new_borrow_pos(cls, type_, value, borrow_t):
        return cls(
            type_,
            value,
            borrow_t.start_pos,
            borrow_t.line,
            borrow_t.column,
            borrow_t.end_line,
            borrow_t.end_column,
            borrow_t.end_pos,
        )

    def __reduce__(self):
        return (
            self.__class__,
            (self.type, self.value, self.start_pos, self.line, self.column),
        )

    def __repr__(self):
        return "Token(%r, %r)" % (self.type, self.value)

    def __deepcopy__(self, memo):
        return Token(self.type, self.value, self.start_pos, self.line, self.column)

    def __eq__(self, other):
        if isinstance(other, Token) and self.type != other.type:
            return False
        return str.__eq__(self, other)

    __hash__ = str.__hash__
