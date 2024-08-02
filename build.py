import sys
import os
from glob import glob
from pybind11.setup_helpers import (
    Pybind11Extension,
    intree_extensions,
    build_ext as pybind11_build_ext,
)
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a console handler to inform user about progress
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# create a formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# add the handler to the logger
logger.addHandler(console_handler)


class OptionalBuildExt(pybind11_build_ext):
    def run(self):
        try:
            logger.info(
                "Attempting to compile C++ code for reading/writing ENDF-6 files..."
            )
            super().run()
        except Exception as exc:
            logger.warn(
                f"Failed to compile C++ read/write module code. "
                + "Accelerated parsing will not be available."
            )


def build(setup_kwargs):
    # perform option C++ module compilation
    compile_env_var = os.environ.get("INSTALL_ENDF_PARSERPY_CPP", "optional")
    if compile_env_var == "no":
        logger.info(
            "Skipping generation of C++ ENDF-6 read/write module as per environment variable."
        )
        return
    # import function to generate C++ code
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from endf_parserpy.compiler.compiler import _prepare_cpp_parsers_subpackage

    # generate the C++ code module with functions for reading and writing ENDF-6
    logger.info(
        "Generate the C++ modules with functions for reading and writing ENDF-6 files."
    )
    _prepare_cpp_parsers_subpackage(overwrite=True)
    # ext_modules = intree_extensions(glob("endf_parserpy/cpp_parsers/*.cpp"))
    subpackage_prefix = "endf_parserpy.cpp_parsers."
    cpp_files = glob("endf_parserpy/cpp_parsers/*.cpp")
    ext_modules = [
        Pybind11Extension(
            subpackage_prefix + os.path.splitext(os.path.basename(cpp_file))[0],
            [cpp_file],
            extra_compile_args=["-std=c++11"],
        )
        for cpp_file in cpp_files
    ]

    my_build_ext = pybind11_build_ext if compile_env_var == "yes" else OptionalBuildExt
    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmdclass": {"build_ext": my_build_ext},
            "zip_safe": False,
        }
    )
