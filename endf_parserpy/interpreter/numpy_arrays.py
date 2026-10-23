############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Support of ``array_type="numpy"`` in :class:`~endf_parserpy.EndfParserPy`.

With ``array_type="numpy"``, the Python parser returns the same result
as :class:`~endf_parserpy.EndfParserCpp` with this option. The recipe
parse trees are annotated with the container kinds of the variables
(:mod:`endf_parserpy.interpreter.numpy_annotation`). While parsing, the
interpreter records for each section dictionary the kind of each
variable when it executes a node at which the C++ code assigns the
variable (:func:`mark_assignments`), and creates the possibly empty
elements of nested arrays where the C++ code creates them
(:func:`prepare_elements`). After an MF/MT section has been parsed as with
``array_type="list"``, :func:`convert_arrays` converts the arrays of
numbers according to the recorded kinds.

The kind recorded first for a variable in a section dictionary is used.
The generated C++ code raises an error if a variable is assigned with
different kinds, and it does not change the type of a variable when it
only checks the value of a variable read before; therefore the C++
variable that is stored is that of the first assignment.

The elements of nested arrays are also created with ``array_type="list"``
and ``"list_slow"``, so that empty inner arrays are empty lists as with
:class:`~endf_parserpy.EndfParserCpp` (:func:`fill_empty_elements`), and
the writer registers the start indices of nested arrays at the same
places in these modes.

