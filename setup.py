import setuptools
from glob import glob
import logging
import sys
import os
import platform
from pybind11.setup_helpers import (
    Pybind11Extension,
    build_ext as pybind11_build_ext,
    ParallelCompile,
)


# ParallelCompile patches `CCompiler.compile()` to use a thread pool when
# given a list of sources. It does NOT parallelize across `Extension`
# instances (that's setuptools' own `parallel` knob -- enabled below in
# CustomBuildExt.finalize_options). It does help here for the explicit
# multi-source `self.compiler.compile([...])` call we use to pre-build
# the deduplicated shared chunks ahead of the per-extension build.
ParallelCompile("INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS", default=0).install()

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


class CustomBuildExt(pybind11_build_ext):
    def _create_dynamic_files(self):
        # package functionality is already needed during building the package
        add_project_dir_to_syspath()
        from endf_parserpy.compiler.compiler import (
            _prepare_cpp_parsers_subpackage,
            is_shared_chunk_filename,
        )

        logger.info("Generating C++ modules for ENDF-6 files.")
        cpp_files = _prepare_cpp_parsers_subpackage(
            overwrite=True, only_filenames=False
        )
        # Record exactly the shared translation units that were just
        # generated, so the shared-TU pre-compile uses this authoritative
        # list rather than rediscovering files on disk.
        self._shared_tu_files = [
            os.path.basename(f)
            for f in cpp_files
            if is_shared_chunk_filename(os.path.basename(f))
        ]

    def finalize_options(self):
        super().finalize_options()
        # Enable parallel compilation of the flavor extensions.
        # setuptools' build_ext checks `self.parallel`; if set to N it
        # builds N extensions concurrently via a ThreadPoolExecutor.
        # Default to all CPU cores; user can override (or disable with `1`)
        # via the INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS environment variable.
        if not self.parallel:
            jobs_env = os.environ.get("INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS", "")
            try:
                jobs = int(jobs_env) if jobs_env else (os.cpu_count() or 1)
            except ValueError:
                jobs = os.cpu_count() or 1
            self.parallel = max(jobs, 1)
            logger.info(f"Building C++ extensions with parallel={self.parallel}")

    def _compile_shared_object_if_present(self):
        """Pre-compile all deduplicated shared TUs (``_shared.cpp`` or
        ``_shared_part_NN.cpp``) once each, then attach the resulting
        ``.o`` files to every Pybind11Extension via ``extra_objects``.

        With ``ParallelCompile`` installed at module top, the single
        ``self.compiler.compile([...])`` call below fans out across all
        cores, so multiple shared chunks compile concurrently. The
        per-extension parallel build then proceeds afterwards.

        Must be called *after* pybind11's cxx_std auto-detect has run
        and finalized each extension's ``extra_compile_args`` /
        ``include_dirs``, otherwise the shared TUs are compiled with the
        wrong flags.
        """
        cpp_parsers_dir = os.path.join("endf_parserpy", "cpp_parsers")
        # Use the authoritative list of shared TUs produced by the code
        # generator in _create_dynamic_files, not a directory scan, so a
        # stale shared file from a previous build with a different layout
        # cannot be compiled and linked alongside the current ones. Fall
        # back to a directory scan only if generation did not run.
        shared_names = getattr(self, "_shared_tu_files", None)
        if shared_names is None:
            shared_names = [
                name
                for name in os.listdir(cpp_parsers_dir)
                if name == "_shared.cpp"
                or (name.startswith("_shared_part_") and name.endswith(".cpp"))
            ]
        shared_sources = [
            os.path.join(cpp_parsers_dir, name) for name in sorted(shared_names)
        ]
        if not shared_sources:
            return
        # Filter shared sources out of every extension's source list so
        # the default per-extension build doesn't compile each chunk
        # again (and so we don't end up with the same symbols defined in
        # two object files of the same flavor).
        shared_basenames = {os.path.basename(s) for s in shared_sources}
        for ext in self.extensions:
            ext.sources = [
                s for s in ext.sources if os.path.basename(s) not in shared_basenames
            ]
        if not self.extensions:
            return
        logger.info(
            f"Pre-compiling {len(shared_sources)} shared TU(s) "
            "(ParallelCompile fans out across CPU cores)"
        )
        sample_ext = self.extensions[0]
        objects = self.compiler.compile(
            shared_sources,
            output_dir=self.build_temp,
            macros=sample_ext.define_macros
            + [(u, None) for u in sample_ext.undef_macros],
            include_dirs=sample_ext.include_dirs,
            debug=self.debug,
            extra_postargs=sample_ext.extra_compile_args or [],
            depends=sample_ext.depends,
        )
        if not objects:
            raise RuntimeError(f"failed to compile shared TUs: {shared_sources}")
        logger.info(
            f"Shared TUs compiled to {len(objects)} object file(s); "
            "linking into each flavor"
        )
        for ext in self.extensions:
            existing = list(ext.extra_objects or [])
            ext.extra_objects = existing + list(objects)

    def build_extensions(self):
        # Re-implement pybind11_build_ext's cxx_std auto-detection so we
        # can slot the shared-TU pre-compile in *after* flags are finalized
        # but *before* the per-extension build kicks off.
        from pybind11.setup_helpers import auto_cpp_level

        for ext in self.extensions:
            if hasattr(ext, "_cxx_level") and ext._cxx_level == 0:
                ext.cxx_std = auto_cpp_level(self.compiler)
        try:
            self._compile_shared_object_if_present()
        except Exception as exc:
            logger.error(f"shared-TU pre-compile failed: {exc}")
            raise
        # Skip pybind11_build_ext.build_extensions (we replicated its
        # prefix above) and call setuptools' build_extensions directly.
        from setuptools.command.build_ext import (
            build_ext as _setuptools_build_ext,
        )

        _setuptools_build_ext.build_extensions(self)

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
    """Generate C++ modules from ENDF recipes and register as extension modules.

    Shared TUs (``_shared.cpp`` or ``_shared_part_NN.cpp``) are
    intentionally NOT registered as their own ``Pybind11Extension``.
    They have no PYBIND11_MODULE block and are meant to be compiled
    once and linked into each flavor's ``.so`` as extra objects; that
    wiring happens inside :class:`CustomBuildExt.build_extensions`.
    """
    # package functionality is already needed during building the package
    add_project_dir_to_syspath()
    from endf_parserpy.compiler.compiler import (
        _prepare_cpp_parsers_subpackage,
        is_shared_chunk_filename,
    )

    if cpp_compilation == "no":
        logger.info("Disabling C++ ENDF-6 read/write module generation.")
        return []

    optim_flags = determine_optimization_flags(optim_level)

    logger.info("Retrieve C++ module filenames")
    cpp_files = _prepare_cpp_parsers_subpackage(overwrite=True, only_filenames=True)
    flavor_files = [
        f for f in cpp_files if not is_shared_chunk_filename(os.path.basename(f))
    ]

    subpackage_prefix = "endf_parserpy.cpp_parsers."
    cpp_filepaths = [
        os.path.join("endf_parserpy", "cpp_parsers", f) for f in flavor_files
    ]
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
    )


if __name__ == "__main__":
    main()
