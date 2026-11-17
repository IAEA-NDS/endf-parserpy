import setuptools
from glob import glob
import logging
import sys
import os
import platform
import re
from pybind11.setup_helpers import (
    Pybind11Extension,
    build_ext as pybind11_build_ext,
    ParallelCompile,
)


# ParallelCompile patches `CCompiler.compile()` to use a thread pool when
# given a list of sources. The C++ code is one extension module whose
# translation units (the shared chunks, one file per flavor and the
# module init) are compiled in parallel this way and linked once.
ParallelCompile("INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS", default=0).install()

# the package of the extension module
CPP_PACKAGE_PREFIX = "endf_parserpy.cpp_parsers."

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


def get_packages():
    return setuptools.find_packages(include=["endf_parserpy*"])


def add_project_dir_to_syspath():
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def determine_optimization_flags(optim_flag):
    """Determine compiler optimization flags from environment variable."""
    if optim_flag == "auto":
        return []

    if optim_flag is not None:
        return [str(optim_flag)]

    if platform.system() in ("Darwin", "Linux"):
        return ["-O1"]

    if platform.system() == "Windows":
        return ["/O2"]

    print(
        f">>>> setup.py: Unrecognized platform {platform.system()} - "
        "ignore optimization level in envvar INSTALL_ENDF_PARSERPY_CPP_OPTIM"
    )
    return []


def remove_stale_flavor_extensions(directory):
    """Remove the extension modules of the flavors from before the module
    with all flavors (e.g. ``endf6.cpython-311-x86_64-linux-gnu.so``) in
    ``directory``, for any Python version and platform.

    In a source checkout with an in-place build, such a file would be
    imported instead of the Python module of the same name that stands
    for the entry of the flavor in the module with all flavors. Only the
    files of the old flavor modules are removed (see
    ``endf_parserpy.cpp_parsers._historical_modules``), no other file.

    Returns the paths of the removed files.
    """
    add_project_dir_to_syspath()
    from endf_parserpy.cpp_parsers._historical_modules import (
        is_stale_extension_filename,
    )

    if not os.path.isdir(directory):
        return []
    removed = []
    for basename in sorted(os.listdir(directory)):
        path = os.path.join(directory, basename)
        if is_stale_extension_filename(basename) and os.path.isfile(path):
            os.remove(path)
            removed.append(path)
            logger.info(f"Removed the extension module of the old layout {path}")
    return removed


def optimization_flags(args, compiler_type):
    """The optimization flags of a compiler command line, in their order
    (the last one applies): ``-O...`` and, for MSVC, ``/O...``."""
    pattern = r"^[-/]O" if compiler_type == "msvc" else r"^-O"
    return [a for a in args if re.match(pattern, a)]


def build_info_macros(compiler, ext, debug):
    """The compile definitions with the build information of the module,
    which its function ``_build_info`` reports: the origin (a wheel built
    by cibuildwheel or a build with setup.py), the build type and the
    optimization flags of the command line of the compiler, i.e. the
    flags of the compiler (with those of Python's configuration and of
    the environment variable CFLAGS), then those of the extension.

    The values are hexadecimal digits (see
    ``endf_parserpy.compiler.cpp_boilerplate_reading.build_info_value``),
    which need no quoting for GCC, Clang or MSVC.
    """
    add_project_dir_to_syspath()
    from endf_parserpy.compiler.cpp_boilerplate_reading import (
        BUILD_INFO_MACROS,
        build_info_value,
    )

    compiler_type = getattr(compiler, "compiler_type", "")
    if compiler_type == "msvc":
        if not getattr(compiler, "initialized", True):
            compiler.initialize()
        base = getattr(
            compiler, "compile_options_debug" if debug else "compile_options", []
        )
    else:
        base = getattr(compiler, "compiler_so_cxx", None) or getattr(
            compiler, "compiler_so", []
        )
    args = list(base or []) + list(ext.extra_compile_args or [])
    origin = "cibuildwheel" if os.environ.get("CIBUILDWHEEL") == "1" else "setup.py"
    values = {
        "origin": origin,
        "build_type": "Debug" if debug else "Release",
        "optimization_flags": " ".join(optimization_flags(args, compiler_type)),
    }
    return [
        (BUILD_INFO_MACROS[key], build_info_value(value))
        for key, value in values.items()
    ]


class CustomBuildExt(pybind11_build_ext):
    def build_extension(self, ext):
        # the build information, from the command line of the compiler
        # (known only now), replacing that of an earlier attempt
        add_project_dir_to_syspath()
        from endf_parserpy.compiler.compiler import CPP_MODULE_NAME

        if ext.name == CPP_PACKAGE_PREFIX + CPP_MODULE_NAME:
            macros = build_info_macros(self.compiler, ext, self.debug)
            names = set(name for name, _ in macros)
            ext.define_macros = [
                m for m in (ext.define_macros or []) if m[0] not in names
            ] + macros
        super().build_extension(ext)

    def _create_dynamic_files(self):
        # package functionality is already needed during building the package
        add_project_dir_to_syspath()
        from endf_parserpy.compiler.compiler import (
            _prepare_cpp_parsers_subpackage,
            CPP_MODULE_NAME,
        )

        logger.info("Generating C++ code for ENDF-6 files.")
        cpp_files = _prepare_cpp_parsers_subpackage(
            overwrite=True, only_filenames=False
        )
        # The translation units that were just generated are the sources
        # of the module (the list computed before the generation may name
        # a shared chunk that turned out empty).
        sources = [os.path.join("endf_parserpy", "cpp_parsers", f) for f in cpp_files]
        for ext in self.extensions:
            if ext.name == CPP_PACKAGE_PREFIX + CPP_MODULE_NAME:
                ext.sources = sources

    def _remove_stale_flavor_extensions(self):
        # the old flavor modules in the source tree (from an in-place
        # build) and in the build directory, whose content setuptools
        # copies into the installation or the wheel
        cpp_parsers = os.path.join("endf_parserpy", "cpp_parsers")
        directories = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), cpp_parsers)
        ]
        if self.build_lib:
            directories.append(os.path.join(self.build_lib, cpp_parsers))
        removed = []
        for directory in directories:
            removed.extend(remove_stale_flavor_extensions(directory))
        if removed:
            logger.info(
                f"Removed {len(removed)} extension module(s) of the flavors "
                "from before the module with all flavors"
            )

    def run(self):
        self._create_dynamic_files()
        self._remove_stale_flavor_extensions()
        super().run()


