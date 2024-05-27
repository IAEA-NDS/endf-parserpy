############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/27
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from . import cpp_primitives as cpp


def module_header_writing():
    code = r"""

    struct WritingOptions {
      bool abuse_signpos;
      bool keep_E;
    };


    WritingOptions default_writing_options() {
      return WritingOptions{
        false,  // abuse_signpos
        false  // keep_E
      };
    }


    namespace pybind11 { namespace detail {
      template <> struct type_caster<WritingOptions> {
      public:
        PYBIND11_TYPE_CASTER(WritingOptions, _("WritingOptions"));

        // conversion from Python to C++
        bool load(handle src, bool) {
          if (!py::isinstance<py::dict>(src))
            return false;
          auto d = reinterpret_borrow<py::dict>(src);
          py::object keys = d.attr("keys")();
          for (auto key : keys) {
            std::string key_str = py::str(key);
            if (key_str == "abuse_signpos")
              value.abuse_signpos = d["abuse_signpos"].cast<bool>();
            else if (key_str == "keep_E")
              value.keep_E = d["keep_E"].cast<bool>();
            else
              throw std::runtime_error("unknown option `" + key_str + "` provided");
          }

          // use default values for missing options
          WritingOptions default_opts = default_writing_options();

          if (! d.contains("abuse_signpos")) {
            value.abuse_signpos = default_opts.abuse_signpos;
          }
          if (! d.contains("keep_E")) {
            value.keep_E = default_opts.keep_E;
          }
          return true;
        }

        // conversion from C++ to Python
        static handle cast(const WritingOptions &src, return_value_policy, handle) {
          py::dict d;
          d["abuse_signpos"] = src.abuse_signpos;
          d["keep_E"] = src.keep_E;
          return d.release();
        }

      };
    }}


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


    void cpp_write_line_number(std::string& str, int value) {
      cpp_write_custom_int_field(str, 75, 5, value);
    }


    std::string cpp_prepare_line(int mat, int mf, int mt, int &linenum) {
      std::string line(80, ' ');
      line += '\n';
      cpp_write_mat_number(line, mat);
      cpp_write_mf_number(line, mf);
      cpp_write_mt_number(line, mt);
      cpp_write_line_number(line, ++linenum);
      return line;
    }


    std::string float2endfstr_helper(
      double value, int prec, WritingOptions &write_opts
    ) {
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
      if (! write_opts.keep_E) {
        numstr.erase(exp_pos, 1);
      }
      return numstr;
    }


    std::string float2endfstr(double value, WritingOptions &write_opts) {
      std::ostringstream oss;
      std::string numstr;
      int number_length = 10;
      int digits_after_comma = 6;
      if (write_opts.keep_E) {
        digits_after_comma--;
      }
      if (value >= 0 & write_opts.abuse_signpos) {
        number_length++;
        digits_after_comma++;
      }
      numstr = float2endfstr_helper(value, digits_after_comma, write_opts);
      int prec_red = numstr.size() - number_length;
      if (value < 0) {
        prec_red -= 1;
      }
      if (prec_red > 0) {
        numstr = float2endfstr_helper(value, digits_after_comma - prec_red, write_opts);
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
    void cpp_write_field(std::string& line, const char fieldnum, T value, WritingOptions &write_opts) {
      static_assert(std::is_same<T, double>::value || std::is_same<T, int>::value, "T must be int or double");
      std::string fieldstr;
      if (std::is_same<T, double>::value) {
        fieldstr = float2endfstr(value, write_opts);
      } else {
        fieldstr = int2endfstr(value);
      }
      if (fieldstr.size() != 11) { throw std::runtime_error(std::string("wrong size") + std::to_string(fieldstr.size())); }
      line.replace(fieldnum*11, 11, fieldstr);
    }


    void write_tab1_body(
      std::string& line, Tab1Body tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
    ) {
      assert(tab_body.INT.size() == tab_body.NBT.size() && "INT and NBT must have same size");
      assert(tab_body.X.size() == tab_body.Y.size() && "X and Y must have same size");
      int nr = tab_body.INT.size();
      int np = tab_body.X.size();
      std::ostringstream oss;
      std::string curline = cpp_prepare_line(mat, mf, mt, linenum);
      int j = 0;
      for (int i=0; i < nr; i++) {
        cpp_write_field(curline, j++, tab_body.NBT[i], write_opts);
        cpp_write_field(curline, j++, tab_body.INT[i], write_opts);
        if (j > 5 && i+1 < nr) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt, linenum);
          j = 0;
        }
      }
      oss << curline;

      j = 0;
      curline = cpp_prepare_line(mat, mf, mt, linenum);
      for (int i=0; i < np; i++) {
        cpp_write_field(curline, j++, tab_body.X[i], write_opts);
        cpp_write_field(curline, j++, tab_body.Y[i], write_opts);
        if (j > 5 && i+1 < np) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt, linenum);
          j = 0;
        }
      }
      oss << curline;
      line = oss.str();
    }


    void write_tab2_body(
      std::string& line, Tab2Body tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
    ) {
      assert(tab_body.INT.size() == tab_body.NBT.size() && "INT and NBT must have same size");
      int nr = tab_body.INT.size();
      std::ostringstream oss;
      std::string curline = cpp_prepare_line(mat, mf, mt, linenum);
      int j = 0;
      for (int i=0; i < nr; i++) {
        cpp_write_field(curline, j++, tab_body.NBT[i], write_opts);
        cpp_write_field(curline, j++, tab_body.INT[i], write_opts);
        if (j > 5 && i+1 < nr) {
          oss << curline;
          curline = cpp_prepare_line(mat, mf, mt, linenum);
          j = 0;
        }
      }
      oss << curline;
      line = oss.str();
    }


    std::string cpp_prepare_send(int mat, int mf, WritingOptions &write_opts) {
      std::string line(80, ' ');
      line += '\n';
      cpp_write_mat_number(line, mat);
      cpp_write_mf_number(line, mf);
      cpp_write_mt_number(line, 0);
      cpp_write_field(line, 0, 0.0, write_opts);
      cpp_write_field(line, 1, 0.0, write_opts);
      cpp_write_field(line, 2, 0, write_opts);
      cpp_write_field(line, 3, 0, write_opts);
      cpp_write_field(line, 4, 0, write_opts);
      cpp_write_field(line, 5, 0, write_opts);
      if (mf == 0) {
        // for writing FEND/MEND/TEND record
        cpp_write_line_number(line, 0);
      } else {
        cpp_write_line_number(line, 99999);
      }
      return line;
    }


    int get_mat_from_mfmt_section(py::object mfmt_section) {
      int mat;
      if (py::isinstance<py::dict>(mfmt_section)) {
        py::dict mfmt_section_dict = py::cast<py::dict>(mfmt_section);
        mat = py::cast<int>(mfmt_section_dict["MAT"]);
        return mat;
      }
      if (! py::isinstance<py::list>(mfmt_section)) {
        throw std::runtime_error(
          "expect section to be represented by `list` or `dict`"
        );
      }
      py::list mfmt_section_list = py::cast<py::list>(mfmt_section);
      if (mfmt_section_list.size() == 0) {
        throw std::runtime_error("list representing section is empty");
      }
      std::string first_line = py::cast<std::string>(mfmt_section_list[0]);
      std::string matstr = first_line.substr(66, 4);
      mat = std::stoi(matstr);
      return mat;
    }


    void write_section_verbatim(
      std::ostream& oss, py::list mfmt_section, WritingOptions &write_opts
    ) {
      if (mfmt_section.size() == 0) {
        throw std::runtime_error("an MF/MT section must not be represented by an empty list");
      }
      int mat;
      int mf;
      int mt;
      for (const auto& item : mfmt_section) {
        std::string linestr = py::cast<std::string>(item);
        if (linestr.back() != '\n') {
          linestr.push_back('\n');
        }
        mat = cpp_read_mat_number(linestr.c_str());
        mf = cpp_read_mf_number(linestr.c_str());
        mt = cpp_read_mt_number(linestr.c_str());
        oss << linestr;
      }
      std::string send_line = cpp_prepare_send(mat, mf, write_opts);
      oss << send_line;
    }
    """
    return cpp.indent_code(code, -4)


def writefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
        void {fun_name}(
          std::ostream& cont, py::dict endf_dict, WritingOptions &write_opts
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
