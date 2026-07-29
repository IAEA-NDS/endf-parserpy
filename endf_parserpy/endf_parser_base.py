############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/06/01
# Last modified:   2026/07/29
# License:         MIT
# Copyright (c) 2025-2026 International Atomic Energy Agency (IAEA)
#
############################################################

import typing
import inspect
import functools
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


def _check_array_type(array_type):
    """Reject unknown ``array_type`` values.

    The Python and C++ parsers interpret unrecognized values in
    opposite ways (falling back to dict and list mode, respectively),
    so an invalid value must not pass silently.
    """
    valid_array_types = ("dict", "list", "list_slow")
    if array_type not in valid_array_types:
        raise ValueError(
            f"invalid array_type `{array_type}`, " f"must be one of {valid_array_types}"
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
    :func:`_record_init_kwargs` for this to work.
    """

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