class OptionalBuildExt(CustomBuildExt):
    def run(self):
        # the state before the first attempt: the options compiler and
        # inplace (build_ext.run replaces the first by the compiler object,
        # setuptools resets the second during the build)
        compiler_option, inplace = self.compiler, self.inplace
        saved = [(ext, list(ext.define_macros or [])) for ext in self.extensions]
        try:
            logger.info("Attempting to compile C++ code for reading/writing ENDF files")
            super().run()
            return
        except Exception as exc:
            logger.warning("Failed to compile C++ read/write module code.")
            logger.warning("Reason: %s", exc)
        # Once more without the vector tiers of the row kernels (e.g. for a
        # compiler that lacks some of their intrinsics), which then only
        # costs speed, not the C++ module.
        logger.warning("Retrying without the vector tiers (CPP_ROW_NO_VECTOR_TIERS)")
        for ext, define_macros in saved:
            ext.define_macros = define_macros + [("CPP_ROW_NO_VECTOR_TIERS", None)]
        self.compiler, self.inplace = compiler_option, inplace
        self.force = True
        try:
            super().run()
        except Exception as exc:
            logger.warning(
                f"Failed to compile C++ read/write module code. "
                "Accelerated parsing will not be available."
            )
            logger.warning("Reason: %s", exc)


def generate_ext_module_list(cpp_compilation, optim_level):
    """Register the extension module with the C++ code of all flavors.

    The module ``endf_parserpy.cpp_parsers._flavors`` has one entry per
    build target. Its translation units are the shared chunks with the
    deduplicated recipe functions, one file per flavor and the module
    init; ``ParallelCompile`` compiles them in parallel and they are
    linked once.
    """
    # package functionality is already needed during building the package
    add_project_dir_to_syspath()
    from endf_parserpy.compiler.compiler import (
        _prepare_cpp_parsers_subpackage,
        CPP_MODULE_NAME,
    )

    if cpp_compilation == "no":
        logger.info("Disabling C++ ENDF-6 read/write module generation.")
        return []

    optim_flags = determine_optimization_flags(optim_level)

    logger.info("Retrieve C++ source filenames")
    cpp_files = _prepare_cpp_parsers_subpackage(overwrite=True, only_filenames=True)
    cpp_filepaths = [os.path.join("endf_parserpy", "cpp_parsers", f) for f in cpp_files]
    ext_modules = [
        Pybind11Extension(
            CPP_PACKAGE_PREFIX + CPP_MODULE_NAME,
            cpp_filepaths,
            extra_compile_args=["-std=c++11"] + optim_flags,
        )
    ]
    return ext_modules


def main():
    # these variable values may be substituted before package building
    cibuildwheel_hack = False
    if cibuildwheel_hack:
        osenv = os.environ
        osenv["INSTALL_ENDF_PARSERPY_CPP"] = "__INSTALL_ENDF_PARSERPY_CPP__"
        osenv["INSTALL_ENDF_PARSERPY_CPP_OPTIM"] = "__INSTALL_ENDF_PARSERPY_CPP_OPTIM__"

    logger.info("Environment variables related to C++ compilation")
    logger.info(f"INSTALL_ENDF_PARSERPY_CPP: {os.getenv('INSTALL_ENDF_PARSERPY_CPP')}")
    logger.info(
        f"INSTALL_ENDF_PARSERPY_CPP_OPTIM: {os.getenv('INSTALL_ENDF_PARSERPY_CPP_OPTIM')}"
    )

    optim_flag = os.environ.get("INSTALL_ENDF_PARSERPY_CPP_OPTIM", None)
    cpp_compilation = os.environ.get("INSTALL_ENDF_PARSERPY_CPP", "optional")

    ext_modules = generate_ext_module_list(cpp_compilation, optim_flag)
    custom_build_ext = CustomBuildExt if cpp_compilation == "yes" else OptionalBuildExt

    setuptools.setup(
        name="endf-parserpy",
        version=get_package_version(),
        packages=get_packages(),
        cmdclass={
            "build_ext": custom_build_ext,
        },
        ext_modules=ext_modules,
        zip_safe=False,
        include_package_data=True,
        # the C++ sources are listed as package data because they are the
        # sources of the extension module, but they are not needed once
        # it is compiled
        exclude_package_data={"endf_parserpy.cpp_parsers": ["*.cpp"]},
    )


if __name__ == "__main__":
    main()
