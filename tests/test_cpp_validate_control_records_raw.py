"""EndfParserCpp(validate_control_records=True) with sections read
verbatim (include/exclude, sections without a recipe).

The lines of a section read verbatim are those up to the first line
with other MF/MT numbers (the SEND record, the first line of the next
section, or the first line of the material after the tape head). That
line was compared with the MAT/MF/MT numbers of the section, so that
valid files were rejected (e.g. "Expected MAT=1 but found MAT=2925" for
the line after the tape head of Cu-63, "Expected MT=1 but found MT=0"
for the SEND record of a section). Every line of a section read
verbatim is checked for the MAT number of its first line, and its SEND
record for the MAT and MF numbers, as in a section read with its recipe
and as by EndfParserPy, which checks them in any case.
"""

from pathlib import Path

import pytest

from endf_parserpy import EndfParserCpp, EndfParserPy

TESTDATA = Path(__file__).resolve().parent / "testdata"
CU63 = TESTDATA / "n_2925_29-Cu-63.endf"
PU244 = TESTDATA / "dec-094_Pu_244.endf"

SELECTIONS = [
    {},
    {"include": [(3, 1)]},
    {"include": [3]},
    {"exclude": [3]},
    {"include": []},
    {"include": [(1, 451)]},
    {"include": [(0, 0)]},
    {"exclude": [(1, 451)]},
]


@pytest.mark.parametrize("kwargs", SELECTIONS, ids=str)
@pytest.mark.parametrize("lenient", [False, True])
def test_valid_file_with_raw_sections(kwargs, lenient):
    opts = {"ignore_send_records": lenient}
    checked = EndfParserCpp(validate_control_records=True, **opts)
    unchecked = EndfParserCpp(**opts)
    assert checked.parsefile(CU63, **kwargs) == unchecked.parsefile(CU63, **kwargs)


@pytest.mark.parametrize("kwargs", [{}, {"include": [8]}, {"exclude": [8]}], ids=str)
def test_valid_decay_file(kwargs):
    checked = EndfParserCpp(validate_control_records=True)
    assert checked.parsefile(PU244, **kwargs) == EndfParserCpp().parsefile(
        PU244, **kwargs
    )


def _section_lines(lines, mf, mt):
    return [i for i, line in enumerate(lines) if line[70:75] == "%2d%3d" % (mf, mt)]


def _corrupt_mat(path, tmp_path, index):
    lines = path.read_text().splitlines()
    line = lines[index]
    lines[index] = line[:66] + "%4d" % (int(line[66:70]) + 1) + line[70:]
    out = tmp_path / "corrupt.endf"
    out.write_text("\n".join(lines) + "\n")
    return out, index + 1


def _cases():
    lines = PU244.read_text().splitlines()
    mt451 = _section_lines(lines, 1, 451)
    mt457 = _section_lines(lines, 8, 457)
    send451 = _section_lines(lines, 1, 0)[0]
    return {
        "line_of_mf1": mt451[5],
        "head_of_mf1": mt451[0],
        "send_of_mf1": send451,
        "line_of_mf8": mt457[3],
    }


CASES = _cases()


@pytest.mark.parametrize("name", sorted(CASES))
@pytest.mark.parametrize(
    "kwargs",
    # MF1/MT451 parsed or read verbatim, MF8/MT457 alike
    [{}, {"include": [(1, 451)]}, {"include": [8]}, {"exclude": [1, 8]}],
    ids=str,
)
def test_wrong_mat_reported(name, kwargs, tmp_path):
    path, line = _corrupt_mat(PU244, tmp_path, CASES[name])
    with pytest.raises(Exception, match="Invalid MAT encountered") as exc_info:
        EndfParserCpp(validate_control_records=True).parsefile(path, **kwargs)
    # the line of the wrong MAT number, or for the first line of a section
    # (whose number the section takes), the line after it
    expected_line = line + 1 if name == "head_of_mf1" else line
    assert f"Line {expected_line}:" in str(exc_info.value)
    # EndfParserPy reports it as well
    with pytest.raises(Exception, match="MAT=3565"):
        EndfParserPy().parsefile(path, **kwargs)


@pytest.mark.parametrize("kwargs", [{}, {"include": [(1, 451)]}, {"include": [8]}])
def test_wrong_mat_of_send_with_ignore_send_records(kwargs, tmp_path):
    # a SEND record that is read is checked for its MAT number with
    # validate_control_records, as in cpp_read_send
    path, line = _corrupt_mat(PU244, tmp_path, CASES["send_of_mf1"])
    parser = EndfParserCpp(validate_control_records=True, ignore_send_records=True)
    with pytest.raises(Exception, match="Invalid MAT encountered"):
        parser.parsefile(path, **kwargs)
    EndfParserCpp(ignore_send_records=True).parsefile(path, **kwargs)
