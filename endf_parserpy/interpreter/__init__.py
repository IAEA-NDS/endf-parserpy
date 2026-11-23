"""The Python parser :class:`~endf_parserpy.EndfParserPy`.

Its module ``endf_parser`` is imported when it or one of the names
below is first accessed (PEP 562), so that the helper modules of this
package (e.g. ``custom_exceptions``, ``endf_utils``) can be imported
without the parser.
"""

import importlib as _importlib

_PARSER_NAMES = (
    "EndfParserPy",
    "EndfParser",  # deprecated alias
    "BasicEndfParser",  # deprecated alias
)


def __getattr__(name):
    if name in _PARSER_NAMES or name == "endf_parser":
        module = _importlib.import_module(".endf_parser", __name__)
        if name == "endf_parser":
            return module
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_PARSER_NAMES) | {"endf_parser"})
