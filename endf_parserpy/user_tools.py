############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/09/12
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
        except:
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


def path_to_list(path):
    if isinstance(path, str):
        path_parts = path.split('/')
    else:
        path_parts = [str(cur) for cur in path]
    return path_parts


def list_to_path(path):
    return '/'.join([str(x) for x in path])


def enter_section(endf_dic, path, create_missing=False):
    curdic = endf_dic
    path_parts = path_to_list(path)
    for cur in path_parts:
        if cur.strip() == '':
            continue
        curkey = int(cur) if cur.isdigit() else cur
        if curkey not in curdic and create_missing:
            curdic[curkey] = {}
        curdic = curdic[curkey]
    return curdic


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


class EndfVariable:

    def __init__(self, path, endf_dict, value=None):
        path_parts = path_to_list(path)
        create_missing = value is not None
        parent_dict = enter_section(endf_dict, path_parts[:-1], create_missing)
        self._path_parts = path_parts
        self._pardict = parent_dict
        self._varname = path_parts[-1]
        self._endf_dict = endf_dict
        if value is not None:
            self.value = value
        else:
            if self._varname not in self._pardict:
                pathstr = list_to_path(self._path_parts[:-1])
                raise KeyError(
                    f'variable `{self._varname}` does not exist at location `{pathstr}`'
                )

    def __repr__(self):
        pathstr = list_to_path(self._path_parts + [self._varname])
        return (f'EndfVariable({pathstr!r}, ' +
                f'{type(self._endf_dict)} at {hex(id(self._endf_dict))}, ' +
                f'value={self.value})')

    def __call__(self):
        return self.value

    @property
    def name(self):
        return self._varname

    @property
    def value(self):
        return self._pardict[self._varname]

    @value.setter
    def value(self, value):
        self._pardict[self._varname] = value

    @property
    def endf_dict(self):
        return self._endf_dict

    @property
    def parent_dict(self):
        return self._pardict
