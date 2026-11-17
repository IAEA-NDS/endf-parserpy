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

"""The functions of the C++ module with a tape structure in their options.

The functions of an entry of ``endf_parserpy.cpp_parsers._flavors``
return a material as the list of its sections and write a material in
either form; the tape structure is passed with the options as
``TapeStructure.cpp_options()``. The inputs are those of
``test_tape_structure_py.py`` (the recipes of ``endf6``), and the results
are compared with those of ``EndfParserPy``.
"""

import pytest

from endf_parserpy import EndfParserPy, TapeStructure, to_dict_form
from test_tape_structure_py import FREE, PU, _text

flavors = pytest.importorskip("endf_parserpy.cpp_parsers._flavors")
entry = flavors.endf6


def _opts(spec, **kwargs):
    return dict(kwargs, tape_structure=TapeStructure.from_spec(spec).cpp_options())


def test_list_of_sections():
    material = entry.parse_endf_file(str(PU))
    assert isinstance(material, list)
    assert to_dict_form(material) == EndfParserPy().parsefile(str(PU))
    # writing accepts both forms with the same output
    assert entry.write_endf(material) == entry.write_endf(to_dict_form(material))


@pytest.mark.parametrize("exclude", [None, [1, 8]])
def test_free_order_and_repeats(exclude):
    text = _text("tpid", "457", "452", "451", "457", "mend", "tend")
    material = entry.parse_endf(text, exclude, None, _opts(FREE))
    py = EndfParserPy(tape_structure=FREE, material_form="list")
    assert material == py.parse(text, exclude=exclude)
    written = entry.write_endf(material, None, None, _opts(FREE))
    assert written.split("\n") == py.write(material)


def test_repeat_not_allowed():
    text = _text("tpid", "457", "452", "451", "457", "mend", "tend")
    with pytest.raises(RuntimeError) as exc:
        entry.parse_endf(text, None, None, _opts(dict(FREE, repeat=False)))
    assert str(exc.value).startswith(
        "section MF=8/MT=457 of MAT 3564 occurs a second time in the material, "
        "which the tape structure does not allow\nLine "
    )


def test_fend_not_expected():
    text = _text("tpid", "451", "452", "fend1", "457", "mend", "tend")
    with pytest.raises(RuntimeError) as exc:
        entry.parse_endf(text, None, None, _opts(FREE))
    assert str(exc.value).startswith(
        "Unexpected FEND record after MF=1: the tape structure has no FEND "
        "record after the sections of this MF\nLine "
    )


def test_blank_end_records():
    material = entry.parse_endf_file(str(PU))
    written = entry.write_endf(
        material, None, None, _opts({"end_record_fill": "blank"})
    )
    py = EndfParserPy(tape_structure={"end_record_fill": "blank"}).write(material)
    assert written.split("\n") == py


def test_write_of_several_materials(tmp_path):
    from endf_parserpy import EndfParserCpp
    from test_tape_structure_py import check_write_of_several_materials

    check_write_of_several_materials(EndfParserCpp, tmp_path)
