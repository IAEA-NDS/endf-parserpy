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
        read_fort_floats, write_fort_floats)


def read_ctrl(line, nofail=False):
    if nofail:
        try:
            mat = int(line[66:70])
            mf = int(line[70:72])
            mt = int(line[72:75])
        except:
            mat = 0
            mf = 0
            mt = 0
    else:
        # blank fields are interpreted as zero
        matstr = line[66:70].strip()
        mfstr = line[70:72].strip()
        mtstr = line[72:75].strip()
        mat = int(matstr) if matstr != '' else 0
        mf = int(mfstr) if mfstr != '' else 0
        mt = int(mtstr) if mtstr != '' else 0
    return {'MAT': mat, 'MF': mf, 'MT': mt}

def write_ctrl(dic, ns=None):
    nsstr = '' if not ns else str(ns).rjust(5)
    return '{:>4}{:>2}{:>3}'.format( dic['MAT'], dic['MF'], dic['MT']) + nsstr

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

def read_text(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    line = lines[ofs]
    dic = {'HL': line[0:66]}
    if with_ctrl:
        ctrl = read_ctrl(line)
        dic.update(ctrl)
    return dic, ofs+1

def write_text(dic, with_ctrl=True):
    TEXT = dic['HL'].ljust(66)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [TEXT + CTRL]

def read_dir(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    line = lines[ofs]
    dic = {'L1' : int(line[22:33]),
           'L2' : int(line[33:44]),
           'N1' : int(line[44:55]),
           'N2' : int(line[55:66])}
    if with_ctrl:
        ctrl = read_ctrl(line)
        dic.update(ctrl)
    return dic, ofs+1

def write_dir(dic, with_ctrl=True):
    C1 = ' '*11
    C2 = ' '*11
    L1 = str(dic['L1']).rjust(11)
    L2 = str(dic['L2']).rjust(11)
    N1 = str(dic['N1']).rjust(11)
    N2 = str(dic['N2']).rjust(11)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL]

def read_cont(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    line = lines[ofs]
    dic = {'C1' : fortstr2float(line[0:11]),
           'C2' : fortstr2float(line[11:22]),
           'L1' : int(line[22:33]),
           'L2' : int(line[33:44]),
           'N1' : int(line[44:55]),
           'N2' : int(line[55:66])}
    if with_ctrl:
        ctrl = read_ctrl(line)
        dic.update(ctrl)
    return dic, ofs+1

def write_cont(dic, with_ctrl=True):
    C1 = float2fortstr(dic['C1'])
    C2 = float2fortstr(dic['C2'])
    L1 = str(dic['L1']).rjust(11)
    L2 = str(dic['L2']).rjust(11)
    N1 = str(dic['N1']).rjust(11)
    N2 = str(dic['N2']).rjust(11)
    CTRL = write_ctrl(dic) if with_ctrl else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL]

def prepare_zerostr_fields(zero_as_blank):
    zerostr = ' '*11 if zero_as_blank else float2fortstr(0)
    zerostr2 = ' '*11 if zero_as_blank else '0'.rjust(11)
    C1 = zerostr
    C2 = zerostr
    L1 = zerostr2
    L2 = zerostr2
    N1 = zerostr2
    N2 = zerostr2
    return C1, C2, L1, L2, N1, N2

def read_send(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    dic, ofs = read_cont(lines, ofs, with_ctrl)
    if dic['C1'] != 0 or dic['C2'] != 0 or \
       dic['L1'] != 0 or dic['L2'] != 0 or \
       dic['N1'] != 0 or dic['N2'] != 0 or \
       dic['MT'] != 0:
           raise ValueError('Not a Section End (SEND) record')
    return dic, ofs

def write_send(dic, with_ctrl=True, with_ns=True, zero_as_blank=False):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank)
    ctrl_dic = get_ctrl(dic)
    ctrl_dic['MT'] = 0
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '99999' if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_fend(dic, with_ctrl=True, with_ns=True, zero_as_blank=False):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank)
    ctrl_dic = get_ctrl(dic)
    ctrl_dic['MF'] = 0
    ctrl_dic['MT'] = 0
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_mend(dic=None, with_ctrl=True, with_ns=True, zero_as_blank=False):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank)
    ctrl_dic = {'MAT': 0, 'MF': 0, 'MT': 0}
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]

def write_tend(dic=None, with_ctrl=True, with_ns=True, zero_as_blank=False):
    C1, C2, L1, L2, N1, N2 = prepare_zerostr_fields(zero_as_blank)
    ctrl_dic = {'MAT': -1, 'MF': 0, 'MT': 0}
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    NS = '0'.rjust(5) if with_ns else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL + NS]


# alias for the endf HEAD record type
# which is for the time being dealt with
# in exactly the same way as the CONT record type
write_head = write_cont
read_head = read_cont

def read_list(lines, ofs=0, with_ctrl=True, callback=None):
    ofs = skip_blank_lines(lines, ofs)
    dic, ofs = read_cont(lines, ofs, with_ctrl)
    NPL = dic['N1']
    if NPL == 0:
        dic['vals'] = []
        ofs += 1
    else:
        vals, ofs = read_endf_numbers(lines, NPL, ofs)
        dic['vals'] = vals
    return dic, ofs

