#ifndef MODULE_HEADER_WRITING_HPP
#define MODULE_HEADER_WRITING_HPP

// When Python merges the various
// C++ files, there is no need
// to include it here
#ifndef PYTHON_COMPILE
#include "module_header.hpp"
#endif

#ifndef DOUBLE_TYPE
#define DOUBLE_TYPE double
#endif


struct WritingOptions {
  bool abuse_signpos;
  bool keep_E;
  bool prefer_noexp;
  bool skip_intzero;
  bool preserve_value_strings;
  bool include_linenum;
  std::string array_type;
};


WritingOptions default_writing_options() {
  return WritingOptions{
    false,  // abuse_signpos
    false,  // keep_E
    false,  // prefer_noexp
    false,  // skip_intzero
    false,  // preserve_value_strings
    true,   // include_linenum
    "dict"  // array_type
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
        else if (key_str == "prefer_noexp")
          value.prefer_noexp = d["prefer_noexp"].cast<bool>();
        else if (key_str == "skip_intzero")
          value.skip_intzero = d["skip_intzero"].cast<bool>();
        else if (key_str == "include_linenum")
          value.include_linenum = d["include_linenum"].cast<bool>();
        else if (key_str == "preserve_value_strings")
          value.preserve_value_strings = d["preserve_value_strings"].cast<bool>();
        else if (key_str == "array_type")
          value.array_type = d["array_type"].cast<std::string>();
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
      if (! d.contains("prefer_noexp")) {
        value.prefer_noexp = default_opts.prefer_noexp;
      }
      if (! d.contains("skip_intzero")) {
        value.skip_intzero = default_opts.skip_intzero;
      }
      if (! d.contains("preserve_value_strings")) {
        value.preserve_value_strings = default_opts.preserve_value_strings;
      }
      if (! d.contains("include_linenum")) {
        value.include_linenum = default_opts.include_linenum;
      }
      if (! d.contains("array_type")) {
        value.array_type = default_opts.array_type;
      }
      return true;
    }

    // conversion from C++ to Python
    static handle cast(const WritingOptions &src, return_value_policy, handle) {
      py::dict d;
      d["abuse_signpos"] = src.abuse_signpos;
      d["keep_E"] = src.keep_E;
      d["prefer_noexp"] = src.prefer_noexp;
      d["skip_intzero"] = src.skip_intzero;
      d["preserve_value_strings"] = src.preserve_value_strings;
      d["include_linenum"] = src.include_linenum;
      d["array_type"] = src.array_type;
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


std::string cpp_prepare_line(
  int mat, int mf, int mt, int &linenum, WritingOptions &write_opts
) {
  int line_width = (write_opts.include_linenum) ? 80 : 75;
  std::string line(line_width, ' ');
  line += '\n';
  cpp_write_mat_number(line, mat);
  cpp_write_mf_number(line, mf);
  cpp_write_mt_number(line, mt);
  if (write_opts.include_linenum) {
    cpp_write_line_number(line, (linenum % 99999)+1);
  }
  linenum++;
  return line;
}


void normalize_exponent(std::string& numstr) {
  size_t strsize = numstr.size();
  size_t zerostart = std::string::npos;
  size_t exp_pos = numstr.find("e");
  if (exp_pos == std::string::npos) {
    throw std::runtime_error("`e` character not found");
  }
  size_t expnum_start = exp_pos+2;
  for (int i=expnum_start; i < strsize; i++) {
    if (numstr[i] != '0') {
      numstr.erase(expnum_start, i-expnum_start);
      return;
    } else if (i+1 == strsize) {
      numstr.erase(expnum_start, i-expnum_start);
      return;
    }
  }
}


std::string get_scientific_numstr(double value, int precision, bool abuse_signpos) {
  std::ostringstream oss;
  oss << std::scientific << std::setprecision(precision) << value;
  std::string numstr = oss.str();
  normalize_exponent(numstr);
  if (! abuse_signpos && value >= 0) {
    numstr.insert(0, " ");
  }
  return numstr;
}


std::string float2endfstr_helper(double value, size_t width, WritingOptions &write_opts)
{
  std::string numstr = get_scientific_numstr(value, 6, write_opts.abuse_signpos);
  // re-calculate precision to match width specification
  size_t prec = 6 - (numstr.size() - width);
  numstr = get_scientific_numstr(value, prec, write_opts.abuse_signpos);
  // in rare cases, we may still be off the desired width due to
  // situations like 9.9999e-10 vs 1.000e-9
  if (numstr.size() < width) {
    std::string old_numstr;
    do {
      old_numstr = numstr;
      numstr = get_scientific_numstr(value, ++prec, write_opts.abuse_signpos);
    } while (numstr.size() <= width);
    numstr = old_numstr;
    if (numstr.size() < width) {
      numstr.insert(0, " ");
    }
  } else if (numstr.size() > width) {
    do {
      numstr = get_scientific_numstr(value, --prec, write_opts.abuse_signpos);
    } while (numstr.size() > width);
  }
  return numstr;
}


std::string float2endfstr_decimal_helper(
  double value, int width, WritingOptions &write_opts
) {
  std::stringstream ss;
  std::string numstr;
  int commapos;
  ss << std::fixed << std::setprecision(16) << value;
  numstr = ss.str();
  commapos = numstr.find('.');
  if (commapos == std::string::npos) {
    throw std::runtime_error("error occured while converting float to string");
  }
  bool is_intzero_case = (
    write_opts.skip_intzero && static_cast<int>(value) == 0
  );
  int prec = width - commapos - 1;
  if (value >= 0 && ! write_opts.abuse_signpos) {
    prec--;
  }
  if (is_intzero_case) {
    prec++;
  }
  if (prec < 0) {
    prec = 0;
  }
  std::stringstream ss2;
  ss2 << std::fixed << std::setprecision(prec) << value;
  // strip insignificant trailing zeros for compatibility with Python output
  std::string sout = ss2.str();
  commapos = numstr.find('.');
  if (commapos != std::string::npos) {
    int last_nonzero_pos = sout.substr(commapos).find_last_not_of('0');
    sout.erase(commapos + last_nonzero_pos + 1);
    if (sout.back() == '.') {
      sout.pop_back();
    } else if (is_intzero_case) {
      // strip unnecessary integer zero
      if (numstr[commapos-1] != '0') {
        throw std::runtime_error("integer zero matching failed");
      }
      sout.erase(commapos-1, 1);
    }
  }
  if (! write_opts.abuse_signpos && value >= 0) {
    sout.insert(0, " ");
  }
  // right-adjust the number
  std::ostringstream oss3;
  oss3 << std::right << std::setw(width) << sout;
  return oss3.str();
}


std::string float2endfstr(double value, WritingOptions &write_opts) {
  std::ostringstream oss;
  std::string numstr;
  int width = 11;
  int effwidth = width;
  if (! write_opts.keep_E) {
      effwidth++;
  }
  numstr = float2endfstr_helper(
    value, effwidth, write_opts
  );
  if (write_opts.prefer_noexp) {
    std::string numstr_noexp = float2endfstr_decimal_helper(
      value, width, write_opts
    );
    if (numstr_noexp.size() <= width) {
      double recon_value = std::stod(numstr);
      double recon_value_noexp = std::stod(numstr_noexp);
      double recon_value_diff = std::abs(recon_value - value);
      double recon_value_reldiff = recon_value_diff / (std::abs(value)+1e-12);
      double recon_value_noexp_diff = std::abs(recon_value_noexp - value);
      double recon_value_noexp_reldiff =  recon_value_noexp_diff / (std::abs(value)+1e-12);
      if (recon_value_reldiff >= recon_value_noexp_reldiff) {
          return numstr_noexp;
      }
    }
  }
  // delete exp character if demanded
  if (! write_opts.keep_E) {
    size_t exp_pos = numstr.find('e');
    numstr.erase(exp_pos, 1);
  }
  return numstr;
}


std::string int2endfstr(int value) {
  std::ostringstream oss;
  oss << std::right << std::setw(11) << value;
  return oss.str();
}


void field_size_check(const std::string& field) {
  if (field.size() != 11) {
    throw std::runtime_error(
      std::string("wrong size")
      + std::to_string(field.size())
      + std::string("  ") + field
    );
  }
}


// value is float case
void cpp_write_field_double(
  std::string& line, const char fieldnum, const double& value,
  WritingOptions& write_opts
) {
  std::string fieldstr = float2endfstr(value, write_opts);
  field_size_check(fieldstr);
  line.replace(fieldnum*11, 11, fieldstr);
}


// value is EndfFloatCpp case
void cpp_write_field_EndfFloatCpp(
  std::string& line, const char fieldnum, const EndfFloatCpp& value,
  WritingOptions& write_opts
) {
  std::string fieldstr;
  std::string orig_str = value.get_original_string();
  if (orig_str.empty() || !write_opts.preserve_value_strings) {
    fieldstr = float2endfstr(value, write_opts);
  } else {
    fieldstr = orig_str;
  }
  field_size_check(fieldstr);
  line.replace(fieldnum*11, 11, fieldstr);
}


// value is int case
void cpp_write_field_int(
  std::string& line, const char fieldnum, const int& value,
  WritingOptions& write_opts
) {
  std::string fieldstr = int2endfstr(value);
  line.replace(fieldnum*11, 11, fieldstr);
}


// templated cpp_write_field
template<typename T>
 void cpp_write_field(
  std::string& line, const char fieldnum, const T& value,
  WritingOptions& write_opts
) {
  static_assert(
    std::is_same<T, double>::value
    || std::is_same<T, EndfFloatCpp>::value
    || std::is_same<T, int>::value
    , "T must be int, double or EndfFloatCpp"
  );
  if (std::is_same<T, double>::value) {
    return cpp_write_field_double(line, fieldnum, value, write_opts);
  } else if (std::is_same<T, EndfFloatCpp>::value) {
    return cpp_write_field_EndfFloatCpp(line, fieldnum, value, write_opts);
  } else {
    return cpp_write_field_int(line, fieldnum, value, write_opts);
  }
}


void write_tab1_body(
  std::string& line, Tab1Body tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  assert(tab_body.INT.size() == tab_body.NBT.size() && "INT and NBT must have same size");
  assert(tab_body.X.size() == tab_body.Y.size() && "X and Y must have same size");
  int nr = tab_body.INT.size();
  int np = tab_body.X.size();
  std::ostringstream oss;
  std::string curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
  int j = 0;
  for (int i=0; i < nr; i++) {
    cpp_write_field(curline, j++, tab_body.NBT[i], write_opts);
    cpp_write_field(curline, j++, tab_body.INT[i], write_opts);
    if (j > 5 && i+1 < nr) {
      oss << curline;
      curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
      j = 0;
    }
  }
  oss << curline;

  j = 0;
  curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
  for (int i=0; i < np; i++) {
    cpp_write_field(curline, j++, tab_body.X[i], write_opts);
    cpp_write_field(curline, j++, tab_body.Y[i], write_opts);
    if (j > 5 && i+1 < np) {
      oss << curline;
      curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
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
  std::string curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
  int j = 0;
  for (int i=0; i < nr; i++) {
    cpp_write_field(curline, j++, tab_body.NBT[i], write_opts);
    cpp_write_field(curline, j++, tab_body.INT[i], write_opts);
    if (j > 5 && i+1 < nr) {
      oss << curline;
      curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
      j = 0;
    }
  }
  oss << curline;
  line = oss.str();
}


std::string cpp_prepare_send(
  int mat, int mf, WritingOptions &write_opts, bool newline=true) {
  int line_width = (write_opts.include_linenum) ? 80 : 75;
  std::string line(line_width, ' ');
  if (newline) {
      line += '\n';
  }
  cpp_write_mat_number(line, mat);
  cpp_write_mf_number(line, mf);
  cpp_write_mt_number(line, 0);
  cpp_write_field<DOUBLE_TYPE>(line, 0, 0.0, write_opts);
  cpp_write_field<DOUBLE_TYPE>(line, 1, 0.0, write_opts);
  cpp_write_field<int>(line, 2, 0, write_opts);
  cpp_write_field<int>(line, 3, 0, write_opts);
  cpp_write_field<int>(line, 4, 0, write_opts);
  cpp_write_field<int>(line, 5, 0, write_opts);
  if (write_opts.include_linenum) {
    if (mf == 0) {
      // for writing FEND/MEND/TEND record
      cpp_write_line_number(line, 0);
    } else {
      cpp_write_line_number(line, 99999);
    }
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
  std::string first_line = py::cast<std::string>(mfmt_section[0]);
  int mat = cpp_read_mat_number(first_line.c_str());
  int mf = cpp_read_mf_number(first_line.c_str());
  int mt = cpp_read_mt_number(first_line.c_str());
  int linenum = (mf != 0) ? 1 : 0;  // linenum starts at 0 for tape head
  for (const auto& item : mfmt_section) {
    std::string linestr = py::cast<std::string>(item);
    if (write_opts.include_linenum) {
      linestr.resize(80);
      cpp_write_line_number(linestr, linenum++);
    } else {
      linestr.erase(75, std::string::npos);
    }
    if (linestr.back() != '\n') {
      linestr.push_back('\n');
    }
    oss << linestr;
  }
  if (mf != 0) {
      std::string send_line = cpp_prepare_send(mat, mf, write_opts);
      oss << send_line;
  }
}

#endif // MODULE_HEADER_WRITING_HPP
