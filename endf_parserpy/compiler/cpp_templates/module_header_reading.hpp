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
  bool accept_nan_inf;
  bool accept_d_exponent;
  bool preserve_value_strings;
  bool validate_control_records;
  bool load_file_into_memory;
  std::string array_type;
};


inline ParsingOptions default_parsing_options() {
  return ParsingOptions{
    false,  // ignore_number_mismatch
    true,  // ignore_zero_mismatch
    true,  // ignore_varspec_mismatch
    true,  // accept_spaces
    false,  // ignore_blank_lines
    false,  // ignore_send_records
    false,  // ignore_missing_tpid
    true,   // accept_nan_inf
    true,   // accept_d_exponent
    false,  // preserve_value_strings
    false,  // validate_control_records
    true,   // load_file_into_memory
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
        else if (key_str == "accept_nan_inf")
          value.accept_nan_inf = d["accept_nan_inf"].cast<bool>();
        else if (key_str == "accept_d_exponent")
          value.accept_d_exponent = d["accept_d_exponent"].cast<bool>();
        else if (key_str == "preserve_value_strings")
          value.preserve_value_strings = d["preserve_value_strings"].cast<bool>();
        else if (key_str == "validate_control_records")
          value.validate_control_records = d["validate_control_records"].cast<bool>();
        else if (key_str == "load_file_into_memory")
          value.load_file_into_memory = d["load_file_into_memory"].cast<bool>();
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

      if (! d.contains("accept_nan_inf")) {
        value.accept_nan_inf = default_opts.accept_nan_inf;
      }

      if (! d.contains("accept_d_exponent")) {
        value.accept_d_exponent = default_opts.accept_d_exponent;
      }

      if (! d.contains("preserve_value_strings")) {
        value.preserve_value_strings = default_opts.preserve_value_strings;
      }

      if (! d.contains("validate_control_records")) {
        value.validate_control_records = default_opts.validate_control_records;
      }

      if (! d.contains("load_file_into_memory")) {
        value.load_file_into_memory = default_opts.load_file_into_memory;
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
      d["accept_nan_inf"] = src.accept_nan_inf;
      d["accept_d_exponent"] = src.accept_d_exponent;
      d["preserve_value_strings"] = src.preserve_value_strings;
      d["validate_control_records"] = src.validate_control_records;
      d["load_file_into_memory"] = src.load_file_into_memory;
      d["array_type"] = src.array_type;
      return d.release();
    }

  };
}}


inline py::object py_create_container(bool list_mode) {
    if (list_mode) {
        return py::list();
    } else {
        return py::dict();
    }
}


