############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2026/11/21
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import Mapping
from endf_parserpy.interpreter.endf_utils import split_sections
import re


__all__ = [
    "set_library",
    "get_description",
    "set_description",
    "insert_description",
    "update_directory",
]


def set_library(endf_dic, libtype):
    mt451 = endf_dic[1][451]
    if libtype == "ENDF/B-VII.0":
        mt451["NLIB"] = 0
        mt451["NVER"] = 7
        mt451["LREL"] = 0
        txt = "ENDF/B-VII.0"
    elif libtype == "ENDF/B-VII.1":
        mt451["NLIB"] = 0
        mt451["NVER"] = 7
        mt451["LREL"] = 1
        txt = "ENDF/B-VII.1"
    elif libtype == "ENDF/B-VIII.0":
        mt451["NLIB"] = 0
        mt451["NVER"] = 8
        mt451["LREL"] = 0
        txt = "ENDF/B-VIII.0"
    elif libtype == "FENDL-3.2":
        mt451["NLIB"] = 33
        mt451["NVER"] = 3
        mt451["LREL"] = 2
        txt = "FENDL-3.2"
    else:
        raise TypeError("Unknown library type")
    # update the human readable library specification
    if "DESCRIPTION" not in mt451:
        raise ValueError("No description in MF1/MT451 found")
    descr = mt451["DESCRIPTION"]
    if 3 not in descr:
        raise IndexError("No third line found in description")
    if not re.match("---- *[A-Z][^ ]+", descr[3]):
        raise ValueError("Signature of line three is wrong")
    new_descr_line = ("----" + txt).ljust(22) + descr[3][22:]
    descr[3] = new_descr_line


def _array_values(arr):
    # the elements of an array in the order of their indices: a dict
    # (array_type="dict"), a list ("list") or a numpy array ("numpy")
    if isinstance(arr, Mapping):
        return [arr[k] for k in sorted(arr)]
    return list(arr)


def _array_form(mt451):
    # the form of the arrays of MF1/MT451: "dict", "list" or "numpy"
    # (the strings of DESCRIPTION are a list also with array_type="numpy")
    for name in ("MFx", "DESCRIPTION"):
        arr = mt451.get(name)
        if arr is None:
            continue
        if isinstance(arr, Mapping):
            return "dict"
        if hasattr(arr, "__array_interface__"):
            return "numpy"
        return "list"
    return "dict"


def _new_array(values, form, like=None):
    # an array with the given elements (counted from 1) in the given form
    if form == "dict":
        return {i: v for i, v in enumerate(values, start=1)}
    if form == "numpy" and like is not None:
        import numpy as np

        return np.array(values, dtype=like.dtype)
    return list(values)


def get_description(endf_dic):
    """Retrieve the description from MF1/MT451 section.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data, parsed with any ``array_type``
        (``"dict"``, ``"list"`` or ``"numpy"``).

    Returns
    -------
    str
        String with the description
        extracted from MF1/MT451
    """
    descr = endf_dic[1][451]["DESCRIPTION"]
    return "\n".join(_array_values(descr))


def set_description(endf_dic, text):
    """Set the description in the MF1/MT451 section.

    Updates the ``DESCRIPTION`` variable in
    ``endf_dic[1][451]`` and adjusts the corresponding
    counter variable ``NWD``.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data, parsed with any ``array_type``
        (``"dict"``, ``"list"`` or ``"numpy"``). The new
        ``DESCRIPTION`` has the form of the arrays in MF1/MT451:
        a :class:`dict` with the line numbers (from 1) as keys, or
        a :class:`list` of the lines (also with ``"numpy"``, whose
        description is a :class:`list` of strings).
    text : str
        String with description. Lines with fewer than 66
        characters are padded with blanks to 66 characters.

    Raises
    ------
    ValueError
        If a line has more than 66 characters, the width of a
        TEXT record, naming the first such line (counted from 1)
        and its length. The description is then not changed.
    """
    lines = text.splitlines()
    for number, line in enumerate(lines, start=1):
        if len(line) > 66:
            raise ValueError(
                f"line {number} of the description has {len(line)} characters, "
                "but a line of the description (a TEXT record) can have at "
                "most 66 characters"
            )
    mt451 = endf_dic[1][451]
    form = "dict" if _array_form(mt451) == "dict" else "list"
    mt451["NWD"] = len(lines) + 5
    mt451["DESCRIPTION"] = _new_array([line.ljust(66) for line in lines], form)


