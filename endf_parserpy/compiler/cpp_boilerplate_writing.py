############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/19
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from . import cpp_primitives as cpp


def module_header_writing():
    code = r"""

    void cpp_write_custom_int_field(std::string &str, int start, int length, int value) {
      std::ostringstream oss;
      oss << std::right << std::setw(length) << value;
      str.replace(start, length, oss.str());
    }


    void cpp_write_mat_number(std::string& str, int value) {
      cpp_write_custom_int_field(str, 66, 4, value);
    }


    void cpp_write_mf_number(std::string& str, int value) {
      cpp_write_custom_int_field(str, 70, 2, value);
    }


    void cpp_write_mt_number(std::string& str, int value) {
      cpp_write_custom_int_field(str, 72, 3, value);
    }


    std::string cpp_prepare_line(int mat, int mf, int mt) {
      std::string line(75, ' ');
      cpp_write_mat_number(line, mat);
      cpp_write_mf_number(line, mf);
      cpp_write_mt_number(line, mt);
      return line;
    }


    std::string float2endfstr(double value) {
      std::ostringstream oss;
      oss << std::scientific << std::setprecision(6);
      oss << std::setw(11) << value;
      return oss.str();
    }


    std::string int2endfstr(int value) {
      std::ostringstream oss;
      oss << std::right << std::setw(11) << value;
      return oss.str();
    }


    template<typename T>
    void cpp_write_field(std::string& line, const char fieldnum, T value) {
      static_assert(std::is_same<T, double>::value || std::is_same<T, int>::value, "T must be int or double");
      std::string fieldstr;
      if (std::is_same<T, double>::value) {
        fieldstr = float2endfstr(value);
      } else {
        fieldstr = int2endfstr(value);
      }
      line.replace(fieldnum*11, 11, fieldstr);
    }
    """
    return cpp.indent_code(code, -4)


def writefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        py::dict {fun_name}(
          std::istream& cont, ParsingOptions &parse_opts
        ) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          py::dict cpp_parent_dict;
          py::dict cpp_current_dict;
          std::string cpp_line;
          std::string cpp_template;
          double cpp_float_val;
          std::string cpp_draft_line;
        """,
        -8,
    )
    return code


def writefun_footer():
    code = cpp.statement("return cpp_current_dict", cpp.INDENT)
    code += cpp.close_block()
    return code
