def defdic(dic, index, recipe):
    """store recipe in nested dictionary"""
    curdic = dic
    for idx in index[:-1]:
        curdic = curdic.setdefault(idx, {})
    curdic[index[-1]] = recipe
