############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/09
# Last modified:   2025/06/02
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import MutableMapping, MutableSequence
from endf_parserpy.utils.math_utils import math_allclose
from endf_parserpy.utils.accessories import EndfDict
from .math_utils import EndfFloat


def smart_is_equal(x, y, atol=1e-8, rtol=1e-6):
    if type(x) != type(y):
        return False
    elif isinstance(x, float):
        return math_allclose(x, y, atol=atol, rtol=rtol)
    elif isinstance(x, int):
        return x == y
    else:
        return x == y


def compare_objects(
    obj1,
    obj2,
    atol=1e-8,
    rtol=1e-6,
    strlen_only=False,
    do_rstrip=False,
    rstrcut=None,
    fail_on_diff=True,
    diff_log=None,
):
    """Compare recursively two objects.

    This function enables the recursive comparison of two objects
    possible being or containing objects of type :class:`dict` or
    iterable array-like objects. For example, this class can be
    used to confirm or reject the equality of two nested dictionaries
    resulting from the parsing of ENDF-6 files via the
    :func:`~endf_parserpy.EndfParserPy.parsefile`
    method of the :class:`~endf_parserpy.EndfParserPy` class.
    The function can print out meaningful information where the
    discrepancies are present in the objects with a nested structure.

    Parameters
    ----------
    obj1 : object
        Any kind of object but usually it will be a nested :class:`dict`-like structure.
    obj2 : object
        Any kind of object but usually it will be a nested :class:`dict`-like structure.
    atol : float
        The absolute tolerance for the comparison of two :class:`float` variables.
    rtol : float
        The relative tolerance for the comparison of two :class:`float` variables.
    strlen_only : bool
        If ``True``, only compare the lengths of strings, otherwise also
        the content of the strings is considered in the comparison.
    do_rstrip : bool
        If ``True``, strip whitespace
        characters at the end of the strings before comparison.
    rstrcut : Union[None, int]
        If an integer is provided, only retain the first ``rstrcut`` characters
        of the strings in the comparison. If ``None``, strings are compared
        as they are.
    fail_on_diff : bool
        If ``True``, this function will raise an exception at the first encounter
        of a difference. Otherwise, the function will fully compare the objects
        and return ``True`` if the two objects are equal and ``False`` if they
        exhibit differences. The second option is mostly useful in combination
        with ``diff_log=True``.
    diff_log : Union[None, List]
        A :class:`list` object can be passed which will be filled with
        strings that indicate the differences found.
        This option is only useful in combination with ``fail_on_diff=false``.
    """
    if isinstance(obj1, EndfDict):
        obj1 = obj1.unwrap()
    if isinstance(obj2, EndfDict):
        obj2 = obj2.unwrap()
    return _compare_objects(
        obj1,
        obj2,
        curpath="",
        atol=atol,
        rtol=rtol,
        strlen_only=strlen_only,
        do_rstrip=do_rstrip,
        rstrcut=rstrcut,
        fail_on_diff=fail_on_diff,
        diff_log=diff_log,
    )


