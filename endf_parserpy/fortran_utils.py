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

from .custom_exceptions import (
        InvalidIntegerError,
        InvalidFloatError
    )
from math import log10, floor


def read_fort_int(valstr, blank_as_zero=False):
    if blank_as_zero and valstr.strip() == '':
        return 0
    else:
        try:
            return int(valstr)
        except ValueError as valerr:
            raise InvalidIntegerError(valerr)


def fortstr2float(valstr, blank=None):
    if valstr.strip() == '' and blank is not None:
        return blank
    digitchars = tuple(str(i) for i in range(10))
    for i, c in enumerate(valstr):
        if i>0 and (c == '+' or c == '-'):
            if valstr[i-1] in digitchars:
                return float(valstr[:i] + 'E' + valstr[i:])
    try:
        return float(valstr)
    except ValueError as valerr:
        raise InvalidFloatError(valerr)


def float2basicnumstr(val, width=11, abuse_signpos=False,
                      skip_intzero=False):
    intpart = int(val)
    len_intpart = len(str(abs(intpart)))
    # -1 due to a minus sign slot
    # -1 due to the decimal point
    waste_space = 2
    intpos = 1
    if abuse_signpos and val > 0:
        waste_space -= 1
        intpos = 0
    should_skip_zero = skip_intzero and intpart == 0
    if should_skip_zero:
        width += 1
    is_integer = (intpart == val)
    if is_integer:
        waste_space -= 1
    floatwidth = width - waste_space - len_intpart
    if floatwidth > 0 and (not is_integer or val == 0):
        numstr = f'{{:{width}.{floatwidth}f}}'.format(val)
    elif log10(abs(intpart)) < width:
        numstr = f'{{:{width}d}}'.format(int(val))
    else:
        raise ValueError('cannot represent the number')
    if should_skip_zero:
        numstr = numstr[:intpos] + numstr[intpos+1:]
    return numstr


def float2expformstr(val, width=11, abuse_signpos=False):
    av = abs(val)
    if av >= 1e-9 and av < 1e10:
        nexp = 1
    elif av >= 1e-99 and av < 1e100:
        nexp = 2
    elif av == 0.0:
        nexp = 1
    else:
        nexp = 3
    is_pos = val >= 0
    sign_dec = 0 if abuse_signpos and is_pos else 1
    exponent = floor(log10(av)) if av != 0 else 0
    mantissa = abs(val / 10**exponent)
    is_expo_pos = exponent >= 0
    absexponent = abs(exponent)
    mantissa_len = width - 1 - nexp - sign_dec
    mantissa_str = f'{{:.{mantissa_len-2}f}}'.format(mantissa)
    exposign_str = '+' if is_expo_pos else '-'
    exponent_str = f'{{:{nexp}d}}'.format(absexponent)
    if is_pos:
        sign_str = '' if abuse_signpos else ' '
    else:
        sign_str = '-'
    return sign_str + mantissa_str + exposign_str + exponent_str


def is_noexpform_more_precise(val, width, skip_intzero, abuse_signpos):
    if val == 0:
        return True
    digit_advantage = 2
    if skip_intzero and abs(int(val)) < 1:
        digit_advantage += 1
    expo = log10(abs(val)) if val != 0 else 0
    if expo < 0:
        return digit_advantage + expo >= 0
    else:
        sign_inc = 1 if val > 0 and abuse_signpos else 0
        int_inc = 1 if int(val) == val else 0
        # -1 for decimal point
        # -1 for sign slot
        num_digits = width - 2 + sign_inc + int_inc
        return num_digits > expo


def float2fortstr(val, width=11, prefer_noexp=False,
                  skip_intzero=False, abuse_signpos=False):
    noexp_more_precise = is_noexpform_more_precise(val, width,
                                                   skip_intzero,
                                                   abuse_signpos)
    if prefer_noexp and noexp_more_precise:
        return float2basicnumstr(val, width,
                                 abuse_signpos=abuse_signpos,
                                 skip_intzero=skip_intzero)
    else:
        return float2expformstr(val, width=11,
                                abuse_signpos=abuse_signpos)


def read_fort_floats(line, n=6, w=11, blank=None):
    assert isinstance(line, str)
    vals = []
    for i in range(0, n*w, w):
        if line[i:i+w] == ' '*w:
            if blank is None:
                raise ValueError('blank encountered but blank=None')
            else:
                vals.append(blank)
        else:
            vals.append(fortstr2float(line[i:i+w]))
    return vals


def write_fort_floats(vals, w=11, prefer_noexp=False,
                      skip_intzero=False, abuse_signpos=False):
    line = ''
    for i, v in enumerate(vals):
        line += float2fortstr(v, w,
                              prefer_noexp=prefer_noexp,
                              skip_intzero=skip_intzero,
                              abuse_signpos=abuse_signpos)
    return line