def write_list(dic, with_ctrl=True):
    NPL = len(dic['vals'])
    tmpdic = dic.copy()
    tmpdic['N1'] = NPL
    lines = write_cont(dic, with_ctrl)
    if NPL == 0:
        body_lines = write_endf_numbers([0.0 for i in range(6)])
    else:
        ext_vals = dic['vals'].copy()
        if NPL % 6 != 0:
            ext_vals += [0.0 for i in range(6 - NPL % 6)]
        body_lines = write_endf_numbers(ext_vals)
    if with_ctrl:
        ctrl = write_ctrl(dic)
        body_lines = [t + ctrl for t in body_lines]
    lines += body_lines
    return lines

def read_tab2(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    startline = lines[ofs]
    dic, ofs = read_cont(lines, ofs)
    vals, ofs = read_endf_numbers(lines, 2*dic['N1'], ofs, to_int=True)
    NBT = vals[::2]
    INT = vals[1::2]
    dic['table'] = {'NBT': NBT, 'INT': INT}
    if with_ctrl:
        ctrl = read_ctrl(startline)
        dic.update(ctrl)
    return dic, ofs

def write_tab2(dic, with_ctrl=True):
    dic = dic.copy()
    tbl_dic = dic['table']
    NBT = tbl_dic['NBT']
    INT = tbl_dic['INT']
    if len(NBT) != len(INT):
        raise ValueError('NBT and INT must be of same length')
    dic.update({'N1': len(NBT)})
    lines = write_cont(dic, with_ctrl)
    vals = [None]*(2*len(NBT))
    vals[::2] = NBT
    vals[1::2] = INT
    tbl_lines = write_endf_numbers(vals, to_int=True)
    if with_ctrl:
        ctrl = write_ctrl(dic)
        tbl_lines = [t + ctrl for t in tbl_lines]
    return lines + tbl_lines

def read_tab1(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    startline = lines[ofs]
    dic, ofs = read_cont(lines, ofs, with_ctrl)
    tbl_dic, ofs = read_tab1_body_lines(lines, ofs, dic['N1'], dic['N2'])
    dic['table'] = tbl_dic
    if with_ctrl:
        ctrl = read_ctrl(startline)
        dic.update(ctrl)
    return dic, ofs

def write_tab1(dic, with_ctrl=True):
    dic = dic.copy()
    tbl_dic = dic['table']
    dic.update({'N1': len(tbl_dic['NBT']),
                'N2': len(tbl_dic['X'])})
    lines = write_cont(dic, with_ctrl)
    tbl_lines = write_tab1_body_lines(
            tbl_dic['NBT'], tbl_dic['INT'],
            tbl_dic['X'], tbl_dic['Y'])
    if with_ctrl:
        ctrl = write_ctrl(dic)
        tbl_lines = [t + ctrl for t in tbl_lines]
    return lines + tbl_lines

def read_tab1_body_lines(lines, ofs, nr, np):
    vals, ofs = read_endf_numbers(lines, 2*nr, ofs, to_int=True)
    NBT = vals[::2]
    INT = vals[1::2]
    vals, ofs = read_endf_numbers(lines, 2*np, ofs)
    xvals = vals[::2]
    yvals = vals[1::2]
    return {'NBT': NBT, 'INT': INT, 'X': xvals,'Y':  yvals}, ofs

def write_tab1_body_lines(NBT, INT, xvals, yvals):
    assert len(NBT) == len(INT)
    assert len(xvals) == len(yvals)
    vals = [None]*(2*len(NBT))
    vals[::2] = NBT
    vals[1::2] = INT
    lines = write_endf_numbers(vals, to_int=True)
    vals = [None]*(2*len(xvals))
    vals[::2] = xvals
    vals[1::2] = yvals
    lines.extend(write_endf_numbers(vals))
    return lines

def read_endf_numbers(lines, num, ofs, to_int=False):
    vals = []
    while num > 0:
        l = lines[ofs]
        m = min(6, num)
        vals += read_fort_floats(l, m)
        num -= 6
        ofs += 1
    if to_int:
        vals = [int(v) for v in vals]
    return vals, ofs

def write_endf_numbers(vals, to_int=False):
    lines = []
    for i in range(0, len(vals), 6):
        m = min(i+6, len(vals))
        if to_int:
            lines.append(''.join([str(v).rjust(11) for v in vals[i:m]]))
        else:
            lines.append(write_fort_floats(vals[i:m], w=11))
    lines[-1] = lines[-1].ljust(66)
    return lines

def is_blank_line(line):
    l = ''.join(line.strip())
    return l == ''

def skip_blank_lines(lines, ofs):
    if ofs >= len(lines):
        raise IndexError('expected input but consumed all lines')
    while is_blank_line(lines[ofs]):
        ofs += 1
        if ofs >= len(lines):
            raise IndexError('expected input but consumed all lines')
    return ofs

def split_sections(lines):
    mfdic = {}
    for line in lines:
        if is_blank_line(line):
            continue
        dic = read_ctrl(line, nofail=True)
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

