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

from .endf_parser import BasicEndfParser
from .endf_utils import split_sections
import re


class ExtEndfParser(BasicEndfParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_library(self, endf_dic, libtype):
        mt451 = endf_dic[1][451]
        if libtype == 'ENDF/B-VII.0':
            mt451['NLIB'] = 0
            mt451['NVER'] = 7
            mt451['LREL'] = 0
            txt = 'ENDF/B-VII.0'
        elif libtype == 'ENDF/B-VII.1':
            mt451['NLIB'] = 0
            mt451['NVER'] = 7
            mt451['LREL'] = 1
            txt = 'ENDF/B-VII.1'
        elif libtype == 'ENDF/B-VIII.0':
            mt451['NLIB'] = 0
            mt451['NVER'] = 8
            mt451['LREL'] = 0
            txt = 'ENDF/B-VIII.0'
        elif libtype == 'FENDL-3.2':
            mt451['NLIB'] = 33
            mt451['NVER'] = 3
            mt451['LREL'] = 2
            txt = 'FENDL-3.2'
        else:
            raise TypeError('Unknown library type')
        # update the human readable library specification
        if 'DESCRIPTION' not in mt451:
            raise ValueError('No description in MF1/MT451 found')
        descr = mt451['DESCRIPTION']
        if 3 not in descr:
            raise IndexError('No third line found in description')
        if not re.match('---- *[A-Z][^ ]+', descr[3]):
            raise ValueError('Signature of line three is wrong')
        new_descr_line = ('----' + txt).ljust(22) + descr[3][22:]
        descr[3] = new_descr_line

    def get_description(self, endf_dic):
        descr_dic = endf_dic[1][451]['DESCRIPTION']
        descr_list = []
        for k in sorted(descr_dic.keys()):
            descr_list.append(descr_dic[k])
        return '\n'.join(descr_list)

    def set_description(self, endf_dic, text):
        lines = text.splitlines()
        numlines = len(lines)
        endf_dic[1][451]['NWD'] = numlines
        descr_dic = {}
        for k in range(1, numlines+1):
            descr_dic[k] = lines[k-1]
        endf_dic[1][451]['DESCRIPTION'] = descr_dic

    def insert_description(self, endf_dic, text, after_line=0):
        descr = self.get_description(endf_dic)
        lines = descr.splitlines()
        newlines = lines[:after_line] + text.splitlines()
        if after_line < len(lines):
            newlines += lines[after_line:]
        newdescr = '\n'.join(newlines)
        self.set_description(endf_dic, newdescr)

    def update_dictionary(self, endf_dic, lines=None):
        if not lines:
            lines = self.write(endf_dic)
        # determine the lengths of the sections
        # the checks for mf=0 and mt=0 are here
        # to not consider the tape head as a section
        mfdic = split_sections(lines)
        countdic = {}
        numsecs = 0
        for mf, mfsec in mfdic.items():
            if mf == 0:
                continue
            countdic.setdefault(mf, {})
            for mt, mtsec in mfsec.items():
                if mt == 0:
                    continue
                numsecs += 1
                countdic[mf][mt] = len(mtsec)
        # record the length of MF1/MT451 itself
        mf1mt451_len = 4 + endf_dic[1][451]['NWD'] + numsecs
        countdic[1][451] = mf1mt451_len
        # build up a MOD dic to retrieve the
        # previous value of MOD (modified version number)
        moddic = {}
        mt451 = endf_dic[1][451]
        ilist = mt451['MFx'].keys() if 'MFx' in mt451 else tuple()
        for i in ilist:
            curmf = mt451['MFx'][i]
            curmt = mt451['MTx'][i]
            curmod = mt451['MOD'][i]
            moddic[(curmf, curmt)] = curmod
        # construct the dictionaries
        MFx = {}; MTx = {}; NCx = {}; MOD = {}
        i = 0
        for mf, mfsec in countdic.items():
            for mt, count in mfsec.items():
                i += 1
                MFx[i] = mf
                MTx[i] = mt
                NCx[i] = countdic[mf][mt]
                MOD[i] = moddic.get((mf,mt), 0)
        # update MT451
        mt451['MFx'] = MFx
        mt451['MTx'] = MTx
        mt451['NCx'] = NCx
        mt451['MOD'] = MOD
        # finally, update the counter NXC
        mt451['NXC'] = numsecs

    def write(self, endf_dic, exclude=None, include=None, zero_as_blank=False):
        should_skip_mf1mt451 = self.should_skip_section(1, 451, exclude, include)
        has_mf1mt451sec = 1 in endf_dic and 451 in endf_dic[1]
        # we provide a dummy NXC item in case it does not exist.
        # the value will be updated accordingly below
        if not should_skip_mf1mt451 and has_mf1mt451sec:
            endf_dic[1][451]['NXC'] = 0
        # we use the base parser only to split the lines
        # and put them into the nested endf_dic so that
        # we can replace MF1/MT451 with the updated dictionary
        # and write out everything again
        lines = super().write(endf_dic, exclude, include, zero_as_blank)
        # afterwards we update the dictionary and
        # write out once again but with updated dictionary
        if not should_skip_mf1mt451 and has_mf1mt451sec:
            self.update_dictionary(endf_dic, lines)
            endf_dic2 = self.parse(lines, include=[])
            endf_dic2[1][451] = endf_dic[1][451]
            lines = super().write(endf_dic2, exclude, include, zero_as_blank)
        return lines

