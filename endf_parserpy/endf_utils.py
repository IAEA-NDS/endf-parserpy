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

from .fortran_utils import (float2fortstr, fortstr2float,
        read_fort_floats, write_fort_floats, read_fort_int)
from .custom_exceptions import (
        NotSectionEndError,
        UnexpectedEndOfInputError,
        InvalidIntegerError,
        MoreListElementsExpectedError,
        UnconsumedListElementsError
    )


def read_ctrl(line, nofail=False, **read_opts):
    width = read_opts.get('width', 11)
    ofs = 6*width
    if nofail:
        try:
            mat = int(line[ofs:ofs+4])
            mf = int(line[ofs+4:ofs+6])
            mt = int(line[ofs+6:ofs+9])
        except Exception:
            mat = 0
            mf = 0
            mt = 0
    else:
        # blank fields are interpreted as zero
        matstr = line[ofs:ofs+4].strip()
        mfstr = line[ofs+4:ofs+6].strip()
        mtstr = line[ofs+6:ofs+9].strip()
        mat = int(matstr) if matstr != '' else 0
        mf = int(mfstr) if mfstr != '' else 0
        mt = int(mtstr) if mtstr != '' else 0
    return {'MAT': mat, 'MF': mf, 'MT': mt}

def write_ctrl(dic, ns=None):
    nsstr = '' if not ns else str(ns).rjust(5)
    return '{:>4}{:>2}{:>3}'.format(dic['MAT'], dic['MF'], dic['MT']) + nsstr

def get_ctrl(dic, nofail=False):
    while 'MAT' not in dic and '__up' in dic:
        dic = dic['__up']
    if nofail:
        mat = 0 if 'MAT' not in dic else dic['MAT']
        mf = 0 if 'MF' not in dic else dic['MF']
        mt = 0 if 'MT' not in dic else dic['MT']
    else:
        mat = dic['MAT']
        mf = dic['MF']
        mt = dic['MT']
    return {'MAT': mat, 'MF': mf, 'MT': mt}

def read_text(lines, ofs=0, with_ctrl=True, **read_opts):
    width = read_opts.get('width', 11)
    ofs2 = width * 6
    line = lines[ofs]
    dic = {'HL': line[0:ofs2]}
    if with_ctrl:
        ctrl = read_ctrl(line, **read_opts)
        dic.update(ctrl)
    return dic, ofs+1

def write_text(dic, with_ctrl=True, **write_opts):
    ofs2 = write_opts.get('width', 11) * 6
    TEXT = dic['HL'].ljust(ofs2)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [TEXT + CTRL]

def read_dir(lines, ofs=0, with_ctrl=True, blank_as_zero=False, **read_opts):
    width = read_opts.get('width', 11)
    line = lines[ofs]
    dic = {'L1' : read_fort_int(line[2*width:3*width], blank_as_zero),
           'L2' : read_fort_int(line[3*width:4*width], blank_as_zero),
           'N1' : read_fort_int(line[4*width:5*width], blank_as_zero),
           'N2' : read_fort_int(line[5*width:6*width], blank_as_zero)}
    if with_ctrl:
        ctrl = read_ctrl(line, **read_opts)
        dic.update(ctrl)
    return dic, ofs+1

def write_dir(dic, with_ctrl=True, **write_opts):
    width = write_opts.get('width', 11)
    C1 = ' '*width
    C2 = ' '*width
    L1 = str(dic['L1']).rjust(width)
    L2 = str(dic['L2']).rjust(width)
    N1 = str(dic['N1']).rjust(width)
    N2 = str(dic['N2']).rjust(width)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL]

def read_intg(lines, ofs=0, with_ctrl=True, blank_as_zero=False,
              ndigit=None, **read_opts):
    if ndigit is None:
        raise ValueError('ndigit must be specified')
    if int(ndigit) != ndigit:
        raise InvalidIntegerError('NDIGIT must be integer')
    elif ndigit < 2 or ndigit > 6:
        raise InvalidIntegerError('NDIGIT must be between 2 and 6')
    ndigit = int(ndigit)
    range_iter = range(11, 65, ndigit+1) if ndigit <= 5 else range(10, 65, ndigit+1)
    line = lines[ofs]
    dic = {'II': read_fort_int(line[0:5], blank_as_zero=blank_as_zero),
           'JJ': read_fort_int(line[5:10], blank_as_zero=blank_as_zero),
           'KIJ': [read_fort_int(line[i:i+ndigit+1], blank_as_zero=blank_as_zero)
                   for i in range_iter]}
    if with_ctrl:
        ctrl = read_ctrl(line, **read_opts)
        dic.update(ctrl)
    return dic, ofs+1

