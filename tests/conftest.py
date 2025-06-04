from pathlib import Path


def str_to_bool(value):
    if value.lower() in ["true", "1", "yes", "on"]:
        return True
    elif value.lower() in ["false", "0", "no", "off"]:
        return False
    else:
        raise ValueError(f"Invalid truth value: {value}")


def pytest_addoption(parser):
    parser.addoption("--endfdir", type=str, default="testdata")
    parser.addoption("--endffile", type=str, default=None)
    parser.addoption("--mf", type=int, default=None)
    parser.addoption("--ignore_zero_mismatch", type=str_to_bool, default=True)
    parser.addoption("--ignore_number_mismatch", type=str_to_bool, default=False)
    parser.addoption("--ignore_varspec_mismatch", type=str_to_bool, default=False)
    parser.addoption("--fuzzy_matching", type=str_to_bool, default=True)
    parser.addoption("--array_type", type=str, default="dict")
    # defaults writing options chosen to preserve maximal accuracy
    parser.addoption("--abuse_signpos", type=str_to_bool, default=True)
    parser.addoption("--skip_intzero", type=str_to_bool, default=True)
    parser.addoption("--prefer_noexp", type=str_to_bool, default=True)
    # defaults for reading options
    parser.addoption("--accept_spaces", type=str_to_bool, default=True)
    parser.addoption("--ignore_blank_lines", type=str_to_bool, default=False)
    parser.addoption("--ignore_send_records", type=str_to_bool, default=False)
    parser.addoption("--ignore_missing_tpid", type=str_to_bool, default=False)
    parser.addoption("--preserve_value_strings", type=str_to_bool, default=False)
    # endf format
    parser.addoption("--endf_format", type=str, default="endf6-ext")


def pytest_generate_tests(metafunc):
    endf_dir = Path(__file__).parent / metafunc.config.option.endfdir
    if "endf_file" in metafunc.fixturenames:
        file_opt = metafunc.config.option.endffile
        if file_opt is not None:
            endf_files = [endf_dir / file_opt]
        else:
            endf_files = list(endf_dir.glob("*.endf"))
        metafunc.parametrize(
            "endf_file", endf_files, ids=[str(f.name) for f in endf_files]
        )

    parse_opts = (
        "ignore_zero_mismatch",
        "ignore_number_mismatch",
        "ignore_varspec_mismatch",
        "fuzzy_matching",
        "array_type",
        "abuse_signpos",
        "skip_intzero",
        "prefer_noexp",
        "accept_spaces",
        "ignore_blank_lines",
        "ignore_send_records",
        "ignore_missing_tpid",
        "preserve_value_strings",
        "endf_format",
    )

    opts = metafunc.config.option
    for curopt in parse_opts:
        if curopt in metafunc.fixturenames:
            argval = opts.__dict__[curopt]
            metafunc.parametrize(curopt, [argval], scope="module")

    # to selectively test MF sections and MF/MT subsections
    if "mf_sel" in metafunc.fixturenames:
        if metafunc.config.option.mf is not None:
            argval = (int(metafunc.config.option.mf),)
        else:
            argval = None
        metafunc.parametrize("mf_sel", [argval], scope="module")
