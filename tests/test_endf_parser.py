from pathlib import Path
import os
import pytest
from endf_parserpy.endf_parser import BasicEndfParser 
from endf_parserpy.debugging_utils import smart_is_equal, compare_objects


@pytest.fixture(scope="module")
def myBasicEndfParser():
    return BasicEndfParser()


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
    endf_dic2 = myBasicEndfParser.parsefile(endf_file)
    compare_objects(endf_dic, endf_dic2, atol=1e-6, rtol=1e-5)
