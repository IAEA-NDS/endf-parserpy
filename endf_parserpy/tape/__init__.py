############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/08
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Support for ENDF files containing several materials (tapes)."""

from .errors import (
    TapeError,
    TapeStructureError,
    AmbiguousMaterialError,
    SectionParseError,
    SectionRenderError,
    StaleSourceError,
)
from .splitter import split_materials
from .operations import (
    parse_tape,
    parse_tape_file,
    iter_parse_tape,
    iter_parse_tape_file,
    write_tape,
    write_tape_file,
    FailedMaterial,
)
from .index import TapeIndex, MaterialIndexEntry, SectionIndexEntry
from .address import EndfMaterialPath
from .material import MaterialView
from .endf_file import EndfFile, FailedSection
from .framing import check_framing, FramingProblem

__all__ = (
    "parse_tape",
    "parse_tape_file",
    "iter_parse_tape",
    "iter_parse_tape_file",
    "write_tape",
    "write_tape_file",
    "split_materials",
    "FailedMaterial",
    "TapeIndex",
    "MaterialIndexEntry",
    "SectionIndexEntry",
    "EndfFile",
    "EndfMaterialPath",
    "MaterialView",
    "FailedSection",
    "check_framing",
    "FramingProblem",
    "TapeError",
    "TapeStructureError",
    "AmbiguousMaterialError",
    "SectionParseError",
    "SectionRenderError",
    "StaleSourceError",
)
