############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2023/12/27
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2023-2024 International Atomic Energy Agency (IAEA)
#
############################################################

import re
import sys
from collections.abc import (
    Mapping,
    MutableMapping,
    Sequence,
    MutableSequence,
)
from ..interpreter.helpers import (
    list_setdefault,
    list_set,
)


def is_numpy_array(obj):
    """Check whether an object is a numpy array with at least one dimension.

    numpy is not imported for this check: if it has not been imported,
    there can be no numpy arrays.
    """
    numpy = sys.modules.get("numpy")
    return numpy is not None and isinstance(obj, numpy.ndarray) and obj.ndim > 0


def _is_array_like(obj):
    return (isinstance(obj, Sequence) and not isinstance(obj, str)) or is_numpy_array(
        obj
    )


def _check_resizable(obj, action):
    if is_numpy_array(obj):
        raise TypeError(
            f"cannot {action} a numpy array, as its size is fixed; "
            + "assign a new array to the enclosing element instead"
        )


_POSITION_TOKEN = re.compile(r"#([0-9]+)")
_OCCURRENCE_TOKEN = re.compile(r"([0-9]+)#([0-9]+)")


class _Position:
    """The section selector ``#k`` of an :class:`EndfPath`: the section at
    position ``k`` of a material (the tape head not counted)."""

    __slots__ = ("k",)

    def __init__(self, k):
        self.k = k

    def __str__(self):
        return f"#{self.k}"

    def __repr__(self):
        return f"_Position({self.k})"

    def __eq__(self, other):
        return isinstance(other, _Position) and other.k == self.k

    def __hash__(self):
        return hash(("#", self.k))


class _Occurrence:
    """The element ``MT#k`` of the section selector ``MF/MT#k`` of an
    :class:`EndfPath`: the ``k``-th section labelled MF/MT."""

    __slots__ = ("mt", "k")

    def __init__(self, mt, k):
        self.mt = mt
        self.k = k

    def __str__(self):
        return f"{self.mt}#{self.k}"

    def __repr__(self):
        return f"_Occurrence({self.mt}, {self.k})"

    def __eq__(self, other):
        return isinstance(other, _Occurrence) and (other.mt, other.k) == (
            self.mt,
            self.k,
        )

    def __hash__(self):
        return hash((self.mt, "#", self.k))


_SELECTOR_TOKENS = (_Position, _Occurrence)


def _parse_selector_token(token):
    m = _POSITION_TOKEN.fullmatch(token)
    if m:
        return _Position(int(m.group(1)))
    m = _OCCURRENCE_TOKEN.fullmatch(token)
    if m:
        return _Occurrence(int(m.group(1)), int(m.group(2)))
    raise ValueError(
        f"invalid section selector '{token}'; expected MF/MT, MF/MT#k or #k "
        "with non-negative integers"
    )


def _path_str(path_elements):
    return "/".join(str(x) for x in path_elements)


def _check_placement(path_elements):
    """Raise if a section selector token is not at the start of a path."""
    for i, el in enumerate(path_elements):
        if isinstance(el, _Position) and i != 0:
            raise ValueError(
                f"the section selector '{el}' must be the first element of "
                f"the path '{_path_str(path_elements)}'"
            )
        if isinstance(el, _Occurrence) and (
            i != 1 or not isinstance(path_elements[0], int)
        ):
            raise ValueError(
                f"the occurrence '{el}' must follow the MF at the start of the "
                f"path '{_path_str(path_elements)}'"
            )


def recursive_equality_check(obj1, obj2, ids):
    """Compare recursively two nested data structures.

    This function performs a comparison of two nested
    data structures that may contain basic datatypes
    (:class:`int`, :class:`float`, :class:`str`),
    objects that are subclasses of :class:`collections.abc.Sequence`
    (e.g. :class:`list` and :class:`tuple`),
    :class:`collections.abc.Mapping` (e.g. :class:`dict`)
    and numpy arrays, which are compared element by element
    with each other and with sequences.
    """
    if id(obj1) == id(obj2):
        return True
    elif is_numpy_array(obj1) or is_numpy_array(obj2):
        if not (_is_array_like(obj1) and _is_array_like(obj2)):
            return False
        if is_numpy_array(obj1) and is_numpy_array(obj2):
            return obj1.shape == obj2.shape and bool((obj1 == obj2).all())
        if len(obj1) != len(obj2):
            return False
        for x, y in zip(obj1, obj2):
            if not recursive_equality_check(x, y, ids):
                return False
    elif isinstance(obj1, Sequence) and isinstance(obj2, Sequence):
        if len(obj1) != len(obj2):
            return False
        if isinstance(obj1, str):
            return obj1 == obj2
        if id(obj1) in ids:
            raise IndexError("there is a cycle in the nested data structure")
        ids.add(id(obj1))
        for x, y in zip(obj1, obj2):
            if not recursive_equality_check(x, y, ids):
                return False
    elif isinstance(obj1, Mapping) and isinstance(obj2, Mapping):
        if len(obj1) != len(obj2):
            return False
        if len(set(obj1).intersection(obj2)) != len(obj1):
            return False
        if id(obj1) in ids:
            raise IndexError("there is a cycle in the nested data structure")
        ids.add(id(obj1))
        for k in obj1:
            if not recursive_equality_check(obj1[k], obj2[k], ids):
                return False
    else:
        return obj1 == obj2
    return True


