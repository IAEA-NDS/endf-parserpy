from lark import Lark, Visitor, Transformer
from lark.reconstruct import Reconstructor

# [MAT, MF, MT/ content] RECORD-TYPE
# [MAT, MF, MT/ HL] TEXT


# [MAT,MF,MT/C1,C2,L1,L2,N1,N2]CONT
# [MAT,MF,MT/ZA,AWR,L1,L2,N1,N2]HEAD

# [MAT,MF,MT/blank,blank,L1,L2,N1,N2]DIR
# [MAT,MF,MT/ C1, C2, L1, L2, NPL, N2/ Bn ] LIST
# [MAT,MF,MT/ C1, C2, L1, L2, NR, NP/xint /y(x)]TAB1
# [MAT,MF,MT/ C1, C2, L1, L2, NR, NZ/ Zint ]TAB2
# [MAT, MF, MT / II, JJ, KIJ ] INTG

mygrammar = r"""
%import common.DIGIT
%import common.NEWLINE
%import common.STRING
%import common.CNAME
%ignore " "

mf1mt451_header : NEWLINE* head_line cont_line cont_line cont_line 

head_line : "[" ctrl_spec "/" head_fields "]" "HEAD" NEWLINE*
head_fields : CFIELD "," CFIELD "," IFIELD "," IFIELD "," IFIELD "," IFIELD 
cont_line : "[" ctrl_spec "/" cont_fields "]" "CONT" NEWLINE* 
cont_fields : CFIELD "," CFIELD "," IFIELD "," IFIELD "," IFIELD "," IFIELD 
ctrl_spec : mat_spec "," mf_spec "," mt_spec
mat_spec : "MAT" | DIGIT+ 
mf_spec : "MF" | DIGIT+
mt_spec : "MT" | DIGIT+
CFIELD: CNAME | "0.0"
IFIELD: CNAME | "0"
"""

myparser = Lark(mygrammar, start='mf1mt451_header')

endf_spec = \
"""
[MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
[MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
[MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
[MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT 
"""

endf_cont = """
 2.906300+4 6.238900+1          1          0          0          52925 1451    1
 0.000000+0 0.000000+0          0          0          0          62925 1451    2
 1.000000+0 1.500000+8          8          0         10          72925 1451    3
 0.000000+0 0.000000+0          0          0        481        1152925 1451    4
 29-Cu- 63 LANL,ORNL  EVAL-FEB98 A.Koning,M.Chadwick,Hetrick      2925 1451    5
"""

tree = myparser.parse(endf_spec)
print(tree.pretty())

def read_cont(line):
    fields = [line[i:i+11] for i in range(0,len(line),11)]
    return fields

def write_cont(fields):
    line = ''.join([str(f).ljust(11) for f in fields]) 
    return line


class EndfConverter(Visitor):

    def head_fields(self, tree):
        varnames = [str(tok) for tok in tree.children]
        if 'ZA' not in varnames or 'AWR' not in varnames:
            raise TypeError('The first two fields of a HEAD record must be named ZA and AWR')
        if self.__mode == 'read':
            values = read_cont(self.__lines[self.__ofs])
            self.__datadic.update({k: v for k,v in zip(varnames, values)}) 
        else:
            d = self.__datadic
            values = [d[k] for k in varnames]
            self.__lines.append(write_cont(values))
        self.__ofs += 1

    def cont_fields(self, tree):
        varnames = [str(tok) for tok in tree.children]
        if self.__mode == 'read': 
            values = read_cont(self.__lines[self.__ofs])
            self.__datadic.update({k: v for k,v in zip(varnames, values)}) 
        else:
            d = self.__datadic
            values = [d[k] for k in varnames]
            self.__lines.append(write_cont(values))
        self.__ofs += 1

    def endf2dic(self, lines, tree):
        self.__ofs = 0
        self.__datadic = {}
        lines = [l for l in lines if l.strip()]
        self.__lines = lines
        self.__mode = 'read'
        super().visit(tree)
        return self.__datadic

    def dic2endf(self, datadic, tree):
        self.__ofs = 0
        self.__datadic = datadic
        self.__lines = []
        self.__mode = 'write'
        super().visit(tree)
        return self.__lines



mylines = endf_cont.splitlines()
converter = EndfConverter()
datadic = converter.endf2dic(mylines, tree)
newline = converter.dic2endf(datadic, tree)
print(datadic)
print(newline)


