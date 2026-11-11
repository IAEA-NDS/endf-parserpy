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
  bool standard_form_on_tie;
  bool preserve_value_strings;
  bool include_linenum;
  bool accept_non_ascii;
  bool ignore_missing_tpid;
  std::string array_type;
};


inline WritingOptions default_writing_options() {
  return WritingOptions{
    false,  // abuse_signpos
    false,  // keep_E
    false,  // prefer_noexp
    false,  // skip_intzero
    false,  // standard_form_on_tie
    false,  // preserve_value_strings
    true,   // include_linenum
    true,   // accept_non_ascii
    false,  // ignore_missing_tpid
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
        else if (key_str == "standard_form_on_tie")
          value.standard_form_on_tie = d["standard_form_on_tie"].cast<bool>();
        else if (key_str == "include_linenum")
          value.include_linenum = d["include_linenum"].cast<bool>();
        else if (key_str == "preserve_value_strings")
          value.preserve_value_strings = d["preserve_value_strings"].cast<bool>();
        else if (key_str == "accept_non_ascii")
          value.accept_non_ascii = d["accept_non_ascii"].cast<bool>();
        else if (key_str == "ignore_missing_tpid")
          value.ignore_missing_tpid = d["ignore_missing_tpid"].cast<bool>();
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
      if (! d.contains("standard_form_on_tie")) {
        value.standard_form_on_tie = default_opts.standard_form_on_tie;
      }
      if (! d.contains("preserve_value_strings")) {
        value.preserve_value_strings = default_opts.preserve_value_strings;
      }
      if (! d.contains("include_linenum")) {
        value.include_linenum = default_opts.include_linenum;
      }
      if (! d.contains("accept_non_ascii")) {
        value.accept_non_ascii = default_opts.accept_non_ascii;
      }
      if (! d.contains("ignore_missing_tpid")) {
        value.ignore_missing_tpid = default_opts.ignore_missing_tpid;
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
      d["standard_form_on_tie"] = src.standard_form_on_tie;
      d["preserve_value_strings"] = src.preserve_value_strings;
      d["include_linenum"] = src.include_linenum;
      d["accept_non_ascii"] = src.accept_non_ascii;
      d["ignore_missing_tpid"] = src.ignore_missing_tpid;
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
  // n == length, as the number is padded to the width of the field
  if (start >= 0 && static_cast<std::size_t>(start) + n <= str.size()) {
    std::memcpy(&str[start], buf, n);
  } else {
    str.replace(start, length, buf, n);
  }
}


// The position of the first character outside printable ASCII (codes
// 32 to 126) among the first size characters of str, or size if none.
inline std::size_t cpp_find_non_ascii(const char* str, std::size_t size) {
  for (std::size_t i = 0; i < size; i++) {
    unsigned char c = static_cast<unsigned char>(str[i]);
    if (c < 32 || c > 126) return i;
  }
  return size;
}


// The value of a text field must have the length of the field in the
// recipe; the value of a field without a length in the recipe (which
// spans the remaining text columns) may be shorter and is padded with
// blanks. A value of another length would shift the following columns.
// With accept_non_ascii=false, the value must consist of printable ASCII
// characters.
inline void cpp_write_text_field(
  std::string& line, int start, int length, const std::string& value,
  const char* varname, bool pad, WritingOptions &write_opts
) {
  if (! write_opts.accept_non_ascii
      && cpp_find_non_ascii(value.data(), value.size()) != value.size()) {
    // raises the error (shared with EndfParserPy)
    cpp_text_encoding_function("check_text_value")(
      cpp_bytes_to_pystr(value), std::string("the string in variable ") + varname, false
    );
    throw std::logic_error("unexpected return from check_text_value");
  }
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


// The characters of the MAT, MF and MT numbers (columns 67 to 75) of the
// lines prepared with it, formatted once for each combination of the
// numbers instead of for every line.
struct CppLineStamp {
  CppLineStamp() : valid(false), mat(0), mf(0), mt(0) {}
  bool valid;
  int mat;
  int mf;
  int mt;
  char chars[9];
};


// Writes the MAT, MF and MT numbers into the columns 67 to 75 of the line
// starting at position start of str, with the characters of stamp if it
// holds these numbers; otherwise they are formatted (raising the error of
// a number that does not fit) and stored in stamp.
inline void cpp_stamp_control_numbers(
  std::string& str, std::size_t start, CppLineStamp& stamp, int mat, int mf, int mt
) {
  if (stamp.valid && stamp.mat == mat && stamp.mf == mf && stamp.mt == mt) {
    std::memcpy(&str[start + 66], stamp.chars, 9);
    return;
  }
  cpp_write_custom_int_field(str, start + 66, 4, mat);
  cpp_write_custom_int_field(str, start + 70, 2, mf);
  cpp_write_custom_int_field(str, start + 72, 3, mt);
  std::memcpy(stamp.chars, &str[start + 66], 9);
  stamp.mat = mat;
  stamp.mf = mf;
  stamp.mt = mt;
  stamp.valid = true;
}


// Fills line with a blank line carrying the MAT, MF and MT numbers and the
// line number (if include_linenum) and a line ending. The memory of line
// is reused, so that a line variable refilled for each line of a record
// is not allocated anew, and each column is written once: the blanks of
// the columns 1 to 66, the control numbers (see CppLineStamp), the line
// number and the line ending.
inline void cpp_prepare_line(
  std::string& line, CppLineStamp& stamp, int mat, int mf, int mt, int &linenum,
  WritingOptions &write_opts
) {
  std::size_t line_width = (write_opts.include_linenum) ? 80 : 75;
  if (line.size() != line_width + 1) {
    line.assign(line_width + 1, ' ');
  }
  std::memset(&line[0], ' ', 66);
  cpp_stamp_control_numbers(line, 0, stamp, mat, mf, mt);
  if (write_opts.include_linenum) {
    cpp_write_line_number(line, (linenum % 99999)+1);
  }
  line[line_width] = '\n';
  linenum++;
}


inline void cpp_prepare_line(
  std::string& line, int mat, int mf, int mt, int &linenum, WritingOptions &write_opts
) {
  CppLineStamp stamp;
  cpp_prepare_line(line, stamp, mat, mf, mt, linenum, write_opts);
}


// Appends a line prepared as by cpp_prepare_line to out.
inline void cpp_append_line(
  std::string& out, CppLineStamp& stamp, int mat, int mf, int mt, int &linenum,
  WritingOptions &write_opts
) {
  std::size_t start = out.size();
  int line_width = (write_opts.include_linenum) ? 80 : 75;
  out.append(line_width, ' ');
  out += '\n';
  cpp_stamp_control_numbers(out, start, stamp, mat, mf, mt);
  if (write_opts.include_linenum) {
    cpp_write_custom_int_field(out, start + 75, 5, (linenum % 99999)+1);
  }
  linenum++;
}


inline std::string cpp_prepare_line(
  int mat, int mf, int mt, int &linenum, WritingOptions &write_opts
) {
  std::string line;
  cpp_prepare_line(line, mat, mf, mt, linenum, write_opts);
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
  n = cpp_snprintf_c_decimal_point(p, n);
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


// Estimate of floor(log10(a)) for a positive normal double a, which is
// exact or one too small: floor((b - 1) * log10(2)), where b is the binary
// exponent of a as given by std::frexp (a = f * 2^b, 0.5 <= f < 1), i.e.
// b - 1 is the biased exponent minus 1023. It is computed in integer
// arithmetic as floor(k * 78913 / 2^18) with k = b - 1, which is the same
// as floor(k * 0.30102999566398120) in double arithmetic for all
// exponents of normal doubles (-1022 <= k <= 1023; checked for all of them
// by tests/cpp/float_field_writing_equivalence.cpp).
inline int cpp_decimal_exponent_estimate(double a) {
  std::uint64_t bits;
  std::memcpy(&bits, &a, sizeof(bits));
  const int k = static_cast<int>((bits >> 52) & 0x7ff) - 1023;
  // rounded down also for k < 0, without a right shift of a negative number
  return (k >= 0) ? ((k * 78913) >> 18) : -((-k * 78913 + 262143) >> 18);
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
  // (a is a normal number here)
  int e10 = cpp_decimal_exponent_estimate(a);
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


// The decimal form of a field for prefer_noexp: the value with as many
// decimals as fit into the width, without trailing zeros (and without
// the integer zero with skip_intzero), right-adjusted. It was computed
// with string streams (std::fixed with std::setprecision), whose
// conversion the C++ standard defines as that of std::printf with %.*f;
// std::snprintf with %.*f gives the same characters, apart from the
// decimal point of the C locale, which cpp_snprintf_c_decimal_point
// replaces by a period.
inline std::string float2endfstr_decimal_helper(
  double value, int width, WritingOptions &write_opts
) {
  // the string stream writes nan or inf without a decimal point
  if (! std::isfinite(value)) {
    throw std::runtime_error("error occured while converting float to string");
  }
  // Position of the decimal point in the 16-decimal string (%.16f): the
  // sign and the integer digits. They are those of |value|: the rounding
  // to 16 decimals cannot carry into the integer part, as the distance
  // of a magnitude from 0.5 below 10^k (k >= 0) to 10^k is at least its
  // spacing, 2^-53 or more, i.e. more than 0.5e-16, and magnitudes below
  // 0.5 round to at most 0.5. The comparisons with the powers of ten
  // (exact doubles) are exact.
  static const double p10[] = {
    1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11, 1e12, 1e13, 1e14
  };
  const double absval = std::fabs(value);
  int commapos = std::signbit(value) ? 1 : 0;
  // %.16f and the rounded string below have at most 309 integer digits,
  // a sign, and 17 resp. width + 1 more characters
  char buf[400];
  if (absval < 1e15) {
    int ndig = 1;
    while (ndig < 15 && absval >= p10[ndig-1]) ndig++;
    commapos += ndig;
  } else {
    // (rare) the integer digits of the 16-decimal string itself
    std::snprintf(buf, sizeof(buf), "%.16f", absval);
    commapos += static_cast<int>(std::strspn(buf, "0123456789"));
  }
  // the integer part is zero; a magnitude test, as the conversion of a
  // double outside the range of int to int is undefined behaviour
  bool is_intzero_case = (
    write_opts.skip_intzero && absval < 1.0
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
  int n = std::snprintf(buf, sizeof(buf), "%.*f", prec, value);
  n = cpp_snprintf_c_decimal_point(buf, n);
  // strip insignificant trailing zeros for compatibility with Python output
  // The decimal point of the rounded string: without decimals (prec 0)
  // it has none, e.g. 1000000000 for 999999999.5, and a carry of the
  // rounding into a new integer digit (9.99... to 10.0...) moves it.
  const char* point = static_cast<const char*>(std::memchr(buf, '.', n));
  if (point != nullptr) {
    // strip trailing zeros; at most up to the decimal point, which is kept
    // if all decimals are zero and removed below
    while (buf[n-1] == '0') {
      n--;
    }
    const int pointpos = static_cast<int>(point - buf);
    if (buf[n-1] == '.') {
      n--;
    } else if (is_intzero_case) {
      // strip unnecessary integer zero
      if (buf[pointpos-1] != '0') {
        throw std::runtime_error("integer zero matching failed");
      }
      std::memmove(buf + pointpos - 1, buf + pointpos, n - pointpos);
      n--;
    }
  }
  // a blank in the sign column, then right-adjusted to the width
  int lead = (! write_opts.abuse_signpos && value >= 0) ? 1 : 0;
  if (n + lead < width) {
    lead = width - n;
  }
  std::string sout(lead, ' ');
  sout.append(buf, n);
  return sout;
}


// std::strtod in the "C" locale (cpp_strtod_c) of a candidate of
// float2endfstr: blanks followed by a number. The exact conversion of the
// reader, cpp_fast_decimal_to_double, gives the same double as
// std::strtod for the numbers it accepts: a significand of at most 15
// digits times 10^k, for |k| <= 22 with a single multiplication or
// division of exact operands, which is correctly rounded, and for
// k < -22 with cpp_decimal_to_double_negexp. Both candidates have at most
// 11 digits, so that only decimal exponents above 22 and the rare cases
// in which the product of cpp_decimal_to_double_negexp does not decide
// the rounding are left to std::strtod.
inline double cpp_writer_read_candidate(const char* s) {
  const char* p = s;
  while (*p == ' ') p++;
  double v;
  if (cpp_fast_decimal_to_double(p, v)) {
    return v;
  }
  return cpp_strtod_c(s, nullptr);
}


// standard_form_on_tie: the exponent form with the sign column of a value
// that is not negative and its standard form (without abuse_signpos) at
// the same width have the same value if the last digit of the mantissa
// of the former is 0. The former is the value rounded to p decimals, the
// largest precision that fits, and the latter has one column less for
// the blank, i.e. p - 1 decimals: the rounding to p - 1 decimals is the
// same number if the p-th decimal is 0 (the value is less than half a
// unit of the p-th decimal from it, and it cannot carry into the next
// decade), with the same exponent, so that the standard form is the
// former without this digit, after a blank. Returns the position of
// this digit in the field f of length len (with or without the
// character e), or -1 if it is not 0, the field is padded with blanks
// or its mantissa has fewer than two decimals.
inline int cpp_sign_column_zero_digit(const char* f, int len) {
  if (f[0] == ' ' || f[1] != '.') {
    return -1;
  }
  // the sign of the exponent, the last sign of the field
  int s = len - 1;
  while (s > 2 && f[s] != '+' && f[s] != '-') s--;
  if (f[s-1] == 'e') s--;
  const int last = s - 1;
  return (last >= 3 && f[last] == '0') ? last : -1;
}


// the field f of length len without the digit at position last, after a
// blank (see cpp_sign_column_zero_digit), and without the character e if
// drop_e, written to dst; returns the length
inline int cpp_standard_form_from_sign_column(
  char* dst, const char* f, int len, int last, bool drop_e
) {
  dst[0] = ' ';
  std::memcpy(dst + 1, f, last);
  int start = last + 1;
  if (drop_e && f[start] == 'e') start++;
  std::memcpy(dst + 1 + last, f + start, len - start);
  return 1 + last + (len - start);
}


// standard_form_on_tie: replaces the field numstr (with the character e)
// by the standard form of value at the width effwidth, the field of the
// default writer (cpp_float2endfstr_helper_chars without abuse_signpos),
// if the standard form reads back at least as close to the value as the
// candidate, whose read-back differs from the value by cand_diff. Returns
// whether it was replaced.
inline bool cpp_standard_form_if_as_close(
  std::string& numstr, double value, int effwidth, double cand_diff
) {
  char stdbuf[64];
  int stdlen = cpp_float2endfstr_helper_chars(stdbuf, value, effwidth, false);
  double std_diff = std::abs(cpp_writer_read_candidate(stdbuf) - value);
  if (std_diff <= cand_diff) {
    numstr.assign(stdbuf, stdlen);
    return true;
  }
  return false;
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
  // the same characters as float2endfstr_helper(value, effwidth, write_opts),
  // including the character e, which is still needed by std::strtod below
  char expbuf[64];
  int explen = cpp_float2endfstr_helper_chars(
    expbuf, value, effwidth, write_opts.abuse_signpos
  );
  numstr.assign(expbuf, explen);
  // With standard_form_on_tie, the field written by the options as given
  // (the candidate) is replaced by the standard form, the field of the
  // default writer (prefer_noexp, abuse_signpos and skip_intzero false),
  // if it reads back at least as close to the value. The exponent form
  // numstr is the standard form unless abuse_signpos is set and the value
  // is not negative (the sign column); otherwise both are the same text
  // and need no comparison.
  const bool sign_column = write_opts.abuse_signpos && value >= 0;
  bool have_exp_diff = false;
  double exp_diff = 0.0;
  if (write_opts.prefer_noexp) {
    std::string numstr_noexp = float2endfstr_decimal_helper(
      value, width, write_opts
    );
    if (numstr_noexp.size() <= width) {
      // std::strtod instead of std::stod, which throws std::out_of_range
      // for subnormal numbers (see cpp_writer_read_candidate); the
      // representation that reproduces the value more closely is used,
      // preferring the one without exponent in case of a tie (as by the
      // Python writer)
      double recon_value = cpp_writer_read_candidate(numstr.c_str());
      double recon_value_noexp = cpp_writer_read_candidate(numstr_noexp.c_str());
      double recon_value_diff = std::abs(recon_value - value);
      double recon_value_noexp_diff = std::abs(recon_value_noexp - value);
      if (recon_value_diff >= recon_value_noexp_diff) {
        if (! write_opts.standard_form_on_tie) {
          return numstr_noexp;
        }
        // the candidate is the decimal form
        const int last = sign_column
          ? cpp_sign_column_zero_digit(numstr.data(), static_cast<int>(numstr.size()))
          : -1;
        if (sign_column && last < 0) {
          if (! cpp_standard_form_if_as_close(
                numstr, value, effwidth, recon_value_noexp_diff)) {
            return numstr_noexp;
          }
        } else {
          // the standard form is numstr, or has its value
          if (recon_value_diff > recon_value_noexp_diff) {
            return numstr_noexp;
          }
          if (last >= 0) {
            char stdbuf[64];
            const int stdlen = cpp_standard_form_from_sign_column(
              stdbuf, numstr.data(), static_cast<int>(numstr.size()), last,
              ! write_opts.keep_E);
            return std::string(stdbuf, stdlen);
          }
        }
        // numstr is now the standard form
        if (! write_opts.keep_E) {
          numstr.erase(numstr.find('e'), 1);
        }
        return numstr;
      }
      have_exp_diff = true;
      exp_diff = recon_value_diff;
    }
  }
  // the candidate is the exponent form numstr
  if (sign_column && write_opts.standard_form_on_tie) {
    const int last = cpp_sign_column_zero_digit(
      numstr.data(), static_cast<int>(numstr.size()));
    if (last >= 0) {
      // the standard form has the same value
      char stdbuf[64];
      const int stdlen = cpp_standard_form_from_sign_column(
        stdbuf, numstr.data(), static_cast<int>(numstr.size()), last,
        ! write_opts.keep_E);
      return std::string(stdbuf, stdlen);
    } else {
      if (! have_exp_diff) {
        exp_diff = std::abs(cpp_writer_read_candidate(numstr.c_str()) - value);
      }
      cpp_standard_form_if_as_close(numstr, value, effwidth, exp_diff);
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
  // standard_form_on_tie with abuse_signpos (see float2endfstr) as well
  if (! std::isfinite(value) || write_opts.prefer_noexp
      || (write_opts.abuse_signpos && write_opts.standard_form_on_tie
          && value >= 0)) {
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


// Number of digits of the decimal exponent e as written (without sign).
inline int cpp_exponent_ndigits(int e) {
  if (e < 0) e = -e;
  return (e < 10) ? 1 : ((e < 100) ? 2 : 3);
}


// The 11 characters of a float field for a finite value without the option
// prefer_noexp, written directly to dst; the same characters as
// float2endfstr_chars(). Returns false without writing anything if the
// value needs the general procedure of cpp_float2endfstr_helper_chars():
// zero is handled here, and so is a nonzero value whose digits are
// determined by cpp_round_decimal_digits() and whose mantissa is not
// 1 followed by zeros only (in that case the rounding may have carried
// into the next decade, and the length of the exponent may change).
//
// Why the result is the same: with lead = 1 for a leading blank and
// neg = 1 for a minus sign, the representation with precision p and the
// decimal exponent E has lead + neg + p + 4 + nd(E) characters
// (including the character e), where nd(E) is the number of exponent
// digits. The general procedure first formats with precision 6 and then
// takes p = width - lead - neg - 4 - nd(E6), where E6 is the exponent at
// precision 6. Without a carry at precision p (p <= 6), there is none at
// precision 6 either, so E6 = E and the representation with this p fills
// the width exactly. Its mantissa is not 1.000..., so the procedure stops
// there. For p = 7 (abuse_signpos, positive value, keep_E false), a carry
// at precision 6 would give E6 = E + 1, which is excluded if it changes
// nd. The exponent of the value is estimated from its binary exponent
// (the estimate may be one too small); if nd of the computed exponent
// differs from the estimate, the digits are computed once more with the
// corrected precision.
//
// The characters are composed in 32-bit arithmetic, two digits at a time
// from a table of the 100 digit pairs. The mantissa has prec + 1 digits:
// m < 10^(prec + 1) <= 10^8 < 2^32, as prec = width - nsign - 4 - nd <= 7
// (width <= 12, nsign >= 0, nd >= 1; cpp_round_decimal_digits returns
// m < 10^nsig, or 10^(nsig - 1) for a carry, which is rejected here; and
// m = 0 for zero). The decimal exponent has at most two digits, as
// cpp_round_decimal_digits scales the value by at most 10^44, so that
// |E| <= 52; the case of three digits is handled for completeness.
inline bool cpp_float_field_fast(char* dst, double value, bool abuse_signpos, bool keep_E) {
  static const unsigned long long p10[] = {
    1ULL, 10ULL, 100ULL, 1000ULL, 10000ULL, 100000ULL, 1000000ULL,
    10000000ULL, 100000000ULL, 1000000000ULL
  };
  static const char digit_pairs[201] =
    "00010203040506070809101112131415161718192021222324252627282930313233343536373839"
    "40414243444546474849505152535455565758596061626364656667686970717273747576777879"
    "8081828384858687888990919293949596979899";
  const bool neg = value < 0;  // false for negative zero, written as zero
  const double a = neg ? -value : value;
  const int width = keep_E ? 11 : 12;  // including the character e
  const int lead = (! abuse_signpos && ! neg) ? 1 : 0;
  const int nsign = lead + (neg ? 1 : 0);
  unsigned long long m = 0;
  int E = 0;
  int nd = 1;
  int prec;
  if (a == 0.0) {
    prec = width - nsign - 5;
  } else {
    // a subnormal number (biased exponent 0) is below the range accepted
    // by cpp_round_decimal_digits
    std::uint64_t bits;
    std::memcpy(&bits, &a, sizeof(bits));
    if (((bits >> 52) & 0x7ff) == 0) return false;
    nd = cpp_exponent_ndigits(cpp_decimal_exponent_estimate(a));
    for (int attempt = 0; ; attempt++) {
      prec = width - nsign - 4 - nd;
      if (! cpp_round_decimal_digits(a, prec + 1, m, E)) return false;
      if (m == p10[prec]) return false;
      int ndE = cpp_exponent_ndigits(E);
      if (ndE == nd) break;
      if (attempt == 1) return false;
      nd = ndE;
    }
    if (prec > 6 && cpp_exponent_ndigits(E + 1) != nd) return false;
  }
  char* p = dst;
  if (lead) *p++ = ' ';
  if (neg) *p++ = '-';
  // prec + 1 digits, the first one before the decimal point and the
  // others at p[2] to p[prec + 1], from the last one backwards
  std::uint32_t m32 = static_cast<std::uint32_t>(m);
  int i = prec + 1;
  for (; i >= 3; i -= 2) {
    const std::uint32_t q = m32 / 100;
    std::memcpy(p + i - 1, digit_pairs + 2 * (m32 - 100 * q), 2);
    m32 = q;
  }
  if (i == 2) {
    const std::uint32_t q = m32 / 10;
    p[2] = static_cast<char>('0' + (m32 - 10 * q));
    m32 = q;
  }
  p[1] = '.';
  p[0] = static_cast<char>('0' + m32);
  p += prec + 2;
  if (keep_E) *p++ = 'e';
  *p++ = (E < 0) ? '-' : '+';
  const std::uint32_t ae = static_cast<std::uint32_t>((E < 0) ? -E : E);
  if (nd == 1) {
    p[0] = static_cast<char>('0' + ae);
  } else if (nd == 2) {
    std::memcpy(p, digit_pairs + 2 * ae, 2);
  } else {
    const std::uint32_t q = ae / 100;
    p[0] = static_cast<char>('0' + q);
    std::memcpy(p + 1, digit_pairs + 2 * (ae - 100 * q), 2);
  }
  return true;
}


// The read-back (cpp_writer_read_candidate) of an 11-character field of
// cpp_float_field_fast(); without keep_E, the character e is inserted
// before the sign of the exponent, the last sign of the field (the sign
// of the number is in the first two columns, that of the exponent after
// at least two digits and the decimal point).
inline double cpp_read_fast_field(const char* field, bool keep_E) {
  char buf[16];
  if (keep_E) {
    std::memcpy(buf, field, 11);
    buf[11] = '\0';
  } else {
    int s = 10;
    while (field[s] != '+' && field[s] != '-') s--;
    std::memcpy(buf, field, s);
    buf[s] = 'e';
    std::memcpy(buf + s + 1, field + s, 11 - s);
    buf[12] = '\0';
  }
  return cpp_writer_read_candidate(buf);
}


// standard_form_on_tie with abuse_signpos and without prefer_noexp, for
// a value that is not negative: the field of cpp_float_field_fast() in
// the standard form (without abuse_signpos) if it reads back at least as
// close to the value as the field with the sign column, otherwise the
// latter; the same characters as float2endfstr_chars(). Returns false
// without writing anything if cpp_float_field_fast() does not handle the
// value.
inline bool cpp_float_field_fast_standard_on_tie(char* dst, double value, bool keep_E) {
  char cand[16];
  char stdf[16];
  if (! cpp_float_field_fast(cand, value, true, keep_E)) {
    return false;
  }
  const int last = cpp_sign_column_zero_digit(cand, 11);
  if (last >= 0) {
    // the standard form has the same value
    cpp_standard_form_from_sign_column(dst, cand, 11, last, false);
    return true;
  }
  if (! cpp_float_field_fast(stdf, value, false, keep_E)) {
    return false;
  }
  const double cand_diff = std::abs(cpp_read_fast_field(cand, keep_E) - value);
  const double std_diff = std::abs(cpp_read_fast_field(stdf, keep_E) - value);
  std::memcpy(dst, std_diff <= cand_diff ? stdf : cand, 11);
  return true;
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


// value is float case; the field starts at position pos of line
inline void cpp_write_field_double_at(
  std::string& line, std::size_t pos, const double& value,
  WritingOptions& write_opts
) {
  if (! write_opts.prefer_noexp && pos + 11 <= line.size() && std::isfinite(value)) {
    if (! write_opts.abuse_signpos || ! write_opts.standard_form_on_tie || value < 0) {
      if (cpp_float_field_fast(&line[pos], value, write_opts.abuse_signpos, write_opts.keep_E)) {
        return;
      }
    } else if (cpp_float_field_fast_standard_on_tie(&line[pos], value, write_opts.keep_E)) {
      return;
    }
  }
  char buf[64];
  int n = float2endfstr_chars(buf, value, write_opts);
  if (n != 11) {
    field_size_check(float2endfstr(value, write_opts));
  }
  line.replace(pos, 11, buf, 11);
}


// value is EndfFloatCpp case
inline void cpp_write_field_EndfFloatCpp_at(
  std::string& line, std::size_t pos, const EndfFloatCpp& value,
  WritingOptions& write_opts
) {
  // the original string of a value (an EndfFloat in the dictionary) is
  // written verbatim whenever it is available, irrespective of the
  // preserve_value_strings option, which only controls parsing
  if (!value.has_original_string()) {
    cpp_write_field_double_at(line, pos, static_cast<double>(value), write_opts);
    return;
  }
  const char* fieldstr = value.original_string_data();
  std::size_t len = value.original_string_size();
  if (len != 11) {
    // of a string longer than EndfFloatCpp::max_stored_size, only its
    // beginning is available and shown
    throw std::runtime_error(
      std::string("wrong size")
      + std::to_string(len)
      + std::string("  ")
      + std::string(fieldstr, value.original_string_stored_size())
    );
  }
  if (pos + 11 <= line.size()) {
    std::memcpy(&line[pos], fieldstr, 11);
  } else {
    line.replace(pos, 11, fieldstr, 11);
  }
}


// value is int case
inline void cpp_write_field_int_at(
  std::string& line, std::size_t pos, const int& value,
  WritingOptions& write_opts
) {
  char buf[32];
  int n = cpp_int_to_padded_chars(buf, 11, value);
  // n == 11, as an int has at most 11 characters
  if (n == 11 && pos + 11 <= line.size()) {
    std::memcpy(&line[pos], buf, 11);
  } else {
    line.replace(pos, 11, buf, n);
  }
}


inline void cpp_write_field_at(
  std::string& line, std::size_t pos, const double& value, WritingOptions& write_opts
) {
  cpp_write_field_double_at(line, pos, value, write_opts);
}


inline void cpp_write_field_at(
  std::string& line, std::size_t pos, const EndfFloatCpp& value, WritingOptions& write_opts
) {
  cpp_write_field_EndfFloatCpp_at(line, pos, value, write_opts);
}


inline void cpp_write_field_at(
  std::string& line, std::size_t pos, const int& value, WritingOptions& write_opts
) {
  cpp_write_field_int_at(line, pos, value, write_opts);
}


inline void cpp_write_field_double(
  std::string& line, const char fieldnum, const double& value,
  WritingOptions& write_opts
) {
  cpp_write_field_double_at(line, fieldnum*11, value, write_opts);
}


inline void cpp_write_field_EndfFloatCpp(
  std::string& line, const char fieldnum, const EndfFloatCpp& value,
  WritingOptions& write_opts
) {
  cpp_write_field_EndfFloatCpp_at(line, fieldnum*11, value, write_opts);
}


inline void cpp_write_field_int(
  std::string& line, const char fieldnum, const int& value,
  WritingOptions& write_opts
) {
  cpp_write_field_int_at(line, fieldnum*11, value, write_opts);
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
  cpp_write_field_at(line, fieldnum*11, value, write_opts);
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


// Appends the lines with the n pairs (first[i], second[i]) to out, three
// pairs per line; no line for n=0, as the parsers read ceil(2n/6) lines.
// The fields are written in place into the lines appended to out.
template<typename T1, typename T2>
inline void cpp_write_pairs(
  std::string& out, const std::vector<T1>& first, const std::vector<T2>& second, int n,
  int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  if (n == 0) return;
  CppLineStamp stamp;
  std::size_t linestart = out.size();
  cpp_append_line(out, stamp, mat, mf, mt, linenum, write_opts);
  int j = 0;
  for (int i=0; i < n; i++) {
    cpp_write_field_at(out, linestart + 11*(j++), first[i], write_opts);
    cpp_write_field_at(out, linestart + 11*(j++), second[i], write_opts);
    if (j > 5 && i+1 < n) {
      linestart = out.size();
      cpp_append_line(out, stamp, mat, mf, mt, linenum, write_opts);
      j = 0;
    }
  }
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
  line.clear();
  cpp_write_pairs(line, tab_body.NBT, tab_body.INT, nr, mat, mf, mt, linenum, write_opts);
  cpp_write_pairs(line, tab_body.X, tab_body.Y, np, mat, mf, mt, linenum, write_opts);
}


inline void write_tab2_body(
  std::string& line, const Tab2Body& tab_body, int mat, int mf, int mt, int& linenum, WritingOptions &write_opts
) {
  cpp_check_same_size(tab_body.NBT.size(), tab_body.INT.size(), "NBT", "INT", "TAB2");
  int nr = tab_body.INT.size();
  line.clear();
  cpp_write_pairs(line, tab_body.NBT, tab_body.INT, nr, mat, mf, mt, linenum, write_opts);
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


// The output of the writing functions. The lines are appended to one
// growing buffer, which becomes the string returned by the writing
// function (see str), or which is written to a file. For a file, the
// buffer is written to it whenever its size exceeds flush_size and when
// the object is destroyed, also during the stack unwinding after an
// exception. As with output written directly to the file stream, the
// file then contains all lines written before the exception.
class CppWriteOutput {
public:
  CppWriteOutput() : file_(nullptr) {}
  explicit CppWriteOutput(std::ostream& file) : file_(&file) {}
  ~CppWriteOutput() { flush(); }
  CppWriteOutput(const CppWriteOutput&) = delete;
  CppWriteOutput& operator=(const CppWriteOutput&) = delete;

  CppWriteOutput& operator<<(const std::string& text) {
    buf_.append(text);
    if (file_ != nullptr && buf_.size() >= flush_size) {
      flush();
    }
    return *this;
  }

  // writes the buffer to the file (if any) and empties it
  void flush() {
    if (file_ != nullptr && ! buf_.empty()) {
      file_->write(buf_.data(), static_cast<std::streamsize>(buf_.size()));
      buf_.clear();
    }
  }

  // the output (without a file)
  const std::string& str() const { return buf_; }

private:
  static const std::size_t flush_size = 1 << 20;
  std::string buf_;
  std::ostream* file_;
};


// The bytes of a line of a section given as a list of strings (see
// cpp_text_from_pyobj); lineno counts from 1, mf and mt are the keys of
// the section in the dictionary.
inline std::string cpp_verbatim_line_from_pyobj(
  const py::handle& obj, int lineno, int mf, int mt
) {
  if (! PyUnicode_Check(obj.ptr())) {
    return py::cast<std::string>(obj);
  }
  std::string out;
  if (! cpp_pystr_to_bytes(obj.ptr(), out)) {
    // raises the error (a character above U+00FF)
    cpp_text_encoding_function("check_verbatim_line")(obj, lineno, mf, mt);
    throw std::logic_error("unexpected string conversion failure");
  }
  return out;
}


// The MAT, MF and MT numbers of a line of a section given as a list of
// strings (lineno counting from 1, mf and mt the keys of the section in
// the dictionary). A field must be blank (zero) or hold an integer (see
// cpp_int_columns_to_int); the columns missing from a short line are
// blanks. Otherwise a ValueError is raised, as by EndfParserPy, which
// reads the MAT/MF/MT numbers of the first and the last line of such a
// section with int().
inline void cpp_verbatim_control_numbers(
  const std::string& line, int lineno, int mf, int mt,
  int& line_mat, int& line_mf, int& line_mt
) {
  std::size_t size = line.size();
  if (size > 0 && line[size-1] == '\n') size--;
  if (size > 0 && line[size-1] == '\r') size--;
  if (size > 75) size = 75;
  char cols[76];
  std::memset(cols, ' ', 75);
  std::memcpy(cols, line.data(), size);
  cols[75] = '\0';
  const char* what = nullptr;
  int start = 0;
  int length = 0;
  if (! cpp_int_columns_to_int(cols, 66, 4, line_mat)) {
    what = "MAT number"; start = 66; length = 4;
  } else if (! cpp_int_columns_to_int(cols, 70, 2, line_mf)) {
    what = "MF number"; start = 70; length = 2;
  } else if (! cpp_int_columns_to_int(cols, 72, 3, line_mt)) {
    what = "MT number"; start = 72; length = 3;
  }
  if (what != nullptr) {
    std::string msg = cpp_int_columns_error_message(what, cols, start, length);
    msg += " in line " + std::to_string(lineno) + " of the section MF="
        + std::to_string(mf) + "/MT=" + std::to_string(mt)
        + " given as a list of lines";
    throw py::value_error(cpp_escape_message(msg.c_str()));
  }
}


inline int get_mat_from_mfmt_section(py::object mfmt_section, int mf, int mt) {
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
  std::string first_line = cpp_verbatim_line_from_pyobj(mfmt_section_list[0], 1, mf, mt);
  // a blank MAT field (e.g. of a TPID record) reads as zero, as in EndfParserPy
  int line_mf, line_mt;
  cpp_verbatim_control_numbers(first_line, 1, mf, mt, mat, line_mf, line_mt);
  return mat;
}


inline void write_section_verbatim(
  CppWriteOutput& oss, py::list mfmt_section, WritingOptions &write_opts,
  int dict_mf, int dict_mt
) {
  if (mfmt_section.size() == 0) {
    throw std::runtime_error("an MF/MT section must not be represented by an empty list");
  }
  std::string first_line = cpp_verbatim_line_from_pyobj(mfmt_section[0], 1, dict_mf, dict_mt);
  int mat, mf, mt;
  cpp_verbatim_control_numbers(first_line, 1, dict_mf, dict_mt, mat, mf, mt);
  // the numbers of the last line must be numbers too (EndfParserPy
  // reads them for the SEND record)
  const int nlines = static_cast<int>(mfmt_section.size());
  if (nlines > 1) {
    int last_mat, last_mf, last_mt;
    std::string last_line = cpp_verbatim_line_from_pyobj(
      mfmt_section[nlines - 1], nlines, dict_mf, dict_mt
    );
    cpp_verbatim_control_numbers(
      last_line, nlines, dict_mf, dict_mt, last_mat, last_mf, last_mt
    );
  }
  int linenum = (mf != 0) ? 0 : -1;  // first written number is 0 for tape head
  int lineno = 0;
  for (const auto& item : mfmt_section) {
    std::string linestr = cpp_verbatim_line_from_pyobj(item, ++lineno, dict_mf, dict_mt);
    if (! write_opts.accept_non_ascii) {
      // the columns that are written (see below), without the line ending
      std::size_t size = linestr.size();
      if (size > 0 && linestr[size-1] == '\n') size--;
      if (size > 0 && linestr[size-1] == '\r') size--;
      if (size > 75) size = 75;
      if (cpp_find_non_ascii(linestr.data(), size) != size) {
        // raises the error (shared with EndfParserPy)
        cpp_text_encoding_function("check_verbatim_line")(
          item, lineno, dict_mf, dict_mt, false
        );
        throw std::logic_error("unexpected return from check_verbatim_line");
      }
    }
    // the columns of the line without its line ending; the columns
    // missing from a short line are written as blanks, as they are read
    // as blanks (resize would otherwise pad with NUL characters)
    std::size_t size = linestr.size();
    if (size > 0 && linestr[size-1] == '\n') size--;
    if (size > 0 && linestr[size-1] == '\r') size--;
    linestr.resize(size);
    if (write_opts.include_linenum) {
      linestr.resize(80, ' ');
      cpp_write_line_number(linestr, (linenum % 99999) + 1);
      linenum++;
    } else {
      linestr.resize(75, ' ');
    }
    linestr.push_back('\n');
    oss << linestr;
  }
  if (mf != 0) {
      std::string send_line = cpp_prepare_send(mat, mf, write_opts);
      oss << send_line;
  }
}

#endif // MODULE_HEADER_WRITING_HPP