def write_intg(dic, with_ctrl=True, ndigit=None, **write_opts):
    width = write_opts.get('width', 11)
    if not isinstance(ndigit, int):
        raise ValueError('ndigit must be specified')
    II = str(dic['II']).rjust(5)
    JJ = str(dic['JJ']).rjust(5)
    spacer = '' if ndigit == 6 else ' '
    KIJ = ''.join([str(c).rjust(ndigit+1) for c in dic['KIJ']])
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [(II + JJ + spacer + KIJ).ljust(width*6) + CTRL]

def read_cont(lines, ofs=0, with_ctrl=True, blank_as_zero=False, **read_opts):
    width = read_opts.get('width', 11)
    line = lines[ofs]
    dic = {'C1' : fortstr2float(line[0:width],
                                blank=0.0 if blank_as_zero else None,
                                **read_opts),
           'C2' : fortstr2float(line[width:2*width],
                                blank=0.0 if blank_as_zero else None,
                                **read_opts),
           'L1' : read_fort_int(line[2*width:3*width], blank_as_zero),
           'L2' : read_fort_int(line[3*width:4*width], blank_as_zero),
           'N1' : read_fort_int(line[4*width:5*width], blank_as_zero),
           'N2' : read_fort_int(line[5*width:6*width], blank_as_zero)}
    if with_ctrl:
        ctrl = read_ctrl(line, **read_opts)
        dic.update(ctrl)
    return dic, ofs+1

def write_cont(dic, with_ctrl=True, **write_opts):
    width = write_opts.get('width', 11)
    for varname in ('L1', 'L2', 'N1', 'N2'):
        if not isinstance(dic[varname], int):
            raise InvalidIntegerError(
                    f'variable `{varname}` is not of type integer')
    C1 = float2fortstr(dic['C1'], **write_opts)
    C2 = float2fortstr(dic['C2'], **write_opts)
    L1 = str(dic['L1']).rjust(width)
    L2 = str(dic['L2']).rjust(width)
    N1 = str(dic['N1']).rjust(width)
    N2 = str(dic['N2']).rjust(width)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL]

def prepare_zerostr_fields(zero_as_blank, **write_opts):
    width = write_opts.get('width', 11)
    zerostr = ' '*width if zero_as_blank else float2fortstr(0, **write_opts)
    zerostr2 = ' '*width if zero_as_blank else '0'.rjust(width)
    C1 = zerostr
    C2 = zerostr
    L1 = zerostr2
    L2 = zerostr2
    N1 = zerostr2
    N2 = zerostr2
    return C1, C2, L1, L2, N1, N2

def read_send(lines, ofs=0, with_ctrl=True, blank_as_zero=False, **read_opts):
    dic, ofs = read_cont(lines, ofs, with_ctrl, blank_as_zero=blank_as_zero,
                         **read_opts)
    if dic['C1'] != 0 or dic['C2'] != 0 or \
       dic['L1'] != 0 or dic['L2'] != 0 or \
       dic['N1'] != 0 or dic['N2'] != 0 or \
       dic['MT'] != 0:
           raise NotSectionEndError('Not a Section End (SEND) record')
    return dic, ofs

def write_send(dic, with_ctrl=True, with_ns=True,
               zero_as_blank=False, **write_opts):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank, **write_opts)
    ctrl_dic = get_ctrl(dic)
    ctrl_dic['MT'] = 0
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '99999' if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_fend(dic, with_ctrl=True, with_ns=True,
               zero_as_blank=False, **write_opts):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank, **write_opts)
    ctrl_dic = get_ctrl(dic)
    ctrl_dic['MF'] = 0
    ctrl_dic['MT'] = 0
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_mend(dic=None, with_ctrl=True, with_ns=True,
               zero_as_blank=False, **write_opts):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank, **write_opts)
    ctrl_dic = {'MAT': 0, 'MF': 0, 'MT': 0}
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_tend(dic=None, with_ctrl=True, with_ns=True,
               zero_as_blank=False, **write_opts):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank, **write_opts)
    ctrl_dic = {'MAT': -1, 'MF': 0, 'MT': 0}
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]


