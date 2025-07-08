############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/06/01
# Last modified:   2025/07/08
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
############################################################

import typing
from typing import Optional, Union
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod


StringInput = Union[str, List[str]]

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
    """

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
