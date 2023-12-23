############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import MutableMapping


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


def path_to_list(path):
    if not isinstance(path, str):
        return path
    path_parts = path.split('/')
    path_parts = [cur for cur in path_parts if cur != '']
    path_parts = [int(cur) if cur.isdigit() else cur for cur in path_parts]
    return path_parts


def list_to_path(path):
    return '/'.join([str(x) for x in path])


def enter_section(endf_dic, path, create_missing=False, trunc=0):
    curdic = endf_dic
    path_parts = path_to_list(path)
    if trunc > 0:
        path_parts = path_parts[:-trunc]
    for cur in path_parts:
        if cur not in curdic and create_missing:
            curdic[cur] = dict()
        curdic = curdic[cur]
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
        self._pardict = parent_dict
        self._varname = path_parts[-1]
        self._endf_dict = endf_dict
        self._path = list_to_path(path_parts)
        if value is not None:
            self.value = value
        else:
            if self._varname not in self._pardict:
                raise KeyError(f'variable `{self._path}` does not exist')

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
    def path(self):
        return self._path

    @property
    def endf_dict(self):
        return self._endf_dict

    @property
    def parent_dict(self):
        return self._pardict


class EndfDict(MutableMapping):

    def __init__(self, mapping=None):
        if mapping is None:
            self._store = dict()
        elif isinstance(mapping, MutableMapping):
            self._store = mapping
        else:
            raise TypeError(
                'exepcted `mapping` to be an instance of MutableMapping'
            )

    def _get_pardic_and_varname(self, path, create_missing):
        if isinstance(path, int):
            return self._store, path
        if isinstance(path, str) and '/' not in path:
            if path.isdigit():
                path = int(path)
            return self._store, path
        path_parts = path_to_list(path)
        pardic = enter_section(self._store, path_parts[:-1], create_missing)
        varname = path_parts[-1]
        return pardic, varname

    def __repr__(self):
        return f'{self._store!r}'

    def __str__(self):
        return str(self._store)

    def __getitem__(self, key):
        parent_dict, local_key = self._get_pardic_and_varname(key, False)
        ret = parent_dict[local_key]
        if isinstance(ret, MutableMapping) and not isinstance(ret, EndfDict):
            ret = EndfDict(ret)
        return ret

    def __setitem__(self, key, value):
        parent_dict, local_key = self._get_pardic_and_varname(key, True)
        parent_dict[local_key] = value

    def __delitem__(self, key):
        parent_dict, local_key = self._get_pardic_and_varname(key, False)
        del parent_dict[local_key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def keys(self):
        return self._store.keys()

    def values(self):
        return self._store.values()

    def items(self):
        return self._store.items()
