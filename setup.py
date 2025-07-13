import setuptools
from glob import glob
import logging
import sys
import os
import platform
from setuptools.command.build_py import build_py as _build_py
from pybind11.setup_helpers import (
    Pybind11Extension,
    build_ext as pybind11_build_ext,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - >>>> setup.py: %(message)s"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def get_package_version():
    version_file = os.path.join(
        os.path.dirname(__file__), "endf_parserpy", "__init__.py"
    )
    with open(version_file, "r") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[-1].strip().strip('"').strip("'")
                logger.info(f"package version: {version}")
                return version
    raise RuntimeError("Unable to find version string")


def add_project_dir_to_syspath():
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def determine_optimization_flags(optim_level):
    """Determine compiler optimization flags from environment variable."""
    if optim_level is None:
        return []
    try:
        optim_level = int(optim_level)
    except ValueError:
        optim_level = None
    if optim_level is None or optim_level not in (0, 1, 2, 3):
        raise ValueError("Optimization level must be 0, 1, 2, or 3.")

    if platform.system() in ("Darwin", "Linux"):
        return [f"-O{optim_level}"]
    elif platform.system() == "Windows":
        if optim_level == 3:
            optim_level = "x"
        return [f"/O{optim_level}"]
    else:
        print(
            f">>>> setup.py: Unrecognized platform {platform.system()} - "
            "ignore optimization level in envvar INSTALL_ENDF_PARSERPY_CPP_OPTIM"
        )
        return []


class CustomBuildPy(_build_py):
    def run(self):
        add_project_dir_to_syspath()
        from endf_parserpy.endf_recipes.utils import _populate_recipe_cache

        logger.info("Populate ENDF recipe cache directory within package directory")
        _populate_recipe_cache(clear_dir=True)
        super().run()


class CustomBuildExt(pybind11_build_ext):
    def _create_dynamic_files(self):
        # package functionality is already needed during building the package
        add_project_dir_to_syspath()
        from endf_parserpy.compiler.compiler import _prepare_cpp_parsers_subpackage

        logger.info("Generating C++ modules for ENDF-6 files.")
        cpp_files = _prepare_cpp_parsers_subpackage(
            overwrite=True, only_filenames=False
        )

    def run(self):
        self._create_dynamic_files()
        super().run()


class OptionalBuildExt(CustomBuildExt):
    def run(self):
        try:
            logger.info("Attempting to compile C++ code for reading/writing ENDF files")
            super().run()
        except Exception as exc:
            logger.warning(
                f"Failed to compile C++ read/write module code. "
                "Accelerated parsing will not be available."
            )
            logger.warning("Reason: %s", exc)


def generate_ext_module_list(cpp_compilation, optim_level):
    """Generate C++ modules from ENDF recipes and register as extension modules."""
    # package functionality is already needed during building the package
    add_project_dir_to_syspath()
    from endf_parserpy.compiler.compiler import _prepare_cpp_parsers_subpackage

    if cpp_compilation == "no":
        logger.info("Disabling C++ ENDF-6 read/write module generation.")
        return []

    optim_flags = determine_optimization_flags(optim_level)

    logger.info("Retrieve C++ module filenames")
    cpp_files = _prepare_cpp_parsers_subpackage(overwrite=True, only_filenames=True)

    subpackage_prefix = "endf_parserpy.cpp_parsers."
    cpp_filepaths = [os.path.join("endf_parserpy", "cpp_parsers", f) for f in cpp_files]
    ext_modules = [
        Pybind11Extension(
            subpackage_prefix + os.path.splitext(os.path.basename(cpp_fp))[0],
            [cpp_fp],
            extra_compile_args=["-std=c++11"] + optim_flags,
        )
        for cpp_fp in cpp_filepaths
    ]
    return ext_modules


def main():
    # these variable values may be substituted before package building
    cibuildwheel_hack = False
    if cibuildwheel_hack:
        os.environ["INSTALL_ENDF_PARSERPY_CPP"] = "__INSTALL_ENDF_PARSERPY_CPP__"
        os.environ["INSTALL_ENDF_PARSERPY_CPP_OPTIM"] = (
            "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__"
        )
    logger.info("Environment variables related to C++ compilation")
    logger.info(f"INSTALL_ENDF_PARSERPY_CPP: {os.getenv('INSTALL_ENDF_PARSERPY_CPP')}")
    logger.info(
        f"INSTALL_ENDF_PARSERPY_CPP_OPTIM: {os.getenv('INSTALL_ENDF_PARSERPY_CPP_OPTIM')}"
    )

    optim_level = os.environ.get("INSTALL_ENDF_PARSERPY_CPP_OPTIM", None)
    cpp_compilation = os.environ.get("INSTALL_ENDF_PARSERPY_CPP", "optional")

    ext_modules = generate_ext_module_list(cpp_compilation, optim_level)
    custom_build_ext = CustomBuildExt if cpp_compilation == "yes" else OptionalBuildExt

    setuptools.setup(
        name="endf-parserpy",
        version=get_package_version(),
        packages=setuptools.find_packages(exclude=["tests*", "docs*", "examples*"]),
        cmdclass={
            "build_py": CustomBuildPy,
            "build_ext": custom_build_ext,
        },
        ext_modules=ext_modules,
        zip_safe=False,
        install_requires=[
            "lark>=1.0.0",
            "platformdirs>=4.3.6",
        ],
    )


if __name__ == "__main__":
    main()
