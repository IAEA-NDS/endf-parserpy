############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from ..compat_wrappers.importlib_resources import open_text
from . import cpp_primitives as cpp


def module_header_reading():
    with open_text(
        "endf_parserpy.compiler.cpp_templates", "module_header_reading.hpp"
    ) as f:
        code = f.read()

    return code


def _registration_code(code):
    return cpp.indent_code(code, -4)


# the commented-out registration of ParsingOptions (kept for reference)
_PARSING_OPTIONS_COMMENT = r"""
    // static bool parsing_options_registered = false;
    // if (! parsing_options_registered) {
    //   py::class_<ParsingOptions>(m, "ParsingOptions")
    //     .def(py::init<>())
    //     .def_readwrite("ignore_number_mismatch", &ParsingOptions::ignore_number_mismatch)
    //     .def_readwrite("ignore_zero_mismatch", &ParsingOptions::ignore_zero_mismatch)
    //     .def_readwrite("ignore_varspec_mismatch", &ParsingOptions::ignore_varspec_mismatch)
    //     .def_readwrite("accept_spaces", &ParsingOptions::accept_spaces)
    //     .def_readwrite("ignore_blank_lines", &ParsingOptions::ignore_blank_lines)
    //     .def_readwrite("ignore_send_records", &ParsingOptions::ignore_send_records)
    //     .def_readwrite("ignore_missing_tpid", &ParsingOptions::ignore_missing_tpid)
    //     .def_readwrite("validate_control_records", &ParsingOptions::validate_control_records);
    //   parsing_options_registered = true;
    // }

"""


_LINE_READ_COUNTS = r"""    // numbers of lines read as views and as copies (see CppLine) since
    // the module was loaded or the last reset, for tests
    m.def("_line_read_counts", [](bool reset) {
      cpp_line_read_counts& counts = cpp_line_read_counter();
      py::tuple res = py::make_tuple(counts.views, counts.copies);
      if (reset) {
        counts.views = 0;
        counts.copies = 0;
      }
      return res;
    }, py::arg("reset") = false);

"""


_ROW_SELECTION_WARNING = r"""    // the row kernel for float fields, selected once when the module is
    // loaded (see cpp_row_selected)
    {
      const cpp_row_selection& sel = cpp_row_selected();
      if (sel.warning != nullptr) {
        std::string msg = std::string("ENDF_PARSERPY_CPP_BULK_BODIES=")
          + sel.requested + ": " + sel.warning;
        if (PyErr_WarnEx(PyExc_RuntimeWarning, msg.c_str(), 1) < 0) {
          throw py::error_already_set();
        }
      }
    }

"""


