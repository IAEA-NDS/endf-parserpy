from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--endfdir", action="store", default="testdata")
    parser.addoption("--endffile", action="store", default=None)
    parser.addoption("--mf", action="store", default=None)
    parser.addoption("--ignore_zero_mismatch", action="store", default='true')
    parser.addoption("--ignore_number_mismatch", action="store", default='false')
    parser.addoption("--ignore_varspec_mismatch", action="store", default='false')
    parser.addoption("--fuzzy_matching", action="store", default='true')
    parser.addoption("--blank_as_zero", action="store", default='true')
    # defaults of writing options chosen to preserve maximal accuracy
    parser.addoption("--abuse_signpos", action="store", default='true')
    parser.addoption("--skip_intzero", action="store", default='true')
    parser.addoption("--prefer_noexp", action="store", default='true')


def pytest_generate_tests(metafunc):
    endf_dir = Path(__file__).parent / metafunc.config.option.endfdir
    if "endf_file" in metafunc.fixturenames:
        file_opt = metafunc.config.option.endffile
        if file_opt is not None:
            endf_files = [endf_dir / file_opt]
        else:
            endf_files = endf_dir.glob("*.endf")
        metafunc.parametrize("endf_file", endf_files)

    argval = metafunc.config.option.ignore_zero_mismatch.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("ignore_zero_mismatch", [argval], scope="module")

    argval = metafunc.config.option.ignore_number_mismatch.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("ignore_number_mismatch", [argval], scope="module")

    argval = metafunc.config.option.ignore_varspec_mismatch.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("ignore_varspec_mismatch", [argval], scope="module")

    argval = metafunc.config.option.fuzzy_matching.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("fuzzy_matching", [argval], scope="module")

    argval = metafunc.config.option.blank_as_zero.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("blank_as_zero", [argval], scope="module")

    argval = metafunc.config.option.abuse_signpos.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("abuse_signpos", [argval], scope="module")

    argval = metafunc.config.option.skip_intzero.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("skip_intzero", [argval], scope="module")

    argval = metafunc.config.option.prefer_noexp.lower().strip()
    argval = argval == 'true'
    metafunc.parametrize("prefer_noexp", [argval], scope="module")

    # to selectively test MF sections and MF/MT subsections
    if metafunc.config.option.mf is not None:
        argval = (int(metafunc.config.option.mf),)
    else:
        argval = None
    metafunc.parametrize("mf_sel", [argval], scope="module")
