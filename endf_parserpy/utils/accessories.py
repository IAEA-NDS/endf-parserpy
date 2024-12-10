############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2023/12/27
# Last modified:   2024/12/10
# License:         MIT
# Copyright (c) 2023-2024 International Atomic Energy Agency (IAEA)
#
############################################################

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


def recursive_equality_check(obj1, obj2, ids):
    """Compare recursively two nested data structures.

    This function performs a comparison of two nested
    data structures that may contain basic datatypes
    (:class:`int`, :class:`float`, :class:`str`),
    objects that are subclasses of :class:`collections.abc.Sequence`
    (e.g. :class:`list` and :class:`tuple`)
    and :class:`collections.abc.Mapping` (e.g. :class:`dict`).
    """
    if id(obj1) == id(obj2):
        return True
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
    using the ``==`` operator. Also iterating over the individual
    keys within a reference works, which are returned as
    :class:`EndfPath` instances.
    """

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
        >>> p6 = EndfPath('a[1]']) + EndfPath('2/c')
        >>> assert p1 == p2 and p2 == p3 and p3 == p4
        >>> assert p4 == p5 and p5 == p6
        """
        if isinstance(pathspec, EndfPath):
            self._path_elements = pathspec._path_elements
            self.array_type = pathspec.array_type
            self.leading = pathspec.leading
            return
        if isinstance(pathspec, int):
            pathspec = str(pathspec)
        if isinstance(pathspec, str):
            pathspec = pathspec.split("/")
        if not isinstance(pathspec, Sequence):
            raise TypeError("expected pathspec to be sequence or string")
        self._path_elements = self._standardize_path_tuple(pathspec)
        self.array_type = array_type
        self.leading = leading

    def _standardize_path_tuple(self, path_tuple):
        p = path_tuple
        p = (str(x) for x in p)
        p = (x.strip() for x in p)
        p = (x for x in p if x != "")
        res = tuple()
        for t in p:
            res = res + self._expand_array_notation(t)
        res = tuple(int(x) if x.isdigit() else x for x in res)
        self._validate_path(res)
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
            if not isinstance(el, int):
                if (
                    not el.replace("_", "").isalnum() or el[0].isdigit()
                ) and not el == "*":
                    raise ValueError(f"invalid path element `{el}`")

    def __eq__(self, other):
        if isinstance(other, EndfPath):
            p1 = self._path_elements
            p2 = other._path_elements
            return all(x == y for x, y in zip(p1, p2))
        return False

    def __str__(self):
        return "/".join([str(x) for x in self._path_elements])

    def __repr__(self):
        return f"EndfPath('{str(self)}')"

    def __getitem__(self, key):
        return EndfPath(self._path_elements[key])

    def __len__(self, *args, **kwargs):
        return len(self._path_elements)

    def __add__(self, other):
        if not isinstance(other, EndfPath):
            other = EndfPath(other)
        new_endfpath = EndfPath(
            self._path_elements + other._path_elements, self.array_type, self.leading
        )
        return new_endfpath

    def __radd__(self, other):
        other = EndfPath(other)
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
        cur = dict_like
        for el in self._path_elements:
            cur = cur[el]
        return cur

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
        cur = dict_like
        in_leading = True
        pathels = self._path_elements
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
        cur = dict_like
        for el in self._path_elements[:-1]:
            cur = cur[el]
        del cur[self._path_elements[-1]]


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

    def __getitem__(self, key):
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
        the ``path`` attribute contains the associated location in
        the nested dictionary.

        Example
        -------
        >>> testdict = {'a': {'b': 'c'}}
        >>> viewdict = EndfDict(testdict)
        >>> viewdict2 = viewdict['a/b']
        >>> assert viewdict2.path == EndfPath('a/b')
        """
        return self._path


class EndfDict(EndfObject, MutableMapping):
    """EndfDict class extends :class:`dict` with :class:`EndfPath` functionality.

    The :class:`EndfDict` class behaves like a :class:`list`
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
