############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/11/25
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


def fortstr2float(valstr, blank=None, **read_opts):
    accept_spaces = read_opts.get('accept_spaces', True)
    if valstr.strip() == '' and blank is not None:
        return blank
    if accept_spaces:
        valstr = valstr.replace(' ', '')
    for i, c in enumerate(valstr):
        if i > 0 and (c == '+' or c == '-'):
            if valstr[i-1].isdigit():
                return float(valstr[:i] + 'E' + valstr[i:])
    try:
        return float(valstr)
    except ValueError as valerr:
        raise InvalidFloatError(valerr)


def float2basicnumstr(val, **write_opts):
    width = write_opts.get('width', 11)
    effwidth = width
    abuse_signpos = write_opts.get('abuse_signpos', False)
    skip_intzero = write_opts.get('skip_intzero', False)
    intpart = int(val)
    len_intpart = len(str(abs(intpart)))
    is_integer = (intpart == val)
    if is_integer and intpart == 0:
        return '0'.rjust(effwidth)
    # -1 due to a minus sign slot
    # -1 due to the decimal point
    waste_space = 2
    if abuse_signpos and val > 0:
        waste_space -= 1
    should_skip_zero = skip_intzero and intpart == 0
    if should_skip_zero:
        effwidth += 1
    if is_integer:
        waste_space -= 1
    floatwidth = effwidth - waste_space - len_intpart
    if floatwidth > 0 and not is_integer:
        numstr = f'{{:{effwidth}.{floatwidth}f}}'.format(val)
        if should_skip_zero:
            dotpos = numstr.index('.')
            numstr = numstr[:dotpos-1] + numstr[dotpos:]
    else:
        numstr = '{:d}'.format(int(val))
        if val > 0 and not abuse_signpos:
            numstr = ' ' + numstr
        if len(numstr) <= width-2:
            numstr += '.'
            numstr = numstr.ljust(width, '0')
    numstr = numstr.rjust(width)
    return numstr


def float2expformstr(val, **write_opts):
    width = write_opts.get('width', 11)
    abuse_signpos = write_opts.get('abuse_signpos', False)
    keep_E = write_opts.get('keep_E', False)
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
    expsymb_dec = 1 if keep_E else 0
    exponent = floor(log10(av)) if av != 0 else 0
    mantissa = abs(val / 10**exponent)
    is_expo_pos = exponent >= 0
    absexponent = abs(exponent)
    mantissa_len = width - 1 - nexp - sign_dec - expsymb_dec
    mantissa_str = f'{{:.{mantissa_len-2}f}}'.format(mantissa)
    expsymb_str = 'E' if keep_E else ''
    exposign_str = '+' if is_expo_pos else '-'
    exponent_str = f'{{:{nexp}d}}'.format(absexponent)
    if is_pos:
        sign_str = '' if abuse_signpos else ' '
    else:
        sign_str = '-'
    res_str = sign_str + mantissa_str + expsymb_str + exposign_str + exponent_str
    if len(res_str) > width:
        # special case: we have 9.999999999 in the mantissa, which will
        #               be rounded to 10.0000000 so we have too many digits.
        #               Hack: Pass the rounded number again to this function.
        tmp_str = sign_str + mantissa_str + 'e' + exposign_str + exponent_str
        res_str = float2expformstr(float(tmp_str), **write_opts)
    return res_str


def count_signif_digits(valstr):
    num_signif = 0
    in_signif = False
    zero_acc = 0
    for c in valstr:
        if not in_signif and c.isdigit() and c != '0':
            in_signif = True
        if in_signif:
            if c.isdigit():
                if c != '0':
                    num_signif += 1 + zero_acc
                    zero_acc = 0
                else:
                    zero_acc += 1
            elif c != '.':
                break
    return num_signif


def float2fortstr(val, **write_opts):
    width = write_opts.get('width', 11)
    prefer_noexp = write_opts.get('prefer_noexp', False)
    valstr_exp = float2expformstr(val, **write_opts)
    if not prefer_noexp:
        return valstr_exp
    valstr_basic = float2basicnumstr(val, **write_opts)
    if '.' in valstr_basic:
        valstr_basic = valstr_basic.rstrip('0').rstrip('.')
        # next line to deal with case -.00 and .00
        if valstr_basic in ('+', '-', ''):
            valstr_basic = '0'
    if len(valstr_basic) > width:
        return valstr_exp
    delta1 = abs(fortstr2float(valstr_basic) - val)
    delta2 = abs(fortstr2float(valstr_exp) - val)
    if delta2 < delta1:
        return valstr_exp
    valstr_basic = valstr_basic.rjust(width)
    return valstr_basic


def read_fort_floats(line, n=6, blank=None, **read_opts):
    accept_spaces = read_opts.get('accept_spaces', True)
    width = read_opts.get('width', 11)
    assert isinstance(line, str)
    vals = []
    for i in range(0, n*width, width):
        if line[i:i+width] == ' '*width:
            if blank is None:
                raise ValueError('blank encountered but blank=None')
            else:
                vals.append(blank)
        else:
            vals.append(fortstr2float(line[i:i+width],
                                      accept_spaces=accept_spaces))
    return vals


def write_fort_floats(vals, **write_opts):
    line = ''
    for i, v in enumerate(vals):
        line += float2fortstr(v, **write_opts)
    return line