# alias for the endf HEAD record type
# which is for the time being dealt with
# in exactly the same way as the CONT record type
write_head = write_cont
read_head = read_cont

def read_list(lines, ofs=0, with_ctrl=True, callback=None,
              blank_as_zero=False, **read_opts):
    dic, ofs = read_cont(lines, ofs, with_ctrl, blank_as_zero=blank_as_zero,
                         **read_opts)
    NPL = dic['N1']
    if NPL == 0:
        dic['vals'] = []
        ofs += 1
    else:
        vals, ofs = read_endf_numbers(lines, NPL, ofs,
                                      blank_as_zero=blank_as_zero,
                                      **read_opts)
        dic['vals'] = vals
    return dic, ofs

def write_list(dic, with_ctrl=True, **write_opts):
    NPL = dic['N1']
    num_vals = len(dic['vals'])
    if NPL < num_vals:
        raise UnconsumedListElementsError(
            f'NPL={NPL} (N1 slot) indicates fewer elements than present ({num_vals})'
        )
    elif NPL > num_vals:
        raise MoreListElementsExpectedError(
            f'NPL={NPL} (N1 slot) indicates more elements than present ({num_vals})'
        )
    lines = write_cont(dic, with_ctrl, **write_opts)
    if NPL == 0:
        body_lines = write_endf_numbers([0.0 for i in range(6)],
                                        **write_opts)
    else:
        ext_vals = dic['vals'].copy()
        if NPL % 6 != 0:
            ext_vals += [0.0 for i in range(6 - NPL % 6)]
        body_lines = write_endf_numbers(ext_vals, **write_opts)
    if with_ctrl:
        ctrl = write_ctrl(dic)
        body_lines = [t + ctrl for t in body_lines]
    lines += body_lines
    return lines

def read_tab2(lines, ofs=0, with_ctrl=True,
              blank_as_zero=False, **read_opts):
    startline = lines[ofs]
    dic, ofs = read_cont(lines, ofs, blank_as_zero=blank_as_zero,
                         **read_opts)
    vals, ofs = read_endf_numbers(lines, 2*dic['N1'], ofs, to_int=True,
                                  blank_as_zero=blank_as_zero,
                                  **read_opts)
    NBT = vals[::2]
    INT = vals[1::2]
    dic['table'] = {'NBT': NBT, 'INT': INT}
    if with_ctrl:
        ctrl = read_ctrl(startline, **read_opts)
        dic.update(ctrl)
    return dic, ofs

def write_tab2(dic, with_ctrl=True, **write_opts):
    dic = dic.copy()
    tbl_dic = dic['table']
    NBT = tbl_dic['NBT']
    INT = tbl_dic['INT']
    if len(NBT) != len(INT):
        raise ValueError('NBT and INT must be of same length')
    dic.update({'N1': len(NBT)})
    lines = write_cont(dic, with_ctrl, **write_opts)
    vals = [None]*(2*len(NBT))
    vals[::2] = NBT
    vals[1::2] = INT
    tbl_lines = write_endf_numbers(vals, to_int=True, **write_opts)
    if with_ctrl:
        ctrl = write_ctrl(dic)
        tbl_lines = [t + ctrl for t in tbl_lines]
    return lines + tbl_lines

def read_tab1(lines, ofs=0, with_ctrl=True, blank_as_zero=False,
              **read_opts):
    startline = lines[ofs]
    dic, ofs = read_cont(lines, ofs, with_ctrl,
                         blank_as_zero=blank_as_zero, **read_opts)
    tbl_dic, ofs = read_tab1_body_lines(lines, ofs, dic['N1'], dic['N2'],
                                        blank_as_zero=blank_as_zero,
                                        **read_opts)
    dic['table'] = tbl_dic
    if with_ctrl:
        ctrl = read_ctrl(startline, **read_opts)
        dic.update(ctrl)
    return dic, ofs

