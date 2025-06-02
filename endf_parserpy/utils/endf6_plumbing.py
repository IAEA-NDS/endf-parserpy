############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/06/02
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################

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


def get_description(endf_dic):
    """Retrieve the description from MF1/MT451 section.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data

    Returns
    -------
    str
        String with the description
        extracted from MF1/MT451
    """
    descr_dic = endf_dic[1][451]["DESCRIPTION"]
    descr_list = []
    for k in sorted(descr_dic.keys()):
        descr_list.append(descr_dic[k])
    return "\n".join(descr_list)


def set_description(endf_dic, text):
    """Set the description in the MF1/MT451 section.

    Updates the ``DESCRIPTION`` variable in
    ``endf_dic[1][451]`` and adjusts the corresponding
    counter variable ``NWD``.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data
    text : str
        String with description.
        Lines with more than 66 characters are trimmed.
    """
    lines = text.splitlines()
    numlines = len(lines)
    endf_dic[1][451]["NWD"] = numlines + 5
    descr_dic = {}
    for k in range(1, numlines + 1):
        descr_dic[k] = lines[k - 1].ljust(66)
    endf_dic[1][451]["DESCRIPTION"] = descr_dic


def insert_description(endf_dic, text, after_line=0):
    """Insert text in the description in MF1/MT451.

    Insert the text provided into the `DESCRIPTION`
    in `endf_dic[1][451]` and adjusts the corresponding
    counter variable `NWD`.

    Parameters
    ----------
    endf_dic : dict
        Dictionary with ENDF-6 data
    text : str
        String with text to be inserted.
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
        Dictionary of appropriate structure with ENDF-6 data.
    parser : EndfParserBase
        An :class:`~endf_parserpy.EndfParserBase` instance
    lines: list[str]
        A list of strings with the ENDF-6 formatted data
        corresponding to the data in ``endf_dict``.
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
            raise TypeError("provide either`parser` or `lines` argument")
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
    ilist = mt451["MFx"].keys() if "MFx" in mt451 else tuple()
    for i in ilist:
        curmf = mt451["MFx"][i]
        curmt = mt451["MTx"][i]
        curmod = mt451["MOD"][i]
        moddic[(curmf, curmt)] = curmod
    # construct the dictionaries
    MFx = {}
    MTx = {}
    NCx = {}
    MOD = {}
    i = 0
    for mf, mfsec in countdic.items():
        for mt, count in mfsec.items():
            i += 1
            MFx[i] = mf
            MTx[i] = mt
            NCx[i] = countdic[mf][mt]
            MOD[i] = moddic.get((mf, mt), 0)
    # update MT451
    mt451["MFx"] = MFx
    mt451["MTx"] = MTx
    mt451["NCx"] = NCx
    mt451["MOD"] = MOD
    # finally, update the counter NXC
    mt451["NXC"] = numsecs
