############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/05/05
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from . import cpp_primitives as cpp
from .cpp_types.cpp_type_information import get_vartype_definitions
from .cpp_types.cpp_varaux import construct_vartype_dtype_enum


def module_header():
    code = r"""
    #include <pybind11/pybind11.h>
    #include <pybind11/stl.h> // Necessary for STL containers like std::map

    #include <stdexcept>
    #include <iostream>
    #include <sstream>
    #include <fstream>
    #include <vector>
    #include <string>

    namespace py = pybind11;


    double endfstr2float(const char* str) {
      char tbuf[13];
      int j = 0;
      bool in_number = false;
      bool in_exponent = false;
      for (int i=0; i < 11; i++) {
        char c = str[i];
        if (c == ' ') continue;
        if (in_number) {
          if (!in_exponent) {
            if (c=='+' || c=='-') {
              tbuf[j++] = 'e';
              in_exponent = true;
            } else if (c=='e' || c=='E') {
              in_exponent = true;
            }
          }
        } else {
          if (c == '.' || (c >= '0' && c <= '9')) {
            in_number = true;
          }
        }
        tbuf[j++] = c;
      }
      if (j==0) tbuf[j++] = '0';
      tbuf[j++] = '\0';
      return std::stod(tbuf);
    }


    int endfstr2int(const char* str) {
      char strzero[12];
      std::memcpy(strzero, str, 11);
      strzero[11] = '\0';
      for (int i=0; i < 11; i++) {
        if (str[i] != ' ') {
          return std::atoi(strzero);
        }
      }
      return 0;
    }


    template<typename T>
    T cpp_read_field(const char *str, const char fieldnum) {
      static_assert(std::is_same<T, double>::value || std::is_same<T, int>::value, "T must be int or double");
      if (std::is_same<T, double>::value) {
        return endfstr2float(str+fieldnum*11);
      } else {
        return endfstr2int(str+fieldnum*11);
      }
    }


    double cpp_read_custom_int_field(const char *str, int start_pos, int length) {
      char strzero[length+1];
      std::memcpy(strzero, str+start_pos, length);
      strzero[length] = '\0';
      for (int i=0; i < length; i++) {
        if (strzero[i] != ' ') {
          return std::atoi(strzero);
        }
      }
      return 0;
    }


    std::string cpp_read_line(std::istream& cont) {
      std::string line;
      std::getline(cont, line);
      return line;
    }


    void cpp_read_send(std::istream& cont) {
      std::string line = cpp_read_line(cont);
      int mtnum = std::stoi(line.substr(72, 3));
      if (cpp_read_field<double>(line.c_str(), 0) != 0.0 ||
        cpp_read_field<double>(line.c_str(), 1) != 0.0 ||
        cpp_read_field<int>(line.c_str(), 2) != 0 ||
        cpp_read_field<int>(line.c_str(), 3) != 0 ||
        cpp_read_field<int>(line.c_str(), 4) != 0 ||
        cpp_read_field<int>(line.c_str(), 5) != 0 ||
        mtnum != 0) {

        std::cout << line << std::endl;  // debug
        throw std::runtime_error("expected SEND record");
      }
    }


    template<typename T>
    std::vector<T> cpp_read_vec(std::istream& cont, const int numel) {
      int j = 0;
      std::vector<T> res;
      std::string line = cpp_read_line(cont);
      for (int i=0; i < numel; i++) {
        res.push_back(cpp_read_field<T>(line.c_str(), j++));
        if (j > 5 && i+1 < numel) {
          line = cpp_read_line(cont);
          j = 0;
        }
      }
      return res;
    }


    struct Tab1Body {
      std::vector<int> INT;
      std::vector<int> NBT;
      std::vector<double> X;
      std::vector<double> Y;
    };


    struct Tab2Body {
      std::vector<int> INT;
      std::vector<int> NBT;
    };


    Tab2Body read_tab2_body(std::istream& cont, int nr) {
      Tab2Body tab_body;
      std::vector<int> interp = cpp_read_vec<int>(cont, 2*nr);
      int j = 0;
      for (int i=0; i < nr; i++) {
        tab_body.NBT.push_back(interp[j++]);
        tab_body.INT.push_back(interp[j++]);
      }
      return tab_body;
    }


    Tab1Body read_tab1_body(std::istream& cont, int nr, int np) {
      Tab1Body tab_body;
      std::vector<int> interp = cpp_read_vec<int>(cont, 2*nr);
      int j = 0;
      for (int i=0; i < nr; i++) {
        tab_body.NBT.push_back(interp[j++]);
        tab_body.INT.push_back(interp[j++]);
      }
      std::vector<double> data = cpp_read_vec<double>(cont, 2*np);
      j = 0;
      for (int i=0; i < np; i++) {
        tab_body.X.push_back(data[j++]);
        tab_body.Y.push_back(data[j++]);
      }
      return tab_body;
    }


    bool seq_contains(py::sequence seq, py::object value) {
      int i = 0;
      for (const auto& item : seq) {
        if (py::cast<py::object>(item).equal(value)) {
          return true;
        }
      }
      return false;
    }


    bool should_parse_section(int mf, int mt, py::object& exclude, py::object& include) {
      py::tuple mf_mt_tup = py::make_tuple(mf, mt);
      if (! exclude.is_none()) {
        if (! py::isinstance<py::sequence>(exclude)) {
          throw std::runtime_error("`exclude` argument must be of sequence type");
        }
        if (seq_contains(exclude, py::int_(mf)) || seq_contains(exclude, mf_mt_tup)) {
          return false;
        } else {
          return true;
        }
      } else if (! include.is_none()) {
        if (! py::isinstance<py::sequence>(include)) {
          throw std::runtime_error("`include` argument must be of sequence type");
        }
        if (seq_contains(include, py::int_(mf)) || seq_contains(include, mf_mt_tup)) {
          return true;
        } else {
          return false;
        }
      } else {
        return true;
      }
    }


    std::vector<std::string> read_section_verbatim(
        int mf, int mt, std::istream& cont, bool is_first=false
    ) {
      std::streampos curpos;
      std::string line;
      std::vector<std::string> secvec;
      int curmf;
      int curmt;
      size_t lastpos;
      while (std::getline(cont, line)) {
        // remove trailing \r that we may
        // get from reading win-style line endings
        lastpos = line.size() - 1;
        if (line[lastpos] == '\r') {
          line.erase(lastpos);
        }
        curmf = std::stoi(line.substr(70, 2));
        curmt = std::stoi(line.substr(72, 3));
        if (curmf != mf || curmt != mt) break;
        // the newline for compatibility with the Python parser
        secvec.push_back(line + "\n");
        curpos = cont.tellg();
      }
      if (! is_first && (curmf != mf || curmt != 0)) {
         std::string errmsg = "expected SEND of MF/MT " +
                              std::to_string(mf) + "/" + std::to_string(mt);
         throw std::runtime_error(errmsg);
      }
      if (is_first) {
        // we rewind one line because in the case of MF0/MT0 (tapeid)
        // we have also consumed the HEAD record of the next section
        cont.seekg(curpos);
      }
      return secvec;
    }


    void raise_vartype_mismatch() {
      std::string errmsg =
        std::string("variable MF now with different type ")
        + "which must not happen. Either ENDF recipe wrong "
        + "or the ENDF file has some forbidden flag values.";
      throw std::runtime_error(errmsg);
    }
    """
    code = cpp.indent_code(code, -4)
    code += cpp.line("")
    code += construct_vartype_dtype_enum()
    code += cpp.line("")
    for vartype_definition in get_vartype_definitions():
        code += vartype_definition
    return code


def parsefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        py::dict {fun_name}(std::istream& cont) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          py::dict cpp_parent_dict;
          py::dict cpp_current_dict;
          py::dict cpp_workdict;
          int cpp_idxnum;
          std::string cpp_line;
          double cpp_float_val;
        """,
        -8,
    )
    return code


def parsefun_footer():
    code = cpp.statement("return cpp_current_dict", cpp.INDENT)
    code += cpp.close_block()
    return code


def register_pybind_module(module_name, inner_code):
    code = cpp.line("") + cpp.line("")
    code += cpp.line(f"PYBIND11_MODULE({module_name}, m) {{")
    code += cpp.indent_code(inner_code, cpp.INDENT)
    code += cpp.close_block()
    return code


def register_cpp_parsefuns(parsefuns, module_name, *extra_args):
    args_str = ", ".join(arg for arg in extra_args)
    args_str = ", " + args_str if args_str != "" else args_str
    code = ""
    for parsefun in parsefuns:
        curcode = cpp.statement(
            f'm.def("{parsefun}", &{parsefun}, "parsing function"{args_str})'
        )
        code += curcode
    return code


def generate_cmake_content(module_name):
    code = cpp.indent_code(
        f"""
        cmake_minimum_required(VERSION 3.12)
        project({module_name})

        find_package(pybind11 REQUIRED)

        # Create the C++ executable
        pybind11_add_module({module_name} SHARED {module_name}.cpp)

        add_compile_options(-O3)
        set_property(TARGET {module_name} PROPERTY CXX_STANDARD 11)
        """,
        -8,
    )
    return code