def _compare_objects(
    obj1,
    obj2,
    curpath="",
    atol=1e-8,
    rtol=1e-6,
    strlen_only=False,
    do_rstrip=False,
    rstrcut=None,
    fail_on_diff=True,
    diff_log=None,
):
    if diff_log is None:
        diff_log = []

    found_diff = False

    def treat_diff(msg, exc):
        nonlocal found_diff
        found_diff = True
        if fail_on_diff:
            raise exc(msg)
        else:
            diff_log.append(msg)
            print(msg)

    if isinstance(obj1, EndfFloat):
        obj1 = float(obj1)
    if isinstance(obj2, EndfFloat):
        obj2 = float(obj2)

    if type(obj1) != type(obj2):
        treat_diff(
            f"at path {curpath}: " + f"type mismatch found, obj1: {obj1}, obj2: {obj2}",
            TypeError,
        )

    elif isinstance(obj1, dict):
        only_in_obj1 = set(obj1).difference(obj2)
        if len(only_in_obj1) > 0:
            treat_diff(
                f"at path {curpath}: only obj1 contains {only_in_obj1}", IndexError
            )

        only_in_obj2 = set(obj2).difference(obj1)
        if len(only_in_obj2) > 0:
            treat_diff(
                f"at path {curpath}: only obj2 contains {only_in_obj2}", IndexError
            )

        common_keys = set(obj1).intersection(set(obj2))
        common_int_keys = [k for k in common_keys if isinstance(k, int)]
        common_nonint_keys = [k for k in common_keys if not isinstance(k, int)]
        common_int_keys.sort()
        common_nonint_keys.sort()
        common_keys = common_nonint_keys + common_int_keys

        for key in common_keys:
            ret = _compare_objects(
                obj1[key],
                obj2[key],
                "/".join((curpath, str(key))),
                atol=atol,
                rtol=rtol,
                strlen_only=strlen_only,
                do_rstrip=do_rstrip,
                rstrcut=rstrcut,
                fail_on_diff=fail_on_diff,
                diff_log=diff_log,
            )
            found_diff = found_diff or not ret
    else:
        if isinstance(obj1, str):
            if do_rstrip:
                obj1 = obj1.rstrip()
                obj2 = obj2.rstrip()
            if rstrcut is not None:
                obj1 = obj1[:rstrcut]
                obj2 = obj2[:rstrcut]
            if strlen_only:
                if len(obj1) != len(obj2):
                    treat_diff(
                        f"at path {curpath}: string lengths differ "
                        f"({obj1} != {obj2})",
                        ValueError,
                    )
            elif obj1 != obj2:
                treat_diff(
                    f"at path {curpath}: strings differ " f"({obj1} != {obj2})",
                    ValueError,
                )

        elif hasattr(obj1, "__iter__"):
            len_obj1 = len(tuple(obj1))
            len_obj2 = len(tuple(obj2))
            if len_obj1 != len_obj2:
                treat_diff(
                    f"Length mismatch at {curpath} " f"({len_obj1} vs {len_obj2})",
                    ValueError,
                )

            for i, (subel1, subel2) in enumerate(zip(obj1, obj2)):
                ret = _compare_objects(
                    subel1,
                    subel2,
                    f"{curpath}[{str(i)}]",
                    atol=atol,
                    rtol=rtol,
                    strlen_only=strlen_only,
                    do_rstrip=do_rstrip,
                    rstrcut=rstrcut,
                    fail_on_diff=fail_on_diff,
                    diff_log=diff_log,
                )
                found_diff = found_diff or not ret
        else:
            if not smart_is_equal(obj1, obj2, atol=atol, rtol=rtol):
                treat_diff(
                    f"Value mismatch at {curpath} " f"({obj1} vs {obj2})", ValueError
                )

    # return True if equivalent
    return not found_diff


