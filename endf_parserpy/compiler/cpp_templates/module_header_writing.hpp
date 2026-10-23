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


inline WritingOptions default_writing_options() {
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


// Right-aligned decimal representation of `value` padded with blanks to
// `width` characters, i.e. the same as `std::setw(width) << value` on an
// ostream. Writes into buf (at least 12 + width bytes) and returns the
// number of characters written (more than width if the number is wider).
inline int cpp_int_to_padded_chars(char* buf, int width, int value) {
  char tmp[16];
  int n = 0;
  unsigned int u = (value < 0) ? 0u - static_cast<unsigned int>(value)
                               : static_cast<unsigned int>(value);
  do {
    tmp[n++] = static_cast<char>('0' + u % 10);
    u /= 10;
  } while (u != 0);
  if (value < 0) tmp[n++] = '-';
  int pad = (n < width) ? width - n : 0;
  for (int i = 0; i < pad; i++) buf[i] = ' ';
  for (int i = 0; i < n; i++) buf[pad + i] = tmp[n - 1 - i];
  return pad + n;
}


inline void cpp_write_custom_int_field(std::string &str, int start, int length, int value) {
  char buf[32];
  int n = cpp_int_to_padded_chars(buf, length, value);
  if (n > length) {
    // a wider number would shift the following fields of the line
    throw std::runtime_error(
      "integer " + std::to_string(value) + " does not fit into a field of width "
      + std::to_string(length)
    );
  }
  str.replace(start, length, buf, n);
}


// The value of a text field must have the length of the field in the
// recipe; the value of a field without a length in the recipe (which
// spans the remaining text columns) may be shorter and is padded with
// blanks. A value of another length would shift the following columns.
inline void cpp_write_text_field(
  std::string& line, int start, int length, const std::string& value,
  const char* varname, bool pad
) {
  int size = static_cast<int>(value.size());
  if (size > length || (! pad && size != length)) {
    throw std::runtime_error(
      std::string("string in variable ") + varname + " is of length "
      + std::to_string(size) + " but expected to be of length "
      + (pad ? "at most " : "") + std::to_string(length)
    );
  }
  // the line is prepared with blanks, so a shorter value leaves blanks
  line.replace(start, size, value);
}


inline void cpp_write_mat_number(std::string& str, int value) {
  cpp_write_custom_int_field(str, 66, 4, value);
}


inline void cpp_write_mf_number(std::string& str, int value) {
  cpp_write_custom_int_field(str, 70, 2, value);
}


inline void cpp_write_mt_number(std::string& str, int value) {
  cpp_write_custom_int_field(str, 72, 3, value);
}


inline void cpp_write_line_number(std::string& str, int value) {
  cpp_write_custom_int_field(str, 75, 5, value);
}


inline std::string cpp_prepare_line(
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


inline void normalize_exponent(std::string& numstr) {
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


inline std::string get_scientific_numstr(double value, int precision, bool abuse_signpos) {
  std::ostringstream oss;
  oss << std::scientific << std::setprecision(precision) << value;
  std::string numstr = oss.str();
  normalize_exponent(numstr);
  if (! abuse_signpos && value >= 0) {
    numstr.insert(0, " ");
  }
  return numstr;
}


inline bool is_carried_mantissa(const std::string& numstr) {
  // whether the mantissa is 1 followed by zeros only, e.g. "-1.0000e-9"
  size_t pos = numstr.find_first_not_of(" -+");
  if (pos == std::string::npos || numstr[pos] != '1') {
    return false;
  }
  for (size_t i = pos + 1; i < numstr.size() && numstr[i] != 'e'; i++) {
    if (numstr[i] != '0' && numstr[i] != '.') {
      return false;
    }
  }
  return true;
}


// ---------------------------------------------------------------------
// Fast float formatting. The functions below produce exactly the same
// characters as get_scientific_numstr() / float2endfstr_helper() /
// float2endfstr() but avoid iostreams. The decimal digits are computed
// with exact double arithmetic where this provably yields the correctly
// rounded result; otherwise (values near a rounding tie, very large or
// very small magnitudes) std::snprintf is used, which is what the
// iostream implementation relies on as well.
// ---------------------------------------------------------------------

// snprintf-based equivalent of get_scientific_numstr(); writes into buf
// (>= 64 bytes) and returns the length.
inline int cpp_sci_numstr_snprintf(char* buf, double value, int precision, bool abuse_signpos) {
  char* p = buf;
  if (! abuse_signpos && value >= 0) *p++ = ' ';
  int n = std::snprintf(p, 48, "%.*e", precision, value);
  char* end = p + n;
  char* e = static_cast<char*>(std::memchr(p, 'e', n));
  if (e == nullptr) {
    throw std::runtime_error("`e` character not found");
  }
  // strip leading zeros of the exponent but keep at least one digit
  char* d = e + 2;
  char* q = d;
  while (q + 1 < end && *q == '0') q++;
  if (q != d) {
    std::memmove(d, q, end - q);
    end -= (q - d);
  }
  *end = '\0';
  return static_cast<int>(end - buf);
}


// Determine the correctly rounded nsig-digit decimal representation
// a = m * 10^(E-nsig+1) of a finite double a > 0. Returns false if this
// cannot be decided reliably with double arithmetic.
inline bool cpp_round_decimal_digits(double a, int nsig, unsigned long long &m, int &E) {
  static const double p10[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
  };
  if (nsig < 1 || nsig > 9) return false;
  if (! (a >= 1e-280 && a <= 1e280)) return false;
  // estimate of floor(log10(a)), may be one too small; corrected below
  int bexp;
  std::frexp(a, &bexp);
  int e10 = static_cast<int>(std::floor((bexp - 1) * 0.30102999566398120));
  for (int attempt = 0; attempt < 4; attempt++) {
    // scaled = a / 10^s is computed with at most two roundings, hence
    // with a relative error below 3e-16
    int s = e10 - nsig + 1;
    double scaled;
    if (s >= 0) {
      if (s <= 22) scaled = a / p10[s];
      else if (s <= 44) scaled = (a / p10[22]) / p10[s - 22];
      else return false;
    } else {
      int t = -s;
      if (t <= 22) scaled = a * p10[t];
      else if (t <= 44) scaled = (a * p10[22]) * p10[t - 22];
      else return false;
    }
    const double lo = p10[nsig - 1];
    const double hi = p10[nsig];
    if (scaled < lo - 0.25) { e10--; continue; }
    if (scaled >= hi + 0.25) { e10++; continue; }
    double fl = std::floor(scaled);
    double frac = scaled - fl;
    // too close to a rounding tie to decide safely
    if (std::fabs(frac - 0.5) < hi * 1e-14) return false;
    unsigned long long mm = static_cast<unsigned long long>(fl) + (frac > 0.5 ? 1 : 0);
    unsigned long long ilo = static_cast<unsigned long long>(lo);
    unsigned long long ihi = static_cast<unsigned long long>(hi);
    if (mm < ilo) { e10--; continue; }
    if (mm >= ihi) {
      if (mm == ihi && fl < hi) {
        // rounding carries over into the next decade
        m = ilo;
        E = e10 + 1;
        return true;
      }
      e10++;
      continue;
    }
    m = mm;
    E = e10;
    return true;
  }
  return false;
}


// assemble "[ ][-]d.ddd...e<sign><exponent without leading zeros>"
inline int cpp_compose_sci_numstr(
  char* buf, bool neg, bool lead_blank, unsigned long long m, int nsig, int E
) {
  char* p = buf;
  if (lead_blank) *p++ = ' ';
  if (neg) *p++ = '-';
  char dig[24];
  for (int i = nsig - 1; i >= 0; i--) {
    dig[i] = static_cast<char>('0' + m % 10);
    m /= 10;
  }
  *p++ = dig[0];
  if (nsig > 1) {
    *p++ = '.';
    for (int i = 1; i < nsig; i++) *p++ = dig[i];
  }
  *p++ = 'e';
  *p++ = (E < 0) ? '-' : '+';
  int ae = (E < 0) ? -E : E;
  int nd = 1;
  for (int t = ae; t >= 10; t /= 10) nd++;
  for (int i = nd - 1; i >= 0; i--) {
    p[i] = static_cast<char>('0' + ae % 10);
    ae /= 10;
  }
  p += nd;
  *p = '\0';
  return static_cast<int>(p - buf);
}


// same characters as get_scientific_numstr(value, precision, abuse_signpos)
inline int cpp_sci_numstr(char* buf, double value, int precision, bool abuse_signpos) {
  bool lead_blank = (! abuse_signpos && value >= 0);
  if (precision >= 0 && precision <= 8) {
    if (value == 0.0) {
      return cpp_compose_sci_numstr(
        buf, std::signbit(value), lead_blank, 0, precision + 1, 0
      );
    }
    unsigned long long m;
    int E;
    bool neg = value < 0;
    if (cpp_round_decimal_digits(neg ? -value : value, precision + 1, m, E)) {
      return cpp_compose_sci_numstr(buf, neg, lead_blank, m, precision + 1, E);
    }
  }
  return cpp_sci_numstr_snprintf(buf, value, precision, abuse_signpos);
}


// same characters as is_carried_mantissa() for the buf content
inline bool cpp_is_carried_mantissa_chars(const char* buf, int len) {
  int pos = 0;
  while (pos < len && (buf[pos] == ' ' || buf[pos] == '-' || buf[pos] == '+')) pos++;
  if (pos == len || buf[pos] != '1') {
    return false;
  }
  for (int i = pos + 1; i < len && buf[i] != 'e'; i++) {
    if (buf[i] != '0' && buf[i] != '.') {
      return false;
    }
  }
  return true;
}


// same characters as float2endfstr_helper(value, width, write_opts)
inline int cpp_float2endfstr_helper_chars(
  char* buf, double value, int width, bool abuse_signpos
) {
  int len = cpp_sci_numstr(buf, value, 6, abuse_signpos);
  int prec = 6 - (len - width);
  if (prec < 0) {
    prec = 0;
  }
  if (prec != 6) {
    // (for prec == 6 the call would reproduce the current content of buf)
    len = cpp_sci_numstr(buf, value, prec, abuse_signpos);
  }
  while (len > width && prec > 0) {
    len = cpp_sci_numstr(buf, value, --prec, abuse_signpos);
  }
  // largest precision that fits, see float2endfstr_helper()
  while (prec < 20 && cpp_is_carried_mantissa_chars(buf, len)) {
    char candidate[64];
    int candlen = cpp_sci_numstr(candidate, value, prec + 1, abuse_signpos);
    if (candlen > width) {
      break;
    }
    std::memcpy(buf, candidate, candlen + 1);
    len = candlen;
    prec++;
  }
  if (len < width) {
    int pad = width - len;
    std::memmove(buf + pad, buf, len + 1);
    std::memset(buf, ' ', pad);
    len = width;
  }
  return len;
}


inline std::string float2endfstr_helper(double value, size_t width, WritingOptions &write_opts)
{
  std::string numstr = get_scientific_numstr(value, 6, write_opts.abuse_signpos);
  // re-calculate precision to match width specification
  int prec = 6 - (static_cast<int>(numstr.size()) - static_cast<int>(width));
  if (prec < 0) {
    prec = 0;
  }
  numstr = get_scientific_numstr(value, prec, write_opts.abuse_signpos);
  while (numstr.size() > width && prec > 0) {
    numstr = get_scientific_numstr(value, --prec, write_opts.abuse_signpos);
  }
  // Use the largest precision for which the number still fits. A carry in
  // the rounding changes the length of the exponent: 9.99999949e-10 needs
  // more digits to fill the field than its precision-6 estimate suggests
  // (1.00000e-9), and 9999999500 fits with more digits (9.9999995+9) than
  // with fewer (1.000000+10). Without a carry (the mantissa is not 1.000...),
  // one more digit makes the number one character longer, so that it no
  // longer fits; the loop is then skipped.
  while (prec < 20 && is_carried_mantissa(numstr)) {
    std::string candidate = get_scientific_numstr(
      value, prec + 1, write_opts.abuse_signpos);
    if (candidate.size() > width) {
      break;
    }
    numstr = candidate;
    prec++;
  }
  if (numstr.size() < width) {
    numstr.insert(0, width - numstr.size(), ' ');
  }
  return numstr;
}


inline std::string float2endfstr_decimal_helper(
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


inline std::string float2endfstr(double value, WritingOptions &write_opts) {
  std::ostringstream oss;
  std::string numstr;
  int width = 11;
  // Non-finite values (NaN, +/-inf) cannot be represented in the standard
  // ENDF compact float format. Emit a textual right-aligned representation
  // that strtod can read back; this matches the convention seen in real
  // evaluations (e.g. TENDL-2025/he3/he3_026-Fe-52M_2620.dat) that store
  // "NaN" verbatim in the 11-char field.
  if (! std::isfinite(value)) {
    std::string repr;
    if (std::isnan(value)) repr = "NaN";
    else if (value > 0) repr = "Inf";
    else repr = "-Inf";
    oss << std::right << std::setw(width) << repr;
    return oss.str();
  }
  // negative zero is written as zero (as by the Python writer)
  if (value == 0.0) {
    value = 0.0;
  }
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
      // std::strtod instead of std::stod, which throws std::out_of_range
      // for subnormal numbers; the representation that reproduces the
      // value more closely is used, preferring the one without exponent
      // in case of a tie (as by the Python writer)
      double recon_value = std::strtod(numstr.c_str(), nullptr);
      double recon_value_noexp = std::strtod(numstr_noexp.c_str(), nullptr);
      double recon_value_diff = std::abs(recon_value - value);
      double recon_value_noexp_diff = std::abs(recon_value_noexp - value);
      if (recon_value_diff >= recon_value_noexp_diff) {
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


inline std::string int2endfstr(int value) {
  char buf[32];
  int n = cpp_int_to_padded_chars(buf, 11, value);
  return std::string(buf, n);
}


// Same characters as float2endfstr(value, write_opts); writes into buf
// (>= 64 bytes) and returns the length.
inline int float2endfstr_chars(char* buf, double value, WritingOptions &write_opts) {
  if (! std::isfinite(value) || write_opts.prefer_noexp) {
    std::string numstr = float2endfstr(value, write_opts);
    size_t n = std::min(numstr.size(), static_cast<size_t>(63));
    std::memcpy(buf, numstr.data(), n);
    buf[n] = '\0';
    return static_cast<int>(numstr.size() <= 63 ? n : numstr.size());
  }
  // negative zero is written as zero, see float2endfstr()
  if (value == 0.0) {
    value = 0.0;
  }
  int width = write_opts.keep_E ? 11 : 12;
  int len = cpp_float2endfstr_helper_chars(buf, value, width, write_opts.abuse_signpos);
  if (! write_opts.keep_E) {
    char* e = static_cast<char*>(std::memchr(buf, 'e', len));
    std::memmove(e, e + 1, (buf + len) - e);
    len--;
  }
  return len;
}


inline void field_size_check(const std::string& field) {
  if (field.size() != 11) {
    throw std::runtime_error(
      std::string("wrong size")
      + std::to_string(field.size())
      + std::string("  ") + field
    );
  }
}


// value is float case
inline void cpp_write_field_double(
  std::string& line, const char fieldnum, const double& value,
  WritingOptions& write_opts
) {
  char buf[64];
  int n = float2endfstr_chars(buf, value, write_opts);
  if (n != 11) {
    field_size_check(float2endfstr(value, write_opts));
  }
  line.replace(fieldnum*11, 11, buf, 11);
}


// value is EndfFloatCpp case
inline void cpp_write_field_EndfFloatCpp(
  std::string& line, const char fieldnum, const EndfFloatCpp& value,
  WritingOptions& write_opts
) {
  // the original string of a value (an EndfFloat in the dictionary) is
  // written verbatim whenever it is available, irrespective of the
  // preserve_value_strings option, which only controls parsing
  if (!value.has_original_string()) {
    cpp_write_field_double(line, fieldnum, static_cast<double>(value), write_opts);
    return;
  }
  const std::string& fieldstr = value.original_string_ref();
  field_size_check(fieldstr);
  line.replace(fieldnum*11, 11, fieldstr);
}


// value is int case
inline void cpp_write_field_int(
  std::string& line, const char fieldnum, const int& value,
  WritingOptions& write_opts
) {
  char buf[32];
  int n = cpp_int_to_padded_chars(buf, 11, value);
  line.replace(fieldnum*11, 11, buf, n);
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


// the arrays of a TAB1/TAB2 table that are written in pairs must have
// the same number of elements
inline void cpp_check_same_size(
  std::size_t size1, std::size_t size2, const char* name1, const char* name2, const char* rectype
) {
  if (size1 != size2) {
    throw std::runtime_error(
      std::string("the arrays ") + name1 + " and " + name2 + " of a " + rectype
      + " record must have the same number of elements (" + std::to_string(size1)
      + " and " + std::to_string(size2) + ")"
    );
  }
}


// lines with the n pairs (first[i], second[i]), three pairs per line;
// no line for n=0, as the parsers read ceil(2n/6) lines
template<typename T1, typename T2>
inline void cpp_write_pairs(
  std::ostringstream& oss, const std::vector<T1>& first, const std::vector<T2>& second, int n,
  int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  if (n == 0) return;
  std::string curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
  int j = 0;
  for (int i=0; i < n; i++) {
    cpp_write_field(curline, j++, first[i], write_opts);
    cpp_write_field(curline, j++, second[i], write_opts);
    if (j > 5 && i+1 < n) {
      oss << curline;
      curline = cpp_prepare_line(mat, mf, mt, linenum, write_opts);
      j = 0;
    }
  }
  oss << curline;
}


inline void write_tab1_body(
  std::string& line, const Tab1Body& tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  // checked at runtime (not with assert, which is disabled in release
  // builds), as the loops below index both arrays of a pair
  cpp_check_same_size(tab_body.NBT.size(), tab_body.INT.size(), "NBT", "INT", "TAB1");
  cpp_check_same_size(tab_body.X.size(), tab_body.Y.size(), "x", "y", "TAB1");
  int nr = tab_body.INT.size();
  int np = tab_body.X.size();
  std::ostringstream oss;
  cpp_write_pairs(oss, tab_body.NBT, tab_body.INT, nr, mat, mf, mt, linenum, write_opts);
  cpp_write_pairs(oss, tab_body.X, tab_body.Y, np, mat, mf, mt, linenum, write_opts);
  line = oss.str();
}


inline void write_tab2_body(
  std::string& line, const Tab2Body& tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  cpp_check_same_size(tab_body.NBT.size(), tab_body.INT.size(), "NBT", "INT", "TAB2");
  int nr = tab_body.INT.size();
  std::ostringstream oss;
  cpp_write_pairs(oss, tab_body.NBT, tab_body.INT, nr, mat, mf, mt, linenum, write_opts);
  line = oss.str();
}


inline std::string cpp_prepare_send(
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


inline int get_mat_from_mfmt_section(py::object mfmt_section) {
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


inline void write_section_verbatim(
  std::ostream& oss, py::list mfmt_section, WritingOptions &write_opts
) {
  if (mfmt_section.size() == 0) {
    throw std::runtime_error("an MF/MT section must not be represented by an empty list");
  }
  std::string first_line = py::cast<std::string>(mfmt_section[0]);
  int mat = cpp_read_mat_number(first_line.c_str());
  int mf = cpp_read_mf_number(first_line.c_str());
  int mt = cpp_read_mt_number(first_line.c_str());
  int linenum = (mf != 0) ? 0 : -1;  // first written number is 0 for tape head
  for (const auto& item : mfmt_section) {
    std::string linestr = py::cast<std::string>(item);
    if (write_opts.include_linenum) {
      linestr.resize(80);
      cpp_write_line_number(linestr, (linenum % 99999) + 1);
      linenum++;
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
