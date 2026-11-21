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


from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence


def locate(dic, varname, as_string=False):
    path = []
    locations = []

    def recfun(dic):
        nonlocal path
        nonlocal locations
        if varname in dic:
            path.append(varname)
            locations.append(tuple(path))
            del path[-1]
            return
        else:
            for key, item in dic.items():
                if isinstance(item, dict):
                    path.append(key)
                    recfun(item)
                    del path[-1]
        return

    recfun(dic)
    if as_string:
        locations = ["/".join(str(s) for s in loc) for loc in locations]
    return tuple(locations)


def get_endf_values(dic, locations):
    values = []
    for loc in locations:
        curdic = dic
        for locpart in loc[:-1]:
            curdic = curdic[locpart]
        values.append(curdic[loc[-1]])
    return tuple(values)


def list_unparsed_sections(dic):
    """List all MF/MT sections that are not parsed.

    Parameters
    ----------
    dic : Union[dict, list, MaterialView]
        A material in the form as returned by the
        :meth:`~endf_parserpy.EndfParserPy.parsefile` method of the :class:`~endf_parserpy.EndfParserPy` class,
        the nested dictionary (or another mapping of the same structure)
        or the list of its sections, or a material of an
        :class:`~endf_parserpy.EndfFile` (a
        :class:`~endf_parserpy.tape.MaterialView`, whose sections are
        parsed by this function if they have not been, and which has
        no tape head among its sections).

    Returns
    -------
    tuple[tuple[int,int]]
        A tuple of tuples with pairs of MF and MT numbers that were not parsed.
        For instance, if MF=1/MT=451 and MF=2/MT=151 were not parsed,
        the return value would be ``((1, 451), (2, 151))``.
        The tape head counts as a section with MF=0/MT=0: if it was
        not parsed, e.g. with ``include=[3]``, ``(0, 0)`` is listed
        as well.
    """
    unparsed = []
    for mf, mt, mtsec in _labelled_sections(dic):
        if not isinstance(mtsec, Mapping) and isinstance(mtsec, Sequence):
            unparsed.append((mf, mt))
    return tuple(unparsed)


def list_parsed_sections(dic):
    """List all MF/MT sections that were parsed.

    Parameters
    ----------
    dic : Union[dict, list, MaterialView]
        A material in the form as returned by the
        ``.parsefile()`` method of the :class:`~endf_parserpy.EndfParserPy` class,
        the nested dictionary (or another mapping of the same structure)
        or the list of its sections, or a material of an
        :class:`~endf_parserpy.EndfFile` (see :func:`list_unparsed_sections`).

    Returns
    -------
    tuple[tuple[int,int]]
        A tuple of tuples with pairs of MF and MT numbers that are available in parsed form.
        For instance, if MF=1/MT=451 and MF=2/MT=151 were parsed,
        the return value would be ``((1, 451), (2, 151))``.
    """
    parsed = []
    for mf, mt, mtsec in _labelled_sections(dic):
        if isinstance(mtsec, Mapping):
            parsed.append((mf, mt))
    return tuple(parsed)


def _labelled_sections(material):
    """Yield ``(MF, MT, section)`` of a material in the nested form or in
    the list form (in the order of the list, a label once per section),
    also of a MaterialView of an EndfFile (in the order of its sections,
    each read by its position, so also a label that occurs several
    times)."""
    if isinstance(material, list):
        from .tape_structure import section_label

        for section in material:
            _, mf, mt = section_label(section)
            yield mf, mt, section
        return
    if not isinstance(material, Mapping) and hasattr(material, "sections"):
        for k, (mf, mt) in enumerate(material.sections()):
            yield mf, mt, material[f"#{k}"]
        return
    for mf, mfsec in material.items():
        for mt, mtsec in mfsec.items():
            yield mf, mt, mtsec


def sanitize_fieldname_types(dic):
    """Sanitize the keys of a ``dict`` object with ENDF-6 data.

    The Python :class:`dict` datatype supports the use of keys of
    type :class:`int` whereas hashtable implementations in other
    language may only allow the use of strings. For example,
    the JSON format only allows strings as keys. This function
    undoes this conversion: it recursively replaces all keys of type
    :class:`str` that are the canonical text of an integer number,
    i.e. the text that :class:`str` gives for it (``"3"``, ``"-1"``),
    by this integer. Other strings, e.g. ``" 3 "``, ``"03"``, ``"+3"``
    or ``"1_0"``, are kept, and so are keys that are already of type
    :class:`int`, so that the function can be applied again to its
    result.

    The function recurses into the values of the :class:`dict` objects
    and into the elements of :class:`list` objects. A :class:`list` can
    be given as ``dic``: a material in the list form (e.g. with
    ``material_form="list"``, the form of GENDF materials), whose
    sections are sanitized one by one and whose sections of raw lines
    are kept, or a list of materials, as JSON gives for a tape with
    several materials.

    Noteworthy, this conversion is necessary before using the :meth:`~endf_parserpy.EndfParserPy.writefile`
    method of the :class:`~endf_parserpy.EndfParserPy`
    class if the dictionary with ENDF-6 data has been retrieved from a JSON file.

    Parameters
    ----------
    dic : Union[dict, list]
        A :class:`dict`-like object, or a :class:`list` of them.

    Returns
    -------
    None
        Datatypes are changed in-place in the object provided as ``dic`` argument.

    Raises
    ------
    TypeError
        If ``dic`` is neither a :class:`dict` nor a :class:`list`.
    IndexError
        If a :class:`dict` has both a key and the text of the same
        integer as keys, e.g. ``3`` and ``"3"``.
    """
    if isinstance(dic, list):
        for element in dic:
            if isinstance(element, (dict, list)):
                sanitize_fieldname_types(element)
        return
    if not isinstance(dic, dict):
        raise TypeError("please provide dictionary or list")
    items = []
    changed = False
    for key, value in dic.items():
        if type(key) is str:
            intkey = _canonical_int(key)
            if intkey is not None:
                if intkey in dic:
                    raise IndexError(
                        f"the keys {intkey!r} and {key!r} both exist, but the "
                        "string is converted to the integer"
                    )
                key = intkey
                changed = True
        items.append((key, value))
    if changed:
        # the same order of the keys
        dic.clear()
        dic.update(items)
    # recurse into sub-dictionaries and lists
    for value in dic.values():
        if isinstance(value, (dict, list)):
            sanitize_fieldname_types(value)


def _canonical_int(key):
    # the integer whose text (str) is the string key, otherwise None
    try:
        intkey = int(key)
    except ValueError:
        return None
    return intkey if str(intkey) == key else None


def show_content(endf_dic, maxlevel=0, prefix="/"):
    if isinstance(endf_dic, (int, float, str)):
        print(endf_dic)
        return
    elif isinstance(endf_dic, MutableMapping):
        keys = endf_dic.keys()
        values = endf_dic.values()
    elif isinstance(endf_dic, MutableSequence):
        keys = range(len(endf_dic))
        values = endf_dic
    else:
        raise NotImplementedError("Problem in code logic, contact developer")

    maxlen = max(len(prefix + str(s)) for s in keys)
    for k, v in zip(keys, values):
        if isinstance(v, (MutableSequence, MutableMapping)):
            if maxlevel > 0:
                show_content(v, maxlevel - 1, prefix=prefix + str(k) + "/")
            else:
                fp = (prefix + str(k) + ":").ljust(maxlen + 2)
                print(fp + "subsection or array")
        else:
            fp = (prefix + str(k) + ":").ljust(maxlen + 2)
            print(fp + str(v))
