#ifndef MODULE_HEADER_READING_HPP
#define MODULE_HEADER_READING_HPP

// When Python merges the various
// C++ files, there is no need
// to include them here
#ifndef PYTHON_COMPILE
#include "module_header.hpp"
#endif

#ifndef DOUBLE_TYPE
#define DOUBLE_TYPE double
#endif


struct ParsingOptions {
  bool ignore_number_mismatch;
  bool ignore_zero_mismatch;
  bool ignore_varspec_mismatch;
  bool accept_spaces;
  bool ignore_blank_lines;
  bool ignore_send_records;
  bool ignore_missing_tpid;
  bool preserve_value_strings;
  bool validate_control_records;
  std::string array_type;
};


ParsingOptions default_parsing_options() {
  return ParsingOptions{
    false,  // ignore_number_mismatch
    true,  // ignore_zero_mismatch
    true,  // ignore_varspec_mismatch
    true,  // accept_spaces
    false,  // ignore_blank_lines
    false,  // ignore_send_records
    false,  // ignore_missing_tpid
    false,  // preserve_value_strings
    false,  // validate_control_records
    "dict"  // array_type
  };
}


namespace pybind11 { namespace detail {
  template <> struct type_caster<ParsingOptions> {
  public:
    PYBIND11_TYPE_CASTER(ParsingOptions, _("ParsingOptions"));

    // conversion from Python to C++
    bool load(handle src, bool) {
      if (!py::isinstance<py::dict>(src))
        return false;
      auto d = reinterpret_borrow<py::dict>(src);
      py::object keys = d.attr("keys")();
      for (auto key : keys) {
        std::string key_str = py::str(key);
        if (key_str == "ignore_number_mismatch")
          value.ignore_number_mismatch = d["ignore_number_mismatch"].cast<bool>();
        else if (key_str == "ignore_zero_mismatch")
          value.ignore_zero_mismatch = d["ignore_zero_mismatch"].cast<bool>();
        else if (key_str == "ignore_varspec_mismatch")
          value.ignore_varspec_mismatch = d["ignore_varspec_mismatch"].cast<bool>();
        else if (key_str == "accept_spaces")
          value.accept_spaces = d["accept_spaces"].cast<bool>();
        else if (key_str == "ignore_blank_lines")
          value.ignore_blank_lines = d["ignore_blank_lines"].cast<bool>();
        else if (key_str == "ignore_send_records")
          value.ignore_send_records = d["ignore_send_records"].cast<bool>();
        else if (key_str == "ignore_missing_tpid")
          value.ignore_missing_tpid = d["ignore_missing_tpid"].cast<bool>();
        else if (key_str == "preserve_value_strings")
          value.preserve_value_strings = d["preserve_value_strings"].cast<bool>();
        else if (key_str == "validate_control_records")
          value.validate_control_records = d["validate_control_records"].cast<bool>();
        else if (key_str == "array_type")
          value.array_type = d["array_type"].cast<std::string>();
        else
          throw std::runtime_error("unknown option `" + key_str + "` provided");
      }

      // use default values for missing options
      ParsingOptions default_opts = default_parsing_options();

      if (! d.contains("ignore_number_mismatch")) {
        value.ignore_number_mismatch = default_opts.ignore_number_mismatch;
      }

      if (! d.contains("ignore_zero_mismatch")) {
        value.ignore_zero_mismatch = default_opts.ignore_zero_mismatch;
      }

      if (! d.contains("ignore_varspec_mismatch")) {
        value.ignore_varspec_mismatch = default_opts.ignore_varspec_mismatch;
      }

      if (! d.contains("accept_spaces")) {
        value.accept_spaces = default_opts.accept_spaces;
      }

      if (! d.contains("ignore_blank_lines")) {
        value.ignore_blank_lines = default_opts.ignore_blank_lines;
      }

      if (! d.contains("ignore_send_records")) {
        value.ignore_send_records = default_opts.ignore_send_records;
      }

      if (! d.contains("ignore_missing_tpid")) {
        value.ignore_missing_tpid = default_opts.ignore_missing_tpid;
      }

      if (! d.contains("preserve_value_strings")) {
        value.preserve_value_strings = default_opts.preserve_value_strings;
      }

      if (! d.contains("validate_control_records")) {
        value.validate_control_records = default_opts.validate_control_records;
      }

      if (! d.contains("array_type")) {
        value.array_type = default_opts.array_type;
      }

      return true;
    }

    // conversion from C++ to Python
    static handle cast(const ParsingOptions &src, return_value_policy, handle) {
      py::dict d;
      d["ignore_number_mismatch"] = src.ignore_number_mismatch;
      d["ignore_zero_mismatch"] = src.ignore_zero_mismatch;
      d["ignore_varspec_mismatch"] = src.ignore_varspec_mismatch;
      d["accept_spaces"] = src.accept_spaces;
      d["ignore_blank_lines"] = src.ignore_blank_lines;
      d["ignore_send_records"] = src.ignore_send_records;
      d["ignore_missing_tpid"] = src.ignore_missing_tpid;
      d["preserve_value_strings"] = src.preserve_value_strings;
      d["validate_control_records"] = src.validate_control_records;
      d["array_type"] = src.array_type;
      return d.release();
    }

  };
}}