inline py::object py_append_container(py::object pyobj, int key, bool list_mode, py::object elem=py::none()) {
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


// Format a value for inclusion in an error message. For floating-point
// values this prints numeric_limits<double>::digits10 significant digits
// instead of the stream default of 6, so that a small difference between
// two otherwise similar values (e.g. AWR=11.89691 vs AWR=11.8969) stays
// visible while remaining free of floating-point rounding noise.
// std::setprecision has no effect on integer or string values.
template<typename T>
inline std::string format_mismatch_value(const T &value) {
  std::stringstream ss;
  ss << std::setprecision(std::numeric_limits<double>::digits10) << value;
  return ss.str();
}


template<typename U, typename V, typename W>
inline void throw_mismatch_error(
  U quantity, V expected_value, W actual_value,
  std::string line, std::string template_line
) {
  std::stringstream errmsg;
  errmsg << "Invalid " << quantity << " encountered! "
         << "Expected " << quantity << "=" << format_mismatch_value(expected_value)
         << " but found " << quantity <<"=" << format_mismatch_value(actual_value) << std::endl;
  if (template_line.size() > 0) {
    errmsg << "Template: " << template_line << std::endl;
  }
  if (line.size() > 0) {
    errmsg << "Line: " << line << std::endl;
  }
  throw std::runtime_error(errmsg.str());
}


template<typename V, typename W>
inline void throw_number_mismatch_error(
  V expected_value, W actual_value,
  std::string line, std::string template_line
) {
  std::stringstream errmsg;
  errmsg << "Expected a field to contain the value " << format_mismatch_value(expected_value)
         << " but found instead the value " << format_mismatch_value(actual_value) << "." << std::endl;
  if (template_line.size() > 0) {
    errmsg << "Template: " << template_line << std::endl;
  }
  if (line.size() > 0) {
    errmsg << "Line: " << line << std::endl;
  }
  throw std::runtime_error(errmsg.str());
}


// Fast exact conversion of a plain decimal number of the form
// [+-]digits[.digits][(e|E)[+-]digits] (as assembled by endfstr2float)
// to double. If the significand has at most 15 digits and the decimal
// exponent is at most 22 in magnitude, both the significand and the
// power of ten are exactly representable and a single IEEE multiplication
// or division yields the correctly rounded result, i.e. the same value as
// std::strtod. Returns false for anything else, in which case std::strtod
// must be used.
inline bool cpp_fast_decimal_to_double(const char* s, double &result) {
  static const double p10[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
  };
  const char* p = s;
  bool neg = false;
  if (*p == '+' || *p == '-') {
    neg = (*p == '-');
    p++;
  }
  unsigned long long mant = 0;
  int ndig = 0;          // significant digits accumulated in mant
  int nfrac = 0;         // digits after the decimal point
  bool any_digit = false;
  for (; *p >= '0' && *p <= '9'; p++) {
    any_digit = true;
    if (mant == 0 && *p == '0') continue;   // leading zeros
    if (++ndig > 15) return false;
    mant = mant * 10 + static_cast<unsigned>(*p - '0');
  }
  if (*p == '.') {
    p++;
    for (; *p >= '0' && *p <= '9'; p++) {
      any_digit = true;
      nfrac++;
      if (mant == 0 && *p == '0') continue;
      if (++ndig > 15) return false;
      mant = mant * 10 + static_cast<unsigned>(*p - '0');
    }
  }
  if (! any_digit) return false;
  int expo = 0;
  if (*p == 'e' || *p == 'E') {
    p++;
    bool eneg = false;
    if (*p == '+' || *p == '-') {
      eneg = (*p == '-');
      p++;
    }
    if (! (*p >= '0' && *p <= '9')) return false;
    for (; *p >= '0' && *p <= '9'; p++) {
      if (expo > 1000) return false;
      expo = expo * 10 + (*p - '0');
    }
    if (eneg) expo = -expo;
  }
  if (*p != '\0') return false;
  int k = expo - nfrac;
  double v = static_cast<double>(mant);
  if (mant != 0) {
    if (k > 22 || k < -22) return false;
    if (k > 0) v *= p10[k];
    else if (k < 0) v /= p10[-k];
  }
  result = neg ? -v : v;
  return true;
}


// Single-pass conversion of the 11 characters of a float field for the
// common case: leading spaces, a decimal number of the form
// [+-]digits[.digits] optionally followed by an exponent introduced by
// e/E (or d/D if accepted) or directly by its sign, and trailing spaces.
// If the significand has at most 15 significant digits and the decimal
// exponent is at most 22 in magnitude, both the significand and the
// power of ten are exactly representable and a single IEEE multiplication
// or division gives the correctly rounded result, i.e. the same value as
// std::strtod. Returns false for any other content of the field, which
// is then handled by the general code path.
inline bool cpp_fast_field_to_double(const char* str, bool accept_d_exponent, double &result) {
  static const double p10[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
  };
  const char* p = str;
  const char* const e = str + 11;
  while (p < e && *p == ' ') p++;
  if (p == e) {
    result = 0.0;   // blank field
    return true;
  }
  bool neg = false;
  if (*p == '+' || *p == '-') {
    neg = (*p == '-');
    p++;
  }
  unsigned long long mant = 0;
  int ndig = 0;          // significant digits accumulated in mant
  int nfrac = 0;         // digits after the decimal point
  bool any_digit = false;
  for (; p < e && *p >= '0' && *p <= '9'; p++) {
    any_digit = true;
    if (mant == 0 && *p == '0') continue;   // leading zeros
    if (++ndig > 15) return false;
    mant = mant * 10 + static_cast<unsigned>(*p - '0');
  }
  if (p < e && *p == '.') {
    p++;
    for (; p < e && *p >= '0' && *p <= '9'; p++) {
      any_digit = true;
      nfrac++;
      if (mant == 0 && *p == '0') continue;
      if (++ndig > 15) return false;
      mant = mant * 10 + static_cast<unsigned>(*p - '0');
    }
  }
  if (! any_digit) return false;
  int expo = 0;
  if (p < e && *p != ' ') {
    char c = *p;
    if (c == 'e' || c == 'E' || ((c == 'd' || c == 'D') && accept_d_exponent)) {
      p++;
      if (p == e) return false;
      c = *p;
    } else if (c != '+' && c != '-') {
      return false;
    }
    bool eneg = false;
    if (c == '+' || c == '-') {
      eneg = (c == '-');
      p++;
    }
    if (p == e || ! (*p >= '0' && *p <= '9')) return false;
    for (; p < e && *p >= '0' && *p <= '9'; p++) {
      expo = expo * 10 + (*p - '0');
    }
    if (eneg) expo = -expo;
  }
  for (; p < e; p++) {
    if (*p != ' ') return false;
  }
  int k = expo - nfrac;
  double v = static_cast<double>(mant);
  if (mant != 0) {
    if (k > 22 || k < -22) return false;
    if (k > 0) v *= p10[k];
    else if (k < 0) v /= p10[-k];
  }
  result = neg ? -v : v;
  return true;
}


// Single-pass conversion of an integer field for the common case:
// leading spaces, an optional sign, at most 9 digits, trailing spaces.
// Returns false for any other content (handled by the general code path).
inline bool cpp_fast_field_to_int(const char* str, int &result) {
  const char* p = str;
  const char* const e = str + 11;
  while (p < e && *p == ' ') p++;
  if (p == e) {
    result = 0;
    return true;
  }
  bool neg = false;
  if (*p == '+' || *p == '-') {
    neg = (*p == '-');
    p++;
  }
  const char* d = p;
  int val = 0;
  for (; p < e && *p >= '0' && *p <= '9'; p++) {
    val = val * 10 + (*p - '0');
  }
  int ndig = static_cast<int>(p - d);
  if (ndig == 0 || ndig > 9) return false;
  for (; p < e; p++) {
    if (*p != ' ') return false;
  }
  result = neg ? -val : val;
  return true;
}


inline double endfstr2float(const char* str, ParsingOptions &parse_opts) {
  double fast_value;
  if (cpp_fast_field_to_double(str, parse_opts.accept_d_exponent, fast_value)) {
    return fast_value;
  }
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
        errmsg << "encountered number with spaces: \""
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
        } else if ((c=='d' || c=='D') && parse_opts.accept_d_exponent) {
          // Fortran double-precision exponent, e.g. 5.438673D-4
          c = 'e';
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
  // Use std::strtod rather than std::stod because libstdc++'s std::stod throws
  // std::out_of_range for subnormal underflow (any value below DBL_MIN), even
  // though such values are representable as denormals. ENDF tape generators
  // routinely emit very small values like "4.3709-320" in S(alpha,beta) tails.
  // strtod silently returns the denormal (or 0) on underflow, matching ENDF
  // convention, while still letting us detect malformed input (no chars
  // consumed or trailing garbage) and reject overflow/NaN/inf via isfinite.
  double v;
  if (cpp_fast_decimal_to_double(tbuf, v)) {
    // exact fast path; result is finite and identical to std::strtod
    return v;
  }
  char* end = nullptr;
  v = std::strtod(tbuf, &end);
  if (end == tbuf || *end != '\0') {
    std::stringstream errmsg;
    errmsg << "malformed number field: \""
           << std::string(str, 11) << "\"" << std::endl;
    throw std::runtime_error(errmsg.str());
  }
  if (!parse_opts.accept_nan_inf && !std::isfinite(v)) {
    std::stringstream errmsg;
    errmsg << "non-finite value (overflow / inf / NaN) in field: \""
           << std::string(str, 11) << "\". "
           << "Set `accept_nan_inf=true` to allow non-finite values." << std::endl;
    throw std::runtime_error(errmsg.str());
  }
  return v;
}


inline int endfstr2int(const char* str, ParsingOptions &parse_opts) {
  int fast_value;
  if (cpp_fast_field_to_int(str, fast_value)) {
    return fast_value;
  }
  // Locate first/last non-space so we can both detect blank fields
  // (ENDF convention: blank == 0) and detect trailing garbage like "0.0".
  int start = 0;
  while (start < 11 && str[start] == ' ') start++;
  if (start == 11) return 0;
  int end = 10;
  while (end > start && str[end] == ' ') end--;
  char buf[12];
  int len = end - start + 1;
  std::memcpy(buf, str + start, len);
  buf[len] = '\0';
  // Strict integer parse: reject anything `std::atoi` would have silently
  // truncated (e.g. "0.000000+0" -> 0, "4.000000-6" -> 4). Mirrors the
  // Python parser's read_fort_int, which calls int(valstr) and rejects
  // any float-shaped string.
  errno = 0;
  char *endptr;
  long val = std::strtol(buf, &endptr, 10);
  if (endptr == buf || *endptr != '\0' || errno == ERANGE
      || val < INT_MIN || val > INT_MAX) {
    std::stringstream errmsg;
    errmsg << "invalid integer in field: \""
           << std::string(str, 11) << "\".";
    throw std::runtime_error(errmsg.str());
  }
  return static_cast<int>(val);
}

// case for EndfFloatCpp
inline EndfFloatCpp cpp_read_field_EndfFloatCpp(
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
inline T cpp_read_field(const char *str, const char fieldnum, ParsingOptions &parse_opts) {
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
inline typename std::enable_if<std::is_scalar<T>::value, bool>::type
is_zero_check(const T value) {
  return value == 0;
}


template<typename T>
typename std::enable_if<! std::is_scalar<T>::value, bool>::type
is_zero_check(const T value) {
  return false;
}


// scalar values in the sense of cpp_validate_field: numbers, values of
// float fields and exact fractions (results of divisions of integers)
template<typename T>
struct is_validation_scalar {
  static const bool value = std::is_scalar<T>::value
    || std::is_same<T, DOUBLE_TYPE>::value
    || std::is_same<T, EndfRational>::value;
};


// equality of an expected and an actual field value; exact if both are
// integers or fractions, otherwise via double (as in the Python parser)
template<typename U, typename V>
inline bool cpp_values_equal(const U& x, const V& y) {
  return static_cast<double>(x) == static_cast<double>(y);
}
inline bool cpp_values_equal(const EndfRational& x, const EndfRational& y) { return x == y; }
inline bool cpp_values_equal(const EndfRational& x, int y) { return x == y; }
inline bool cpp_values_equal(int x, const EndfRational& y) { return x == y; }


template<typename U, typename V>
typename std::enable_if<
  !is_validation_scalar<U>::value || !is_validation_scalar<V>::value, void
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
  is_validation_scalar<U>::value && is_validation_scalar<V>::value, void
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
  if (cpp_values_equal(expected_value, actual_value)) return;

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

inline int cpp_read_custom_int_field(const char *str, int start_pos, int length) {
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


inline int cpp_read_mat_number(const char *str) {
  return cpp_read_custom_int_field(str, 66, 4);
}


inline int cpp_read_mf_number(const char *str) {
  return cpp_read_custom_int_field(str, 70, 2);
}


inline int cpp_read_mt_number(const char *str) {
  return cpp_read_custom_int_field(str, 72, 3);
}


inline bool cpp_is_blank_line(const std::string& line) {
  // scanning from the end exits early for regular lines, which end
  // with the MAT/MF/MT numbers (and possibly a line number)
  for (std::size_t i = line.size(); i > 0; i--) {
    if (line[i-1] != ' ') return false;
  }
  return true;
}


// Access to the get area of a stream buffer, i.e. to protected members
// of std::streambuf, via pointers to members (see cpp_getline).
struct cpp_streambuf_access : public std::streambuf {
  static char* get_gptr(std::streambuf* sb) {
    return (sb->*(&cpp_streambuf_access::gptr))();
  }
  static char* get_egptr(std::streambuf* sb) {
    return (sb->*(&cpp_streambuf_access::egptr))();
  }
  static void advance(std::streambuf* sb, int n) {
    (sb->*(&cpp_streambuf_access::gbump))(n);
  }
};


// Equivalent of std::getline(is, line) with '\n' as delimiter, including
// the state flags set on the stream. Instead of extracting the line
// character by character, the get area of the stream buffer is searched
// for the delimiter and whole chunks are appended to the line.
inline std::istream& cpp_getline(std::istream& is, std::string& line) {
  typedef std::char_traits<char> traits;
  std::istream::sentry sen(is, true);
  if (! sen) return is;
  line.clear();
  std::streambuf* sb = is.rdbuf();
  bool extracted = false;
  while (true) {
    char* p = cpp_streambuf_access::get_gptr(sb);
    char* e = cpp_streambuf_access::get_egptr(sb);
    if (p == e) {
      traits::int_type c = sb->sgetc();
      if (traits::eq_int_type(c, traits::eof())) {
        is.setstate(extracted ? std::ios_base::eofbit
                              : std::ios_base::eofbit | std::ios_base::failbit);
        return is;
      }
      if (cpp_streambuf_access::get_gptr(sb) == cpp_streambuf_access::get_egptr(sb)) {
        // stream buffer without get area: extract a single character
        sb->sbumpc();
        extracted = true;
        if (traits::to_char_type(c) == '\n') return is;
        line.push_back(traits::to_char_type(c));
      }
      continue;
    }
    std::ptrdiff_t n = e - p;
    if (n > INT_MAX) n = INT_MAX;  // gbump takes an int
    char* nl = static_cast<char*>(std::memchr(p, '\n', n));
    if (nl != nullptr) {
      line.append(p, nl - p);
      cpp_streambuf_access::advance(sb, static_cast<int>(nl - p + 1));
      return is;
    }
    line.append(p, n);
    cpp_streambuf_access::advance(sb, static_cast<int>(n));
    extracted = true;
  }
}


// Pauses Python's cyclic garbage collector while a parse function builds
// its result. The result consists of a large number of container objects
// (and, with preserve_value_strings, EndfFloat objects), whose creation
// triggers repeated collections that traverse all objects created so far.
// The previous state of the collector is restored when the guard goes out
// of scope, also if an exception is thrown.
class cpp_gc_pause {
public:
  cpp_gc_pause() : gc_module(py::module::import("gc")), was_enabled(false) {
    was_enabled = gc_module.attr("isenabled")().cast<bool>();
    if (was_enabled) {
      gc_module.attr("disable")();
    }
  }

  ~cpp_gc_pause() {
    if (! was_enabled) return;
    // keep a pending Python error, if any, and never throw here
    PyObject *type, *value, *traceback;
    PyErr_Fetch(&type, &value, &traceback);
    PyObject* res = PyObject_CallMethod(gc_module.ptr(), "enable", nullptr);
    if (res == nullptr) {
      PyErr_Clear();
    } else {
      Py_DECREF(res);
    }
    PyErr_Restore(type, value, traceback);
  }

private:
  py::object gc_module;
  bool was_enabled;
  cpp_gc_pause(const cpp_gc_pause&);
  cpp_gc_pause& operator=(const cpp_gc_pause&);
};


// Read-only stream buffer over a block of memory (the content of a file
// or string). Repositioning (tellg/seekg) only moves the read pointer,
// whereas a file stream discards its buffered data on every seekg.
class cpp_memory_streambuf : public std::streambuf {
public:
  cpp_memory_streambuf(const char* data, std::size_t size) {
    // the get area is only read from, never written to
    char* begin = const_cast<char*>(data);
    setg(begin, begin, begin + size);
  }

protected:
  pos_type seekoff(
    off_type off, std::ios_base::seekdir dir, std::ios_base::openmode which
  ) override {
    if (! (which & std::ios_base::in)) return pos_type(off_type(-1));
    off_type base;
    if (dir == std::ios_base::beg) {
      base = 0;
    } else if (dir == std::ios_base::cur) {
      base = gptr() - eback();
    } else {
      base = egptr() - eback();
    }
    off_type newpos = base + off;
    if (newpos < 0 || newpos > egptr() - eback()) return pos_type(off_type(-1));
    setg(eback(), eback() + newpos, egptr());
    return pos_type(newpos);
  }

  pos_type seekpos(pos_type pos, std::ios_base::openmode which) override {
    return seekoff(off_type(pos), std::ios_base::beg, which);
  }
};


// Read the complete content of an input stream (opened file) into a string;
// if the stream is not seekable, it is copied through its stream buffer.
inline std::string cpp_read_stream_content(std::istream& in) {
  std::string content;
  std::istream::pos_type start = in.tellg();
  if (start != std::istream::pos_type(-1) && in.seekg(0, std::ios_base::end)) {
    std::istream::pos_type end = in.tellg();
    in.seekg(start);
    if (end != std::istream::pos_type(-1) && in) {
      content.resize(static_cast<std::size_t>(end - start));
      in.read(&content[0], static_cast<std::streamsize>(content.size()));
      content.resize(static_cast<std::size_t>(in.gcount()));
      return content;
    }
  }
  in.clear();
  std::ostringstream oss;
  oss << in.rdbuf();
  return oss.str();
}


// The functions reading a line into an existing string reuse its
// allocated memory; the line is cleared first so that a failed read
// leaves an empty line.
inline void cpp_read_raw_line(std::string& line, std::istream& cont) {
  line.clear();
  cpp_getline(cont, line);
}


inline std::string cpp_read_raw_line(std::istream& cont) {
  std::string line;
  cpp_read_raw_line(line, cont);
  return line;
}


inline void cpp_read_line(
  std::string& line, std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  line.clear();
  cpp_getline(cont, line);
  if (parse_opts.ignore_blank_lines) {
    while (cpp_is_blank_line(line) && cpp_getline(cont, line)) {
      // skip blank lines
    }
  }
  if (cpp_is_blank_line(line)) {
    throw std::runtime_error(
      "Blank line detected: Correct file or use `ignore_blank_lines` option"
    );
  }

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
}


inline std::string cpp_read_line(
  std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::string line;
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  return line;
}


inline std::string cpp_read_send(std::istream& cont, int mat, int mf, ParsingOptions &parse_opts) {
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


inline bool cpp_is_fend_record(std::string line, int mat, ParsingOptions &parse_opts) {
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


inline bool cpp_is_mend_record(std::string line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.c_str());
  bool cond = cpp_is_fend_record(line, 0, parse_opts);
  cond &= (mat == 0);
  return cond;
}


inline bool cpp_is_tend_record(std::string line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.c_str());
  bool cond = cpp_is_fend_record(line, -1, parse_opts);
  cond &= (mat == -1);
  return cond;
}


// Number of elements to reserve for a vector whose size is given by a
// count in the data; capped so that a corrupt count does not lead to a
// huge allocation before the reading fails.
inline std::size_t cpp_reserve_size(int numel) {
  const int max_reserve = 1 << 20;
  return static_cast<std::size_t>(numel < max_reserve ? numel : max_reserve);
}


// Read n pairs of values, i.e. 2*n values, alternately into a and b.
// The lines are consumed exactly as by cpp_read_vec with 2*n elements.
template<typename T>
inline void cpp_read_pairs(
  std::istream& cont, const int n, std::vector<T>& a, std::vector<T>& b,
  int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  const int numel = 2*n;
  if (numel <= 0) return;
  a.reserve(cpp_reserve_size(n));
  b.reserve(cpp_reserve_size(n));
  int j = 0;
  std::string line;
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i += 2) {
    a.push_back(cpp_read_field<T>(line.c_str(), j++, parse_opts));
    b.push_back(cpp_read_field<T>(line.c_str(), j++, parse_opts));
    if (j > 5 && i+2 < numel) {
      cpp_read_line(line, cont, mat, mf, mt, parse_opts);
      j = 0;
    }
  }
}


template<typename T>
inline std::vector<T> cpp_read_vec(
  std::istream& cont, const int numel, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::vector<T> res;
  // Empty body: do not consume a line. This matters for e.g. TAB1 records
  // with NP=0 (an empty interpolation table) which TENDL emits for some
  // metastable evaluations. Consuming a line here would eat the SEND record.
  if (numel <= 0) return res;
  res.reserve(cpp_reserve_size(numel));
  int j = 0;
  std::string line;
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i++) {
    res.push_back(cpp_read_field<T>(line.c_str(), j++, parse_opts));
    if (j > 5 && i+1 < numel) {
      cpp_read_line(line, cont, mat, mf, mt, parse_opts);
      j = 0;
    }
  }
  return res;
}


template<typename T>
inline std::vector<T> cpp_read_vec_debug(
  std::istream& cont, std::string& line, const int numel, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  std::vector<T> res;
  if (numel <= 0) {
    line = "";
    return res;
  }
  int j = 0;
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


inline Tab2Body read_tab2_body_debug(
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


inline Tab2Body read_tab2_body(
  std::istream& cont, int nr, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  Tab2Body tab_body;
  cpp_read_pairs<int>(cont, nr, tab_body.NBT, tab_body.INT, mat, mf, mt, parse_opts);
  return tab_body;
}


inline Tab1Body read_tab1_body_debug(
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


inline Tab1Body read_tab1_body(
  std::istream& cont, int nr, int np,
  int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  Tab1Body tab_body;
  cpp_read_pairs<int>(cont, nr, tab_body.NBT, tab_body.INT, mat, mf, mt, parse_opts);
  cpp_read_pairs<DOUBLE_TYPE>(cont, np, tab_body.X, tab_body.Y, mat, mf, mt, parse_opts);
  return tab_body;
}


inline std::vector<std::string> read_section_verbatim(
    int mat, int mf, int mt, std::istream& cont, bool is_first, ParsingOptions &parse_opts
) {
  std::streampos curpos;
  std::string line;
  std::vector<std::string> secvec;
  int curmf;
  int curmt;
  size_t lastpos;
  while (! cont.eof()) {
    cpp_read_line(line, cont, mat, mf, mt, parse_opts);
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
