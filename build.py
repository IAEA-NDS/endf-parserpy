import sys
import os
from glob import glob
from pybind11.setup_helpers import (
    Pybind11Extension,
    intree_extensions,
    build_ext as pybind11_build_ext,
)
import logging


class CustomBuildExt(pybind11_build_ext):
    def run(self):
        try:
            logging.info(
                "Attempting to compile C++ code for reading/writing ENDF-6 files..."
            )
            super().run()
        except Exception as exc:
            logging.warn(
                f"Failed to compile C++ read/write module code. "
                + "Accelerated parsing will not be available."
            )


def build(setup_kwargs):
    compile_env_var = os.environ.get("INSTALL_ENDF_PARSERPY_CPP", "yes")
    if compile_env_var != "yes":
        return
    # import function to generate C++ code
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from endf_parserpy.compiler.compiler import _prepare_cpp_parsers_subpackage

    # generate the C++ code module with functions for reading and writing ENDF-6
    _prepare_cpp_parsers_subpackage(overwrite=True)
    ext_modules = intree_extensions(glob("endf_parserpy/cpp_parsers/*.cpp"))
    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmd_class": {"build_ext": CustomBuildExt},
            "zip_safe": False,
        }
    )
