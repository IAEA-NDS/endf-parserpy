import sys
import os

sys.path.append("../")
from endf_parserpy import EndfParser
from endf_parserpy.utils.user_tools import (
    locate,
    get_endf_values,
    list_unparsed_sections,
    list_parsed_sections,
)

parser = EndfParser()
endf_file = "../tests/testdata/n_2925_29-Cu-63.endf"
endf_dic = parser.parsefile(endf_file)

# list the MF sections present in the ENDF file
endf_dic.keys()
# list the MT sections present in MF3
endf_dic[3].keys()
# list the MF/MT sections that were successfully parsed
list_parsed_sections(endf_dic)
# list the MF/MT sections that were not parsed but
# kept as a list of the lines in the ENDF file
list_unparsed_sections(endf_dic)

# write out the ENDF file
parser.writefile(endf_file + ".writeback", endf_dic)