This module does not import numpy itself; the functions that need it
receive the numpy module as argument.
"""

import sys
from endf_parserpy.utils.tree_utils import get_child
from collections.abc import Mapping
from .endf_mapping_utils import get_indexvalue, eval_expr_without_unknown_var
from .helpers import shift_indices, list_setdefault


def _kinds_of(forms, datadic):
    entry = forms.get(id(datadic))
    if entry is None or entry[0] is not datadic:
        entry = (datadic, {})
        forms[id(datadic)] = entry
    return entry[1]


def mark_assignments(forms, datadic, marks):
    """Record the kinds of the variables assigned at a node.

    ``forms`` maps the ``id`` of each section dictionary to the
    dictionary and a dictionary of the kinds of its variables;
    ``marks`` is the ``_np_marks`` annotation of the node.
    """
    kinds = _kinds_of(forms, datadic)
    for varname, kind in marks:
        if varname not in kinds:
            kinds[varname] = kind


def _index_values(indexspecs, datadic, loop_vars, parse_opts):
    # an index is given by the name of a loop variable or by an
    # indexquant node
    return [
        (
            loop_vars[q]
            if type(q) is str
            else get_indexvalue(q, datadic, loop_vars, parse_opts, True)
        )
        for q in indexspecs
    ]


def _create_element(datadic, varname, idcs, parse_opts):
    # create the (possibly nested) element with the recipe indices idcs
    # in the internal representation of arrays, as dictionaries (keys are
    # the indices of the recipe) or, with array_type="list_slow", as
    # lists; returns the element and its container and key in the
    # container, or None if an element on the way is not an array
    if parse_opts["internal_array_type"] == "list":
        idcs = shift_indices(varname, idcs, datadic)
        cur = datadic.setdefault(varname, [])
        parent = key = None
        for idx in idcs:
            parent, key = cur, idx
            cur = list_setdefault(cur, idx, [])
        return cur, parent, key
    cur = datadic.get(varname)
    if cur is None:
        cur = datadic[varname] = {}
    parent = key = None
    for idx in idcs:
        if type(cur) is not dict:
            return None
        parent, key = cur, idx
        nxt = cur.get(idx)
        if nxt is None:
            nxt = cur[idx] = {}
        cur = nxt
    return cur, parent, key


def prepare_elements(forms, datadic, loop_vars, parse_opts, preparations):
    """Create the elements of nested arrays created before a loop.

    ``preparations`` is the ``_np_prepare`` annotation of the loop node.
    The elements are created in the internal representation of arrays,
    as dictionaries (keys are the indices of the recipe) or, with
    ``array_type="list_slow"``, as lists. When writing (in the list
    modes), only the start indices of the arrays are registered, so that
    the elements are found at the same positions as after parsing.
    """
    kinds = _kinds_of(forms, datadic)
    for varname, indexspecs, kind in preparations:
        idcs = _index_values(indexspecs, datadic, loop_vars, parse_opts)
        if "array_write" in parse_opts:
            # writing: only the start indices are registered
            if parse_opts["internal_array_type"] == "list":
                shift_indices(varname, idcs, datadic)
            continue
        _create_element(datadic, varname, idcs, parse_opts)
        if varname not in kinds:
            kinds[varname] = kind


class EmptyBlock(dict):
    """A regular block without elements, with its shape.

    With ``array_type="numpy"``, a regular block of numbers with leading
    indices is a numpy array of the shape of the block also if it has no
    elements, e.g. of shape ``(0, 3)``; the shape is only known from the
    limits of the loops of the block. It is recorded by representing the
    block as instance of this class instead of a dictionary until the
    conversion to numpy arrays (:func:`convert_arrays`). An empty
    dictionary is not converted to a list (see ``array_dict_to_list``).
    """

    __slots__ = ("shape",)


def create_blocks(datadic, loop_vars, parse_opts, blocks):
    """Create the regular blocks created before a loop.

    ``blocks`` is the ``_np_blocks`` annotation of the loop node. A block
    with leading indices is an element of the array, created where the
    C++ code creates it. If the block has no elements, it is the empty
    list of rows (if its first dimension is not zero, e.g. ``[[], []]``
    for the shape ``(2, 0)``) or, if it is converted to a numpy array, an
    :class:`EmptyBlock`. A block without leading indices is the whole
    variable, which only exists if the block has elements (as in the C++
    code), so nothing needs to be done.
    """
    if "array_write" in parse_opts:
        return
    keep_floats = parse_opts.get("numpy_keep_floats")
    for varname, indexspecs, loops, kind in blocks:
        if len(indexspecs) == 0:
            continue
        shape = tuple(
            max(0, stop - start + 1)
            for start, stop in (
                loop_limits(loop, datadic, loop_vars, parse_opts) for loop in loops
            )
        )
        if all(shape):
            continue
        idcs = _index_values(indexspecs, datadic, loop_vars, parse_opts)
        created = _create_element(datadic, varname, idcs, parse_opts)
        if created is None:
            continue
        block, parent, key = created
        is_numeric = kind[1] == "int" or (kind[1] == "float" and not keep_floats)
        if keep_floats is not None and is_numeric:
            if type(block) is dict and len(block) == 0:
                parent[key] = EmptyBlock()
                parent[key].shape = shape
            continue
        # the rows (and rows of rows...) before the first dimension zero
        firsts = [loop_limits(l, datadic, loop_vars, parse_opts)[0] for l in loops]
        for pos in _positions(shape[: shape.index(0)]):
            row = [first + p for first, p in zip(firsts, pos)]
            _create_element(datadic, varname, idcs + row, parse_opts)


def loop_limits(loop, datadic, loop_vars, parse_opts):
    """The first and last value of the variable of a for or LIST loop."""
    head = get_child(loop, "for_head" if loop.data == "for_loop" else "list_for_head")
    return tuple(
        int(
            eval_expr_without_unknown_var(
                get_child(head, n), datadic, loop_vars, parse_opts
            )
        )
        for n in ("for_start", "for_stop")
    )


def _positions(dims):
    if len(dims) == 0:
        return
    if len(dims) == 1:
        for i in range(dims[0]):
            yield (i,)
        return
    for i in range(dims[0]):
        for rest in _positions(dims[1:]):
            yield (i,) + rest


def fill_empty_elements(forms):
    """Replace the elements created without values by empty lists.

    Used with ``array_type="list"`` after the conversion of the arrays
    from their internal representation as dictionaries, which leaves the
    created elements as empty dictionaries.
    """
    for datadic, kinds in forms.values():
        for varname in kinds:
            value = datadic.get(varname)
            if type(value) is dict or type(value) is list:
                datadic[varname] = _empty_dicts_to_lists(value)


def _empty_dicts_to_lists(value):
    if type(value) is dict:
        return [] if len(value) == 0 else value
    for i, v in enumerate(value):
        if type(v) is dict or type(v) is list:
            value[i] = _empty_dicts_to_lists(v)
    return value


# ---------------------------------------------------------------------
# conversion of the "list"-mode result
# ---------------------------------------------------------------------

_VEC_DTYPES = {"floatvec": "float", "intvec": "int"}


class _Converter:

    def __init__(self, np, keep_floats):
        self.np = np
        self.dtypes = {"float": np.float64, "int": np.int64}
        self.keep_floats = keep_floats

    def element_dtype(self, dtype):
        # numpy dtype of the arrays of numbers, None if there are none
        dtype = _VEC_DTYPES.get(dtype, dtype)
        if dtype == "float" and self.keep_floats:
            return None
        return self.dtypes.get(dtype)

    def convert(self, value, kind):
        container, dtype, nidx, rank = kind
        npdtype = self.element_dtype(dtype)
        if container == "Scalar":
            if dtype not in _VEC_DTYPES:
                return value
            return self.to_nested(value, npdtype, 1, 1)
        if dtype in _VEC_DTYPES:
            return self.to_nested(value, npdtype, nidx + 1, 1)
        # the trailing `rank` indices of a regular block form one array
        if rank < 2 or npdtype is None:
            rank = 1
        return self.to_nested(value, npdtype, nidx, rank)

    def to_nested(self, value, npdtype, depth, rank):
        # value has `depth` indices, the last `rank` of which form a
        # single numpy array
        if type(value) is EmptyBlock:
            return self.np.empty(value.shape, dtype=npdtype)
        if type(value) is dict and len(value) == 0:
            # an element created before a loop without assigned elements
            if depth == 1 and npdtype is not None:
                return self.np.empty(0, dtype=npdtype)
            return []
        if type(value) is not list:
            return value
        if depth == rank:
            if npdtype is None:
                return value
            if rank == 1:
                return self.to_1d(value, npdtype)
            arr = self.np.array(value, dtype=npdtype)
            if arr.ndim != rank:
                raise TypeError("regular block is not rectangular")
            return arr
        return [self.to_nested(v, npdtype, depth - 1, rank) for v in value]

    def to_1d(self, value, npdtype):
        if type(value) is not list:
            return value
        try:
            arr = self.np.array(value, dtype=npdtype)
        except TypeError:
            # an array with missing elements (None), which cannot occur
            # in the C++ parser, remains a list
            return value
        if arr.ndim != 1:
            raise TypeError("unexpected nested array")
        return arr


def convert_arrays(np, forms, keep_floats):
    """Convert the arrays of the ``"list"``-mode result of a section in place.

    Parameters
    ----------
    np : module
        The numpy module.
    forms : dict
        The kinds of the variables recorded during parsing, see
        :func:`mark_assignments`.
    keep_floats : bool
        If ``True`` (``preserve_value_strings=True``), arrays of floats
        remain lists.
    """
    conv = _Converter(np, keep_floats)
    for datadic, kinds in forms.values():
        for varname, kind in kinds.items():
            value = datadic.get(varname)
            if type(value) is list or type(value) is dict:
                datadic[varname] = conv.convert(value, kind)


# ---------------------------------------------------------------------
# writing: numpy arrays and scalars as Python objects
# ---------------------------------------------------------------------


def numpy_to_python(obj):
    """Return ``obj`` with numpy arrays and scalars replaced by Python objects.

    Numpy arrays become (nested) lists of Python numbers (via ``tolist``),
    numpy scalars Python numbers, so that the writer treats them exactly
    like lists and Python numbers. Dictionaries and lists containing numpy
    objects are copied, the argument is never modified; objects without
    numpy objects are returned as they are. If numpy has not been
    imported, there cannot be any numpy objects and ``obj`` is returned.
    """
    np = sys.modules.get("numpy")
    if np is None:
        return obj
    return _numpy_to_python(obj, (np.ndarray, np.generic))


def _numpy_to_python(obj, np_types):
    t = type(obj)
    if t is float or t is int or t is str:
        return obj
    if t is list:
        new = None
        for i, v in enumerate(obj):
            tv = type(v)
            if tv is float or tv is int or tv is str:
                continue
            nv = _numpy_to_python(v, np_types)
            if nv is not v:
                if new is None:
                    new = list(obj)
                new[i] = nv
        return obj if new is None else new
    if t is dict or isinstance(obj, Mapping):
        new = None
        for k, v in obj.items():
            nv = _numpy_to_python(v, np_types)
            if nv is not v:
                if new is None:
                    new = dict(obj)
                new[k] = nv
        return obj if new is None else new
    if isinstance(obj, np_types):
        ret = obj.tolist()
        # elements of arrays of dtype object may be numpy objects
        if getattr(obj, "dtype", None) is not None and obj.dtype.kind == "O":
            ret = _numpy_to_python(ret, np_types)
        return ret
    if t is tuple:
        new = tuple(_numpy_to_python(v, np_types) for v in obj)
        return obj if all(a is b for a, b in zip(new, obj)) else new
    return obj
