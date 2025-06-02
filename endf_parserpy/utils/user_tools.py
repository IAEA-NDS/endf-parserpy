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


from collections.abc import MutableMapping, MutableSequence


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
    dic : dict
        A ``dict`` in the form as returned by the
        :meth:`~endf_parserpy.EndfParserPy.parsefile` method of the :class:`~endf_parserpy.EndfParserPy` class.

    Returns
    -------
    tuple[tuple[int,int]]
        A tuple of tuples with pairs of MF and MT numbers that were not parsed.
        For instance, if MF=1/MT=451 an MF=2/MT=151 were not parsed,
        the return value would be ``((1, 451), (2, 151))``.
    """
    unparsed = []
    for mf, mfsec in dic.items():
        for mt, mtsec in mfsec.items():
            if isinstance(mtsec, list):
                unparsed.append((mf, mt))
    return tuple(unparsed)


def list_parsed_sections(dic):
    """List all MF/MT sections that were parsed.

    Parameters
    ----------
    dic : dict
        A ``dict`` in the form as returned by the
        ``.parsefile()`` method of the :class:`endf_parserpy.endf_parser.EndfParserPy` class.

    Returns
    -------
    tuple[tuple[int,int]]
        A tuple of tuples with pairs of MF and MT numbers that are available in parsed form.
        For instance, if MF=1/MT=451 an MF=2/MT=151 were not parsed,
        the return value would be ``((1, 451), (2, 151))``.
    """
    parsed = []
    for mf, mfsec in dic.items():
        for mt, mtsec in mfsec.items():
            if isinstance(mtsec, dict):
                parsed.append((mf, mt))
    return tuple(parsed)


def sanitize_fieldname_types(dic):
    """Sanitize the keys of a ``dict`` object with ENDF-6 data.

    The Python :class:`dict` datatype supports the use of keys of
    type :class:`int` whereas hashtable implementations in other
    language may only allow the use of strings. For example,
    the JSON format only allows strings as keys. This function
    recursively replaces all keys containing integer numbers
    but being of type :class:`str` to type :class:`int`.

    Noteworthy, this conversion is necessary before using the :meth:`~endf_parserpy.EndfParserPy.writefile`
    method of the :class:`~endf_parserpy.EndfParserPy`
    class if the dictionary with ENDF-6 data has been retrieved from a JSON file.

    Parameters
    ----------
    dic : dict
        A :class:`dict`-like object.

    Returns
    -------
    None
        Datatypes are changed in-place in the :class:`dict`-like object provided as ``dic`` argument.
    """
    if not isinstance(dic, dict):
        raise TypeError("please provide dictionary")
    keys = tuple(dic.keys())
    for key in keys:
        try:
            intkey = int(key)
        except Exception:
            intkey = None
        if intkey is not None:
            if intkey in dic:
                raise IndexError(
                    "integer version of key already exists, something wrong"
                )
            cont = dic[key]
            dic[intkey] = cont
            del dic[key]
    # recurse into sub-dictionaries
    keys = tuple(dic.keys())
    for key in keys:
        if isinstance(dic[key], dict):
            sanitize_fieldname_types(dic[key])


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
