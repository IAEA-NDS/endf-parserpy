############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/06/01
# Last modified:   2026/11/21
# License:         MIT
# Copyright (c) 2025-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import typing
import inspect
import functools
import numbers
import os
import secrets
import shutil
import tempfile
from typing import Optional, Union
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod


StringInput = Union[str, List[str]]


def _record_init_kwargs(init):
    """Decorate an ``__init__`` so its arguments are recorded for pickling.

    The wrapped ``__init__`` stores the (fully defaulted) arguments it
    was called with on the instance as ``_init_kwargs``. This lets
    :class:`EndfParserBase` pickle a parser *by recipe* -- the arguments
    it was built with -- instead of by its live state, which is heavy
    and, for the C++ parser, not picklable at all. The parser is rebuilt
    on unpickling by re-running ``__init__`` with those arguments.

    A parser subclass must decorate its ``__init__`` with this for the
    parser to be picklable.
    """
    signature = inspect.signature(init)

    @functools.wraps(init)
    def wrapper(self, *args, **kwargs):
        bound = signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        self._init_kwargs = {
            name: value for name, value in bound.arguments.items() if name != "self"
        }
        return init(self, *args, **kwargs)

    return wrapper


def _check_material_form(material_form):
    """Reject unknown ``material_form`` values."""
    if material_form not in (None, "dict", "list"):
        raise ValueError(
            'material_form must be None, "dict" or "list", not ' f"{material_form!r}"
        )


def _check_array_type(array_type):
    """Reject unknown ``array_type`` values.

    The Python and C++ parsers interpret unrecognized values in
    opposite ways (falling back to dict and list mode, respectively),
    so an invalid value must not pass silently.
    """
    valid_array_types = ("dict", "list", "list_slow", "numpy")
    if array_type not in valid_array_types:
        raise ValueError(
            f"invalid array_type `{array_type}`, " f"must be one of {valid_array_types}"
        )


def _check_numpy_available(array_type):
    """Raise an :exc:`ImportError` if ``array_type="numpy"`` cannot be used.

    Both parsers return numpy arrays with this option, so the numpy
    package is required whichever parser is selected.
    """
    if array_type == "numpy":
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "array_type `numpy` requires the numpy package, which could "
                'not be imported. Install it with `pip install "endf-parserpy[fast]"` '
                "or `pip install numpy`."
            ) from exc


def _is_int(value):
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _normalize_section_selection(selection, name):
    """Return the ``include`` or ``exclude`` argument ``selection`` (named
    ``name`` in the messages) in the form used by both parsers: ``None``,
    or a tuple of MF numbers (int) and ``(MF, MT)`` tuples.

    A single MF number stands for a tuple with this number, and an
    ``[MF, MT]`` pair may be given as a list (or another sequence) as
    well as a tuple. Any other entry raises an exception: a
    :exc:`TypeError` for an entry or selection of a wrong type, a
    :exc:`ValueError` for a pair without exactly two numbers.
    """
    if selection is None:
        return None
    if _is_int(selection):
        return (int(selection),)
    if isinstance(selection, (str, bytes, dict)) or not hasattr(selection, "__iter__"):
        raise TypeError(
            f"`{name}` must be a sequence of MF numbers and (MF, MT) pairs, "
            f"e.g. (3, (1, 451)), not {selection!r}"
        )
    normalized = []
    for entry in selection:
        if _is_int(entry):
            normalized.append(int(entry))
            continue
        if isinstance(entry, (str, bytes, dict)) or not hasattr(entry, "__iter__"):
            raise TypeError(
                f"invalid entry {entry!r} in `{name}`: an entry must be an MF "
                "number (int) or an (MF, MT) pair of two ints, e.g. 3 or (3, 1)"
            )
        pair = tuple(entry)
        if len(pair) != 2:
            raise ValueError(
                f"invalid entry {entry!r} in `{name}`: an (MF, MT) pair must "
                f"have two numbers, not {len(pair)}"
            )
        if not (_is_int(pair[0]) and _is_int(pair[1])):
            raise TypeError(
                f"invalid entry {entry!r} in `{name}`: the MF and MT numbers "
                "of a pair must be ints"
            )
        normalized.append((int(pair[0]), int(pair[1])))
    return tuple(normalized)


def _normalize_section_selections(exclude, include):
    """The ``exclude`` and ``include`` arguments of a parse or write as
    normalized by :func:`_normalize_section_selection`."""
    return (
        _normalize_section_selection(exclude, "exclude"),
        _normalize_section_selection(include, "include"),
    )


MfNumberType = MtNumberType = int
MfMtTupleType = Tuple[MfNumberType, MtNumberType]
MfMtTuplesType = Tuple[Union[MfNumberType, MfMtTupleType]]

EndfValueType = Union[dict, list, int, float, str]
ParsedEndfSectionType = Dict[str, EndfValueType]
UnparsedEndfSectionType = List[str]
EndfSectionType = Union[ParsedEndfSectionType, UnparsedEndfSectionType]

