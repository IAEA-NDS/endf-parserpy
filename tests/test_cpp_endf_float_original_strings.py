############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/25
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Original strings of EndfFloat values in EndfParserCpp.

EndfParserCpp keeps the original string of a float value inline in the
C++ value (EndfFloatCpp), with room for 15 bytes plus the true length:

- Strings from parsing (11 characters) and strings that can be written
  (exactly 11 characters) are stored completely.
- Writing a value whose original string has another length than 11 is
  rejected with the message "wrong size<N>  <string>". Of a string longer
  than 15 bytes, the message shows only the beginning (15 bytes, or 11
  bytes for strings of 255 bytes or more) but the true length N.
- The conversion of an EndfFloat with a long string does not fail; its
  value is used like any other value.
"""

from pathlib import Path
import json
import os
import subprocess
import sys
import pytest
import endf_parserpy
from endf_parserpy import EndfParserCpp, EndfParserPy
from endf_parserpy.utils.math_utils import EndfFloat


TESTFILE = str(Path(__file__).parent / "testdata" / "tsl_Al.endf")


def _floats(obj):
    if isinstance(obj, dict):
        for key in obj:
            yield from _floats(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            yield from _floats(item)
    elif isinstance(obj, EndfFloat):
        yield obj


def _test_parser(**kwargs):
    return EndfParserCpp(
        endf_format="test",
        ignore_send_records=True,
        ignore_missing_tpid=True,
        **kwargs,
    )


def _section_dict(mt, **variables):
    return {2: {mt: {"MAT": 1, "MF": 2, "MT": mt, **variables}}}


def _lines(written):
    return written.splitlines() if isinstance(written, str) else list(written)


@pytest.mark.parametrize("atype", ["dict", "list", "numpy"])
def test_preserve_round_trip_gives_original_lines(atype):
    parser = EndfParserCpp(preserve_value_strings=True, array_type=atype)
    with open(TESTFILE) as f:
        text = f.read()
    result = parser.parse(text)
    floats = list(_floats(result))
    assert len(floats) > 1000
    assert all(len(x.get_original_string()) == 11 for x in floats)
    written = _lines(parser.write(result))
    assert written == text.splitlines()


def test_parsed_strings_are_the_field_contents():
    parser = EndfParserCpp(preserve_value_strings=True)
    result = parser.parsefile(TESTFILE, include=((7, 4),))
    with open(TESTFILE) as f:
        lines = [l for l in f.read().splitlines() if l[70:75] == " 7  4"]
    awr = result[7][4]["AWR"]
    assert awr.get_original_string() == lines[0][11:22]
    assert float(awr) == float(lines[0][11:22].replace("+", "e+"))


@pytest.mark.parametrize("orig_str", [" 3.000000+0", "3.0        ", " " * 11])
def test_eleven_characters_written_verbatim(orig_str):
    parser = _test_parser()
    lines = _lines(parser.write(_section_dict(18, X=EndfFloat(3.0, orig_str))))
    assert lines[1][:11] == orig_str
    assert lines[1][11:22] == " 1.500000+0"


# The messages are obtained in a separate process: in some builds, a C++
# exception raised by a flavor module other than the first one loaded in
# the process loses its message (see DEFERRED_WORK.md).
_MESSAGE_SCRIPT = """
import json, sys
from endf_parserpy import EndfParserCpp
from endf_parserpy.utils.math_utils import EndfFloat
parser = EndfParserCpp(
    endf_format="test", ignore_send_records=True, ignore_missing_tpid=True
)
messages = []
for orig_str in json.loads(sys.stdin.read()):
    section = {2: {18: {"MAT": 1, "MF": 2, "MT": 18, "X": EndfFloat(3.0, orig_str)}}}
    try:
        parser.write(section)
        messages.append(None)
    except RuntimeError as exc:
        messages.append(str(exc))
