# Strings without their canonical representation ("non-ready" strings),
# which only deprecated C APIs of Python < 3.12 can create, are read
# correctly by EndfParserCpp, both as the data to parse and as text
# values to write.
import ctypes
import sys
from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp

pytestmark = [
    pytest.mark.skipif(
        sys.version_info >= (3, 12)
        or sys.implementation.name != "cpython"
        or not hasattr(ctypes.pythonapi, "PyUnicode_FromUnicode"),
        reason="non-ready strings only exist in CPython < 3.12",
    ),
    pytest.mark.filterwarnings("ignore:PyUnicode_FromUnicode:DeprecationWarning"),
]

TESTFILE = Path(__file__).parent / "testdata" / "dec-094_Pu_244.endf"


def legacy_string(text):
    """A copy of text that is not yet ready (wchar_t representation only)."""
    api = ctypes.pythonapi
    from_unicode = api.PyUnicode_FromUnicode
    from_unicode.restype = ctypes.py_object
    from_unicode.argtypes = [ctypes.c_void_p, ctypes.c_ssize_t]
    as_unicode = api.PyUnicode_AsUnicode
    as_unicode.restype = ctypes.c_void_p
    as_unicode.argtypes = [ctypes.py_object]
    obj = from_unicode(None, len(text))
    buf = as_unicode(obj)
    wchars = (ctypes.c_wchar * len(text)).from_address(buf)
    for i, c in enumerate(text):
        wchars[i] = c
    return obj


def test_parse_legacy_string():
    text = TESTFILE.read_text()
    parser = EndfParserCpp()
    assert parser.parse(legacy_string(text)) == parser.parse(text)


def test_write_legacy_text_value():
    parser = EndfParserCpp()
    endf_dict = parser.parse(TESTFILE.read_text())
    expected = parser.write(endf_dict)
    endf_dict[1][451]["ZSYMAM"] = legacy_string(endf_dict[1][451]["ZSYMAM"])
    assert parser.write(endf_dict) == expected