py::object py_create_container(bool list_mode) {
    if (list_mode) {
        return py::list();
    } else {
        return py::dict();
    }
}


py::object py_append_container(py::object pyobj, int key, bool list_mode, py::object elem=py::none()) {
    if (list_mode) {
        if (elem.is_none()) {
            elem = py::list();
        }
        py::list list = pyobj;
        list.append(elem);
        return elem;
    } else {
        if (elem.is_none()) {
            elem = py::dict();
        }
        return pyobj.attr("setdefault")(py::cast(key), elem);
    }
}


template<typename U, typename V, typename W>
void throw_mismatch_error(
  U quantity, V expected_value, W actual_value,
  std::string line, std::string template_line
) {
  std::stringstream errmsg;
  errmsg << "Invalid " << quantity << " encountered! "
         << "Expected " << quantity << "=" << expected_value
         << " but found " << quantity <<"=" << actual_value << std::endl;
  if (template_line.size() > 0) {
    errmsg << "Template: " << template_line << std::endl;
  }
  if (line.size() > 0) {
    errmsg << "Line: " << line << std::endl;
  }
  throw std::runtime_error(errmsg.str());
}


template<typename V, typename W>
void throw_number_mismatch_error(
  V expected_value, W actual_value,
  std::string line, std::string template_line
) {
  std::stringstream errmsg;
  errmsg << "Expected a field to contain the value " << expected_value
         << " but found instead the value " << actual_value << "." << std::endl;
  if (template_line.size() > 0) {
    errmsg << "Template: " << template_line << std::endl;
  }
  if (line.size() > 0) {
    errmsg << "Line: " << line << std::endl;
  }
  throw std::runtime_error(errmsg.str());
}


double endfstr2float(const char* str, ParsingOptions &parse_opts) {
  char tbuf[13];
  int j = 0;
  bool in_number = false;
  bool in_exponent = false;
  int last_nonspace_pos=-1;
  for (int i=10; i >= 0; i--) {
    if (str[i] != ' ') {
      last_nonspace_pos = i;
      break;
    }
  }
  if (last_nonspace_pos == -1) {
    return 0.0;
  }
  for (int i=0; i <= last_nonspace_pos; i++) {
    char c = str[i];
    if (c == ' ') {
      if (parse_opts.accept_spaces || ! in_number) {
        continue;
      } else {
        std::stringstream errmsg;
        errmsg << "encontered number with spaces: \""
               << std::string(str, 11) << "\"" << std::endl;
        throw std::runtime_error(errmsg.str());
      }
    }
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
      if (c == '.' || (c >= '0' && c <= '9') || c == '-' || c == '+') {
        in_number = true;
      }
    }
    tbuf[j++] = c;
  }
  if (j==0) tbuf[j++] = '0';
  tbuf[j++] = '\0';
  return std::stod(tbuf);
}