_BULK_BODY_INFO = r"""    // the selected row kernel, the tiers and the CPU features, for tests
    // and diagnostics; the content may change between versions
    m.def("_bulk_body_info", []() {
      const cpp_row_selection& sel = cpp_row_selected();
      py::dict cpu;
      cpu["detected"] = sel.cpu.detected;
      cpu["os_ymm"] = sel.cpu.os_ymm;
      cpu["os_zmm"] = sel.cpu.os_zmm;
      cpu["fma"] = sel.cpu.fma;
      cpu["avx2"] = sel.cpu.avx2;
      cpu["avx512f"] = sel.cpu.avx512f;
      cpu["avx512dq"] = sel.cpu.avx512dq;
      cpu["avx512bw"] = sel.cpu.avx512bw;
      cpu["avx512vl"] = sel.cpu.avx512vl;
      cpu["avx512vbmi"] = sel.cpu.avx512vbmi;
      cpu["neon"] = sel.cpu.neon;
      py::dict tiers;
      const cpp_row_tier* table = cpp_row_tiers();
      for (int i = 0; i < CPP_ROW_NUM_TIERS; i++) {
        py::dict tier;
        tier["built"] = table[i].kernel != nullptr;
        tier["supported"] = table[i].supported(sel.cpu);
        tier["vector"] = table[i].vector;
        tier["auto"] = cpp_row_tier_auto(table, i);
        tiers[table[i].name] = tier;
      }
      py::dict info;
      info["variable"] = "ENDF_PARSERPY_CPP_BULK_BODIES";
      info["requested"] = sel.requested_set ? py::object(py::str(sel.requested)) : py::object(py::none());
      info["selected"] = sel.tier;
      info["warning"] = sel.warning != nullptr ? py::object(py::str(sel.warning)) : py::object(py::none());
      info["tiers"] = tiers;
      info["cpu"] = cpu;
      info["compiler"] = cpp_row_compiler();
      info["scalar_kernel_lines"] = cpp_row_scalar_lines();
      // the LIST bodies read in the bulk form (see CppListBody)
      const cpp_list_bulk_counts& bulk = cpp_list_bulk_counter();
      py::dict list_bodies;
      list_bodies["strided"] = bulk.strided;
      list_bodies["looped"] = bulk.looped;
      list_bodies["stopped"] = bulk.stopped;
      list_bodies["byte_range"] = bulk.byte_range;
      list_bodies["line_by_line"] = bulk.line_by_line;
      list_bodies["row_bodies"] = bulk.row_bodies;
      list_bodies["row_values"] = bulk.row_values;
      list_bodies["row_rows"] = bulk.row_rows;
      info["bulk_list_bodies"] = list_bodies;
      info["bulk_all_list_bodies"] = sel.list_all;
      return info;
    });
    """


# The names of the compile definitions with the values of the build that
# _build_info reports, set by setup.py and by the CMakeLists.txt of
# create_project_files. Each value is the text as "0x" followed by two
# hexadecimal digits per byte (see build_info_value), a preprocessing
# number that needs no quoting on the command line of any compiler or
# build tool; the module turns it into a string with the preprocessor
# (#) and decodes it.
BUILD_INFO_MACROS = {
    "origin": "ENDF_PARSERPY_BUILD_ORIGIN",
    "build_type": "ENDF_PARSERPY_BUILD_TYPE",
    "optimization_flags": "ENDF_PARSERPY_BUILD_OPTIM",
}


def build_info_value(text):
    """The value of a compile definition of ``BUILD_INFO_MACROS`` for
    ``text``, e.g. ``0x2d4f31`` for ``-O1``."""
    return "0x" + text.encode("utf-8").hex()


