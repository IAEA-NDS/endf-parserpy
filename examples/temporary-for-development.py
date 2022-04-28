import sys
import os
sys.path.append('../')
from endf_parserpy.endf_parser import BasicEndfParser
from endf_parserpy.fortran_utils import float2fortstr

# HEAD record
testline1 = float2fortstr(3) + float2fortstr(5)
testline1 += ''.join(['0'.rjust(11) for t in range(4)])
#testline1+='1111' + '99'.rjust(2) + '333' 
testline1+='1111' + '99'.rjust(2) + '333' 

# LIST record
testline2 = float2fortstr(1) + float2fortstr(2)
testline2+='3'.rjust(11) + '4'.rjust(11) + '10'.rjust(11) + '6'.rjust(11)
testline2+='1111' + '99'.rjust(2) + '333' 

# LIST body
testline3 = float2fortstr(1) + float2fortstr(2)
testline3 += ''.join([str(i).rjust(11) for i in range(3,7)])
testline3+='1111' + '99'.rjust(2) + '333' 

testline4 = float2fortstr(7) + float2fortstr(8)
testline4 += ''.join([str(i).rjust(11) for i in range(9,13)])
testline4+='1111' + '99'.rjust(2) + '333' 

#testlines = [testline1, testline2, testline3, testline4]
testlines = [testline1, testline2, testline3, testline4]

# initialize a parser and parse n_2925_29-Cu-63
parser = BasicEndfParser()
datadic = parser.parse(testlines)
 
# initialize the parser again and use it to write parsed data back
parser = BasicEndfParser()
newlines = parser.write(datadic)

# write it out for comparison with the original file
outlines = '\n'.join(newlines)
with open('../testdata/n_2925_29-Cu-63_back.endf', 'w') as f:
    f.write(outlines)

