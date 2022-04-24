from fortran_utils import float2fortstr, fortstr2float, read_fort_floats

def skip_blank_lines(lines, ofs):
    if ofs >= len(lines):
        raise IndexError('expected input but consumed all lines')
    while ''.join(lines[ofs].strip()) == '':
        ofs += 1
        if ofs >= len(lines):
            raise IndexError('expected input but consumed all lines')
    return ofs

def read_ctrl(line):
    return {'MAT': int(line[66:70]),
            'MF' : int(line[70:72]),
            'MT' : int(line[72:75])}

def write_ctrl(dic, ns=None):
    nsstr = '' if not ns else str(ns).rjust(5)
    return '{:>4}{:>2}{:>3}'.format( dic['MAT'], dic['MF'], dic['MT']) + nsstr

def get_ctrl(dic):
    return {'MAT': dic['MAT'],
            'MF' : dic['MF'],
            'MT' : dic['MT']}

def read_text(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    line = lines[ofs]
    dic = {'HL': line[0:66]}
    if with_ctrl:
        ctrl = read_ctrl(line)
        dic.update(ctrl)
    return dic, ofs+1

def write_text(dic, with_ctrl=True):
    TEXT = dic['HL']
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

def read_send(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    dic, ofs = read_cont(lines, ofs, with_ctrl)
    if dic['C1'] != 0 or dic['C2'] != 0 or \
       dic['L1'] != 0 or dic['L2'] != 0 or \
       dic['N1'] != 0 or dic['N2'] != 0 or \
       dic['MT'] != 0:
           raise ValueError('Not a Section End (SEND) record')
    return dic, ofs

def write_send(dic, with_ctrl=True):
    C1 = float2fortstr(0)
    C2 = float2fortstr(0)
    L1 = '0'.rjust(11)
    L2 = '0'.rjust(11)
    N1 = '0'.rjust(11)
    N2 = '0'.rjust(11)
    ctrl_dic = get_ctrl(dic)
    ctrl_dic['MT'] = 0
    CTRL = write_ctrl(ctrl_dic) if with_ctrl else ''
    return [C1 + C2 + L1 + L2 + N1 + N2 + CTRL]

# alias for the endf HEAD record type
# which is for the time being dealt with
# in exactly the same way as the CONT record type
write_head = write_cont
read_head = read_cont

def read_tab1(lines, ofs=0, with_ctrl=True):
    ofs = skip_blank_lines(lines, ofs)
    startline = lines[ofs]
    dic, ofs = read_cont(lines, ofs)
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
    lines = write_cont(dic, with_ctrl=True)
    tbl_lines = write_tab1_body_lines(
            tbl_dic['NBT'], tbl_dic['INT'],
            tbl_dic['X'], tbl_dic['Y'])
    if with_ctrl:
        ctrl = write_ctrl(dic)
        tbl_lines = [t + ctrl for t in tbl_lines]
    return lines + tbl_lines

def read_tab1_body_lines(lines, ofs, nr, np):
    NBT = []; INT = []
    for i in range(nr):
        NBT.append(int(lines[ofs+i][:11]))
        INT.append(int(lines[ofs+i][11:22]))
    ofs += nr
    vals = []
    while np > 0:
        l = lines[ofs]
        m = min(6, 2*np)
        vals += read_fort_floats(l, m)
        np -= m // 2
        ofs += 1
    xvals = vals[::2]
    yvals = vals[1::2]
    return {'NBT': NBT, 'INT': INT, 'X': xvals,'Y':  yvals}, ofs

def write_tab1_body_lines(NBT, INT, xvals, yvals):
    assert len(NBT) == len(INT)
    assert len(xvals) == len(yvals)
    lines = []
    for i in range(len(NBT)):
        curline = str(NBT[i]).rjust(11) + str(INT[i]).rjust(11) + ' '*44
        lines.append(curline)
    elcnt = 0
    curline = ''
    for x, y in zip(xvals, yvals):
        curline += float2fortstr(x, width=11) + float2fortstr(y, width=11)
        elcnt += 2
        if elcnt == 6:
            elcnt = 0
            lines.append(curline)
            curline = ''
    if elcnt != 0:
        lines.append(curline)
    return lines