class EndfPath(Sequence):
    """Class to store a reference to a location in a nested dictionary.

    An instance of this class maintains a reference that points to a specific
    location in a nested dictionary.
    It is assumed that all keys in the dictionaries are either of type
    :class:`str` or :class:`int` and that keys of type :class:`str` do not contain slashes.
    Under these assumptions, objects in a nested dictionary can be
    referenced by concatenating the keys referring to different levels in
    the nested hierarchy in a single string, with the individual keys
    separated by a slash. For example, the element
    ``b`` in the nested dictionary ``{'a': {1: {'b': 5}`` can be
    referenced by the string ``a/1/b``. Sometimes, it is a good
    mental model to think of dictionaries with integer keys as
    a kind of array, and it should therefore also be allowed to
    rewrite paths of the form ``a/1/b`` as ``a[1]/b``.

    Once this class is instantiated with a specific reference,
    the methods :func:`get` and :func:`set` can be used to
    retrieve and define, respectively, the object at the associated
    location of a given nested dictionary. The function
    :func:`exists` allows to test whether an object is present
    at the referenced location and finally the function
    :func:`remove` allows to remove a key rom the nested dictionary.

    This class is derived from :class:`collections.abc.Sequence` (like :class:`tuple`)
    with each element in the Sequence being a key associated with
    a specific level in the hierarchy of a nested dictionary.
    As for the :class:`tuple` datatype, references can be concatenated
    using the ``+`` operator and two references can be compared
    using the ``==`` operator; they are equal if they have the same
    keys, so a path is not equal to its prefixes. References are
    hashable and can be used in sets and as dictionary keys.
    Also iterating over the individual keys within a reference works,
    which are returned as :class:`EndfPath` instances.

    **Sections of a material.** Applied to a material, the first
    elements of a path select a section, in one of three ways:

    - ``MF/MT``, e.g. ``3/102``: the section with this label, which must
      be unique in the material;
    - ``MF/MT#k``, e.g. ``3/102#2``: the ``k``-th section with this label,
      for a label that occurs several times (as the tape structure of
      ``gendf`` allows);
    - ``#k``, e.g. ``#0``: the section at position ``k`` of the material.

    ``k`` counts from 0, and the positions do not count the tape head
    (MF0/MT0), which is selected by its label ``0/0``. On a material in
    the list form as returned by ``parse``, whose element 0 is the tape
    head, ``#k`` is therefore the list element ``material[k + 1]``. The
    rest of the path, e.g. ``3/102#2/IZAM``, addresses data within the
    section as before.

    A list is taken as a material in the list form if its first element
    is a section: a mapping with the keys ``MF`` and ``MT``, or a list of
    strings (an unparsed section). On such a list, a path must begin with
    a section selector, ``MF/MT`` included; an ``MF`` alone does not
    select a section. A mapping (the nested form ``{MF: {MT: section}}``)
    is walked by its keys as before; ``MF/MT#k`` and ``#k`` work on it
    as well, with the position in the canonical order (ascending MF,
    then MT). Other lists, e.g. arrays in the ``array_type="list"`` mode,
    are walked as before. The functions of :mod:`endf_parserpy.utils.sections`
    (e.g. :func:`~endf_parserpy.get_section`) do the same without a path.
    """

    # set by the constructor; paths created otherwise have no selector
    _has_tokens = False

    def __init__(self, pathspec="", array_type="dict", leading="dict"):
        """The EndfPath constructor accepts the following parameters.

        Parameters
        ----------
        pathspec : Union[int, str, tuple]
            This argument can be provided in several forms.
            It can be a single key represented by a variable of
            type ``int`` or ``str``.
            It can be a composite key given in a string with
            individual keys separated by a slash, e.g. ``a/b/1``
            or equivalently ``a/b[1]``. This argument can
            also be a tuple containing the indvidual keys,
            e.g. ``('a', 'b', 1)``.
        array_type : str
            Must be either ``"dict"`` or ``"list"`` and determines
            if arrays should be assumed to be represented as
            :class:`dict` (default) or :class:`list`.
        leading : str
            Must be either ``"dict"`` or ``"list"``.
            Arrays with leading consecutive integer path will be
            represented according to this argument choice,
            e.g. for ``(1, 2, a, 3)`` and ``leading="dict"``,
            the first two levels will be of type :class:`dict`.

        Examples
        --------
        >>> p1 = EndfPath('a/1/2/c')
        >>> p2 = EndfPath('a[1]/2/c')
        >>> p3 = EndfPath(('a', '1', '2', 'c'))
        >>> p4 = EndfPath(('a', 1, '2', 'c'))
        >>> p5 = EndfPath('a[1,2]/c')
        >>> p6 = EndfPath('a[1]') + EndfPath('2/c')
        >>> assert p1 == p2 and p2 == p3 and p3 == p4
        >>> assert p4 == p5 and p5 == p6
        """
        if isinstance(pathspec, EndfPath):
            self._path_elements = pathspec._path_elements
            self._has_tokens = pathspec._has_tokens
            self.array_type = pathspec.array_type
            self.leading = pathspec.leading
            return
        self._set_elements(pathspec)
        if self._has_tokens:
            _check_placement(self._path_elements)
        self.array_type = array_type
        self.leading = leading

    def _set_elements(self, pathspec):
        if isinstance(pathspec, int):
            pathspec = str(pathspec)
        if isinstance(pathspec, str):
            pathspec = pathspec.split("/")
        if not isinstance(pathspec, Sequence):
            raise TypeError("expected pathspec to be sequence or string")
        self._path_elements = self._standardize_path_tuple(pathspec)

    @classmethod
    def _unchecked(cls, pathspec):
        """An :class:`EndfPath` whose selector tokens may be anywhere; for
        the pieces of a path, e.g. in ``+``, whose placement is checked
        on the whole path."""
        if isinstance(pathspec, EndfPath):
            return pathspec
        new = cls.__new__(cls)
        new._set_elements(pathspec)
        new.array_type = "dict"
        new.leading = "dict"
        return new

    @classmethod
    def _from_elements(cls, path_elements):
        new = cls.__new__(cls)
        new._path_elements = tuple(path_elements)
        new._has_tokens = any(isinstance(x, _SELECTOR_TOKENS) for x in path_elements)
        new.array_type = "dict"
        new.leading = "dict"
        return new

    def _standardize_path_tuple(self, path_tuple):
        p = path_tuple
        p = (str(x) for x in p)
        p = (x.strip() for x in p)
        p = (x for x in p if x != "")
        res = tuple()
        has_tokens = False
        for t in p:
            if "#" in t:
                # a section selector (#k, or MT#k of MF/MT#k), recognised
                # before the array notation, which it must not contain
                res = res + (_parse_selector_token(t),)
                has_tokens = True
            else:
                res = res + self._expand_array_notation(t)
        if has_tokens:
            res = tuple(
                int(x) if isinstance(x, str) and x.isdigit() else x for x in res
            )
        else:
            res = tuple(int(x) if x.isdigit() else x for x in res)
        self._validate_path(res)
        self._has_tokens = has_tokens
        return res

    def _expand_array_notation(self, extvarname):
        t = extvarname
        if "[" not in t:
            return (extvarname,)
        if not t.endswith("]"):
            raise ValueError(f"invalid path element `{t}`")
        idx = t.index("[")
        varname = t[:idx]
        indices = t[idx + 1 : -1].split(",")
        indices = tuple(s.strip() for s in indices)
        return (varname,) + indices

    def _validate_path(self, path_elements):
        for el in path_elements:
            if not isinstance(el, (int, _Position, _Occurrence)):
                if (
                    not el.replace("_", "").isalnum() or el[0].isdigit()
                ) and not el == "*":
                    raise ValueError(f"invalid path element `{el}`")

    def __eq__(self, other):
        # the location only: array_type and leading, which choose the
        # containers that set creates, do not take part
        if isinstance(other, EndfPath):
            return self._path_elements == other._path_elements
        return False

    def __hash__(self):
        return hash(self._path_elements)

    def __str__(self):
        return "/".join([str(x) for x in self._path_elements])

    def __repr__(self):
        return f"EndfPath('{str(self)}')"

    def __getitem__(self, key):
        elements = self._path_elements[key]
        if not isinstance(key, slice):
            elements = (elements,)
        # the elements are standardized already; a slice may cut off the
        # MF before an occurrence, which is reported when it is applied
        return EndfPath._from_elements(elements)

    def __len__(self, *args, **kwargs):
        return len(self._path_elements)

    def __add__(self, other):
        if not isinstance(other, EndfPath):
            other = EndfPath._unchecked(other)
        # The path elements of both are already standardized, and
        # standardizing their concatenation would leave it unchanged.
        new_endfpath = EndfPath.__new__(EndfPath)
        new_endfpath._path_elements = self._path_elements + other._path_elements
        new_endfpath._has_tokens = self._has_tokens or other._has_tokens
        if new_endfpath._has_tokens:
            _check_placement(new_endfpath._path_elements)
        new_endfpath.array_type = self.array_type
        new_endfpath.leading = self.leading
        return new_endfpath

    def __radd__(self, other):
        other = EndfPath._unchecked(other)
        return other.__add__(self)

    def __int__(self):
        if len(self._path_elements) != 1:
            raise TypeError("Can only convert an EndfPath of length one to `int`")
        return int(self._path_elements[0])

    def get(self, dict_like):
        """Retrieve object from nested dictionary.

        Parameters
        ----------
        dict_like : dict
            The (nested) dictionary from which an object
            should be retrieved.

        Returns
        -------
        object
            The object at the location referred to by this :class:`EndfPath` instance.

        Example
        -------
        >>> testdict = {'a': 1: {'b': 5}}
        >>> p = EndfPath('a/1/b')
        >>> assert p.get(testdict) == 5
        """
        if self._has_tokens or isinstance(dict_like, (list, EndfList)):
            entered = self._enter(dict_like)
            if entered is not None:
                material, mf, mt, occurrence, position, rest = entered
                cur = _sections().get_section(
                    material, mf, mt, occurrence, position=position
                )
                for el in rest:
                    cur = cur[el]
                return cur
        cur = dict_like
        for el in self._path_elements:
            cur = cur[el]
        return cur

    def _enter(self, root):
        """Resolve the section selector at the start of the path.

        Returns ``None`` if the path is to be walked key by key (the root
        is no material in the list form, and the path has no selector
        token), else ``(material, mf, mt, occurrence, position, rest)``
        with ``rest`` the elements of the path within the section.
        """
        sections = _sections()
        if isinstance(root, EndfObject):
            root = root.unwrap()
        els = self._path_elements
        if self._has_tokens:
            _check_placement(els)
        if sections.is_section_list(root):
            in_list = True
        elif self._has_tokens:
            if not (
                isinstance(root, Mapping) and all(isinstance(k, int) for k in root)
            ):
                raise ValueError(
                    f"the path '{self}' starts with a section selector, but the "
                    "object is not a material (a list of sections or a dict "
                    "{MF: {MT: section}})"
                )
            in_list = False
        else:
            return None
        if not els:
            return None
        first = els[0]
        if isinstance(first, _Position):
            return root, None, None, None, first.k, els[1:]
        second = els[1] if len(els) > 1 else None
        if isinstance(first, int):
            if isinstance(second, _Occurrence):
                return root, first, second.mt, second.k, None, els[2:]
            if in_list:
                if second is None:
                    raise ValueError(
                        f"the path '{self}' stops at MF={first}, which addresses "
                        "no section of a material in the list form; use MF/MT, "
                        "MF/MT#k or #k"
                    )
                if isinstance(second, int):
                    return root, first, second, None, None, els[2:]
        if in_list and "*" in els[:2]:
            raise ValueError(
                f"the wildcard '*' in the section selector of '{self}' is not "
                "supported for a material in the list form"
            )
        raise ValueError(
            f"the path '{self}' does not address a section of a material in the "
            "list form; a path on such a material starts with MF/MT, MF/MT#k or #k"
        )

    def set(self, dict_like, value):
        """Insert an object into a nested dictionary at the :class:`EndfPath` location.

        Parameters
        ----------
        dict_like : dict
            The (nested) dictionary to be extended/altered.
        value : Object
            The object that should be inserted at the location
            referenced by this :class:`EndfPath` instance.

        Note
        ----
        Intermediate dictionaries will be created if missing.
        If an intermediate key exists that does not refer to
        a :class:`dict` (or other datatype derived from :class:`collections.abc.MutableMapping`),
        this method will fail.

        Example
        -------
        >>> testdict = {}
        >>> p = EndfPath('a/b/c')
        >>> p.set(testdict, 12)
        >>> print(testdict)
        """
        if isinstance(value, EndfObject):
            value = value.unwrap()
        if self._has_tokens or isinstance(dict_like, (list, EndfList)):
            entered = self._enter(dict_like)
            if entered is not None:
                material, mf, mt, occurrence, position, rest = entered
                if not rest:
                    self._set_section(material, mf, mt, occurrence, position, value)
                    return
                # a field: the section must exist; none is created
                section = _sections().get_section(
                    material, mf, mt, occurrence, position=position
                )
                self._set_in(section, rest, value)
                return
        self._set_in(dict_like, self._path_elements, value)

    def _set_section(self, material, mf, mt, occurrence, position, section):
        sections = _sections()
        if position is not None:
            sections.set_section(material, section, position=position)
            return
        if isinstance(section, MutableMapping):
            section.setdefault("MF", mf)
            section.setdefault("MT", mt)
        label = sections._label(section)
        if label != (mf, mt):
            raise ValueError(
                f"the section has MF={label[0]}/MT={label[1]}, but the path "
                f"'{self}' addresses MF={mf}/MT={mt}"
            )
        sections.set_section(material, section, occurrence)

    def _set_in(self, dict_like, pathels, value):
        cur = dict_like
        in_leading = True
        num_pathels = len(pathels)
        dict_mode = self.array_type == "dict"
        for i, el in enumerate(pathels):
            is_el_int = isinstance(el, int)
            in_leading &= is_el_int
            if dict_mode or (in_leading and self.leading == "dict"):
                if i + 1 < num_pathels:
                    cur = cur.setdefault(el, {})
                else:
                    cur[el] = value
            else:
                if is_el_int and el == len(cur):
                    _check_resizable(cur, "append an element to")
                if i + 1 < num_pathels:
                    is_next_el_int = isinstance(pathels[i + 1], int)
                    new_cont = [] if is_next_el_int and not dict_mode else {}
                    if is_el_int:
                        cur = list_setdefault(cur, el, new_cont)
                    else:
                        cur = cur.setdefault(el, new_cont)
                else:
                    if is_el_int:
                        list_set(cur, el, value)
                    else:
                        cur[el] = value

    def exists(self, dict_like):
        """Test whether a key exists at the :class:`EndfPath` location.

        Parameters
        ----------
        dict_like : dict
            The (nested) dictionary for which the existence
            of a key at the :class:`EndfPath` location should be checked.

        Returns
        -------
        bool
            ``True`` if key exists at :class:`EndfPath` location,
            otherwise ``False``.

        Example
        -------
        >>> testdict = {'a': {1: 10}}
        >>> p = EndfPath('a/1')
        >>> p.exists(testdict)
        """
        try:
            self.get(dict_like)
        except (KeyError, IndexError):
            return False
        except TypeError:
            return False
        return True

    def remove(self, dict_like):
        """Remove key from nested dictionary at :class:`EndfPath` location.

        Parameters
        ----------
        dict_like : dict
            The (nested) dictionary from which the key
            at the :class:`EndfPath` location should be removed.

        Example
        -------
        >>> testdict = {'a': {1: 10}}
        >>> p = EndfPath('a/1')
        >>> p.remove(testdict)
        """
        pathels = self._path_elements
        cur = dict_like
        if self._has_tokens or isinstance(dict_like, (list, EndfList)):
            entered = self._enter(dict_like)
            if entered is not None:
                material, mf, mt, occurrence, position, rest = entered
                if not rest:
                    _sections().remove_section(
                        material, mf, mt, occurrence, position=position
                    )
                    return
                cur = _sections().get_section(
                    material, mf, mt, occurrence, position=position
                )
                pathels = rest
        for el in pathels[:-1]:
            cur = cur[el]
        _check_resizable(cur, "remove an element from")
        del cur[pathels[-1]]


