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

