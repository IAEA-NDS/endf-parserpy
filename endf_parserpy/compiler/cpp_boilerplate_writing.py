############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/24
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
      line += '\n';
      cpp_write_mat_number(line, mat);
      cpp_write_mf_number(line, mf);
      cpp_write_mt_number(line, mt);
      return line;
    }


    std::string float2endfstr_helper(double value, int prec) {
      std::ostringstream oss;
      oss << std::scientific << std::setprecision(prec) << value;
      std::string numstr = oss.str();
      size_t exp_pos = numstr.find("e");
      size_t strsize = numstr.size();
      size_t zerostart = std::string::npos;
      if (exp_pos == std::string::npos) {
        throw std::runtime_error("`e` character not found");
      }
      for (int i=exp_pos+1; i < strsize; i++) {
        if ((numstr[i] >= '1' && numstr[i] <= '9') || i+1 == strsize) {
          if (zerostart != std::string::npos) {
            numstr.erase(zerostart, i - zerostart);
            break;
          }
        } else if (zerostart == std::string::npos && numstr[i] == '0') {
          zerostart = i;
        }
      }
      numstr.erase(exp_pos, 1);
      return numstr;
    }


    std::string float2endfstr(double value) {
      std::ostringstream oss;
      std::string numstr;
      numstr = float2endfstr_helper(value, 6);
      int prec_red = numstr.size() - 10;
      if (prec_red > 0) {
        numstr = float2endfstr_helper(value, 6 - prec_red);
      }
      oss << std::right << std::setw(11) << numstr;
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
      if (fieldstr.size() != 11) { throw std::runtime_error(std::string("wrong size") + std::to_string(fieldstr.size())); }
      line.replace(fieldnum*11, 11, fieldstr);
    }


    void write_tab1_body(
      std::string& line, Tab1Body tab_body, int mat, int mf, int mt
    ) {
      assert(tab_body.INT.size() == tab_body.NBT.size() && "INT and NBT must have same size");
      assert(tab_body.X.size() == tab_body.Y.size() && "X and Y must have same size");
      int nr = tab_body.INT.size();
      int np = tab_body.X.size();
      std::ostringstream oss;
      std::string curline = cpp_prepare_line(mat, mf, mt);
      int j = 0;
      for (int i=0; i < nr; i++) {
        cpp_write_field(curline, j++, tab_body.NBT[i]);
        cpp_write_field(curline, j++, tab_body.INT[i]);
        if (j > 5 && i+1 < nr) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt);
          j = 0;
        }
      }
      oss << curline;

      j = 0;
      curline = cpp_prepare_line(mat, mf, mt);
      for (int i=0; i < np; i++) {
        cpp_write_field(curline, j++, tab_body.X[i]);
        cpp_write_field(curline, j++, tab_body.Y[i]);
        if (j > 5 && i+1 < np) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt);
          j = 0;
        }
      }
      oss << curline;
      line = oss.str();
    }


    void write_tab2_body(
      std::string& line, Tab2Body tab_body, int mat, int mf, int mt
    ) {
      assert(tab_body.INT.size() == tab_body.NBT.size() && "INT and NBT must have same size");
      int nr = tab_body.INT.size();
      std::ostringstream oss;
      std::string curline = cpp_prepare_line(mat, mf, mt);
      int j = 0;
      for (int i=0; i < nr; i++) {
        cpp_write_field(curline, j++, tab_body.NBT[i]);
        cpp_write_field(curline, j++, tab_body.INT[i]);
        if (j > 5 && i+1 < nr) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt);
          j = 0;
        }
      }
      oss << curline;
      line = oss.str();
    }


    std::string cpp_prepare_send(int mat, int mf) {
      std::string line(75, ' ');
      line += '\n';
      cpp_write_mat_number(line, mat);
      cpp_write_mf_number(line, mf);
      cpp_write_mt_number(line, 0);
      cpp_write_field(line, 0, 0.0);
      cpp_write_field(line, 1, 0.0);
      cpp_write_field(line, 2, 0);
      cpp_write_field(line, 3, 0);
      cpp_write_field(line, 4, 0);
      cpp_write_field(line, 5, 0);
      return line;
    }


    int get_mat_from_mfmt_section(py::object mfmt_section) {
      int mat;
      if (py::isinstance<py::dict>(mfmt_section)) {
        mat = py::cast<int>(mfmt_section["MAT"]);
        return mat;
      }
      std::string first_line;
      if (py::isinstance<py::list>(mfmt_section)) {
        first_line = py::cast<std::string>(mfmt_section[0]);
      }
      std::string matstr = first_line.substr(66, 4);
      mat = std::stoi(matstr);
      return mat;
    }
    """
    return cpp.indent_code(code, -4)


def writefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        void {fun_name}(
          std::ostream& cont, py::dict endf_dict, ParsingOptions &parse_opts
        ) {{
          std::vector<int> cpp_intvec;
          std::vector<double> cpp_floatvec;
          std::string cpp_template;
          double cpp_float_val;
          int cpp_nr_val;
          int cpp_np_val;
          Tab1Body tab1_body;
          Tab2Body tab2_body;
        """,
        -8,
    )
    return code


def writefun_footer():
    code = cpp.close_block()
    return code
