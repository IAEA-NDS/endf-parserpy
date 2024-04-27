from glob import glob
from pybind11.setup_helpers import (
    Pybind11Extension,
    intree_extensions,
    build_ext,
)


def build(setup_kwargs):
    print("put your build code here")
    ext_modules = intree_extensions(glob("endf_parserpy/cpp_parsers/*.cpp"))
    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmd_class": {"build_ext": build_ext},
            "zip_safe": False,
        }
    )
