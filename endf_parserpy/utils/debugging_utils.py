############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/09
# Last modified:   2024/04/30
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import MutableMapping
from endf_parserpy.utils.math_utils import math_allclose
from endf_parserpy.utils.accessories import EndfDict


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
    possible being or containing objects of type ``dict`` or
    iterable array-like objects. For example, this class can be
    used to confirm or reject the equality of two nested dictionaries
    resulting from the parsing of ENDF-6 files via the ``parsefile()``
    method of the :class:`endf_parserpy.EndfParser` class.
    The function can print out meaningful information where the
    discrepancies are present in the objects with a nested structure.

    Parameters
    ----------
    obj1 : object
        Any kind of object but usually it will be a nested ``dict_like`` structure.
    obj2 : object
        Any kind of object but usually it will be a nested ``dict_like`` structure.
    atol : float
        The absolute tolerance for the comparison of two ``float`` variables.
    rtol : float
        The relative tolerance for the comparison of two ``float`` variables.
    strlen_only : bool
        If ``true``, only compare the lengths of strings, otherwise also
        the content of the strings is considered in the comparison.
    do_rstrip : bool
        If ``true``, strip whitespace
        characters at the end of the strings before comparison.
    rstrcut : Union[None, int]
        If an integer is provided, only retain the first ``rstrcut`` characters
        of the strings in the comparison. If ``None``, strings are compared
        as they are.
    fail_on_diff : bool
        If ``true``, this function will raise an exception at the first encounter
        of a difference. Otherwise, the function will fully compare the objects
        and return ``true`` if the two objects are equal and ``false`` if they
        exhibit differences. The second option is mostly useful in combination
        with ``diff_log=True``.
    diff_log : Union[None, List]
        A ``list`` object can be passed which will be filled with
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
    """Class for tracking read access of elements in ``dict_like`` objects.

    This class implements an interface to ``dict_like`` objects for
    the purpose of tracking keys whose associated elements were
    retrieved. This tracking is applied recursively, hence also
    keys of ``dict_like`` objects  stored within the root ``dict_like``
    object are potentially tracked. Not all keys are tracked, though.
    Read access to a key is only tracked if the following two criteria are
    met:

    - The key is an integer, i.e. of type ``int``
    - Keys within ``dict_like`` objects are never tracked if
      the ``dict_like`` object itself is stored under a
      key that starts with two underscores (``__``).

    These two rules are owed to the mode of operation of the
    :class:`endf_parserpy.endf_parser.EndfParser` class.
    The methods ``.parsefile()`` and ``.writefile()`` of the
    ``EndfParser`` class will temporarily create auxiliary
    variables stored under keys starting with two underscores.
    It is not pertinent to track read access to those ephemeral
    objects. The purpose of the ``TrackingDict`` class---
    when it comes to writing ENDF-6 formatted data---is to ensure
    that all elements in arrays (emulated with ``dict_like``
    objects containing only integer keys) are accessed.
    Otherwise, it means that some elements have not been written
    to the ENDF-6 file and this situation indicates an inconsistency
    between counter variables and the index range of arrays.
    """

    def __init__(self, dict_like):
        """Initialize a ``TrackingDict`` object.

        Parameters
        __________
        dict_like : dict
            The ``dict_like`` object for which read access should be tracked.
        """
        self._basedict = dict_like
        self._trackingdicts = {}
        self._accessed = set()

    def __getitem__(self, key):
        if isinstance(key, int):
            self._accessed.add(key)
        retval = self._basedict.__getitem__(key)
        if isinstance(retval, MutableMapping) and not str(key).startswith("__"):
            if key not in self._trackingdicts:
                self._trackingdicts[key] = TrackingDict(retval)
            retval = self._trackingdicts[key]
        return retval

    def __setitem__(self, key, value):
        if key in self._accessed:
            self._accessed.remove(key)
        if key in self._trackingdicts:
            self._trackingdicts.__delitem__(key)
        return self._basedict.__setitem__(key, value)

    def __delitem__(self, key):
        if key in self._accessed:
            self._accessed.__delitem__(key)
        if key in self._trackingdicts:
            self._trackingdicts.__delitem__(key)
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
            curval = self.__getitem__(k)
            if isinstance(curval, TrackingDict):
                indexpath = path + "/" + str(k)
                curval._verify_complete_retrieval(indexpath)

    def verify_complete_retrieval(self):
        """Verify that all array elements have been accessed.

        This function will raise an ``IndexError`` exception
        if there are ``dict_like`` objects where at least
        one key of type ``int`` has been accessed but
        more keys exist that have not been accessed.
        """
        self._verify_complete_retrieval()

    def unwrap(self):
        return self._basedict
