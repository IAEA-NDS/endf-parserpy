############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2026/11/05
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


def register_reading_options():
    code = r"""
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

    // numbers of lines read as views and as copies (see CppLine) since
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

    // the row kernel for float fields, selected once when the module is
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

    // the selected row kernel, the tiers and the CPU features, for tests
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
      py::dict tiers;
      const cpp_row_tier* table = cpp_row_tiers();
      for (int i = 0; i < CPP_ROW_NUM_TIERS; i++) {
        py::dict tier;
        tier["built"] = table[i].kernel != nullptr;
        tier["supported"] = table[i].supported(sel.cpu);
        tier["vector"] = table[i].vector;
        tiers[table[i].name] = tier;
      }
      py::dict info;
      info["variable"] = "ENDF_PARSERPY_CPP_BULK_BODIES";
      info["requested"] = sel.requested_set ? py::object(py::str(sel.requested)) : py::object(py::none());
      info["selected"] = sel.tier;
      info["warning"] = sel.warning != nullptr ? py::object(py::str(sel.warning)) : py::object(py::none());
      info["tiers"] = tiers;
      info["cpu"] = cpu;
      info["scalar_kernel_lines"] = cpp_row_scalar_lines();
      // the LIST bodies read in the bulk form (see CppListBody)
      const cpp_list_bulk_counts& bulk = cpp_list_bulk_counter();
      py::dict list_bodies;
      list_bodies["strided"] = bulk.strided;
      list_bodies["looped"] = bulk.looped;
      list_bodies["stopped"] = bulk.stopped;
      list_bodies["byte_range"] = bulk.byte_range;
      list_bodies["line_by_line"] = bulk.line_by_line;
      info["bulk_list_bodies"] = list_bodies;
      info["bulk_all_list_bodies"] = sel.list_all;
      return info;
    });
    """
    return cpp.indent_code(code, -4)


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