MtDictType = Dict[int, EndfSectionType]
MfMtDictType = Dict[int, MtDictType]


def _create_temporary_file(filename, target, target_exists):
    # An empty file next to the target, created with the mode 0o666 that
    # open() uses, so that the operating system applies the umask (and the
    # default ACL of the directory) as for a file created by open().
    dirname, basename = os.path.split(target)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for _ in range(100):
        tmp = os.path.join(dirname, f".{basename}.{secrets.token_hex(4)}.tmp")
        try:
            fd = os.open(tmp, flags, 0o666)
        except FileExistsError:
            continue
        except OSError as exc:
            if target_exists:
                # an existing file in a directory without write
                # permission: its content is replaced by a copy, for which
                # the temporary file can be anywhere
                fd, tmp = tempfile.mkstemp(suffix=".endf.tmp")
                os.close(fd)
                return tmp
            # the error open() gives for the target, e.g. for a missing
            # directory
            raise OSError(exc.errno, exc.strerror, os.fspath(filename)) from None
        os.close(fd)
        return tmp
    raise FileExistsError(f"no temporary file could be created in {dirname}")


def _write_via_temporary_file(filename, write_to_path):
    """Write a file with ``write_to_path(path)`` and keep it only on success.

    ``write_to_path`` writes the file at ``path``, a temporary file; if it
    raises an exception, the temporary file is removed and ``filename``
    is neither created nor changed. Otherwise the result is the same as if
    ``write_to_path`` had written ``filename`` with :func:`open`: a symbolic
    link is followed, a new file gets the permissions given by the umask,
    and an existing file keeps its inode, permissions, owner and links, as
    its content is replaced by a copy of the temporary file (for a new
    file, the temporary file is renamed, in the same directory).
    """
    # open() follows a symbolic link, also a dangling one
    target = os.path.realpath(os.fsdecode(os.fspath(filename)))
    target_exists = os.path.exists(target)
    tmp = _create_temporary_file(filename, target, target_exists)
    try:
        write_to_path(tmp)
        if target_exists:
            shutil.copyfile(tmp, target)
        else:
            os.replace(tmp, target)
    finally:
        # the temporary file is gone after a successful os.replace; an
        # error of the cleanup must not mask the error of the writing
        try:
            os.remove(tmp)
        except OSError:
            pass


class EndfParserBase(ABC):
    """Abstract base class for ENDF parsers.

    This abstract base class defines the basic
    interface that must be provided by ENDF parser classes,
    such as
    :class:`~endf_parserpy.EndfParserPy`
    and :class:`~endf_parserpy.EndfParserCpp`.
    Therefore, any ENDF parser class should be derived
    from this abstract base class.

    A parser is picklable: it is pickled *by recipe* -- the arguments
    it was constructed with -- and rebuilt by re-running ``__init__`` on
    unpickling. A subclass must decorate its ``__init__`` with
    ``_record_init_kwargs`` for this to work.
    """

    # The tape structure of the flavor of the parser (see
    # endf_parserpy.TapeStructure) and the public form of a material that
    # the parser was asked for (None: the form of the tape structure); a
    # parser derived from this class has the structure of ENDF-6 unless it
    # sets these attributes.
    tape_structure = None
    material_form = None

    def _public_material_form(self):
        """The form in which a material is returned: ``"dict"`` or
        ``"list"``."""
        if self.material_form is not None:
            return self.material_form
        ts = self.tape_structure
        return "dict" if ts is None else ts.material_form

    def __getstate__(self):
        """Return the picklable state of the parser: its constructor arguments.

        A parser is pickled by recipe rather than by its live state,
        which is heavy and, for the C++ parser, not picklable at all.
        """
        try:
            return dict(self._init_kwargs)
        except AttributeError:
            raise TypeError(
                f"{type(self).__name__} cannot be pickled: its __init__ does "
                "not record its constructor arguments -- decorate it with "
                "_record_init_kwargs"
            ) from None

    def __setstate__(self, state):
        """Rebuild the parser by re-running ``__init__`` with the saved args."""
        self.__init__(**state)

    @abstractmethod
    def parse(
        self,
        lines: StringInput,
        exclude: Optional[MfMtTuplesType] = None,
        include: Optional[MfMtTuplesType] = None,
    ) -> MfMtDictType:
        pass

    @abstractmethod
    def parsefile(
        self,
        filename: str,
        exclude: Optional[MfMtTuplesType] = None,
        include: Optional[MfMtTuplesType] = None,
    ) -> MfMtDictType:
        pass

    @abstractmethod
    def write(
        self,
        endf_dict: MfMtDictType,
        exclude: Optional[MfMtTuplesType] = None,
        include: Optional[MfMtTuplesType] = None,
    ) -> List[str]:
        pass

    @abstractmethod
    def writefile(
        self,
        filename: str,
        endf_dict: MfMtDictType,
        exclude: Optional[MfMtTuplesType] = None,
        include: Optional[MfMtTuplesType] = None,
        overwrite: bool = False,
    ) -> None:
        pass
