import setuptools
from glob import glob
import logging
import sys
import os
import platform
from pybind11.setup_helpers import (
    Pybind11Extension,
    build_ext as pybind11_build_ext,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Ensure the necessary flags for optimization
def determine_optimization_flags():
    optim_env_var = os.environ.get("INSTALL_ENDF_PARSERPY_CPP_OPTIM", None)
    if optim_env_var is None:
        return []
    try:
        optim_level = int(optim_env_var)
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
        print(f">>>>> {platform.system()}")
        return [f"-O{optim_level}"]
        # return []


# Ensure the C++ modules are built correctly
def run_custom_build_logic():
    module_path = os.path.dirname(__file__)
    sys.path.insert(0, module_path)  # Add the module path if necessary
    from endf_parserpy.endf_recipes.utils import _populate_recipe_cache

    cibuildwheel_hack = False
    if cibuildwheel_hack:
        os.environ["INSTALL_ENDF_PARSERPY_CPP"] = "__INSTALL_ENDF_PARSERPY_CPP__"
        os.environ["INSTALL_ENDF_PARSERPY_CPP_OPTIM"] = (
            "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__"
        )

    print(">>>>> Environment Variables:")
    print(f"INSTALL_ENDF_PARSERPY_CPP: {os.getenv('INSTALL_ENDF_PARSERPY_CPP')}")
    print(
        f"INSTALL_ENDF_PARSERPY_CPP_OPTIM: {os.getenv('INSTALL_ENDF_PARSERPY_CPP_OPTIM')}"
    )

    print("DEBUG #1")

    _populate_recipe_cache(clear_dir=True)

    print("DEBUG #2")

    compile_env_var = os.environ.get("INSTALL_ENDF_PARSERPY_CPP", "optional")
    if compile_env_var == "no":
        logger.info("Skipping C++ ENDF-6 read/write module generation.")
        return []

    print("DEBUG #3")

    optim_flags = determine_optimization_flags()

    print("DEBUG #4")

    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from endf_parserpy.compiler.compiler import _prepare_cpp_parsers_subpackage

    print("DEBUG #5")

    logger.info("Generating C++ modules for ENDF-6 files.")
    _prepare_cpp_parsers_subpackage(overwrite=True)

    print("DEBUG #6")

    subpackage_prefix = "endf_parserpy.cpp_parsers."
    cpp_files = glob("endf_parserpy/cpp_parsers/*.cpp")
    ext_modules = [
        Pybind11Extension(
            subpackage_prefix + os.path.splitext(os.path.basename(cpp_file))[0],
            [cpp_file],
            extra_compile_args=["-std=c++11"] + optim_flags,
        )
        for cpp_file in cpp_files
    ]

    print("DEBUG #7")
    return ext_modules


# class CustomBuildCommand(setuptools.Command):
#     description = "Custom build step for C++ module and recipe cache population"
#     user_options = []
#
#     def initialize_options(self):
#         # Initialize build_lib and build_base
#         # self.build_lib = None
#         # self.build_base = None
#         # self.build_temp = None
#         # self.plat_name = None  # Explicitly initialize plat_name
#         super().initialize_options()
#
#     def finalize_options(self):
#         # Set default values if they are not provided
#         # if self.build_lib is None:
#         #     self.build_lib = os.path.join(self.distribution.get_name(), "build/lib")
#         # if self.build_base is None:
#         #     self.build_base = os.path.join(self.distribution.get_name(), "build")
#         # if self.build_temp is None:
#         #     self.build_temp = os.path.join(self.build_base, "temp")  # Explicitly set build_temp
#         # if self.plat_name is None:
#         #     self.plat_name = (
#         #         platform.system().lower()
#         #     )  # Set platform name, e.g., 'linux', 'win32', etc.
#         super().finalize_options()
#
#     def run(self):
#         # ext_modules = run_custom_build_logic()
#         # self.distribution.ext_modules = ext_modules
#         # setuptools.Command.run(self)  # Ensure the base class is called
#
#         # Run the custom build logic
#         try:
#             ext_modules = run_custom_build_logic()
#             if not isinstance(ext_modules, list):
#                 raise ValueError("Expected 'ext_modules' to be a list.")
#
#             # Make sure `ext_modules` is properly assigned
#             self.distribution.ext_modules = ext_modules
#             print(f"Successfully built extensions: {ext_modules}")
#
#         except Exception as e:
#             print(f"Error during custom build: {e}")
#             raise
#
#         # Explicitly run the build_ext command to handle C++/C extensions
#         # This is critical if you're working with extensions
#         build_ext = self.get_finalized_command('build_ext')
#         build_ext.run()
#
#         # Make sure the base class is called to handle standard build steps
#         setuptools.Command.run(self)

ext_modules = run_custom_build_logic()


# Update setup.py
setuptools.setup(
    name="endf-parserpy",
    version="0.0.0",
    packages=setuptools.find_packages(),
    cmdclass={"build_ext": pybind11_build_ext},
    ext_modules=ext_modules,
    zip_safe=False,
    install_requires=[
        "pybind11>=2.10.0",
        "lark>=1.0.0",
        "platformdirs>=4.3.6",
    ],
)
