import importlib as _importlib

from .endf_parser_base import EndfParserBase
from .endf_parser_factory import EndfParserFactory
from .cpp_parsers import EndfParserCpp
from .utils import (
    debugging_utils,
    accessories,
    user_tools,
    endf6_plumbing,
)
from .utils.accessories import EndfDict
from .utils.accessories import EndfPath
from .utils.accessories import EndfVariable
from .utils.debugging_utils import compare_objects
from .utils.user_tools import (
    list_parsed_sections,
    list_unparsed_sections,
    sanitize_fieldname_types,
)
from .utils.endf6_plumbing import update_directory
from .utils.math_utils import EndfFloat
from .errors import EndfParserpyError
from .utils.tolerated_mismatches import EndfToleratedMismatchWarning
from .utils.tape_structure import (
    TapeStructure,
    section_label,
    to_dict_form,
    to_list_form,
)
from .utils.sections import (
    iter_sections,
    section_positions,
    locate_section,
    get_section,
    set_section,
    insert_section,
    remove_section,
)
from .tape import (
    parse_tape,
    parse_tape_file,
    iter_parse_tape,
    iter_parse_tape_file,
    write_tape,
    write_tape_file,
    FailedMaterial,
    TapeIndex,
    EndfFile,
    EndfMaterialPath,
    TapeError,
    TapeStructureError,
    AmbiguousSectionError,
)


__version__ = "0.19.0"


# The Python parser (endf_parserpy.interpreter.endf_parser and the
# modules it imports) is imported when one of these names is first
# accessed (PEP 562), not with the package: EndfParserCpp, endf-cli and
# the multi-material interface do not need it.
_INTERPRETER_NAMES = (
    "EndfParserPy",
    "EndfParser",  # deprecated alias
    "BasicEndfParser",  # deprecated alias
)


def __getattr__(name):
    if name in _INTERPRETER_NAMES:
        module = _importlib.import_module(".interpreter", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_INTERPRETER_NAMES))


__all__ = (
    "EndfParserBase",
    "EndfParserFactory",
    "EndfParserPy",
    "EndfParserCpp",
    "EndfDict",
    "EndfPath",
    "EndfVariable",
    "EndfFloat",
    "TapeStructure",
    "section_label",
    "to_dict_form",
    "to_list_form",
    "iter_sections",
    "section_positions",
    "locate_section",
    "get_section",
    "set_section",
    "insert_section",
    "remove_section",
    "compare_objects",
    "list_parsed_sections",
    "list_unparsed_sections",
    "sanitize_fieldname_types",
    # package-wide base exception
    "EndfParserpyError",
    # warning about the field mismatches tolerated in a parse
    "EndfToleratedMismatchWarning",
    # multi-material tape interface
    "parse_tape",
    "parse_tape_file",
    "iter_parse_tape",
    "iter_parse_tape_file",
    "write_tape",
    "write_tape_file",
    "FailedMaterial",
    "TapeIndex",
    "EndfFile",
    "EndfMaterialPath",
    "TapeError",
    "TapeStructureError",
    "AmbiguousSectionError",
    # deprecated aliases
    "EndfParser",
    "BasicEndfParser",
)