class TrackingDict(MutableMapping):
    """Class for tracking read access of elements in :class:`dict`-like objects.

    This class implements an interface to :class:`dict`-like objects for
    the purpose of tracking keys whose associated elements were
    retrieved. This tracking is applied recursively, hence also
    elements of :class:`dict`-like and :class:`list`-like objects
    stored within the root :class:`dict`-like object are potentially tracked.
    Not all keys are tracked, though.
    Read access to a key is only tracked if the following two criteria are
    met:

    - The key is an integer, i.e. of type :class:`int`
    - Elements within :class:`dict`-like`` objects are never tracked if
      the :class:`dict`-like object itself is stored under a
      key that starts with two underscores (``__``).
    - If an object is :class:`list`-like, it's elements are tracked.

    The first criteria are owed to the mode of operation of the
    :class:`~endf_parserpy.EndfParserPy` class.
    The methods :func:`~endf_parserpy.EndfParserPy.parsefile` and
    :func:`~endf_parserpy.EndfParserPy.writefile` of the
    :class:`~endf_parserpy.EndfParserPy` class will temporarily create auxiliary
    variables stored under keys starting with two underscores.
    It is not pertinent to track read access to those ephemeral
    objects. The purpose of the
    :class:`~endf_parserpy.utils.debugging_utils.TrackingDict` class---
    when it comes to writing ENDF-6 formatted data---is to ensure
    that all elements in arrays (emulated with :class:`dict`-like
    objects containing only integer keys) are accessed.
    Otherwise, it means that some elements have not been written
    to the ENDF-6 file and this situation indicates an inconsistency
    between counter variables and the index ranges of arrays.
    """

    def __init__(self, dict_like):
        """Initialize a ``TrackingDict`` object.

        Parameters
        __________
        dict_like : dict
            The :class:`dict`-like object for which read access should be tracked.
        """
        self._basedict = dict_like
        self._trackingobjs = {}
        self._accessed = set()

    def _should_track(self, key, obj):
        return not str(key).startswith("__") and isinstance(
            obj, (MutableMapping, MutableSequence)
        )

    def _is_tracked(self, key):
        return key in self._trackingobjs

    def _create_trackobj(self, obj):
        if isinstance(obj, MutableMapping):
            return TrackingDict(obj)
        elif isinstance(obj, MutableSequence):
            return TrackingList(obj)
        else:
            raise TypeError(f"This object of type {type(obj)}  cannot be tracked.")

    def __getitem__(self, key):
        retval = self._basedict.__getitem__(key)
        if isinstance(key, int):
            self._accessed.add(key)
        if self._should_track(key, retval) and not self._is_tracked(key):
            self._trackingobjs[key] = self._create_trackobj(retval)
        retval = self._trackingobjs.get(key, retval)
        return retval

    def __setitem__(self, key, value):
        if key in self._accessed:
            self._accessed.remove(key)
        if key in self._trackingobjs:
            self._trackingobjs.__delitem__(key)
        return self._basedict.__setitem__(key, value)

    def __delitem__(self, key):
        if key in self._accessed:
            self._accessed.__delitem__(key)
        if key in self._trackingobjs:
            self._trackingobjs.__delitem__(key)
        return self._basedict.__delitem__(key)

    def __iter__(self):
        return self._basedict.__iter__()

    def __len__(self):
        return self._basedict.__len__()

    def _verify_complete_retrieval(self, path=""):
        if len(self._accessed) > 0:
            for k in self._basedict:
                if isinstance(k, int) and k not in self._accessed:
                    indexpath = path + "/" + str(k)
                    raise IndexError(f"The content of {indexpath} was not accessed")
        for k in self._basedict:
            if self._is_tracked(k):
                indexpath = path + "/" + str(k)
                curval = self._trackingobjs[k]
                curval._verify_complete_retrieval(indexpath)

    def verify_complete_retrieval(self):
        """Verify that all array elements have been accessed.

        This function will raise an ``IndexError`` exception
        if there are :class:`dict`-like objects where at least
        one key of type :class:`int` has been accessed but
        more keys exist that have not been accessed.
        """
        self._verify_complete_retrieval()

    def unwrap(self):
        return self._basedict


class TrackingList(MutableSequence):

    def __init__(self, list_like):
        """Initialize a ``TrackingList`` object.

        Parameters
        __________
        list_like : list
            The :class:`list`-like object for which read access should be tracked.
        """
        self._baselist = list_like
        self._trackingobjs = [None] * len(list_like)
        self._accessed = [False] * len(list_like)

    def __getitem__(self, key):
        retval = self._baselist.__getitem__(key)
        self._accessed[key] = True
        if isinstance(retval, MutableSequence):
            if key not in self._trackingobjs:
                self._trackingobjs[key] = TrackingList(retval)
            retval = self._trackingobjs[key]
        elif isinstance(retval, MutableMapping):
            if key not in self._trackingobjs:
                self._trackingobjs[key] = TrackingDict(retval)
            retval = self._trackingobjs[key]
        return retval

    def __setitem__(self, key, value):
        retval = self._baselist.__setitem__(key, value)
        self._accessed[key] = False
        self._trackinglists[key] = None
        return retval

    def __delitem__(self, key):
        retval = self._baselists.__delitem__(key)
        self._accessed.__delitem__(key)
        self._trackinglists.__delitem__(key)
        return retval

    def __iter__(self):
        return self._baselist.__iter__()

    def __len__(self):
        return self._baselist.__len__()

    def insert(self, key, value):
        retval = self._baselist.insert(key, value)
        self._accessed.insert(key, False)
        self._trackinglists.insert(key, None)
        return retval

    def _verify_complete_retrieval(self, path=""):
        if any(self._accessed):
            for k in range(len(self._baselist)):
                if not self._accessed[k]:
                    indexpath = path + "/" + str(k)
                    raise IndexError(f"The content of {indexpath} was not accessed")
        for k, curval in enumerate(self._baselist):
            if isinstance(curval, (TrackingList, TrackingDict)):
                indexpath = path + "/" + str(k)
                curval._verify_complete_retrieval(indexpath)

    def verify_complete_retrieval(self):
        """Verify that all array elements have been accessed.

        This function will raise an ``IndexError`` exception
        if not all elements of :class:`list`-like objects
        have been accessed.
        """
        self._verify_complete_retrieval()

    def unwrap(self):
        return self._baselist