def _sections():
    # imported on first use: the module imports from this one
    from . import sections

    return sections


class EndfVariable:
    """Class to keep a reference to a location in a (nested) dictionary.

    An instance of this class is connected to a specific key
    in a (nested) dictionary and its associated object.
    The instance attribute :attr:`value` allows to set or retrieve
    the object linked to the specific key in the dictionary.
    The purpose of this class is to provide a mechanism to
    pass around objects that can be treated like variables
    but are always in sync with the data in a given dictionary.
    """

    def __init__(self, endf_path, endf_dict, value=None):
        """Create and associate :class:`EndfVariable` with location in dictionary.

        Parameters
        ----------
        endf_path : EndfPath
            An :class:`EndfPath` instance (or an object that is accepted
            by the :class:`EndfPath` constructor) establishing the link
            to a specific location in a nested :class:`dict`-like object.
        endf_dict : dict
            A (nested) :class:`dict`-like object that contains a key
            referenced by the ``endf_path`` argument.
        """
        if isinstance(endf_dict, EndfDict):
            endf_dict = endf_dict.unwrap()
        if not isinstance(endf_path, EndfPath):
            endf_path = EndfPath(endf_path)
        els = endf_path._path_elements
        selector_len = 1 if els and isinstance(els[0], _Position) else 2
        if len(els) <= selector_len and (
            endf_path._has_tokens or _sections().is_section_list(endf_dict)
        ):
            raise ValueError(
                "EndfVariable needs a field path in a material in the list form "
                f"or with a section selector, not the section path '{endf_path}'"
            )
        if not endf_path.exists(endf_dict):
            if value is None:
                raise KeyError(f"variable `{endf_path}` does not exist")
            endf_path.set(endf_dict, value)

        self._endf_dict = endf_dict
        self._path = endf_path
        self._varname = endf_path[-1]
        self._parent = endf_path[:-1].get(endf_dict)

    def __repr__(self):
        return (
            f"EndfVariable({self._path!r}, "
            + f"{type(self._endf_dict)} at {hex(id(self._endf_dict))}, "
            + f"value={self.value})"
        )

    def __call__(self):
        return self.value

    @property
    def name(self):
        """Name of the associated key in the nested dictionary.

        Example
        -------
        >>> v = EndfVariable('a/b', {'a': {'b': 5}})
        >>> assert v.name == 'b'
        """
        return self._varname

    @property
    def value(self):
        """Value of the associated key in the nested dictionary.

        The value of this propert can also be modified, which
        accordingly modifies the value stored under the associated
        key in the nested :class:`dict`-like object.

        Example
        -------
        >>> d = {'a': {'b': 5}}
        >>> v = EndfVariable('a/b', d)
        >>> assert v.value == d['a']['b']
        >>> v.value = 10
        >>> assert d['a']['b'] == 10
        """
        return self._varname.get(self._parent)

    @value.setter
    def value(self, value):
        self._varname.set(self._parent, value)

    @property
    def path(self):
        """Path of associated key in nested dictionary.

        Example
        -------
        >>> d = {'a': {'b': 5}}
        >>> v = EndfVariable('a/b', d)
        >>> assert v.path == EndfPath('a/b')
        """
        return self._path

    @property
    def endf_dict(self):
        return self._endf_dict

    @property
    def parent_dict(self):
        return self._parent