int endfstr2int(const char* str, ParsingOptions &parse_opts) {
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

// case for EndfFloatCpp
EndfFloatCpp cpp_read_field_EndfFloatCpp(
  const char *str, const char fieldnum, ParsingOptions &parse_opts
) {
  double float_value = endfstr2float(str+fieldnum*11, parse_opts);
  if (parse_opts.preserve_value_strings) {
    std::string orig_str(str+fieldnum*11, 11);
    return EndfFloatCpp(float_value, orig_str);
  } else {
    return EndfFloatCpp(float_value);
  }
}


template<typename T>
T cpp_read_field(const char *str, const char fieldnum, ParsingOptions &parse_opts) {
  static_assert(
    std::is_same<T, EndfFloatCpp>::value
    || std::is_same<T, int>::value
    || std::is_same<T, double>::value
    , "T must be int or double"
  );
  if (std::is_same<T, double>::value) {
    return endfstr2float(str+fieldnum*11, parse_opts);
  } if (std::is_same<T, EndfFloatCpp>::value) {
    return cpp_read_field_EndfFloatCpp(str, fieldnum, parse_opts);
  } else {
    return endfstr2int(str+fieldnum*11, parse_opts);
  }
}


// the next couple of functions are for handling
// are auxiliary functions to amek cpp_validate_field
// for different types (in particular std::vector and std::string)

template<typename T>
typename std::enable_if<std::is_scalar<T>::value, bool>::type
is_zero_check(const T value) {
  return value == 0;
}


template<typename T>
typename std::enable_if<! std::is_scalar<T>::value, bool>::type
is_zero_check(const T value) {
  return false;
}


template<typename U, typename V>
typename std::enable_if<
  (!std::is_scalar<U>::value && !std::is_same<U, DOUBLE_TYPE>::value)
  || (!std::is_scalar<V>::value && !std::is_same<V, DOUBLE_TYPE>::value), void
>::type
cpp_validate_field(
  U expected_value,
  V actual_value,
  bool contains_variable,
  bool contains_desired_number,
  bool contains_inconsistent_varspec,
  std::string exprstr,
  std::string &line_template,
  std::string &line,
  ParsingOptions &parse_opts
) {
  std::stringstream errmsg;
  errmsg << "Both the expected and actual value are vectors --- "
         << "not implemented at the moment" << std::endl;
  throw std::runtime_error(errmsg.str());
}


template<typename U, typename V>
typename std::enable_if<
  (std::is_scalar<U>::value || std::is_same<U, DOUBLE_TYPE>::value)
   && (std::is_scalar<V>::value || std::is_same<V, DOUBLE_TYPE>::value), void
>::type
cpp_validate_field(
  U expected_value,
  V actual_value,
  bool contains_variable,
  bool contains_desired_number,
  bool contains_inconsistent_varspec,
  std::string exprstr,
  std::string &line_template,
  std::string &line,
  ParsingOptions &parse_opts
) {
  if (static_cast<double>(expected_value) == static_cast<double>(actual_value)) return;

  // inconsistency detected
  if (! contains_variable) {
    // dealing with a number
    // ignore zero mismatch only active for scalar data types
    if (is_zero_check(expected_value) && parse_opts.ignore_zero_mismatch) return;
    if (contains_desired_number && parse_opts.ignore_number_mismatch) return;
    throw_number_mismatch_error(expected_value, actual_value, line, line_template);
  } else {
    // dealing with an expression with variables
    if (contains_inconsistent_varspec && parse_opts.ignore_varspec_mismatch) return;
    throw_mismatch_error(exprstr, expected_value, actual_value, line, line_template);
  }
}

// we are done with the cpp_validate_field related functionality

int cpp_read_custom_int_field(const char *str, int start_pos, int length) {
  std::vector<char> strzero(length+1);
  std::memcpy(strzero.data(), str+start_pos, length);
  strzero[length] = '\0';
  for (int i=0; i < length; i++) {
    if (strzero[i] != ' ') {
      return std::atoi(strzero.data());
    }
  }
  return 0;
}


int cpp_read_mat_number(const char *str) {
  return cpp_read_custom_int_field(str, 66, 4);
}


int cpp_read_mf_number(const char *str) {
  return cpp_read_custom_int_field(str, 70, 2);
}


int cpp_read_mt_number(const char *str) {
  return cpp_read_custom_int_field(str, 72, 3);
}


std::string cpp_read_raw_line(std::istream& cont) {
  std::string line;
  std::getline(cont, line);
  return line;
}


std::string cpp_read_line(
  std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::string line;
  std::getline(cont, line);
  if (parse_opts.validate_control_records) {
    int curmat = cpp_read_mat_number(line.c_str());
    int curmf = cpp_read_mf_number(line.c_str());
    int curmt = cpp_read_mt_number(line.c_str());
    if (curmat != mat)
      throw_mismatch_error("MAT", mat, curmat, line, "");
    if (curmf != mf)
      throw_mismatch_error("MF", mf, curmf, line, "");
    if (curmt != mt)
      throw_mismatch_error("MT", mt, curmt, line, "");
  }
  return line;
}


std::string cpp_read_send(std::istream& cont, int mat, int mf, ParsingOptions &parse_opts) {
  std::string line = cpp_read_line(cont, mat, mf, 0, parse_opts);
  int mtnum = cpp_read_mt_number(line.c_str());
  if (cpp_read_field<DOUBLE_TYPE>(line.c_str(), 0, parse_opts) != 0.0 ||
    cpp_read_field<DOUBLE_TYPE>(line.c_str(), 1, parse_opts) != 0.0 ||
    cpp_read_field<int>(line.c_str(), 2, parse_opts) != 0 ||
    cpp_read_field<int>(line.c_str(), 3, parse_opts) != 0 ||
    cpp_read_field<int>(line.c_str(), 4, parse_opts) != 0 ||
    cpp_read_field<int>(line.c_str(), 5, parse_opts) != 0 ||
    mtnum != 0) {

    std::stringstream errmsg;
    errmsg << "Expected SEND record does not contain one!" << std::endl
           << "Line: " << line << std::endl;
    throw std::runtime_error(errmsg.str());
  }
  if (parse_opts.validate_control_records) {
    int curmat = cpp_read_mat_number(line.c_str());
    int curmf = cpp_read_mf_number(line.c_str());
    if (curmat != mat)
      throw_mismatch_error("MAT", mat, curmat, line, "");
    if (curmf != mf)
      throw_mismatch_error("MF", mf, curmf, line, "");
  }
  return line;
}


bool cpp_is_fend_record(std::string line, int mat, ParsingOptions &parse_opts) {
  int curmat = cpp_read_mat_number(line.c_str());
  if (mat != curmat && parse_opts.validate_control_records) {
      throw_mismatch_error("MAT", mat, curmat, line, "");
  }
  int mf = cpp_read_mf_number(line.c_str());
  int mt = cpp_read_mt_number(line.c_str());
  double c1 = cpp_read_field<DOUBLE_TYPE>(line.c_str(), 0, parse_opts);
  double c2 = cpp_read_field<DOUBLE_TYPE>(line.c_str(), 1, parse_opts);
  int n1 = cpp_read_field<int>(line.c_str(), 2, parse_opts);
  int n2 = cpp_read_field<int>(line.c_str(), 3, parse_opts);
  int l1 = cpp_read_field<int>(line.c_str(), 4, parse_opts);
  int l2 = cpp_read_field<int>(line.c_str(), 5, parse_opts);
  bool cond = (c1 == 0.0 && c2 == 0.0 && n1 == 0 && n2 == 0);
  cond &= (l1 == 0 && l2 == 0 && mf == 0 && mt == 0);
  return cond;
}


bool cpp_is_mend_record(std::string line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.c_str());
  bool cond = cpp_is_fend_record(line, 0, parse_opts);
  cond &= (mat == 0);
  return cond;
}


