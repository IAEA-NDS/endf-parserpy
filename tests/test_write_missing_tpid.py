############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/04
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The ignore_missing_tpid option on the write side.

Writing a dictionary without an MF=0/MT=0 (TPID) section is a
deliberate decision: with the default ``ignore_missing_tpid=False``,
``write`` and ``writefile`` raise an error naming the remedy, and with
``ignore_missing_tpid=True`` they write the data without a tape head.
A parser instance thus round-trips its own output with one assignment
of the option: a strict parser only writes tapes it can read again, and
a lenient parser reads and writes headless tapes. The check runs after
all sections have been written, so that errors in the sections surface
first, and a write restricted with ``exclude`` or ``include`` is exempt
because it produces a deliberate fragment.
"""

import pytest
from endf_parserpy import EndfParserCpp, EndfParserPy


MAT = 2625


def _line(content, mat, mf, mt):
    assert len(content) <= 66
    return f"{content:<66}{mat:>4}{mf:>2}{mt:>3}"


MF3_LINES = [
    _line(
        " 2.906300+4 6.238900+1          0          0          0          0", MAT, 3, 1
    ),
    _line(
        " 0.000000+0 0.000000+0          0          0          1          1", MAT, 3, 1
    ),
    _line("          1          2", MAT, 3, 1),
    _line(" 1.000000+0 2.000000+0", MAT, 3, 1),
]


def _make_tape(with_tpid=True):
    lines = []
    if with_tpid:
        lines.append(_line("test tape for the TPID check on writing", 1, 0, 0))
    lines.extend(MF3_LINES)
    lines.append(_line("", MAT, 3, 0))  # SEND
    lines.append(_line("", MAT, 0, 0))  # FEND
    lines.append(_line("", 0, 0, 0))  # MEND
    lines.append(_line("", -1, 0, 0))  # TEND
    return "".join(l + "\n" for l in lines)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_write_without_tpid_raises_by_default(ParserCls, tmp_path):
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    del endf_dict[0]
    with pytest.raises(Exception) as excinfo:
        parser.write(endf_dict)
    assert "TPID" in str(excinfo.value)
    assert "ignore_missing_tpid" in str(excinfo.value)
    with pytest.raises(Exception) as excinfo:
        parser.writefile(tmp_path / "should_not_be_written.endf", endf_dict)
    assert "TPID" in str(excinfo.value)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_write_without_tpid_with_option(ParserCls):
    parser = ParserCls(ignore_missing_tpid=True)
    endf_dict = parser.parse(_make_tape())
    del endf_dict[0]
    out = parser.write(endf_dict)
    assert int(out[0][66:70]) == MAT  # starts with the first section


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_write_with_tpid_unaffected(ParserCls):
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    out = parser.write(endf_dict)
    assert (int(out[0][66:70]), int(out[0][70:72]), int(out[0][72:75])) == (1, 0, 0)


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
@pytest.mark.parametrize("selection", [{"include": (3,)}, {"exclude": (0,)}])
def test_write_fragment_is_exempt(ParserCls, selection):
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    if "include" in selection:
        del endf_dict[0]
    out = parser.write(endf_dict, **selection)
    assert out


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_same_instance_round_trips_headless_tape(ParserCls):
    # the motivating symmetry: one assignment of the option suffices for
    # parse -> write -> parse of a tape without a tape head
    parser = ParserCls(ignore_missing_tpid=True)
    endf_dict = parser.parse(_make_tape(with_tpid=False))
    out = parser.write(endf_dict)
    endf_dict2 = parser.parse("\n".join(out) + "\n")
    assert endf_dict2[3][1]["xstable"] == endf_dict[3][1]["xstable"]


@pytest.mark.parametrize("ParserCls", [EndfParserCpp, EndfParserPy])
def test_strict_instance_round_trips_own_output(ParserCls):
    # a strict parser only produces output it can read again
    parser = ParserCls()
    endf_dict = parser.parse(_make_tape())
    out = parser.write(endf_dict)
    endf_dict2 = parser.parse("\n".join(out) + "\n")
    assert endf_dict2[3][1]["xstable"] == endf_dict[3][1]["xstable"]
