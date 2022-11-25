from pathlib import Path
import os
import pytest
import json
from endf_parserpy.endf_parser import BasicEndfParser
from endf_parserpy.debugging_utils import smart_is_equal, compare_objects
from endf_parserpy.user_tools import sanitize_fieldname_types


@pytest.fixture(scope="module")
def myBasicEndfParser(ignore_zero_mismatch, ignore_number_mismatch,
                      ignore_varspec_mismatch, fuzzy_matching, blank_as_zero,
                      abuse_signpos, skip_intzero, prefer_noexp):
    return BasicEndfParser(ignore_zero_mismatch=ignore_zero_mismatch,
                           ignore_number_mismatch=ignore_number_mismatch,
                           ignore_varspec_mismatch=ignore_varspec_mismatch,
                           fuzzy_matching=fuzzy_matching,
                           blank_as_zero=blank_as_zero,
                           abuse_signpos=abuse_signpos,
                           skip_intzero=skip_intzero,
                           prefer_noexp=prefer_noexp)


def test_endf_parserpy_never_fails(endf_file, myBasicEndfParser, mf_sel):
    try:
        endfdic = myBasicEndfParser.parsefile(endf_file, include=mf_sel)
    except Exception as exc:
        filename = os.path.basename(endf_file)
        pytest.fail(f'BasicEndfParser failed on file {filename} with exception {exc}')


def test_endf_read_write_read_roundtrip_preserves_content(endf_file, tmp_path, myBasicEndfParser, mf_sel):
    endf_dic = myBasicEndfParser.parsefile(endf_file, include=mf_sel)
    outfile = tmp_path / os.path.basename(endf_file)
    myBasicEndfParser.writefile(outfile, endf_dic)
    endf_dic2 = myBasicEndfParser.parsefile(outfile, include=mf_sel)
    compare_objects(endf_dic, endf_dic2, atol=1e-6, rtol=1e-5)
    # also check if same number of lines of original input and output.
    # with include=tuple() sections are not parsed but taken verbatim as string.
    # original files sometimes contain additional whitespace at the end of line
    # or lack the NS line number field so we cut the strings for comparison after 75 characters
    raw_endf = myBasicEndfParser.parsefile(endf_file, include=tuple())
    raw_endf2 = myBasicEndfParser.parsefile(outfile, include=tuple())
    compare_objects(raw_endf, raw_endf2, strlen_only=True, rstrcut=75)


def test_endf_json_endf_roundtrip_preserves_content(endf_file, tmp_path, myBasicEndfParser, mf_sel):
    endf_dic = myBasicEndfParser.parsefile(endf_file, include=mf_sel)
    jsonstr = json.dumps(endf_dic, ensure_ascii=False)
    endf_dic2 = json.loads(jsonstr)
    sanitize_fieldname_types(endf_dic2)
    compare_objects(endf_dic, endf_dic2, atol=1e-6, rtol=1e-5)