class EndfObject:
    """Class for enhanced access to nested data structures.

    This class facilitates the interaction with
    nested data structures composed of :class:`dict`- and
    :class:`list`-like objects as well as primitive data types
    (:class:`str`, :class:`int`, and :class:`float`).
    More precisely, the retrieval of objects from the nested
    structure and the insertion and modification
    of objects can be performed by making use of
    references as enabled by the
    :class:`EndfPath` class. Therefore access to
    elements is possible with syntax, such as
    ``d['a/b/1/c']`` and ``d['a/b[1]/c']``.
    Apart from the enhanced capabilities to refer to objects
    in a nested data structure, this class behaves
    almost in the same way as a normal Python :class:`dict`
    or :class:`list` (depending on constructor argument ``obj``).
    The exception is that whenever an object
    is retrieved that is :class:`dict`- or :class:`list`-like,
    it will be converted on-the-fly to an :class:`EndfDict`
    or :class:`EndfList`, respectively,
    and returned in that form to the user. Also,
    :class:`EndfDict` and :class:`EndfList` instances to be associated
    with a key are converted to the underlying base object
    before being stored (see :func:`unwrap` method).
    """

    def __init__(self, obj, array_type, leading):
        """The constructor takes two arguments.

        Parameters
        ----------
        obj : Union[None, dict, list]
            The :class:`dict`- or :class:`list`-like object for
            which enhanced access is desired.
        array_type : str
            Either ``"dict"`` or ``"list"``. With the former choice,
            if an array needs to be created, it will be represented
            as :class:`dict`. With the latter choice, it will be
            represented by a :class:`list`.

        Example
        -------
        >>> testdict = {'a': 1, 'b': {1: 'u', 2: 'v'}}
        >>> viewdict = EndfDict(testdict)
        >>> viewdict['b/1'] = 'w'
        >>> assert testdict['b'][1] == 'w'
        >>> assert viewdict['b/1'] == testdict['b'][1]
        >>> viewdict[2, 3] = 7
        >>> assert viewdict['2/3'] == 7
        """
        if isinstance(obj, (MutableMapping, MutableSequence)):
            if isinstance(obj, EndfObject):
                obj = obj.unwrap()
            self._store = obj
        else:
            raise TypeError("expected `obj` to be an instance of MutableMapping")
        self._root = self
        self._path = EndfPath("")
        self._array_type = array_type
        self._leading = leading

    def __repr__(self):
        return f"{self._store!r}"

    def __str__(self):
        return str(self._store)

    def __eq__(self, other):
        obj1 = self._store
        obj2 = other
        ret = recursive_equality_check(obj1, obj2, set())
        return ret

    def _positional(self, key):
        """Whether ``key`` is a Python int that indexes a material in the
        list form positionally (the tape head counted), as a list does."""
        return (
            isinstance(key, int)
            and isinstance(self, EndfList)
            and _sections().is_section_list(self._store)
        )

    def __getitem__(self, key):
        if self._positional(key):
            ret = self._store[key]
            index = key if key >= 0 else key + len(self._store)
            endf_path = EndfPath._from_elements((index,))
        else:
            if isinstance(key, (str, int)):
                endf_path = EndfPath(key, self._array_type, self._leading)
            elif isinstance(key, Sequence):
                endf_path = EndfPath("", self._array_type, self._leading)
                for p in key:
                    endf_path += p
            else:
                raise ValueError("unsupported key data type")
            ret = endf_path.get(self._store)

        if isinstance(ret, MutableMapping) and not isinstance(ret, EndfDict):
            ret = EndfDict(ret, self._array_type)
            ret._root = self._root
            ret._path = endf_path
        elif isinstance(ret, MutableSequence) and not isinstance(ret, EndfList):
            ret = EndfList(ret, self._array_type)
            ret._root = self._root
            ret._path = endf_path

        return ret

    def __setitem__(self, key, value):
        if isinstance(value, EndfObject):
            value = value.unwrap()
        if self._positional(key):
            self._store[key] = value
            return
        if isinstance(key, (str, int)):
            endf_path = EndfPath(key, self._array_type, self._leading)
        elif isinstance(key, Sequence):
            endf_path = EndfPath("", self._array_type, self._leading)
            for p in key:
                endf_path += p
        else:
            raise ValueError("unsupported key data type")
        endf_path.set(self._store, value)

    def __delitem__(self, key):
        if self._positional(key):
            del self._store[key]
            return
        if not isinstance(key, EndfPath):
            endf_path = EndfPath(key, self._array_type, self._leading)
        endf_path.remove(self._store)

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def exists(self, path):
        """Check whether object exists under path.

        Parameters
        ----------
        path : EndfPath
            An :class:`EndfPath` or object that is accepted
            by its constructor.
        """
        path = EndfPath(path, self._array_type, self._leading)
        return path.exists(self._store)

    def _recursive_unwrap(self, element):
        if isinstance(element, MutableMapping):
            if isinstance(element, EndfDict):
                element = element.unwrap()
            for curkey in element:
                element[curkey] = self._recursive_unwrap(element[curkey])
        if isinstance(element, MutableSequence):
            if isinstance(element, EndfList):
                element = element.unwrap()
            for curidx in range(len(element)):
                element[curidx] = self._recursive_unwrap(element[curidx])
        return element

    def unwrap(self, recursive=False):
        """Returns the underlying base object.

        The :class:`EndfObject` class can be regarded as an interface wrapping
        around an underlying :class:`dict`- or :class:`list`-like object.
        This function permits the retrieval of the underlying object.

        Parameters
        ----------
        recursive : bool
            If ``True``, all :class:`EndfObject` objects present in the
            underlying object are recursively converted to their base type,
            i.e. either :class:`dict` or :class:`list`.

        Returns
        -------
        Union[dict, list]
            The underlying base object.

        Note
        ----
        The use of ``recursive=True`` is only necessary if the
        user has stored an :class:`EndfObject` object anywhere in the
        underlying base object. In contrast, if an attempt
        is made to store an :class:`EndfObject` object in another
        :class:`EndfObject` object, the former object is (non-recursively)
        unwrapped (with :func:`unwrap`) before being stored. Therefore,
        as long as the underlying base object is only
        accessed via an :class:`EndfDict` instance, there should never be
        an :class:`EndfObject` object in the underlying base object.

        Example
        -------
        >>> testdict = {'a': 1, 'b': 2}
        >>> viewdict = EndfDict(testdict)
        >>> assert id(testdict) != id(viewdict)
        >>> retdict = viewdict.unwrap()
        >>> assert id(testdict) == id(retdict)
        """
        if recursive:
            self._store = self._recursive_unwrap(self._store)
        return self._store

    @property
    def root(self):
        """Get the :class:`EndfDict` instance associated with the root dictionary.

        Any :class:`dict`-like object retrieved from an :class:`EndfDict`
        (termed the root ``EndfDict``) is automatically enwrapped in
        an :class:`EndfDict` instances before being returned to the user.
        The ``root`` attribute of the returned :class:`EndfDict` instances
        holds a reference to the root :class:`EndfDict` object.

        Example
        -------
        >>> testdict = {'a': {'b': {'c': 'd'}}}
        >>> viewdict = EndfDict(testdict)
        >>> assert id(viewdict) == id(viewdict.root)
        >>> viewdict2 = testdict['a/b']
        >>> assert id(viewdict2.root) == id(viewdict)
        """
        return self._root

    @property
    def path(self):
        """Get the :class:`EndfPath` associated with this :class:`EndfDict`.

        If this :class:`EndfDict` was retrieved from another :class:`EndfDict`,
        the ``path`` attribute contains the location relative to that
        :class:`EndfDict`, i.e. the key or path used to retrieve it.

        Example
        -------
        >>> testdict = {'a': {'b': {'c': 5}}}
        >>> viewdict = EndfDict(testdict)
        >>> viewdict2 = viewdict['a/b']
        >>> assert viewdict2.path == EndfPath('a/b')
        >>> assert viewdict['a']['b'].path == EndfPath('b')
        """
        return self._path