def write_tab1(dic, with_ctrl=True, **write_opts):
    dic = dic.copy()
    tbl_dic = dic['table']
    dic.update({'N1': len(tbl_dic['NBT']),
                'N2': len(tbl_dic['X'])})
    lines = write_cont(dic, with_ctrl, **write_opts)
    tbl_lines = write_tab1_body_lines(
            tbl_dic['NBT'], tbl_dic['INT'],
            tbl_dic['X'], tbl_dic['Y'], **write_opts)
    if with_ctrl:
        ctrl = write_ctrl(dic)
        tbl_lines = [t + ctrl for t in tbl_lines]
    return lines + tbl_lines

def read_tab1_body_lines(lines, ofs, nr, np, blank_as_zero=False,
                         **read_opts):
    vals, ofs = read_endf_numbers(lines, 2*nr, ofs, to_int=True,
                                  blank_as_zero=blank_as_zero,
                                  **read_opts)
    NBT = vals[::2]
    INT = vals[1::2]
    vals, ofs = read_endf_numbers(lines, 2*np, ofs, to_int=False,
                                  blank_as_zero=blank_as_zero,
                                  **read_opts)
    xvals = vals[::2]
    yvals = vals[1::2]
    return {'NBT': NBT, 'INT': INT, 'X': xvals,'Y':  yvals}, ofs

def write_tab1_body_lines(NBT, INT, xvals, yvals, **write_opts):
    assert len(NBT) == len(INT)
    assert len(xvals) == len(yvals)
    vals = [None]*(2*len(NBT))
    vals[::2] = NBT
    vals[1::2] = INT
    lines = write_endf_numbers(vals, to_int=True, **write_opts)
    vals = [None]*(2*len(xvals))
    vals[::2] = xvals
    vals[1::2] = yvals
    lines.extend(write_endf_numbers(vals, **write_opts))
    return lines

def read_endf_numbers(lines, num, ofs, to_int=False,
                      blank_as_zero=False, **read_opts):
    vals = []
    blank_symb = 0. if blank_as_zero else None
    while num > 0:
        l = lines[ofs]
        m = min(6, num)
        vals += read_fort_floats(l, m, blank=blank_symb,
                                 **read_opts)
        num -= 6
        ofs += 1
    if to_int:
        try:
            vals = [int(v) for v in vals]
        except ValueError:
            pass

    return vals, ofs

def write_endf_numbers(vals, to_int=False, **write_opts):
    width = write_opts.get('width', 11)
    lines = []
    for i in range(0, len(vals), 6):
        m = min(i+6, len(vals))
        if to_int:
            lines.append(''.join([str(v).rjust(width) for v in vals[i:m]]))
        else:
            lines.append(write_fort_floats(vals[i:m], **write_opts))
    lines[-1] = lines[-1].ljust(width*6)
    return lines

def is_blank_line(line):
    l = ''.join(line.strip())
    return l == ''

def skip_blank_lines(lines, ofs):
    if ofs >= len(lines):
        raise UnexpectedEndOfInputError(
                'expected input but consumed all lines')
    while is_blank_line(lines[ofs]):
        ofs += 1
        if ofs >= len(lines):
            raise UnexpectedEndOfInputError(
                    'expected input but consumed all lines')
    return ofs

def split_sections(lines, **read_opts):
    mfdic = {}
    for line in lines:
        if is_blank_line(line):
            continue
        dic = read_ctrl(line, nofail=True, **read_opts)
        mf = dic['MF']
        mt = dic['MT']
        # end markers (SEND, MEND, FEND, TEND) ignored
        # but: if the dictionary is empty and we get
        # mf=0 and mt=0, we assume it is the tape head
        # line and store it
        if ((mf != 0 and mt != 0) or
                (mf == 0 and mt == 0 and not mfdic)):
            mfdic.setdefault(mf, {})
            mtdic = mfdic[mf]
            mt = dic['MT']
            mtdic.setdefault(mt, [])
            mtdic[mt].append(line)
    return mfdic