print(json.dumps(messages))
"""


def _write_messages(orig_strs):
    # the package imported by the test, also in the separate process
    env = dict(os.environ)
    pkgdir = str(Path(endf_parserpy.__file__).parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (pkgdir, env.get("PYTHONPATH")) if p)
    res = subprocess.run(
        [sys.executable, "-c", _MESSAGE_SCRIPT],
        input=json.dumps(orig_strs),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return json.loads(res.stdout.strip().splitlines()[-1])


LENGTHS = list(range(1, 11)) + list(range(12, 21)) + [100, 254, 255, 256, 300, 70000]


def test_wrong_length_messages():
    orig_strs = ["".join(chr(ord("a") + i % 26) for i in range(n)) for n in LENGTHS]
    for orig_str, msg in zip(orig_strs, _write_messages(orig_strs)):
        n = len(orig_str)
        # strings of up to 15 characters completely, longer ones truncated
        shown = orig_str if n <= 15 else orig_str[: 15 if n < 255 else 11]
        assert msg == f"wrong size{n}  {shown}", n


def test_wrong_length_messages_non_ascii():
    # the length is counted in bytes of the UTF-8 encoding; bytes outside
    # printable ASCII are escaped in the message
    msgs = _write_messages(["\u20ac" * 5, "\u00e4" * 11])
    assert msgs[0] == "wrong size15  " + "\\xe2\\x82\\xac" * 5
    assert msgs[1] == "wrong size22  " + "\\xc3\\xa4" * 7 + "\\xc3"


def test_eleven_characters_accepted():
    assert _write_messages(["abcdefghijk", "", " " * 11]) == [None, None, None]


def test_empty_string_means_no_original_string():
    parser = _test_parser()
    lines = _lines(parser.write(_section_dict(18, X=EndfFloat(3.0, ""))))
    assert lines[1][:22] == " 3.000000+0 1.500000+0"


class _EndfFloatSubclass(EndfFloat):
    pass


@pytest.mark.parametrize("cls", [EndfFloat, _EndfFloatSubclass])
@pytest.mark.parametrize("length", [16, 40, 300])
def test_long_string_converts_and_value_is_used(cls, length):
    # the field is computed from the value, the string is not written;
    # subclasses take the regular (slower) conversion
    parser = _test_parser()
    value = cls(1.5, "x" * length)
    lines = _lines(parser.write(_section_dict(19, X=value)))
    assert lines[1][:11] == " 3.000000+0"


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("x, expected", [(1.6, "1"), (1.4, "2")])
def test_comparison_of_values_with_original_strings(ParserCls, x, expected):
    kwargs = {"print_cache_info": False} if ParserCls is EndfParserPy else {}
    parser = ParserCls(
        endf_format="test",
        ignore_send_records=True,
        ignore_missing_tpid=True,
        preserve_value_strings=True,
        **kwargs,
    )
    orig_str = f"{x:11.6f}"
    value = EndfFloat(x, orig_str)
    lines = _lines(parser.write(_section_dict(21, X=value, N=6)))
    assert lines[1][:11] == orig_str
    assert lines[2][22:33].strip() == expected
    reparsed = parser.parse("\n".join(lines))
    assert reparsed[2][21]["X"].get_original_string() == orig_str
    assert float(reparsed[2][21]["X"]) == x


def test_numpy_export_of_preserved_values():
    # with preserve_value_strings=True, arrays of floats are lists of
    # EndfFloat objects also with array_type="numpy"
    p_np = EndfParserCpp(preserve_value_strings=True, array_type="numpy")
    p_ls = EndfParserCpp(preserve_value_strings=True, array_type="list")
    r_np = p_np.parsefile(TESTFILE, include=((7, 4),))
    r_ls = p_ls.parsefile(TESTFILE, include=((7, 4),))
    f_np = [(float(x), x.get_original_string()) for x in _floats(r_np)]
    f_ls = [(float(x), x.get_original_string()) for x in _floats(r_ls)]
    assert len(f_np) > 1000
    assert sorted(f_np) == sorted(f_ls)
