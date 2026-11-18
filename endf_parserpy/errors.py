############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Package-wide base exception for endf-parserpy.

Every exception class defined by endf-parserpy ultimately derives from
:class:`EndfParserpyError`, so ``except EndfParserpyError`` catches any
library-specific error regardless of which subsystem raised it: the
parsing engine (``ParserException``), the recipe compiler
(``EquationSolveError``) or the multi-material tape interface
(``TapeError``). It does not catch the errors of the C++ parser, which
are ``RuntimeError``, nor the standard exceptions, such as
``KeyError``, ``IndexError``, ``TypeError`` and ``ValueError``, which
the package raises e.g. for a missing key or section or an invalid
argument.

This module deliberately has no imports so that every subsystem can
derive its own error hierarchy from it without risking a circular
import.
"""


class EndfParserpyError(Exception):
    """Base class of the exception classes defined by endf-parserpy.

    The C++ parser raises ``RuntimeError`` instead, and standard
    exceptions such as ``KeyError`` or ``ValueError`` are raised e.g. for
    a missing key or section or an invalid argument.
    """
