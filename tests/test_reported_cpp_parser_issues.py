import pytest
from endf_parserpy import EndfParserCpp, EndfDict


def test_mt_injection():
    endf_dict = EndfDict()
    endf_dict["3/1"] = {}
    p = endf_dict["3/1"]
    endf_dict["3/1/MAT"] = 1234
    # C++ parser should do this:
    # endf_dict['3/1/MT'] = 1
    endf_dict["3/1/AWR"] = 100
    endf_dict["3/1/ZA"] = 1
    endf_dict["3/1/QM"] = 0.0
    endf_dict["3/1/QI"] = 0.0
    endf_dict["3/1/LR"] = 0
    endf_dict["3/1/xstable/NBT"] = [5]
    endf_dict["3/1/xstable/INT"] = [2]
    endf_dict["3/1/xstable/E"] = [1.0, 2.0, 3.0, 4.0, 5.0]
    endf_dict["3/1/xstable/xs"] = [10.0, 11.0, 12.0, 13.0, 14.0]
    parser = EndfParserCpp()
    parser.write(endf_dict)