class EndfDict(EndfObject, MutableMapping):
    """EndfDict class extends :class:`dict` with :class:`EndfPath` functionality.

    The :class:`EndfDict` class behaves like a :class:`dict`
    but offers in addition enhanced indexing capabilities.
    This class is derived from the :class:`EndfObject` class
    and inherits its methods.
    """

    def __init__(self, obj=None, array_type="dict"):
        """Constructor for the :class:`EndfDict` class.

        Parameters
        ----------
        obj : Optional[dict]
            If ``obj`` is provided, the instantiated
            :class:`EndfDict` class provides a view object.
            Otherwise, the created instance will be initialized
            with an empty dictionary.
        array_type: str
            Can be ``"dict"`` or ``"list"`` and indicates
            the datatype to use for representing arrays.
        """
        if obj is None:
            obj = dict()
        elif not isinstance(obj, MutableMapping):
            raise TypeError("Expected a dict-like object")
        EndfObject.__init__(self, obj, array_type, "dict")

    def keys(self):
        return self._store.keys()

    def values(self):
        return self._store.values()

    def items(self):
        return self._store.items()


class EndfList(EndfObject, MutableSequence):
    """EndfList class extends :class:`list` with :class:`EndfPath` functionality.

    The :class:`EndfDict` class behaves like a :class:`list`
    but offers enhanced indexing capabilities.
    This class is derived from the :class:`EndfObject` class
    and inherits its methods.
    """

    def __init__(self, obj, array_type="list"):
        """Constructor for the :class:`EndfList` class.

        Parameters
        ----------
        obj : Optional[list]
            If ``obj`` is provided, the instantiated
            :class:`EndfDict` class provides a view object.
            Otherwise, the created instance will be initialized
            with an empty list.
        array_type: str
            Can be ``"dict"`` or ``"list"`` and indicates
            the datatype to use for representing arrays.
        """
        if obj is None:
            obj = list()
        elif not isinstance(obj, MutableSequence):
            raise TypeError("Expected a list-like object")
        EndfObject.__init__(self, obj, array_type, "list")

    def insert(self, idx, value):
        if isinstance(value, EndfObject):
            value = value.unwrap()
        self._store.insert(idx, value)
