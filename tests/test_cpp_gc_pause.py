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

"""EndfParserCpp pauses Python's cyclic garbage collector while parsing.

The parse functions disable the collector while they build the result and
restore its previous state afterwards, also if parsing fails. The state of
the collector seen by the caller must therefore never change.
"""

import gc
from pathlib import Path
import pytest
from endf_parserpy import EndfParserCpp


TESTFILE = str(Path(__file__).parent / "testdata" / "tsl_Al.endf")


@pytest.fixture
def restore_gc_state():
    was_enabled = gc.isenabled()
    yield
    if was_enabled:
        gc.enable()
    else:
        gc.disable()


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("from_string", [False, True], ids=["file", "string"])
def test_gc_state_unchanged_by_parsing(restore_gc_state, enabled, from_string):
    gc.enable() if enabled else gc.disable()
    parser = EndfParserCpp(preserve_value_strings=True)
    if from_string:
        result = parser.parse(Path(TESTFILE).read_text())
    else:
        result = parser.parsefile(TESTFILE)
    assert 7 in result
    assert gc.isenabled() is enabled


@pytest.mark.parametrize("enabled", [True, False])
def test_gc_state_restored_after_parse_error(restore_gc_state, enabled):
    lines = Path(TESTFILE).read_text().splitlines()
    # corrupt a number field in the MF7/MT4 section
    for i, line in enumerate(lines):
        if line[70:75] == " 7  4" and i > 0 and lines[i - 1][70:75] == " 7  4":
            lines[i] = "  abcdefgh " + line[11:]
            break
    gc.enable() if enabled else gc.disable()
    with pytest.raises(Exception):
        EndfParserCpp().parse("\n".join(lines))
    assert gc.isenabled() is enabled


def test_result_objects_tracked_after_parsing(restore_gc_state):
    gc.enable()
    result = EndfParserCpp(preserve_value_strings=True).parsefile(TESTFILE)
    # the containers of the result are regular, collectable objects
    assert gc.is_tracked(result)
    assert gc.is_tracked(result[7][4])
