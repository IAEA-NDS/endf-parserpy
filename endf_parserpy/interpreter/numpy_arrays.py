############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/21
# Last modified:   2026/10/21
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

This module does not import numpy itself; the functions that need it
receive the numpy module as argument.
"""

import sys
from collections.abc import Mapping
from .endf_mapping_utils import get_indexvalue


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


def prepare_elements(forms, datadic, loop_vars, parse_opts, preparations):
    """Create the elements of nested arrays created before a loop.

    ``preparations`` is the ``_np_prepare`` annotation of the loop node.
    The elements are created in the internal ``"dict"`` representation
    of arrays (keys are the indices of the recipe).
    """
    kinds = _kinds_of(forms, datadic)
    for varname, indexspecs, kind in preparations:
        cur = datadic.get(varname)
        if cur is None:
            cur = datadic[varname] = {}
        # an index is given by the name of a loop variable or by an
        # indexquant node
        for q in indexspecs:
            if type(cur) is not dict:
                break
            if type(q) is str:
                idx = loop_vars[q]
            else:
                idx = get_indexvalue(q, datadic, loop_vars, parse_opts, True)
            nxt = cur.get(idx)
            if nxt is None:
                nxt = cur[idx] = {}
            cur = nxt
        if varname not in kinds:
            kinds[varname] = kind


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
        container, dtype, nidx, is_triagonal, is_lower = kind
        if container == "Scalar":
            if dtype not in _VEC_DTYPES:
                return value
            return self.to_nested(value, self.element_dtype(dtype), 1)
        npdtype = self.element_dtype(dtype)
        if container == "NestedVector":
            depth = nidx + 1 if dtype in _VEC_DTYPES else nidx
            return self.to_nested(value, npdtype, depth)
        # Matrix2d
        if npdtype is None or type(value) is not list:
            return value
        if is_triagonal:
            return [self.to_1d(row, npdtype) for row in value]
        arr = self.np.array(value, dtype=npdtype)
        if arr.ndim != 2:
            raise TypeError("matrix is not rectangular")
        return arr

    def to_nested(self, value, npdtype, depth):
        if type(value) is dict and len(value) == 0:
            # an element created before a loop without assigned elements
            if depth == 1 and npdtype is not None:
                return self.np.empty(0, dtype=npdtype)
            return []
        if type(value) is not list:
            return value
        if depth == 1:
            return value if npdtype is None else self.to_1d(value, npdtype)
        return [self.to_nested(v, npdtype, depth - 1) for v in value]

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
