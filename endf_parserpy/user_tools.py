############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

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
        locations = ['/'.join(str(s) for s in loc) for loc in locations]
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
    unparsed = []
    for mf, mfsec in dic.items():
        for mt, mtsec in mfsec.items():
            if isinstance(mtsec, list):
                unparsed.append((mf,mt))
    return tuple(unparsed)


def list_parsed_sections(dic):
    parsed = []
    for mf, mfsec in dic.items():
        for mt, mtsec in mfsec.items():
            if isinstance(mtsec, dict):
                parsed.append((mf, mt))
    return tuple(parsed)


def sanitize_fieldname_types(dic):
    if not isinstance(dic, dict):
        raise TypeError('please provide dictionary')
    keys = tuple(dic.keys())
    for key in keys:
        try:
            intkey = int(key)
        except Exception:
            intkey = None
        if intkey is not None:
            if intkey in dic:
                raise IndexError('integer version of key already exists, something wrong')
            cont = dic[key]
            dic[intkey] = cont
            del dic[key]
    # recurse into sub-dictionaries
    keys = tuple(dic.keys())
    for key in keys:
        if isinstance(dic[key], dict):
            sanitize_fieldname_types(dic[key])


def show_content(endf_dic, maxlevel=0, prefix='/'):
    maxlen = max(len(prefix+str(s)) for s in endf_dic.keys())
    for k, v in endf_dic.items():
        if isinstance(v, dict):
            if maxlevel > 0:
                show_content(v, maxlevel-1,
                             prefix=prefix+str(k)+'/')
            else:
                fp = (prefix + str(k) + ':').ljust(maxlen+2)
                print(fp + 'subsection or array')
        else:
            fp = (prefix + str(k) + ':').ljust(maxlen+2)
            print(fp + str(v))
