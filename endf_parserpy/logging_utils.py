############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

import logging


def write_info(message, ofs=None):
    prefix = f'Line #{ofs}: ' if ofs is not None else ''
    logging.info(prefix + message)

def abbreviate_valstr(val):
    if isinstance(val, int) or isinstance(val, float):
        return str(val)
    elif isinstance(val, str):
        if len(val) < 13:
            return val
        else:
            return val[1:5] + '...' + val[1:5]
    elif isinstance(val, dict):
        return '{' + ', '.join(str(k) for k in tuple(val.keys())[:3]) + ', ...' + '}'

def should_skip_logging_info(varnames, datadic):
    if len(varnames) == 0:
        return True
    elif (len(varnames) == 1 and isinstance(datadic[varnames[0]], dict)
           and len(datadic[varnames[0]]) > 1):
        return True
    # if all variables are dictionaries...
    elif len(tuple(1 for v in varnames if isinstance(datadic[v], dict))) == len(varnames):
        # and all these dictionaries have more than one element
        # we skip displaying then because they have been already
        # filled and displayed before
        if len(tuple(1 for v in varnames if len(datadic[v]) <= 1)) == 0:
            return True
        else:
            return False
    else:
        return False

