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

"""The functions of the flavor `jendl` in the C++ module.

Until release 0.18, every flavor had a C++ module of its own, e.g.
``endf_parserpy.cpp_parsers.jendl``. The functions of all flavors are
now in one module, ``endf_parserpy.cpp_parsers._flavors``, and this
module stands for the entry ``jendl`` of it, so that code importing
the module of the flavor keeps working.
"""

import sys
from . import _flavors

sys.modules[__name__] = _flavors.jendl
