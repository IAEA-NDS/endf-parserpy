from ._historical_modules import warn_stale_extension_files

# an extension module of a flavor from before the module with all flavors,
# left in a source checkout, would be imported instead of the shim of the
# flavor (see _historical_modules)
warn_stale_extension_files()

from .endf_parser_cpp import EndfParserCpp