_BUILD_INFO = r"""// how the module was built, for diagnostics and benchmark records;
    // the content may change between versions. The compiler and the C++
    // standard are those of the compiler; the origin, the build type and
    // the optimization flags are given by the build (setup.py or the
    // CMakeLists.txt of create_project_files) as compile definitions
    // with the text in hexadecimal digits after "0x", and are "unknown"
    // if the build gave none.
    #define ENDF_PARSERPY_BUILD_STR_(x) #x
    #define ENDF_PARSERPY_BUILD_STR(x) ENDF_PARSERPY_BUILD_STR_(x)
    m.def("_build_info", []() {
      auto decode = [](const char* hex) -> std::string {
        auto digit = [](char c) -> int {
          if (c >= '0' && c <= '9') return c - '0';
          if (c >= 'a' && c <= 'f') return c - 'a' + 10;
          if (c >= 'A' && c <= 'F') return c - 'A' + 10;
          return -1;
        };
        std::string text;
        if (hex[0] != '0' || (hex[1] != 'x' && hex[1] != 'X')) {
          return "unknown";
        }
        for (const char* p = hex + 2; *p != '\0'; p += 2) {
          int high = digit(p[0]);
          int low = p[1] != '\0' ? digit(p[1]) : -1;
          if (high < 0 || low < 0) {
            return "unknown";
          }
          text += static_cast<char>(high * 16 + low);
        }
        return text;
      };
      (void) decode;
      py::dict info;
      info["compiler"] = cpp_row_compiler();
    #if defined(__clang__)
      info["compiler_version"] = __clang_version__;
    #elif defined(__GNUC__)
      info["compiler_version"] = __VERSION__;
    #elif defined(_MSC_FULL_VER)
      info["compiler_version"] = std::to_string(_MSC_FULL_VER);
    #else
      info["compiler_version"] = "unknown";
    #endif
    #if defined(_MSVC_LANG)
      long cplusplus = _MSVC_LANG;
    #else
      long cplusplus = __cplusplus;
    #endif
      info["cplusplus"] = cplusplus;
      const char* standard = cplusplus >= 202302L ? "C++23"
        : cplusplus >= 202002L ? "C++20"
        : cplusplus >= 201703L ? "C++17"
        : cplusplus >= 201402L ? "C++14"
        : cplusplus >= 201103L ? "C++11"
        : "C++98";
      info["cpp_standard"] = standard;
    #ifdef NDEBUG
      info["ndebug"] = true;
    #else
      info["ndebug"] = false;
    #endif
      std::string origin = "unknown";
      std::string build_type = "unknown";
      std::string optim = "unknown";
    #ifdef ENDF_PARSERPY_BUILD_ORIGIN
      origin = decode(ENDF_PARSERPY_BUILD_STR(ENDF_PARSERPY_BUILD_ORIGIN));
    #endif
    #ifdef ENDF_PARSERPY_BUILD_TYPE
      build_type = decode(ENDF_PARSERPY_BUILD_STR(ENDF_PARSERPY_BUILD_TYPE));
    #endif
    #ifdef ENDF_PARSERPY_BUILD_OPTIM
      optim = decode(ENDF_PARSERPY_BUILD_STR(ENDF_PARSERPY_BUILD_OPTIM));
    #endif
      info["origin"] = origin;
      info["build_type"] = build_type;
      // the optimization flags of the compiler command line in their
      // order, and the last one, which applies; "none" if there is none
      info["optimization_flags"] = optim;
      std::string last = optim;
      if (optim != "unknown") {
        size_t end = optim.find_last_not_of(' ');
        if (end == std::string::npos) {
          last = "none";
        } else {
          size_t start = optim.find_last_of(' ', end);
          start = start == std::string::npos ? 0 : start + 1;
          last = optim.substr(start, end - start + 1);
        }
      }
      info["optimization"] = last;
      return info;
    });
    """


def register_reading_options():
    """Code in the module init of a C++ module of one flavor: the
    diagnostic functions and the warning about the row kernel."""
    code = (
        _PARSING_OPTIONS_COMMENT
        + _LINE_READ_COUNTS
        + _ROW_SELECTION_WARNING
        + _BULK_BODY_INFO
        + _BUILD_INFO
    )
    return _registration_code(code)


def register_diagnostic_functions():
    """Code that defines the diagnostic functions ``_line_read_counts``,
    ``_bulk_body_info`` and ``_build_info`` in the module ``m``.

    In the module with all flavors, the counters are those of the whole
    module, which every flavor entry exposes, and so is the build
    information, which is the same for all entries.
    """
    return _registration_code(_LINE_READ_COUNTS + _BULK_BODY_INFO + _BUILD_INFO)


def row_selection_warning():
    """Code that issues the warning about the requested row kernel, once
    when the module is loaded."""
    return _registration_code(_ROW_SELECTION_WARNING)


def parsefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        py::dict {fun_name}(
          std::istream& cont, ParsingOptions &parse_opts
        ) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          // the template of the current record for error messages
          const char*& cpp_template = parse_opts.current_template;
          int cpp_nr_val;
          int cpp_np_val;
          bool list_mode = parse_opts.array_type != "dict";
          // array_type="numpy": arrays of numbers are numpy arrays, those
          // of floats unless their original strings are preserved
          bool numpy_ints = parse_opts.array_type == "numpy";
          bool numpy_floats = numpy_ints && ! parse_opts.preserve_value_strings;
        """,
        -8,
    )
    # remove empty first line
    code = "\n".join(code.splitlines()[1:])
    return code


def parsefun_footer():
    code = cpp.statement("return cpp_current_dict", cpp.INDENT)
    code += cpp.close_block()
    return code
