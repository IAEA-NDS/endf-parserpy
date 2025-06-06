from pathlib import Path
import os
import pytest
import json
from endf_parserpy.interpreter.endf_parser import EndfParserPy
from endf_parserpy.utils.debugging_utils import smart_is_equal, compare_objects
from endf_parserpy.utils.user_tools import sanitize_fieldname_types


@pytest.fixture(scope="module")
def myEndfParserPy(
    ignore_zero_mismatch,
    ignore_number_mismatch,
    ignore_varspec_mismatch,
    fuzzy_matching,
    array_type,
    abuse_signpos,
    skip_intzero,
    keep_E,
    prefer_noexp,
    accept_spaces,
    ignore_blank_lines,
    ignore_send_records,
    ignore_missing_tpid,
    endf_format,
):
    return EndfParserPy(
        ignore_zero_mismatch=ignore_zero_mismatch,
        ignore_number_mismatch=ignore_number_mismatch,
        ignore_varspec_mismatch=ignore_varspec_mismatch,
        fuzzy_matching=fuzzy_matching,
        array_type=array_type,
        abuse_signpos=abuse_signpos,
        skip_intzero=skip_intzero,
        keep_E=keep_E,
        prefer_noexp=prefer_noexp,
        accept_spaces=accept_spaces,
        ignore_blank_lines=ignore_blank_lines,
        ignore_send_records=ignore_send_records,
        ignore_missing_tpid=ignore_missing_tpid,
        endf_format=endf_format,
    )


def test_endf_parserpy_never_fails(endf_file, myEndfParserPy, mf_sel):
    try:
        endfdic = myEndfParserPy.parsefile(endf_file, include=mf_sel)
    except Exception as exc:
        filename = os.path.basename(endf_file)
        pytest.fail(f"EndfParser failed on file {filename} with exception {exc}")


def test_endf_read_write_read_roundtrip_preserves_content(
    endf_file, tmp_path, myEndfParserPy, mf_sel
):
    endf_dic = myEndfParserPy.parsefile(endf_file, include=mf_sel)
    outfile = tmp_path / os.path.basename(endf_file)
    myEndfParserPy.writefile(outfile, endf_dic)
    endf_dic2 = myEndfParserPy.parsefile(outfile, include=mf_sel)
    compare_objects(endf_dic, endf_dic2, atol=1e-10, rtol=1e-10)
    # also check if same number of lines of original input and output.
    # with include=tuple() sections are not parsed but taken verbatim as string.
    # original files sometimes contain additional whitespace at the end of line
    # or lack the NS line number field so we cut the strings for comparison after 75 characters
    raw_endf = myEndfParserPy.parsefile(endf_file, include=tuple())
    raw_endf2 = myEndfParserPy.parsefile(outfile, include=tuple())
    compare_objects(raw_endf, raw_endf2, strlen_only=True, rstrcut=75)


def test_endf_json_endf_roundtrip_preserves_content(
    endf_file, tmp_path, myEndfParserPy, mf_sel
):
    endf_dic = myEndfParserPy.parsefile(endf_file, include=mf_sel)
    jsonstr = json.dumps(endf_dic, ensure_ascii=False)
    endf_dic2 = json.loads(jsonstr)
    sanitize_fieldname_types(endf_dic2)
    compare_objects(endf_dic, endf_dic2, atol=1e-10, rtol=1e-10)