def insert_description(endf_dic, text, after_line=0):
    """Insert text in the description in MF1/MT451.

    Insert the text provided into the `DESCRIPTION`
    in `endf_dic[1][451]` and adjusts the corresponding
    counter variable `NWD`.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data, parsed with any ``array_type``
        (see :func:`set_description`).
    text : str
        String with text to be inserted. Lines with more than 66
        characters raise a :exc:`ValueError` (see
        :func:`set_description`), whose line number counts the
        lines of the whole new description.
    after_line : int
        After which line ``text`` should be inserted.
        ``after_line=0`` inserted the text provided
        at the very beginning.
    """
    descr = get_description(endf_dic)
    lines = descr.splitlines()
    newlines = lines[:after_line] + text.splitlines()
    if after_line < len(lines):
        newlines += lines[after_line:]
    newdescr = "\n".join(newlines)
    set_description(endf_dic, newdescr)


def update_directory(endf_dic, parser=None, lines=None, read_opts=None):
    """Update the ENDF directory in MF1/MT451.

    Parameters
    ----------
    endf_dic : dict
        Dictionary of appropriate structure with ENDF-6 data, parsed
        with any ``array_type`` (``"dict"``, ``"list"`` or ``"numpy"``).
        The arrays of the directory (``MFx``, ``MTx``, ``NCx``, ``MOD``)
        are replaced by arrays of the same form: :class:`dict` objects,
        :class:`list` objects or numpy arrays. Without a directory
        before, its form is that of ``DESCRIPTION``.
    parser : EndfParserBase
        An :class:`~endf_parserpy.EndfParserBase` instance, used to
        write ``endf_dic`` to determine the lengths of the sections.
        It is required unless ``lines`` is provided, and must
        have been created with the ``array_type`` of ``endf_dic``.
    lines: list[str]
        A list of strings with the ENDF-6 formatted data
        corresponding to the data in ``endf_dic``.
        If this argument is provided, the ``parser``
        argument will be ignored.
    read_opts : dict
        A dictionary with reading options provided as ``read_opts`` argument
        overrides the reading options of the :class:`~endf_parserpy.EndfParserBase` instance.
    """
    if read_opts is None:
        read_opts = {}
    active_read_opts = {}
    if not lines:
        if not parser:
            raise TypeError("provide either `parser` or `lines` argument")
        lines = parser.write(endf_dic)
        active_read_opts.update(parser.read_opts)
    active_read_opts.update(read_opts)
    active_read_opts["ignore_missing_tpid"] = True
    # determine the lengths of the sections
    # the checks for mf=0 and mt=0 are here
    # to not consider the tape head as a section
    mfdic = split_sections(lines, read_opts=active_read_opts)
    countdic = {}
    numsecs = 0
    for mf, mfsec in mfdic.items():
        if mf == 0:
            continue
        countdic.setdefault(mf, {})
        for mt, mtsec in mfsec.items():
            if mt == 0:
                continue
            numsecs += 1
            countdic[mf][mt] = len(mtsec)
    # record the length of MF1/MT451 itself
    mf1mt451_len = 4 + endf_dic[1][451]["NWD"] + numsecs
    countdic[1][451] = mf1mt451_len
    # build up a MOD dic to retrieve the
    # previous value of MOD (modified version number)
    moddic = {}
    mt451 = endf_dic[1][451]
    form = _array_form(mt451)
    old_mfx = mt451.get("MFx")
    if old_mfx is not None:
        for curmf, curmt, curmod in zip(
            _array_values(old_mfx),
            _array_values(mt451["MTx"]),
            _array_values(mt451["MOD"]),
        ):
            moddic[(int(curmf), int(curmt))] = curmod
    # construct the arrays
    MFx = []
    MTx = []
    NCx = []
    MOD = []
    for mf, mfsec in countdic.items():
        for mt, count in mfsec.items():
            MFx.append(mf)
            MTx.append(mt)
            NCx.append(count)
            MOD.append(moddic.get((mf, mt), 0))
    # update MT451, with arrays of the form of the existing ones
    like = old_mfx if form == "numpy" else None
    mt451["MFx"] = _new_array(MFx, form, like)
    mt451["MTx"] = _new_array(MTx, form, like)
    mt451["NCx"] = _new_array(NCx, form, like)
    mt451["MOD"] = _new_array(MOD, form, like)
    # finally, update the counter NXC
    mt451["NXC"] = numsecs