bool cpp_is_tend_record(std::string line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.c_str());
  bool cond = cpp_is_fend_record(line, -1, parse_opts);
  cond &= (mat == -1);
  return cond;
}


bool cpp_is_blank_line(std::string line) {
  for (int i=0; i < line.size(); i++) {
    if (line[i] != ' ') return false;
  }
  return true;
}

template<typename T>
std::vector<T> cpp_read_vec(
  std::istream& cont, const int numel, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  int j = 0;
  std::vector<T> res;
  std::string line = cpp_read_line(cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i++) {
    res.push_back(cpp_read_field<T>(line.c_str(), j++, parse_opts));
    if (j > 5 && i+1 < numel) {
      line = cpp_read_line(cont, mat, mf, mt, parse_opts);
      j = 0;
    }
  }
  return res;
}


template<typename T>
std::vector<T> cpp_read_vec_debug(
  std::istream& cont, std::string& line, const int numel, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  int j = 0;
  std::vector<T> res;
  std::ostringstream oss;
  std::string curline = cpp_read_line(cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i++) {
    res.push_back(cpp_read_field<T>(curline.c_str(), j++, parse_opts));
    if (j > 5 && i+1 < numel) {
      oss << curline << std::endl;
      curline = cpp_read_line(cont, mat, mf, mt, parse_opts);
      j = 0;
    }
  }
  oss << curline << std::endl;
  line = oss.str();
  return res;
}


