from pathlib import Path
import os
import pytest
import json
from endf_parserpy.endf_parser import BasicEndfParser 
from endf_parserpy.debugging_utils import smart_is_equal, compare_objects
from endf_parserpy.user_tools import sanitize_fieldname_types


@pytest.fixture(scope="module")
def myBasicEndfParser(ignore_zero_mismatch, fuzzy_matching, blank_as_zero):
    return BasicEndfParser(ignore_zero_mismatch=ignore_zero_mismatch,
                           fuzzy_matching=fuzzy_matching,
                           blank_as_zero=blank_as_zero)



def test_endf_parserpy_never_fails(endf_file, myBasicEndfParser):
    try:
        endfdic = myBasicEndfParser.parsefile(endf_file) 
    except Exception as exc:
        filename = os.path.basename(endf_file)
        pytest.fail(f'BasicEndfParser failed on file {filename} with exception {exc}')


def test_endf_read_write_read_roundtrip_preserves_content(endf_file, tmp_path, myBasicEndfParser):
    endf_dic = myBasicEndfParser.parsefile(endf_file)
    outfile = tmp_path / os.path.basename(endf_file)
    myBasicEndfParser.writefile(outfile, endf_dic)
    endf_dic2 = myBasicEndfParser.parsefile(outfile)
    compare_objects(endf_dic, endf_dic2, atol=1e-6, rtol=1e-5)
    # also check if same number of lines of original input and output
    # with include=tuple() sections are not parsed but taken verbatim as string
    raw_endf = myBasicEndfParser.parsefile(endf_file, include=tuple())
    raw_endf2 = myBasicEndfParser.parsefile(outfile, include=tuple())
    compare_objects(raw_endf, raw_endf2, strlen_only=True)


def test_endf_json_endf_roundtrip_preserves_content(endf_file, tmp_path, myBasicEndfParser):
    endf_dic = myBasicEndfParser.parsefile(endf_file)
    jsonstr = json.dumps(endf_dic, ensure_ascii=False)
    endf_dic2 = json.loads(jsonstr)
    sanitize_fieldname_types(endf_dic2)
    compare_objects(endf_dic, endf_dic2, atol=1e-6, rtol=1e-5)
