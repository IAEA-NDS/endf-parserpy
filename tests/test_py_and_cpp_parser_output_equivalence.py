import pytest
from endf_parserpy import (
    EndfParserPy,
    EndfParserCpp,
    EndfDict,
)


@pytest.fixture(scope="function")
def mf3_section():
    d = EndfDict()
    d["3/1"] = {}
    dd = d["3/1"]
    dd["MAT"] = 2625
    dd["MF"] = 3
    dd["MT"] = 1
    dd["ZA"] = 26054
    dd["AWR"] = -53.47
    dd["QM"] = 0.0
    dd["QI"] = 0.0
    dd["LR"] = 0
    dd["xstable/E"] = [0, 5, 10, 15, 20]
    dd["xstable/xs"] = [14, 19, 22, 31, 12]
    dd["xstable/NBT"] = [len(dd["xstable/E"])]
    dd["xstable/INT"] = [2]
    return d


def test_prefer_noexp_behavior_equivalence(mf3_section):
    parser_py = EndfParserPy(prefer_noexp=True)
    parser_cpp = EndfParserCpp(prefer_noexp=True)
    endftext_py = parser_py.write(mf3_section)
    endftext_cpp = parser_cpp.write(mf3_section)
    assert endftext_py == endftext_cpp


def test_scientific_rounding_behavior_equivalence(mf3_section):
    # test assumes 11 character field width
    # and we construct numbers to see if both Python
    # and C++ apply the same rounding scheme (banker's rounding)
    mf3_section[3][1]["ZA"] = -2.0000015e15
    mf3_section[3][1]["AWR"] = 1.0000005e1
    mf3_section[3][1]["QM"] = 2.0000015e1
    mf3_section[3][1]["QI"] = -3.000000025
    parser_py = EndfParserPy()
    parser_cpp = EndfParserCpp()
    endftext_py = parser_py.write(mf3_section)
    endftext_cpp = parser_cpp.write(mf3_section)
    assert endftext_py == endftext_cpp


def test_fixdec_rounding_behavior_equivalence(mf3_section):
    # test assumes 11 character field width
    # and we construct numbers to see if both Python
    # and C++ apply the same rounding scheme (banker's rounding)
    mf3_section[3][1]["ZA"] = -2.0000015e15
    mf3_section[3][1]["AWR"] = 1.000000005
    mf3_section[3][1]["QM"] = 2.000000015
    mf3_section[3][1]["QI"] = -3.000000025
    parser_py = EndfParserPy(prefer_noexp=True)
    parser_cpp = EndfParserCpp(prefer_noexp=True)
    endftext_py = parser_py.write(mf3_section)
    endftext_cpp = parser_cpp.write(mf3_section)
    assert endftext_py == endftext_cpp


def test_all_writing_options_equivalence(mf3_section):
    def generate_params():
        for prefer_noexp in (True, False):
            for abuse_signpos in (True, False):
                for skip_intzero in (True, False):
                    for keep_E in (True, False):
                        yield {
                            "prefer_noexp": prefer_noexp,
                            "abuse_signpos": abuse_signpos,
                            "skip_intzero": skip_intzero,
                            "keep_E": keep_E,
                        }

    def generate_numbers():
        for pot in (-150, -100, -99, -11, -10, -9, -5, 0, 5, 9, 10, 11, 99, 100, 150):
            for i in range(1000):
                yield i / 100 * (10**pot)

    numbers = tuple(generate_numbers())
    numbers2 = tuple(1 + n for n in numbers)
    number = numbers + numbers2
    for params in generate_params():
        parser_py = EndfParserPy(**params)
        parser_cpp = EndfParserCpp(**params)
        mf3_section[3][1]["INT"] = [2]
        mf3_section[3][1]["NBT"] = [len(numbers)]
        mf3_section[3][1]["xstable"]["xs"] = numbers
        mf3_section[3][1]["xstable"]["E"] = numbers
        endftext_py = parser_py.write(mf3_section)
        endftext_cpp = parser_cpp.write(mf3_section)
        assert endftext_py == endftext_cpp, f"{params}"
