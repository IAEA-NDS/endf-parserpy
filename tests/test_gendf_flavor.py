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

"""Tests of the ``gendf`` flavor (GENDF tapes of NJOY GROUPR and GAMINR).

The test files in ``tests/testdata/gendf`` are cut down from tapes of
NJOY 2016.72: a few groups per section, the record of the last group
kept, and the framing of NJOY (no SEND after MF1/MT451, no FEND records
between the MFs), which the tape structure of the flavor describes. The
sections are parsed one by one, each as a short tape with the end
records of this structure, and whole tapes are read and written back
byte for byte with both parsers (parsefile/write, parse_tape/write_tape,
EndfFile). The expected values are those of the tapes, checked against
the listings of GROUPR.
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from endf_parserpy import (
    EndfFile,
    EndfParserCpp,
    EndfParserPy,
    section_label,
    to_dict_form,
)
from endf_parserpy.endf_recipes import (
    get_layout_version,
    get_recipe_dict,
    get_tape_structure,
    list_endf_build_targets,
    list_endf_flavors,
    resolve_endf_flavor,
)
from endf_parserpy.interpreter.custom_exceptions import (
    NumberMismatchError,
    UnexpectedControlRecordError,
    UnexpectedEndOfInputError,
)
from endf_parserpy.tape import parse_tape_file, write_tape
from endf_parserpy.tape.errors import (
    AmbiguousMaterialError,
    RepeatedSectionError,
    TapeStructureError,
)


TESTDATA = Path(__file__).parent / "testdata" / "gendf"
FILES = sorted(p.name for p in TESTDATA.iterdir())


def _cpp_available():
    # skipped only without the C++ module; an error if it lacks the entry
    # of the flavor
    try:
        importlib.import_module("endf_parserpy.cpp_parsers._flavors")
    except ImportError:
        return False
    return True


CPP = pytest.param(
    EndfParserCpp,
    marks=pytest.mark.skipif(not _cpp_available(), reason="C++ module is not built"),
    id="cpp",
)
PARSERS = [pytest.param(EndfParserPy, id="py"), CPP]


# --- dividing a GENDF tape into sections ---------------------------------


def _numbers(line):
    return int(line[66:70]), int(line[70:72]), int(line[72:75])


def _split(path):
    """The TPID line and the materials, each a list of (mf, mt, lines)."""
    lines = Path(path).read_text().split("\n")
    if lines[-1] == "":
        lines.pop()
    materials = []
    material = section = None
    for line in lines[1:]:
        mat, mf, mt = _numbers(line)
        if mat > 0 and mf > 0 and mt > 0:
            if material is None:
                material = []
                materials.append((mat, material))
            if section is None or section[:2] != (mf, mt):
                section = (mf, mt, [])
                material.append(section)
            section[2].append(line)
        else:
            section = None
            if mat <= 0:
                material = None
    return lines[0], materials


def _ctrl(mat, mf, mt, ns):
    return " " * 66 + f"{mat:4d}{mf:2d}{mt:3d}{ns:5d}"


GENDF = get_tape_structure("gendf")


def _tape(tpid, mat, mf, mt, lines):
    # the framing of a GENDF tape: no SEND record after MF1/MT451, a FEND
    # record after MF1 only
    send = [_ctrl(mat, mf, 0, 99999)] if GENDF.send(mf, mt) else []
    fend = [_ctrl(mat, 0, 0, 0)] if GENDF.fend(mf) else []
    return "\n".join(
        [tpid] + lines + send + fend + [_ctrl(0, 0, 0, 0), _ctrl(-1, 0, 0, 0)]
    )


def _only_section(material, mf, mt):
    # the section of a material of the tape head and one section, in
    # either form
    if isinstance(material, list):
        assert len(material) == 2
        return material[1]
    return material[mf][mt]


def _sections(filename):
    tpid, materials = _split(TESTDATA / filename)
    for position, (mat, sections) in enumerate(materials):
        for mf, mt, lines in sections:
            yield tpid, position, mat, mf, mt, lines


def _section(filename, mf, mt, position=0, occurrence=0, parser=None, **opts):
    """Parse one section of a test file."""
    found = [s for s in _sections(filename) if s[1] == position and s[3:5] == (mf, mt)]
    tpid, _, mat, mf, mt, lines = found[occurrence]
    if parser is None:
        parser = EndfParserPy(endf_format="gendf", **opts)
    return _only_section(parser.parse(_tape(tpid, mat, mf, mt, lines)), mf, mt)


def _written_lines(text, mf, mt):
    lines = text if isinstance(text, list) else text.split("\n")
    return [line for line in lines if line[70:75] == f"{mf:2d}{mt:3d}"]


# --- the flavor --------------------------------------------------------------


def test_flavor_is_listed():
    assert "gendf" in list_endf_flavors()
    assert "gendf" in list_endf_build_targets()
    assert resolve_endf_flavor("gendf") == "gendf"
    # no layout version yet
    assert get_layout_version("gendf") is None
    assert not [f for f in list_endf_flavors() if f.startswith("gendf@")]


def test_recipes_of_all_mf():
    recipes = get_recipe_dict("gendf")
    assert set(recipes) == {0, 1, 3, 5, 6, 12, 13, 16, 21, 22, 23, 24, 25, 26}
    assert set(recipes[1]) == {451}
    for mf in (3, 5, 6, 12, 13, 16, 21, 22, 24, 25):
        assert "IZAM, NL, NZ, LRFLAG, NGI] HEAD" in recipes[mf]
    for mf in (23, 26):
        assert "AWR, NL, NZ, LRFLAG, NGI] HEAD" in recipes[mf]


# --- round trip ----------------------------------------------------------------


@pytest.mark.parametrize("cls", PARSERS)
@pytest.mark.parametrize("filename", FILES)
def test_sections_round_trip(filename, cls):
    # every section written back gives the same data lines, all 80
    # columns, in the same order
    parser = cls(endf_format="gendf", preserve_value_strings=True)
    count = 0
    for tpid, _, mat, mf, mt, lines in _sections(filename):
        written = parser.write(parser.parse(_tape(tpid, mat, mf, mt, lines)))
        assert _written_lines(written, mf, mt) == lines, f"MF{mf}/MT{mt}"
        count += 1
    assert count > 0


@pytest.mark.parametrize("cls", PARSERS)
def test_writing_from_values(cls):
    # without preserve_value_strings, prefer_noexp and standard_form_on_tie
    # give the number forms of GROUPR for the sections of this file,
    # including its nine-digit form (but not where it ends in zeros)
    parser = cls(endf_format="gendf", prefer_noexp=True, standard_form_on_tie=True)
    for tpid, _, mat, mf, mt, lines in _sections("u238_special_records.gendf"):
        written = parser.write(parser.parse(_tape(tpid, mat, mf, mt, lines)))
        assert _written_lines(written, mf, mt) == lines, f"MF{mf}/MT{mt}"


@pytest.mark.skipif(not _cpp_available(), reason="C++ module is not built")
@pytest.mark.parametrize("mode", ["dict", "list", "numpy"])
@pytest.mark.parametrize("filename", FILES)
def test_parsers_give_equal_dicts(filename, mode):
    if mode == "numpy":
        np = pytest.importorskip("numpy")
    py = EndfParserPy(endf_format="gendf", array_type=mode)
    cpp = EndfParserCpp(endf_format="gendf", array_type=mode)

    def equal(a, b):
        if mode == "numpy" and (isinstance(a, np.ndarray) or isinstance(b, np.ndarray)):
            return (
                isinstance(a, np.ndarray)
                and isinstance(b, np.ndarray)
                and a.dtype == b.dtype
                and np.array_equal(a, b)
            )
        if isinstance(a, dict):
            return (
                isinstance(b, dict)
                and list(a) == list(b)
                and all(equal(a[k], b[k]) for k in a)
            )
        if isinstance(a, (list, tuple)):
            return (
                isinstance(b, (list, tuple))
                and len(a) == len(b)
                and all(equal(x, y) for x, y in zip(a, b))
            )
        return type(a) is type(b) and a == b

    for tpid, _, mat, mf, mt, lines in _sections(filename):
        tape = _tape(tpid, mat, mf, mt, lines)
        assert equal(py.parse(tape), cpp.parse(tape)), f"MF{mf}/MT{mt}"


# --- layout and values -----------------------------------------------------------


def test_mf1_mt451():
    sec = _section("u238_special_records.gendf", 1, 451)
    assert sec["ZA"] == 92238.0
    assert sec["AWR"] == 236.0058
    assert (sec["NZ"], sec["NTW"], sec["NGN"], sec["NGG"]) == (2, 1, 30, 12)
    assert sec["TEMPIN"] == 293.6
    assert sec["TITLE"] == {1: 0.0}
    assert sec["SIGZ"] == {1: 1.0e10, 2: 100.0}
    assert len(sec["EGN"]) == 31 and sec["EGN"][1] == 1.39e-4
    assert sec["EGN"][31] == 1.7e7
    assert len(sec["EGG"]) == 13 and sec["EGG"][13] == 2.0e7


def test_mf1_mt451_gaminr():
    sec = _section("h1_gaminr.gam", 1, 451)
    # GAMINR: the photon groups in NGN, no temperature, sigma zero 1e12
    assert (sec["NZ"], sec["NGN"], sec["NGG"], sec["TEMPIN"]) == (1, 42, 0, 0.0)
    assert sec["SIGZ"] == {1: 1.0e12}
    assert sec["EGG"] == {1: 0.0}


def test_mf3_order_of_values():
    # MF3/MT1 with NL=2 and NZ=2: ANS[i, it, iz, il], flux at it=1
    sec = _section("u238_special_records.gendf", 3, 1)
    assert (sec["NL"], sec["NZ"], sec["NGI"], sec["IZAM"]) == (2, 2, 30, 0.0)
    assert sec["TEMPIN"] == 293.6
    assert sec["IG"] == {1: 1, 2: 2, 3: 30}
    assert sec["NG2"][1] == 2 and sec["IG2LO"][1] == 1
    ans = sec["ANS"][1]
    # flux (iz, il): listing "flux 0 6.99727+0 5.87843+0", "flux 1 ... 4.96763+0"
    assert [[ans[1][iz][il] for il in (1, 2)] for iz in (1, 2)] == [
        [6.997274, 6.997274],
        [5.878425, 4.967634],
    ]
    # total cross section: "1 0 1.98023+1 1.90331+1", "1 1 1.98023+1 1.83345+1"
    assert [[ans[2][iz][il] for il in (1, 2)] for iz in (1, 2)] == [
        [19.80226, 19.80226],
        [19.03314, 18.33451],
    ]


def test_mf3_ratio_quantity():
    # MT452: flux, nubar, fission cross section (NG2=3)
    sec = _section("u238_special_records.gendf", 3, 452)
    assert sec["NG2"][1] == 3
    ans = sec["ANS"][1]
    assert (ans[1][1][1], ans[2][1][1], ans[3][1][1]) == (
        6.997274,
        2.492088,
        6.277215e-5,
    )


def test_mf6_matrix_row():
    sec = _section("u238_special_records.gendf", 6, 2)
    i = 2  # the record of group 2
    assert sec["IG"][i] == 2 and sec["IG2LO"][i] == 1 and sec["NG2"][i] == 3
    ans = sec["ANS"][i]
    # 2 -> 1 and 2 -> 2, P0 and P1, both sigma zeros
    assert [[ans[2][iz][il] for il in (1, 2)] for iz in (1, 2)] == [
        [7.813896e-2, -2.589885e-2],
        [7.797056e-2, -2.578802e-2],
    ]
    assert [[ans[3][iz][il] for il in (1, 2)] for iz in (1, 2)] == [
        [9.170106, 5.202588e-2],
        [9.170264, 5.191498e-2],
    ]


def test_mf6_mt18_from_mf6():
    sec = _section("u238_special_records.gendf", 6, 18)
    assert (sec["NL"], sec["NZ"]) == (1, 1)
    assert sec["IG"][1] == 1 and sec["IG2LO"][1] == 6 and sec["NG2"][1] == 26
    ans = sec["ANS"][1]
    assert ans[2][1][1] == 5.28936e-12
    assert ans[26][1][1] == 2.294348e-9


def test_spectrum_and_production_records():
    # MF16/MT18: the IG=0 record holds the spectrum (no flux), the
    # records with IG2LO=0 the flux and the production cross section
    sec = _section("u238_special_records.gendf", 16, 18)
    assert sec["IG"] == {1: 0, 2: 1, 3: 2, 4: 30}
    assert sec["IG2LO"][1] == 1 and sec["NG2"][1] == 10
    spec = [sec["ANS"][1][it][1][1] for it in range(1, 11)]
    assert spec[:3] == [6.50196e-2, 3.095585e-1, 3.26215e-1]
    assert sec["IG2LO"][2] == 0 and sec["NG2"][2] == 2
    assert (sec["ANS"][2][1][1][1], sec["ANS"][2][2][1][1]) == (
        6.99727406,
        4.728374e-4,
    )


def test_mf6_mt18_from_mf5():
    # fission spectrum in MF5 of the evaluation: IG=0 record and
    # production records in MF6/MT18, replicated for both sigma zeros
    sec = _section("u233_mf5_spectra.gendf", 6, 18)
    assert (sec["NL"], sec["NZ"]) == (1, 2)
    assert sec["IG"] == {1: 0, 2: 1, 3: 10, 4: 30}
    assert (sec["NG2"][1], sec["IG2LO"][1]) == (30, 1)
    assert sec["ANS"][1][1][1][1] == sec["ANS"][1][1][2][1] == 2.58651e-11
    assert sec["IG2LO"][2] == 0
    assert sec["ANS"][2][2][1][1] == 4964.35806  # listing "1 prod 4.96436+3"
    assert sec["IG2LO"][3] == 1 and sec["NG2"][3] == 31


def test_mf5():
    chi = _section("u233_mf5_spectra.gendf", 5, 18)
    assert chi["IG"] == {1: 30} and chi["NG2"][1] == 30 and chi["IG2LO"][1] == 1
    assert chi["ANS"][1][1][1][1] == 2.58651e-11
    delayed = _section("u233_mf5_spectra.gendf", 5, 455)
    # NL = number of families; it=1 holds the decay constants
    assert delayed["NL"] == 6 and delayed["NG2"][1] == 24
    assert [delayed["ANS"][1][1][1][il] for il in range(1, 7)] == [
        1.29e-2,
        3.47e-2,
        1.193e-1,
        2.862e-1,
        7.877e-1,
        2.4417,
    ]
    assert delayed["ANS"][1][2][1][1] == 2.56662e-10


def test_gaminr_sections():
    sec = _section("h1_gaminr.gam", 26, 504)
    assert sec["AWR"] == 0.999242
    assert (sec["NL"], sec["NZ"], sec["LRFLAG"], sec["NGI"]) == (7, 1, 0, 42)
    assert sec["TEMPIN"] == 0.0
    assert "IZAM" not in sec
    sec = _section("h1_gaminr.gam", 23, 501)
    assert (sec["NL"], sec["NGI"]) == (1, 42)


def test_groupr_mf26_has_awr_key():
    # GROUPR's residual nucleus production matrices are MF26 as well
    sec = _section("o16_photon_particle_production.gendf", 26, 2)
    assert sec["AWR"] == 0.0 and sec["NL"] == 2


def test_lrflag():
    for mf in (3, 6):
        sec = _section("li7_lrflag.gendf", mf, 52)
        assert sec["LRFLAG"] == 33
    assert _section("li7_lrflag.gendf", 3, 52)["ANS"][1][2][1][1] == 1.412858e-3


def test_thermal_upscatter():
    sec = _section("h1_thermal_freegas.gendf", 6, 221)
    # group 2 scatters into group 1
    assert sec["IG"][2] == 2 and sec["IG2LO"][2] == 1
    assert sec["ANS"][2][2][1][1] == 11.7931


def test_nuclide_production_has_three_sections_with_same_mt():
    zam = [
        _section("am241_nuclide_production.gendf", 3, 102, occurrence=k)["IZAM"]
        for k in range(3)
    ]
    assert zam == [0.0, 952420.0, 952422.0]


@pytest.mark.parametrize("mode", ["list", "numpy"])
def test_array_modes(mode):
    if mode == "numpy":
        np = pytest.importorskip("numpy")
    sec = _section("u238_special_records.gendf", 6, 2, array_type=mode)
    assert list(sec["IG"]) == [1, 2, 30]
    assert len(sec["ANS"]) == 3
    if mode == "numpy":
        assert isinstance(sec["ANS"][1], np.ndarray)
        # (NG2, NZ, NL), the transpose of GROUPR's ans(nl, nz, ng2)
        assert sec["ANS"][1].shape == (3, 2, 2)
        assert sec["ANS"][1][2, 1, 0] == 9.170264
    else:
        assert sec["ANS"][1][2][1][0] == 9.170264


# --- errors ------------------------------------------------------------------------


def _he4_mf3_mt1():
    found = [
        s for s in _sections("he4_two_temperatures.gendf") if s[1:5] == (0, 228, 3, 1)
    ]
    return found[0]


def _damaged(change):
    tpid, _, mat, mf, mt, lines = _he4_mf3_mt1()
    return _tape(tpid, mat, mf, mt, change(list(lines)))


def _other_temperature(lines):
    lines[3] = " 2.937000+2" + lines[3][11:]
    return lines


def _inconsistent_nw(lines):
    lines[1] = lines[1][:44] + "          3" + lines[1][55:]
    return lines


def _missing_last_group(lines):
    return lines[:-2]


def _truncated_body(lines):
    return lines[:-1]


@pytest.mark.parametrize("cls", PARSERS)
@pytest.mark.parametrize(
    "change, error",
    [
        (_other_temperature, NumberMismatchError),
        (_inconsistent_nw, NumberMismatchError),
        (_missing_last_group, NumberMismatchError),
        (_truncated_body, UnexpectedEndOfInputError),
    ],
    ids=["temperature", "nw", "last-group", "truncated"],
)
def test_damaged_sections_raise(cls, change, error):
    parser = cls(endf_format="gendf")
    if cls is EndfParserCpp:
        # the C++ parser raises its own exception types
        error = Exception
    with pytest.raises(error):
        parser.parse(_damaged(change))


# --- whole tapes ---------------------------------------------------------------------


SINGLE_MATERIAL = sorted(
    p.name for p in TESTDATA.iterdir() if p.name != "he4_two_temperatures.gendf"
)


@pytest.mark.parametrize("cls", PARSERS)
@pytest.mark.parametrize("filename", SINGLE_MATERIAL)
def test_whole_tape_round_trip(filename, cls):
    # a material is the list of its sections in the order of the tape;
    # written back, the tape is the same byte for byte (the numbers as
    # read with preserve_value_strings, the end records generated)
    path = TESTDATA / filename
    parser = cls(endf_format="gendf", preserve_value_strings=True)
    material = parser.parsefile(str(path))
    assert isinstance(material, list)
    text = path.read_text(encoding="latin-1")
    assert "\n".join(parser.write(material)) + "\n" == text


@pytest.mark.parametrize("cls", PARSERS)
@pytest.mark.parametrize("filename", sorted(p.name for p in TESTDATA.iterdir()))
def test_tape_round_trip(filename, cls):
    path = TESTDATA / filename
    text = path.read_text(encoding="latin-1")
    parser = cls(endf_format="gendf", preserve_value_strings=True)
    materials = parse_tape_file(path, parser=parser, on_error="raise")
    assert "".join(write_tape(materials, parser=parser)) == text
    with EndfFile(path, parser=parser) as ef:
        assert ef.to_string() == text


@pytest.mark.parametrize("cls", PARSERS)
def test_nuclide_production_in_the_list(cls):
    parser = cls(endf_format="gendf")
    material = parser.parsefile(str(TESTDATA / "am241_nuclide_production.gendf"))
    labels = [(s["MF"], s["MT"]) for s in material[1:]]
    assert labels == [(1, 451), (3, 102), (3, 102), (3, 102)]
    assert [s["IZAM"] for s in material[2:]] == [0.0, 952420.0, 952422.0]
    # the nested form cannot hold the three sections
    with pytest.raises(TapeStructureError, match="3 sections MF=3/MT=102"):
        cls(endf_format="gendf", material_form="dict").parsefile(
            str(TESTDATA / "am241_nuclide_production.gendf")
        )


@pytest.mark.parametrize("cls", PARSERS)
def test_nested_form_on_request(cls):
    # a material without repeated sections; written back from the nested
    # form, its sections are in ascending order
    path = str(TESTDATA / "u238_special_records.gendf")
    as_list = cls(endf_format="gendf").parsefile(path)
    as_dict = cls(endf_format="gendf", material_form="dict").parsefile(path)
    assert to_dict_form(as_list) == as_dict


def test_endf_file_keeps_temperatures_apart():
    parser = EndfParserPy(endf_format="gendf")
    with EndfFile(TESTDATA / "he4_two_temperatures.gendf", parser=parser) as ef:
        assert len(ef) == 2
        with pytest.raises(AmbiguousMaterialError):
            ef.by_mat(228)
        temps = [ef[k][1, 451]["TEMPIN"] for k in range(2)]
        assert temps == [293.6, 600.0]
        assert list(ef[0].sections()) == [(1, 451), (3, 1), (3, 251), (6, 2)]
        assert list(ef[1].sections()) == [(1, 451), (3, 1), (6, 2)]
        assert ef.by_mat(228, occurrence=1)[3, 1]["TEMPIN"] == 600.0


def test_endf_file_keeps_the_order_and_repeated_sections():
    parser = EndfParserPy(endf_format="gendf")
    path = TESTDATA / "am241_nuclide_production.gendf"
    with EndfFile(path, parser=parser) as ef:
        assert list(ef[0].sections()) == [(1, 451), (3, 102), (3, 102), (3, 102)]
        with pytest.raises(RepeatedSectionError, match="occurs 3 times"):
            ef[0][3, 102]
        assert ef[0][1, 451]["NZ"] == 1
    with EndfFile(TESTDATA / "h1_gaminr.gam", parser=parser) as ef:
        mfs = [mf for mf, _ in ef[0].sections()]
        assert mfs == [1, 23, 26, 23, 26, 23]


def test_parse_tape_of_two_temperatures():
    # parsefile reads one material; a tape of several, with parse_tape
    materials = parse_tape_file(
        TESTDATA / "he4_two_temperatures.gendf",
        parser=EndfParserPy(endf_format="gendf"),
        on_error="raise",
    )
    assert [m[1]["TEMPIN"] for m in materials] == [293.6, 600.0]
    with pytest.raises(UnexpectedControlRecordError, match="parse reads one material"):
        EndfParserPy(endf_format="gendf").parsefile(
            str(TESTDATA / "he4_two_temperatures.gendf")
        )


@pytest.mark.parametrize("cls", PARSERS)
def test_material_from_scratch(cls):
    """A small GENDF material built as a list in Python and written: the end
    records are generated by the tape structure of the flavor."""
    mat = 125
    tpid = [" gendf from scratch".ljust(66) + "   1 0  0    0\n"]
    mf1 = {
        "MAT": mat,
        "MF": 1,
        "MT": 451,
        "ZA": 1001.0,
        "AWR": 0.99917,
        "NZ": 1,
        "NTW": 1,
        "TEMPIN": 293.6,
        "NGN": 2,
        "NGG": 0,
        "TITLE": {1: 0.0},
        "SIGZ": {1: 1e10},
        "EGN": {1: 1e-5, 2: 1.0, 3: 2e7},
        "EGG": {1: 0.0},
    }
    mf3 = {
        "MAT": mat,
        "MF": 3,
        "MT": 1,
        "ZA": 1001.0,
        "IZAM": 0.0,
        "NL": 1,
        "NZ": 1,
        "LRFLAG": 0,
        "NGI": 2,
        "TEMPIN": 293.6,
        "IG": {1: 2},
        "NG2": {1: 2},
        "IG2LO": {1: 0},
        "ANS": {1: {1: {1: {1: 1.5}}, 2: {1: {1: 20.4}}}},
    }
    parser = cls(endf_format="gendf", include_linenum=False)
    lines = parser.write([tpid, mf1, mf3])
    assert [line[66:75] for line in lines] == [
        "   1 0  0",
        " 125 1451",
        " 125 1451",
        " 125 1451",
        " 125 0  0",  # FEND after MF1, no SEND before it
        " 125 3  1",
        " 125 3  1",
        " 125 3  1",
        " 125 3  0",  # SEND, no FEND
        "   0 0  0",
        "  -1 0  0",
    ]
    # the end records are blank, as NJOY writes them
    assert lines[4][:66].strip() == "" and lines[8][:66].strip() == ""
    material = parser.parse(lines)
    assert [section_label(s) for s in material] == [
        (1, 0, 0),
        (125, 1, 451),
        (125, 3, 1),
    ]
    assert material[2]["ANS"][1][2][1][1] == 20.4


def _cli(*argv):
    return subprocess.run(
        [sys.executable, "-m", "endf_parserpy.cli.cmd", *argv],
        capture_output=True,
        text=True,
    )


def test_cli_accepts_the_flavor():
    path = str(TESTDATA / "he4_two_temperatures.gendf")
    result = _cli("list-materials", "--no-cpp", "--endf_format", "gendf", path)
    assert result.returncode == 0, result.stderr
    assert "2 materials" in result.stdout
    # validate checks the framing by the tape structure of the flavor
    for argv in (["--no-cpp"], []):
        for name in ("he4_two_temperatures.gendf", "am241_nuclide_production.gendf"):
            path = str(TESTDATA / name)
            result = _cli("validate", *argv, "--endf_format", "gendf", path)
            assert result.returncode == 0, result.stdout + result.stderr


def test_listing_and_json_of_the_list_form(tmp_path):
    from endf_parserpy import list_parsed_sections, list_unparsed_sections

    path = TESTDATA / "am241_nuclide_production.gendf"
    material = EndfParserPy(endf_format="gendf").parsefile(str(path), exclude=[1])
    assert list_parsed_sections(material) == ((0, 0), (3, 102), (3, 102), (3, 102))
    assert list_unparsed_sections(material) == ((1, 451),)
    # endf-cli convert: a tape of materials in the list form is a JSON array
    # of arrays, and converted back a tape with the same framing and values
    out = tmp_path / "tape.json"
    back = tmp_path / "tape.gendf"
    argv = ("--no-cpp", "--endf_format", "gendf")
    result = _cli("convert", *argv, "--to", "json", str(path), str(out))
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text())[0][1]["MT"] == 451
    result = _cli("convert", *argv, "--to", "endf", str(out), str(back))
    assert result.returncode == 0, result.stderr

    def ctrl(p):
        return [line[66:75] for line in p.read_text(encoding="latin-1").split("\n")]

    assert ctrl(back) == ctrl(path)
    parser = EndfParserPy(endf_format="gendf")
    assert parser.parsefile(str(back)) == parser.parsefile(str(path))