Tab2Body read_tab2_body_debug(
  std::istream& cont, std::string& line, int nr, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::ostringstream oss;
  std::string tmpline;
  Tab2Body tab_body;
  std::vector<int> interp = cpp_read_vec_debug<int>(cont, tmpline, 2*nr, mat, mf, mt, parse_opts);
  oss << tmpline;
  int j = 0;
  for (int i=0; i < nr; i++) {
    tab_body.NBT.push_back(interp[j++]);
    tab_body.INT.push_back(interp[j++]);
  }
  line = oss.str();
  return tab_body;
}


Tab2Body read_tab2_body(
  std::istream& cont, int nr, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  Tab2Body tab_body;
  std::vector<int> interp = cpp_read_vec<int>(cont, 2*nr, mat, mf, mt, parse_opts);
  int j = 0;
  for (int i=0; i < nr; i++) {
    tab_body.NBT.push_back(interp[j++]);
    tab_body.INT.push_back(interp[j++]);
  }
  return tab_body;
}


Tab1Body read_tab1_body_debug(
  std::istream& cont, std::string& line, int nr, int np,
  int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::ostringstream oss;
  std::string tmpline;
  Tab1Body tab_body;
  std::vector<int> interp = cpp_read_vec_debug<int>(cont, tmpline, 2*nr, mat, mf, mt, parse_opts);
  oss << tmpline;
  int j = 0;
  for (int i=0; i < nr; i++) {
    tab_body.NBT.push_back(interp[j++]);
    tab_body.INT.push_back(interp[j++]);
  }
  std::vector<DOUBLE_TYPE> data = cpp_read_vec_debug<DOUBLE_TYPE>(cont, tmpline, 2*np, mat, mf, mt, parse_opts);
  oss << tmpline;
  j = 0;
  for (int i=0; i < np; i++) {
    tab_body.X.push_back(data[j++]);
    tab_body.Y.push_back(data[j++]);
  }
  line = oss.str();
  return tab_body;
}


Tab1Body read_tab1_body(
  std::istream& cont, int nr, int np,
  int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  Tab1Body tab_body;
  std::vector<int> interp = cpp_read_vec<int>(cont, 2*nr, mat, mf, mt, parse_opts);
  int j = 0;
  for (int i=0; i < nr; i++) {
    tab_body.NBT.push_back(interp[j++]);
    tab_body.INT.push_back(interp[j++]);
  }
  std::vector<DOUBLE_TYPE> data = cpp_read_vec<DOUBLE_TYPE>(cont, 2*np, mat, mf, mt, parse_opts);
  j = 0;
  for (int i=0; i < np; i++) {
    tab_body.X.push_back(data[j++]);
    tab_body.Y.push_back(data[j++]);
  }
  return tab_body;
}


std::vector<std::string> read_section_verbatim(
    int mat, int mf, int mt, std::istream& cont, bool is_first, ParsingOptions &parse_opts
) {
  std::streampos curpos;
  std::string line;
  std::vector<std::string> secvec;
  int curmf;
  int curmt;
  size_t lastpos;
  while (! cont.eof()) {
    line = cpp_read_line(cont, mat, mf, mt, parse_opts);
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

#endif // MODULE_HEADER_READING_HPP
