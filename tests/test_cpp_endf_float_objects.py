############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/20
# Last modified:   2026/10/20
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""EndfFloat objects exchanged with EndfParserCpp (preserve_value_strings).

The C++ type caster creates EndfFloat instances without calling the class
and reads their value and original string directly for instances of
exactly this class. The objects must be indistinguishable from regularly
created instances, and objects of other kinds (subclasses, plain floats)
must still be converted correctly.
"""

from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.math_utils import EndfFloat


TESTFILE = str(Path(__file__).parent / "testdata" / "tsl_Al.endf")


def _floats(obj):
    # all EndfFloat objects of a parse result, in a deterministic order
    if isinstance(obj, dict):
        for key in obj:
            yield from _floats(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            yield from _floats(item)
    elif isinstance(obj, EndfFloat):
        yield obj


def test_objects_identical_to_regular_instances():
    result = EndfParserCpp(preserve_value_strings=True).parsefile(TESTFILE)
    floats = list(_floats(result))
    assert len(floats) > 1000
    for x in floats[:: max(1, len(floats) // 2000)]:
        ref = EndfFloat(float(x), x.get_original_string())
        assert type(x) is EndfFloat
        assert list(vars(x).items()) == list(vars(ref).items())


def test_objects_agree_with_python_parser():
    res_cpp = EndfParserCpp(preserve_value_strings=True).parsefile(TESTFILE)
    res_py = EndfParserPy(
        preserve_value_strings=True, print_cache_info=False
    ).parsefile(TESTFILE)
    # the key order of the dictionaries may differ between the parsers
    attrs_cpp = sorted(tuple(vars(x).items()) for x in _floats(res_cpp[7][4]))
    attrs_py = sorted(tuple(vars(x).items()) for x in _floats(res_py[7][4]))
    assert len(attrs_cpp) > 1000
    assert attrs_cpp == attrs_py


class _EndfFloatSubclass(EndfFloat):
    pass


@pytest.mark.parametrize(
    "value",
    [
        EndfFloat(2.5, " 2.500000+0"),
        _EndfFloatSubclass(2.5, " 2.500000+0"),
        2.5,
    ],
    ids=["EndfFloat", "subclass", "float"],
)
def test_writing_values_of_different_kinds(value):
    parser = EndfParserCpp(preserve_value_strings=True)
    section = parser.parsefile(TESTFILE, include=((7, 4),))
    section[7][4]["AWR"] = value
    written = parser.write(section)
    reparsed = parser.parse(written)
    assert float(reparsed[7][4]["AWR"]) == 2.5
