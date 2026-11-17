############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Deprecation warnings attributed to the code that uses the package.

The package issues its deprecation warnings as ``DeprecationWarning``
without changing the warning filters, so that the filters of the user
(``-W``, ``PYTHONWARNINGS``, :func:`warnings.filterwarnings`) decide
whether they are shown. With the default filters of Python, a
``DeprecationWarning`` is shown if it is attributed to ``__main__``
(PEP 565), e.g. a script or an interactive session that calls the
deprecated function; test runners such as pytest show them all.

For that, the warning must be attributed to the code that called into
the package, not to a module of the package (whose warnings the default
filters ignore). :func:`warn_deprecated` finds the first frame outside
the package and the import system, however many functions of the
package (e.g. decorators, subclasses, the module of a shim) lie between.
"""

import os
import sys
import warnings

# the directory of the package, with a trailing separator
_PACKAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ""
)


def _is_bootstrap_frame(filename):
    # importlib._bootstrap and importlib._bootstrap_external, whose
    # frames warnings.warn skips itself when it counts the stacklevel
    return "importlib" in filename and "_bootstrap" in filename


def _is_internal_frame(filename):
    # a frame of the package or of importlib.import_module
    if filename.startswith("<"):
        return False
    path = os.path.abspath(filename)
    if path.startswith(_PACKAGE_DIR):
        return True
    return (
        os.path.basename(path) == "__init__.py"
        and os.path.basename(os.path.dirname(path)) == "importlib"
    )


def _external_stacklevel():
    # The stacklevel of warnings.warn, called by the caller of this
    # function, that gives the first frame outside the package and the
    # import system. Like warnings.warn, it does not count the frames of
    # importlib._bootstrap.
    frame = sys._getframe(1)  # the caller of warnings.warn: level 1
    level = 1
    frame = frame.f_back
    while frame is not None:
        filename = frame.f_code.co_filename
        if not _is_bootstrap_frame(filename):
            level += 1
            if not _is_internal_frame(filename):
                return level
        frame = frame.f_back
    return level


def warn_deprecated(message, category=DeprecationWarning):
    """Issue a deprecation warning attributed to the code that called
    into the package (see the module docstring)."""
    warnings.warn(message, category, stacklevel=_external_stacklevel())
