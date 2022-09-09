from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--endfdir", action="store", default="testdata")
    parser.addoption("--endffile", action="store", default=None)


def pytest_generate_tests(metafunc):
    endf_dir = Path(__file__).parent / metafunc.config.option.endfdir
    if "endf_file" in metafunc.fixturenames:
        file_opt = metafunc.config.option.endffile
        if file_opt is not None:
            endf_files = [endf_dir / file_opt]
        else:
            endf_files = endf_dir.glob("*.endf")
        metafunc.parametrize("endf_file", endf_files)
