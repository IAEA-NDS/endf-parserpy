############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/16
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Deprecated: the functions of the flavor `pendf` in the C++ module.

Until release 0.18, every flavor had a C++ module of its own, e.g.
``endf_parserpy.cpp_parsers.pendf``. The functions of all flavors are
now in one module, ``endf_parserpy.cpp_parsers._flavors``, and this
module stands for its entry ``pendf``, so that code importing the module
of the flavor keeps working. Importing it issues a
``DeprecationWarning``; it will be removed in a later release. Use
``EndfParserCpp(endf_format="pendf")`` instead, and
``importlib.import_module(parser._parse_endf.__module__)`` of such a
parser for the diagnostic functions ``_bulk_body_info`` and
``_line_read_counts``.
"""

import sys
from ._historical_modules import deprecated_entry

sys.modules[__name__] = deprecated_entry(__name__)
