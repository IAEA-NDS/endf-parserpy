from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--endfdir", action="store", default="testdata")
    parser.addoption("--endffile", action="store", default=None)
    parser.addoption("--ignore_zero_mismatch", action="store", default='true')
    parser.addoption("--fuzzy_matching", action="store", default='true')
    parser.addoption("--blank_as_zero", action="store", default='true')
    parser.addoption("--mf", action="store", default=None)


def pytest_generate_tests(metafunc):
    endf_dir = Path(__file__).parent / metafunc.config.option.endfdir
    if "endf_file" in metafunc.fixturenames:
        file_opt = metafunc.config.option.endffile
        if file_opt is not None:
            endf_files = [endf_dir / file_opt]
        else:
            endf_files = endf_dir.glob("*.endf")
        metafunc.parametrize("endf_file", endf_files)
    # because of default=True for --ignore_zero_mismatch above
    # we know that the option is available and don't need
    # to check for the existence of ignore_zero_match in
    # metafunc.config.option
    argval = metafunc.config.option.ignore_zero_mismatch.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("ignore_zero_mismatch", [argval], scope="module")

    argval = metafunc.config.option.fuzzy_matching.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("fuzzy_matching", [argval], scope="module")

    argval = metafunc.config.option.blank_as_zero.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("blank_as_zero", [argval], scope="module")

    # to selectively test MF sections and MF/MT subsections
    if metafunc.config.option.mf is not None:
        argval = (int(metafunc.config.option.mf),)
    else:
        argval = None
    metafunc.parametrize("mf_sel", [argval], scope="module")
