############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/16
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Recursive section views for path-addressed :class:`EndfFile` access.

A section retrieved from an :class:`~endf_parserpy.EndfFile` is never a
defensive copy; it is a lazy *view* over the canonical cached section
(design note ``endf_file_path_addressing.md``, decisions P3/P4). The view
wraps a ``dict`` / ``list`` and, on item access, returns a wrapper of the
same kind for a nested container and the bare value for a scalar.

Two view kinds exist, selected by the file's ``check_edits`` mode:

* :class:`_FrozenMapping` / :class:`_FrozenSequence` -- recursively
  read-only; any mutation raises :class:`TypeError`.
* :class:`_LiveMapping` / :class:`_LiveSequence` -- recursively mutable;
  a write mutates the canonical section in place and invokes a shared
  ``_touch`` callback that installs the section into the material's edit
  overlay (the no-copy-on-write model of the design note).

A view key may be a plain leaf key *or* an :class:`EndfPath` string, so a
view is path-addressable just like an :class:`~endf_parserpy.EndfDict`
(decision P4). :meth:`_SectionView.detach` returns a standalone, plain,
mutable deep copy disconnected from the file.

A numpy array in a section (``array_type="numpy"``) is returned, by
either view kind, as a *read-only* numpy view of the canonical array --
no data is copied. An in-place change of that array therefore raises
numpy's own :class:`ValueError` instead of silently corrupting a frozen
section or bypassing the ``_touch`` callback of a live one. A live view
writes into an array through a path ending at an element
(``view['xstable/xs/0'] = 1.5``) or by assigning a whole new array.
"""

import sys

from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
)

from ..utils.accessories import EndfPath, recursive_equality_check


_FROZEN_WRITE_MSG = (
    "this section was retrieved in check_edits='eager' mode and is "
    "read-only; call .detach() for an editable copy and assign it back, "
    "use the path-based write endf_file[path] = value, or open the "
    "EndfFile with check_edits='deferred' for a live write-through view"
)
_FROZEN_DELETE_MSG = (
    "this section was retrieved in check_edits='eager' mode and is "
    "read-only; assign a whole edited section back, or open the EndfFile "
    "with check_edits='deferred'"
)


def _is_ndarray(obj):
    """Whether ``obj`` is a numpy array (of any dimension).

    numpy is optional and is not imported here: if it has not been
    imported, there can be no numpy arrays.
    """
    numpy = sys.modules.get("numpy")
    return numpy is not None and isinstance(obj, numpy.ndarray)


def _readonly(value):
    """Return a numpy array as a read-only view, anything else unchanged.

    The view shares the data of the canonical array (no copy) but
    cannot be written to, so an in-place change raises numpy's
    :class:`ValueError` rather than bypassing the view.
    """
    if _is_ndarray(value):
        value = value.view()
        value.flags.writeable = False
    return value


def _own_value(value):
    """Prepare a value assigned into a section.

    A section view is detached into a plain copy, and a read-only numpy
    array -- as handed out by a view -- is copied, so that the section
    does not end up sharing (read-only) data with another section.
    """
    if isinstance(value, _SectionView):
        return value.detach()
    if _is_ndarray(value) and not value.flags.writeable:
        return value.copy()
    return value


def _plain(obj):
    """Return ``obj`` as plain, copied ``dict`` / ``list`` / scalars.

    Unwraps any :class:`_SectionView`, recursively rebuilds mappings as
    ordinary ``dict`` and lists as ordinary ``list``, copies numpy
    arrays (same dtype and shape) and leaves scalars (which are
    immutable) untouched. This is the deep copy taken by
    :meth:`_SectionView.detach`.
    """
    if isinstance(obj, _SectionView):
        obj = obj._target
    if isinstance(obj, Mapping):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    if _is_ndarray(obj):
        return obj.copy()
    return obj


def _raw_key(element):
    """Return the bare key carried by a single-element :class:`EndfPath`.

    An :class:`EndfPath` element is either an integer index or a string
    key; ``int()`` recovers it when numeric and ``str()`` otherwise.
    This is how a path element is turned back into a plain ``dict`` /
    ``list`` key without reaching into :class:`EndfPath` internals.
    """
    try:
        return int(element)
    except (ValueError, TypeError):
        return str(element)


def _navigate(target, key):
    """Resolve ``key`` to a ``(parent_container, last_key)`` pair.

    An ``int`` key is a single element addressing ``target`` directly. A
    ``str`` or :class:`EndfPath` key is interpreted as an ``EndfPath``
    relative to ``target`` (decision P4); its leading part is walked by
    the public :meth:`EndfPath.get`, which is agnostic to whether the
    intermediate containers are mappings or lists.
    """
    if isinstance(key, int):
        return target, key
    path = EndfPath(key)
    if len(path) == 0:
        raise KeyError("an empty path does not address anything")
    return path[:-1].get(target), _raw_key(path[-1])


class _SectionView:
    """Base class of the recursive section views.

    Holds the wrapped container ``_target`` and, for a live view, the
    ``_touch`` callback shared by every nested view of the same section.
    """

    __slots__ = ("_target", "_touch")
    _frozen = True

    def __init__(self, target, touch=None):
        self._target = target
        self._touch = touch

    def _wrap(self, value):
        """Wrap a nested container in a view of this view's own kind.

        A numpy array is returned as a read-only view (see
        :func:`_readonly`) and a scalar as is.
        """
        if isinstance(value, Mapping):
            cls = _FrozenMapping if self._frozen else _LiveMapping
            return cls(value, self._touch)
        if isinstance(value, list):
            cls = _FrozenSequence if self._frozen else _LiveSequence
            return cls(value, self._touch)
        return _readonly(value)

    def detach(self):
        """Return a standalone, plain, mutable deep copy of this view.

        The result is built from ordinary ``dict`` and ``list`` objects
        and is disconnected from the :class:`~endf_parserpy.EndfFile`:
        editing it never writes through to the tape. A numpy array is
        copied too, so the result shares no data with the file. It is
        the only operation that takes a deep copy.
        """
        return _plain(self._target)

    def __eq__(self, other):
        # element-wise comparison of numpy arrays (also with lists), as
        # for an EndfDict; ``==`` on an array has no single truth value
        if isinstance(other, _SectionView):
            other = other._target
        return recursive_equality_check(self._target, other, set())

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    __hash__ = None

    def __repr__(self):
        kind = "frozen" if self._frozen else "live"
        return f"<{kind} section view {self._target!r}>"


class _FrozenMapping(_SectionView, Mapping):
    """Recursively read-only mapping view of a parsed section."""

    __slots__ = ()
    _frozen = True

    def __getitem__(self, key):
        cur, last = _navigate(self._target, key)
        return self._wrap(cur[last])

    def __iter__(self):
        return iter(self._target)

    def __len__(self):
        return len(self._target)

    def __setitem__(self, key, value):
        raise TypeError(_FROZEN_WRITE_MSG)

    def __delitem__(self, key):
        raise TypeError(_FROZEN_DELETE_MSG)


class _FrozenSequence(_SectionView, Sequence):
    """Recursively read-only sequence view of a section list."""

    __slots__ = ()
    _frozen = True

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._wrap(self._target[key])
        cur, last = _navigate(self._target, key)
        return self._wrap(cur[last])

    def __len__(self):
        return len(self._target)

    def __setitem__(self, key, value):
        raise TypeError(_FROZEN_WRITE_MSG)

    def __delitem__(self, key):
        raise TypeError(_FROZEN_DELETE_MSG)


class _LiveMapping(_SectionView, MutableMapping):
    """Recursively mutable, write-through mapping view of a section.

    A write mutates the canonical section in place and invokes the
    shared ``_touch`` callback, which installs the section into the
    material's edit overlay (no-copy-on-write).
    """

    __slots__ = ()
    _frozen = False

    def __getitem__(self, key):
        cur, last = _navigate(self._target, key)
        return self._wrap(cur[last])

    def __setitem__(self, key, value):
        value = _own_value(value)
        cur, last = _navigate(self._target, key)
        cur[last] = value
        self._touch()

    def __delitem__(self, key):
        cur, last = _navigate(self._target, key)
        del cur[last]
        self._touch()

    def __iter__(self):
        return iter(self._target)

    def __len__(self):
        return len(self._target)


class _LiveSequence(_SectionView, MutableSequence):
    """Recursively mutable, write-through sequence view of a section list."""

    __slots__ = ()
    _frozen = False

    def __getitem__(self, key):
        if isinstance(key, slice):
            # a slice is a new list and cannot write through; return a
            # detached plain copy, mirroring ordinary list slicing,
            # rather than a live view that would silently drop edits
            return _plain(self._target[key])
        cur, last = _navigate(self._target, key)
        return self._wrap(cur[last])

    def __setitem__(self, key, value):
        value = _own_value(value)
        cur, last = _navigate(self._target, key)
        cur[last] = value
        self._touch()

    def __delitem__(self, key):
        cur, last = _navigate(self._target, key)
        del cur[last]
        self._touch()

    def __len__(self):
        return len(self._target)

    def insert(self, index, value):
        value = _own_value(value)
        self._target.insert(index, value)
        self._touch()
