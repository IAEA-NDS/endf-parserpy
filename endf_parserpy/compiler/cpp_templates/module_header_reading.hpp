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


class cpp_memory_streambuf;
class CppListBody;
struct cpp_tolerated_log;


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
  bool accept_non_ascii;
  bool preserve_value_strings;
  bool validate_control_records;
  bool load_file_into_memory;
  std::string array_type;
  // Not an option: the stream buffer holding the data in memory if the
  // data is parsed from memory (set by the functions called from
  // Python, see CppLine), otherwise nullptr.
  cpp_memory_streambuf* memory_input;
  // Not an option: the template of the record being read, a string
  // literal of the generated code, or nullptr outside a record. It is
  // set at the start of every record (one pointer store) and only read
  // for error messages (see cpp_rethrow_parse_error). While the lines of
  // the body of a TAB1, TAB2 or LIST record are read, it points to the
  // template preceded by CPP_BODY_MARK (see cpp_template_text).
  const char* current_template;
  // Not an option: the log of the mismatches tolerated in the call
  // (see cpp_tolerated_log), set by the functions called from Python
  // that report them, otherwise nullptr (no mismatch is recorded).
  cpp_tolerated_log* tolerated;
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
    true,   // accept_non_ascii
    false,  // preserve_value_strings
    false,  // validate_control_records
    true,   // load_file_into_memory
    "dict",  // array_type
    nullptr,  // memory_input
    nullptr,  // current_template
    nullptr  // tolerated
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
        else if (key_str == "accept_non_ascii")
          value.accept_non_ascii = d["accept_non_ascii"].cast<bool>();
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
      value.memory_input = nullptr;
      value.current_template = nullptr;
      value.tolerated = nullptr;

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

      if (! d.contains("accept_non_ascii")) {
        value.accept_non_ascii = default_opts.accept_non_ascii;
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
      d["accept_non_ascii"] = src.accept_non_ascii;
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


// The first character of ParsingOptions::current_template while the
// lines of the body of a TAB1, TAB2 or LIST record are read; the
// generated code stores a second string literal, the template preceded
// by this character, after the first line of such a record has been read.
#define CPP_BODY_MARK '\001'


// The text of a template stored in ParsingOptions::current_template
// (without CPP_BODY_MARK), or nullptr.
inline const char* cpp_template_text(const char* tmpl) {
  if (tmpl != nullptr && tmpl[0] == CPP_BODY_MARK) return tmpl + 1;
  return tmpl;
}


inline std::string cpp_trim_blanks(const std::string& str) {
  std::size_t start = str.find_first_not_of(" \n");
  if (start == std::string::npos) return "";
  std::size_t end = str.find_last_not_of(" \n");
  return str.substr(start, end - start + 1);
}


// The name of the record type of a template, e.g. TAB1 for
// "[ MAT , 3 , MT / ... ] TAB1 ( xstable )", or an empty string.
inline std::string cpp_template_record_type(const char* tmpl) {
  std::string text(cpp_template_text(tmpl));
  std::size_t pos = text.rfind(']');
  if (pos == std::string::npos) return "";
  pos = text.find_first_not_of(' ', pos + 1);
  if (pos == std::string::npos) return "";
  std::size_t end = text.find_first_of(" (", pos);
  return text.substr(pos, end == std::string::npos ? end : end - pos);
}


// The expression of field fieldnum (counting from 0) of the first line
// of a record in its template, i.e. the six expressions separated by
// commas after the first slash, e.g. AWR for field 1 of
// "[ MAT , 3 , MT / ZA , AWR , 0 , 0 , 0 , 0 ] HEAD". An empty string if
// the template does not list six expressions there.
inline std::string cpp_template_field(const char* tmpl, int fieldnum) {
  const char* p = std::strchr(cpp_template_text(tmpl), '/');
  if (p == nullptr || fieldnum < 0 || fieldnum > 5) return "";
  std::vector<std::string> fields;
  std::string cur;
  int depth = 0;
  for (p++; *p != '\0'; p++) {
    char c = *p;
    if (depth == 0 && (c == '/' || c == ']')) break;
    if (c == '(' || c == '{' || c == '[') depth++;
    if (c == ')' || c == '}' || c == ']') depth--;
    if (depth == 0 && c == ',') {
      fields.push_back(cpp_trim_blanks(cur));
      cur.clear();
    } else {
      cur.push_back(c);
    }
  }
  fields.push_back(cpp_trim_blanks(cur));
  if (fields.size() != 6) return "";
  return fields[fieldnum];
}


// A description of field fieldnum (counting from 0) of the line being
// read for an error message, e.g. "field 2, columns 12-22, variable AWR".
// The variable (or expression) is taken from the template of the record
// if the field belongs to its first line; for a line of the body of a
// TAB1, TAB2 or LIST record, only the record type is given. Only called
// to build error messages.
inline std::string cpp_field_description(int fieldnum, const ParsingOptions& parse_opts) {
  std::ostringstream oss;
  oss << "field " << fieldnum + 1 << ", columns " << 11*fieldnum + 1
      << "-" << 11*fieldnum + 11;
  const char* tmpl = parse_opts.current_template;
  if (tmpl == nullptr) return oss.str();
  if (tmpl[0] == CPP_BODY_MARK) {
    std::string rectype = cpp_template_record_type(tmpl);
    oss << ", in the body of the " << (rectype.empty() ? "" : rectype + " ") << "record";
    return oss.str();
  }
  std::string expr = cpp_template_field(tmpl, fieldnum);
  if (expr.empty()) return oss.str();
  bool is_name = std::isalpha(static_cast<unsigned char>(expr[0])) || expr[0] == '_';
  bool is_number = true;
  for (char c : expr) {
    unsigned char uc = static_cast<unsigned char>(c);
    if (! (std::isalnum(uc) || c == '_')) is_name = false;
    if (! (std::isdigit(uc) || c == '.' || c == '-' || c == '+')) is_number = false;
  }
  if (is_name) {
    oss << ", variable " << expr;
  } else if (! is_number) {
    oss << ", expression " << expr;
  }
  return oss.str();
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


// The template of the record and the line are added to the message by
// cpp_rethrow_parse_error.
template<typename U, typename V, typename W>
inline void throw_mismatch_error(U quantity, V expected_value, W actual_value) {
  std::stringstream errmsg;
  errmsg << "Invalid " << quantity << " encountered! "
         << "Expected " << quantity << "=" << format_mismatch_value(expected_value)
         << " but found " << quantity <<"=" << format_mismatch_value(actual_value) << std::endl;
  throw std::runtime_error(errmsg.str());
}


// fieldnum (counting from 0) is the field of the line holding the value,
// or -1 if unknown. The template of the record and the line are added
// to the message by cpp_rethrow_parse_error.
template<typename V, typename W>
inline void throw_number_mismatch_error(
  V expected_value, W actual_value, int fieldnum, const ParsingOptions& parse_opts
) {
  std::stringstream errmsg;
  errmsg << "Expected a field to contain the value " << format_mismatch_value(expected_value)
         << " but found instead the value " << format_mismatch_value(actual_value);
  if (fieldnum >= 0) {
    errmsg << " (" << cpp_field_description(fieldnum, parse_opts) << ")";
  }
  errmsg << "." << std::endl;
  throw std::runtime_error(errmsg.str());
}


#if defined(_MSC_VER) && ! defined(__clang__) && (defined(_M_X64) || defined(_M_ARM64)) && ! defined(_M_ARM64EC)
#include <intrin.h>
#endif

// CPP_DECIMAL_FORCEINLINE: for cpp_decimal_finish, the last step of the
// conversion of almost every float field, which must not depend on the
// inlining heuristics (GCC -O1 inlines only functions it finds small).
#if defined(__GNUC__) || defined(__clang__)
#define CPP_DECIMAL_NOINLINE __attribute__((noinline))
#define CPP_DECIMAL_FORCEINLINE __attribute__((always_inline)) inline
#elif defined(_MSC_VER)
#define CPP_DECIMAL_NOINLINE __declspec(noinline)
#define CPP_DECIMAL_FORCEINLINE __forceinline
#else
#define CPP_DECIMAL_NOINLINE
#define CPP_DECIMAL_FORCEINLINE inline
#endif

// CPP_TOLERATED_COLD: for the functions recording a tolerated mismatch
// (see cpp_validate_field), which are only called for a mismatch and are
// kept out of the code of the reading functions.
#if defined(__GNUC__) || defined(__clang__)
#define CPP_TOLERATED_COLD __attribute__((noinline, cold)) inline
#elif defined(_MSC_VER)
#define CPP_TOLERATED_COLD __declspec(noinline) inline
#else
#define CPP_TOLERATED_COLD inline
#endif

// high and low 64 bits of the product of a and b
inline void cpp_mul_64x64_128(std::uint64_t a, std::uint64_t b, std::uint64_t &hi, std::uint64_t &lo) {
#if defined(__SIZEOF_INT128__) && ! defined(CPP_DECIMAL_GENERIC_MUL)
  __extension__ typedef unsigned __int128 cpp_uint128;
  const cpp_uint128 p = static_cast<cpp_uint128>(a) * b;
  hi = static_cast<std::uint64_t>(p >> 64);
  lo = static_cast<std::uint64_t>(p);
#elif defined(_MSC_VER) && ! defined(__clang__) && defined(_M_ARM64) && ! defined(_M_ARM64EC) && ! defined(CPP_DECIMAL_GENERIC_MUL)
  hi = __umulh(a, b);
  lo = a * b;
#elif defined(_MSC_VER) && ! defined(__clang__) && defined(_M_X64) && ! defined(_M_ARM64EC) && ! defined(CPP_DECIMAL_GENERIC_MUL)
  lo = _umul128(a, b, &hi);
#else
  // portable version, e.g. for 32-bit targets
  const std::uint64_t a0 = a & 0xFFFFFFFFULL, a1 = a >> 32;
  const std::uint64_t b0 = b & 0xFFFFFFFFULL, b1 = b >> 32;
  const std::uint64_t p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
  const std::uint64_t mid = (p00 >> 32) + (p01 & 0xFFFFFFFFULL) + (p10 & 0xFFFFFFFFULL);
  hi = p11 + (p01 >> 32) + (p10 >> 32) + (mid >> 32);
  lo = (mid << 32) | (p00 & 0xFFFFFFFFULL);
#endif
}

// number of leading zero bits of x > 0
inline int cpp_leading_zeros_64(std::uint64_t x) {
#if (defined(__GNUC__) || defined(__clang__)) && ! defined(CPP_DECIMAL_GENERIC_MUL)
  return __builtin_clzll(x);
#else
  int n = 0;
  if (x >> 32 == 0) { n += 32; x <<= 32; }
  if (x >> 48 == 0) { n += 16; x <<= 16; }
  if (x >> 56 == 0) { n += 8; x <<= 8; }
  if (x >> 60 == 0) { n += 4; x <<= 4; }
  if (x >> 62 == 0) { n += 2; x <<= 2; }
  if (x >> 63 == 0) { n += 1; }
  return n;
#endif
}

// Exact conversion of mant * 10^k for decimal exponents k below -22,
// below the range of the single division in cpp_decimal_finish, i.e. of
// magnitudes below 10^(n-23) for a significand of n digits (below 1e-17
// for the usual layout " d.ddddd-dd"), which occur in many ENDF-6 files
// (14% of the float fields of tsl-HinH2O of ENDF/B-VIII.0). It uses the
// algorithm of Eisel and Lemire as in the fast_float library (D. Lemire,
// "Number parsing at a gigabyte per second", Software: Practice and
// Experience 51(8), 2021): the significand, shifted so that its most
// significant bit is set, is multiplied with a 128-bit approximation of
// 5^k; the upper bits of the product give the significand of the double,
// its exponent follows from k and the shift. The result is the correctly
// rounded double (round half to even), subnormal numbers and underflow to
// zero included, i.e. the same value as std::strtod. The algorithm is
// valid for any significand below 2^64; the callers pass at most 15
// decimal digits (an ENDF-6 field of 11 characters holds at most 10). An
// exact tie between two doubles is impossible for k < -22, as its decimal
// significand would need more than 20 digits.
//
// Sets result to the double nearest to mant * 10^k (ties to even),
// negated if neg, for 0 < mant < 2^64 and k < -22. Returns false, leaving
// result unchanged, for k >= -22 and in the rare cases in which the
// 128-bit product does not determine the rounding; these are left to the
// general code path (cpp_strtod_c, std::strtod in the C locale).
//
// The table holds the entries of fast_float for 5^q, q = -342 ... -23:
// 2^b / 5^-q rounded down, incremented by one, and truncated to 128 bits
// with the most significant bit set. A significand below 2^64 times 10^q
// is below half the smallest subnormal number for q < -342, hence zero.
// Decimal exponents above 22 are not covered (cpp_decimal_finish returns
// false for them) and are left to the general code path, cpp_strtod_c.
// As k counts all digits written after the decimal point, a field whose
// significand has n digits (leading zeros not counted, trailing zeros
// counted) has k > 22 exactly if its magnitude is at least 10^(n+22):
// from 1e28 for the usual layout " d.ddddd+dd" (" 1.23456+28" has
// k = 23), from 1e23 for a single digit ("1+23"), while "1.000000+25"
// (mant = 1000000, k = 19) is converted by cpp_decimal_finish. Such
// fields do not occur in the ENDF/B-VIII.0 sublibraries of neutrons,
// thermal scattering, decay data and electro-atomic data and in the
// ENDF/B-VIII.1 neutron sublibrary: the largest k of their float fields
// is 22 (" 5.36000+27", the half-life of W-186 in seconds).
CPP_DECIMAL_NOINLINE inline bool cpp_decimal_to_double_negexp(std::uint64_t mant, int k, bool neg, double &result) {
  static const std::uint64_t pow5[] = {
    0xeef453d6923bd65aULL, 0x113faa2906a13b3fULL,   // 5^-342
    0x9558b4661b6565f8ULL, 0x4ac7ca59a424c507ULL,   // 5^-341
    0xbaaee17fa23ebf76ULL, 0x5d79bcf00d2df649ULL,   // 5^-340
    0xe95a99df8ace6f53ULL, 0xf4d82c2c107973dcULL,   // 5^-339
    0x91d8a02bb6c10594ULL, 0x79071b9b8a4be869ULL,   // 5^-338
    0xb64ec836a47146f9ULL, 0x9748e2826cdee284ULL,   // 5^-337
    0xe3e27a444d8d98b7ULL, 0xfd1b1b2308169b25ULL,   // 5^-336
    0x8e6d8c6ab0787f72ULL, 0xfe30f0f5e50e20f7ULL,   // 5^-335
    0xb208ef855c969f4fULL, 0xbdbd2d335e51a935ULL,   // 5^-334
    0xde8b2b66b3bc4723ULL, 0xad2c788035e61382ULL,   // 5^-333
    0x8b16fb203055ac76ULL, 0x4c3bcb5021afcc31ULL,   // 5^-332
    0xaddcb9e83c6b1793ULL, 0xdf4abe242a1bbf3dULL,   // 5^-331
    0xd953e8624b85dd78ULL, 0xd71d6dad34a2af0dULL,   // 5^-330
    0x87d4713d6f33aa6bULL, 0x8672648c40e5ad68ULL,   // 5^-329
    0xa9c98d8ccb009506ULL, 0x680efdaf511f18c2ULL,   // 5^-328
    0xd43bf0effdc0ba48ULL, 0x0212bd1b2566def2ULL,   // 5^-327
    0x84a57695fe98746dULL, 0x014bb630f7604b57ULL,   // 5^-326
    0xa5ced43b7e3e9188ULL, 0x419ea3bd35385e2dULL,   // 5^-325
    0xcf42894a5dce35eaULL, 0x52064cac828675b9ULL,   // 5^-324
    0x818995ce7aa0e1b2ULL, 0x7343efebd1940993ULL,   // 5^-323
    0xa1ebfb4219491a1fULL, 0x1014ebe6c5f90bf8ULL,   // 5^-322
    0xca66fa129f9b60a6ULL, 0xd41a26e077774ef6ULL,   // 5^-321
    0xfd00b897478238d0ULL, 0x8920b098955522b4ULL,   // 5^-320
    0x9e20735e8cb16382ULL, 0x55b46e5f5d5535b0ULL,   // 5^-319
    0xc5a890362fddbc62ULL, 0xeb2189f734aa831dULL,   // 5^-318
    0xf712b443bbd52b7bULL, 0xa5e9ec7501d523e4ULL,   // 5^-317
    0x9a6bb0aa55653b2dULL, 0x47b233c92125366eULL,   // 5^-316
    0xc1069cd4eabe89f8ULL, 0x999ec0bb696e840aULL,   // 5^-315
    0xf148440a256e2c76ULL, 0xc00670ea43ca250dULL,   // 5^-314
    0x96cd2a865764dbcaULL, 0x380406926a5e5728ULL,   // 5^-313
    0xbc807527ed3e12bcULL, 0xc605083704f5ecf2ULL,   // 5^-312
    0xeba09271e88d976bULL, 0xf7864a44c633682eULL,   // 5^-311
    0x93445b8731587ea3ULL, 0x7ab3ee6afbe0211dULL,   // 5^-310
    0xb8157268fdae9e4cULL, 0x5960ea05bad82964ULL,   // 5^-309
    0xe61acf033d1a45dfULL, 0x6fb92487298e33bdULL,   // 5^-308
    0x8fd0c16206306babULL, 0xa5d3b6d479f8e056ULL,   // 5^-307
    0xb3c4f1ba87bc8696ULL, 0x8f48a4899877186cULL,   // 5^-306
    0xe0b62e2929aba83cULL, 0x331acdabfe94de87ULL,   // 5^-305
    0x8c71dcd9ba0b4925ULL, 0x9ff0c08b7f1d0b14ULL,   // 5^-304
    0xaf8e5410288e1b6fULL, 0x07ecf0ae5ee44dd9ULL,   // 5^-303
    0xdb71e91432b1a24aULL, 0xc9e82cd9f69d6150ULL,   // 5^-302
    0x892731ac9faf056eULL, 0xbe311c083a225cd2ULL,   // 5^-301
    0xab70fe17c79ac6caULL, 0x6dbd630a48aaf406ULL,   // 5^-300
    0xd64d3d9db981787dULL, 0x092cbbccdad5b108ULL,   // 5^-299
    0x85f0468293f0eb4eULL, 0x25bbf56008c58ea5ULL,   // 5^-298
    0xa76c582338ed2621ULL, 0xaf2af2b80af6f24eULL,   // 5^-297
    0xd1476e2c07286faaULL, 0x1af5af660db4aee1ULL,   // 5^-296
    0x82cca4db847945caULL, 0x50d98d9fc890ed4dULL,   // 5^-295
    0xa37fce126597973cULL, 0xe50ff107bab528a0ULL,   // 5^-294
    0xcc5fc196fefd7d0cULL, 0x1e53ed49a96272c8ULL,   // 5^-293
    0xff77b1fcbebcdc4fULL, 0x25e8e89c13bb0f7aULL,   // 5^-292
    0x9faacf3df73609b1ULL, 0x77b191618c54e9acULL,   // 5^-291
    0xc795830d75038c1dULL, 0xd59df5b9ef6a2417ULL,   // 5^-290
    0xf97ae3d0d2446f25ULL, 0x4b0573286b44ad1dULL,   // 5^-289
    0x9becce62836ac577ULL, 0x4ee367f9430aec32ULL,   // 5^-288
    0xc2e801fb244576d5ULL, 0x229c41f793cda73fULL,   // 5^-287
    0xf3a20279ed56d48aULL, 0x6b43527578c1110fULL,   // 5^-286
    0x9845418c345644d6ULL, 0x830a13896b78aaa9ULL,   // 5^-285
    0xbe5691ef416bd60cULL, 0x23cc986bc656d553ULL,   // 5^-284
    0xedec366b11c6cb8fULL, 0x2cbfbe86b7ec8aa8ULL,   // 5^-283
    0x94b3a202eb1c3f39ULL, 0x7bf7d71432f3d6a9ULL,   // 5^-282
    0xb9e08a83a5e34f07ULL, 0xdaf5ccd93fb0cc53ULL,   // 5^-281
    0xe858ad248f5c22c9ULL, 0xd1b3400f8f9cff68ULL,   // 5^-280
    0x91376c36d99995beULL, 0x23100809b9c21fa1ULL,   // 5^-279
    0xb58547448ffffb2dULL, 0xabd40a0c2832a78aULL,   // 5^-278
    0xe2e69915b3fff9f9ULL, 0x16c90c8f323f516cULL,   // 5^-277
    0x8dd01fad907ffc3bULL, 0xae3da7d97f6792e3ULL,   // 5^-276
    0xb1442798f49ffb4aULL, 0x99cd11cfdf41779cULL,   // 5^-275
    0xdd95317f31c7fa1dULL, 0x40405643d711d583ULL,   // 5^-274
    0x8a7d3eef7f1cfc52ULL, 0x482835ea666b2572ULL,   // 5^-273
    0xad1c8eab5ee43b66ULL, 0xda3243650005eecfULL,   // 5^-272
    0xd863b256369d4a40ULL, 0x90bed43e40076a82ULL,   // 5^-271
    0x873e4f75e2224e68ULL, 0x5a7744a6e804a291ULL,   // 5^-270
    0xa90de3535aaae202ULL, 0x711515d0a205cb36ULL,   // 5^-269
    0xd3515c2831559a83ULL, 0x0d5a5b44ca873e03ULL,   // 5^-268
    0x8412d9991ed58091ULL, 0xe858790afe9486c2ULL,   // 5^-267
    0xa5178fff668ae0b6ULL, 0x626e974dbe39a872ULL,   // 5^-266
    0xce5d73ff402d98e3ULL, 0xfb0a3d212dc8128fULL,   // 5^-265
    0x80fa687f881c7f8eULL, 0x7ce66634bc9d0b99ULL,   // 5^-264
    0xa139029f6a239f72ULL, 0x1c1fffc1ebc44e80ULL,   // 5^-263
    0xc987434744ac874eULL, 0xa327ffb266b56220ULL,   // 5^-262
    0xfbe9141915d7a922ULL, 0x4bf1ff9f0062baa8ULL,   // 5^-261
    0x9d71ac8fada6c9b5ULL, 0x6f773fc3603db4a9ULL,   // 5^-260
    0xc4ce17b399107c22ULL, 0xcb550fb4384d21d3ULL,   // 5^-259
    0xf6019da07f549b2bULL, 0x7e2a53a146606a48ULL,   // 5^-258
    0x99c102844f94e0fbULL, 0x2eda7444cbfc426dULL,   // 5^-257
    0xc0314325637a1939ULL, 0xfa911155fefb5308ULL,   // 5^-256
    0xf03d93eebc589f88ULL, 0x793555ab7eba27caULL,   // 5^-255
    0x96267c7535b763b5ULL, 0x4bc1558b2f3458deULL,   // 5^-254
    0xbbb01b9283253ca2ULL, 0x9eb1aaedfb016f16ULL,   // 5^-253
    0xea9c227723ee8bcbULL, 0x465e15a979c1cadcULL,   // 5^-252
    0x92a1958a7675175fULL, 0x0bfacd89ec191ec9ULL,   // 5^-251
    0xb749faed14125d36ULL, 0xcef980ec671f667bULL,   // 5^-250
    0xe51c79a85916f484ULL, 0x82b7e12780e7401aULL,   // 5^-249
    0x8f31cc0937ae58d2ULL, 0xd1b2ecb8b0908810ULL,   // 5^-248
    0xb2fe3f0b8599ef07ULL, 0x861fa7e6dcb4aa15ULL,   // 5^-247
    0xdfbdcece67006ac9ULL, 0x67a791e093e1d49aULL,   // 5^-246
    0x8bd6a141006042bdULL, 0xe0c8bb2c5c6d24e0ULL,   // 5^-245
    0xaecc49914078536dULL, 0x58fae9f773886e18ULL,   // 5^-244
    0xda7f5bf590966848ULL, 0xaf39a475506a899eULL,   // 5^-243
    0x888f99797a5e012dULL, 0x6d8406c952429603ULL,   // 5^-242
    0xaab37fd7d8f58178ULL, 0xc8e5087ba6d33b83ULL,   // 5^-241
    0xd5605fcdcf32e1d6ULL, 0xfb1e4a9a90880a64ULL,   // 5^-240
    0x855c3be0a17fcd26ULL, 0x5cf2eea09a55067fULL,   // 5^-239
    0xa6b34ad8c9dfc06fULL, 0xf42faa48c0ea481eULL,   // 5^-238
    0xd0601d8efc57b08bULL, 0xf13b94daf124da26ULL,   // 5^-237
    0x823c12795db6ce57ULL, 0x76c53d08d6b70858ULL,   // 5^-236
    0xa2cb1717b52481edULL, 0x54768c4b0c64ca6eULL,   // 5^-235
    0xcb7ddcdda26da268ULL, 0xa9942f5dcf7dfd09ULL,   // 5^-234
    0xfe5d54150b090b02ULL, 0xd3f93b35435d7c4cULL,   // 5^-233
    0x9efa548d26e5a6e1ULL, 0xc47bc5014a1a6dafULL,   // 5^-232
    0xc6b8e9b0709f109aULL, 0x359ab6419ca1091bULL,   // 5^-231
    0xf867241c8cc6d4c0ULL, 0xc30163d203c94b62ULL,   // 5^-230
    0x9b407691d7fc44f8ULL, 0x79e0de63425dcf1dULL,   // 5^-229
    0xc21094364dfb5636ULL, 0x985915fc12f542e4ULL,   // 5^-228
    0xf294b943e17a2bc4ULL, 0x3e6f5b7b17b2939dULL,   // 5^-227
    0x979cf3ca6cec5b5aULL, 0xa705992ceecf9c42ULL,   // 5^-226
    0xbd8430bd08277231ULL, 0x50c6ff782a838353ULL,   // 5^-225
    0xece53cec4a314ebdULL, 0xa4f8bf5635246428ULL,   // 5^-224
    0x940f4613ae5ed136ULL, 0x871b7795e136be99ULL,   // 5^-223
    0xb913179899f68584ULL, 0x28e2557b59846e3fULL,   // 5^-222
    0xe757dd7ec07426e5ULL, 0x331aeada2fe589cfULL,   // 5^-221
    0x9096ea6f3848984fULL, 0x3ff0d2c85def7621ULL,   // 5^-220
    0xb4bca50b065abe63ULL, 0x0fed077a756b53a9ULL,   // 5^-219
    0xe1ebce4dc7f16dfbULL, 0xd3e8495912c62894ULL,   // 5^-218
    0x8d3360f09cf6e4bdULL, 0x64712dd7abbbd95cULL,   // 5^-217
    0xb080392cc4349decULL, 0xbd8d794d96aacfb3ULL,   // 5^-216
    0xdca04777f541c567ULL, 0xecf0d7a0fc5583a0ULL,   // 5^-215
    0x89e42caaf9491b60ULL, 0xf41686c49db57244ULL,   // 5^-214
    0xac5d37d5b79b6239ULL, 0x311c2875c522ced5ULL,   // 5^-213
    0xd77485cb25823ac7ULL, 0x7d633293366b828bULL,   // 5^-212
    0x86a8d39ef77164bcULL, 0xae5dff9c02033197ULL,   // 5^-211
    0xa8530886b54dbdebULL, 0xd9f57f830283fdfcULL,   // 5^-210
    0xd267caa862a12d66ULL, 0xd072df63c324fd7bULL,   // 5^-209
    0x8380dea93da4bc60ULL, 0x4247cb9e59f71e6dULL,   // 5^-208
    0xa46116538d0deb78ULL, 0x52d9be85f074e608ULL,   // 5^-207
    0xcd795be870516656ULL, 0x67902e276c921f8bULL,   // 5^-206
    0x806bd9714632dff6ULL, 0x00ba1cd8a3db53b6ULL,   // 5^-205
    0xa086cfcd97bf97f3ULL, 0x80e8a40eccd228a4ULL,   // 5^-204
    0xc8a883c0fdaf7df0ULL, 0x6122cd128006b2cdULL,   // 5^-203
    0xfad2a4b13d1b5d6cULL, 0x796b805720085f81ULL,   // 5^-202
    0x9cc3a6eec6311a63ULL, 0xcbe3303674053bb0ULL,   // 5^-201
    0xc3f490aa77bd60fcULL, 0xbedbfc4411068a9cULL,   // 5^-200
    0xf4f1b4d515acb93bULL, 0xee92fb5515482d44ULL,   // 5^-199
    0x991711052d8bf3c5ULL, 0x751bdd152d4d1c4aULL,   // 5^-198
    0xbf5cd54678eef0b6ULL, 0xd262d45a78a0635dULL,   // 5^-197
    0xef340a98172aace4ULL, 0x86fb897116c87c34ULL,   // 5^-196
    0x9580869f0e7aac0eULL, 0xd45d35e6ae3d4da0ULL,   // 5^-195
    0xbae0a846d2195712ULL, 0x8974836059cca109ULL,   // 5^-194
    0xe998d258869facd7ULL, 0x2bd1a438703fc94bULL,   // 5^-193
    0x91ff83775423cc06ULL, 0x7b6306a34627ddcfULL,   // 5^-192
    0xb67f6455292cbf08ULL, 0x1a3bc84c17b1d542ULL,   // 5^-191
    0xe41f3d6a7377eecaULL, 0x20caba5f1d9e4a93ULL,   // 5^-190
    0x8e938662882af53eULL, 0x547eb47b7282ee9cULL,   // 5^-189
    0xb23867fb2a35b28dULL, 0xe99e619a4f23aa43ULL,   // 5^-188
    0xdec681f9f4c31f31ULL, 0x6405fa00e2ec94d4ULL,   // 5^-187
    0x8b3c113c38f9f37eULL, 0xde83bc408dd3dd04ULL,   // 5^-186
    0xae0b158b4738705eULL, 0x9624ab50b148d445ULL,   // 5^-185
    0xd98ddaee19068c76ULL, 0x3badd624dd9b0957ULL,   // 5^-184
    0x87f8a8d4cfa417c9ULL, 0xe54ca5d70a80e5d6ULL,   // 5^-183
    0xa9f6d30a038d1dbcULL, 0x5e9fcf4ccd211f4cULL,   // 5^-182
    0xd47487cc8470652bULL, 0x7647c3200069671fULL,   // 5^-181
    0x84c8d4dfd2c63f3bULL, 0x29ecd9f40041e073ULL,   // 5^-180
    0xa5fb0a17c777cf09ULL, 0xf468107100525890ULL,   // 5^-179
    0xcf79cc9db955c2ccULL, 0x7182148d4066eeb4ULL,   // 5^-178
    0x81ac1fe293d599bfULL, 0xc6f14cd848405530ULL,   // 5^-177
    0xa21727db38cb002fULL, 0xb8ada00e5a506a7cULL,   // 5^-176
    0xca9cf1d206fdc03bULL, 0xa6d90811f0e4851cULL,   // 5^-175
    0xfd442e4688bd304aULL, 0x908f4a166d1da663ULL,   // 5^-174
    0x9e4a9cec15763e2eULL, 0x9a598e4e043287feULL,   // 5^-173
    0xc5dd44271ad3cdbaULL, 0x40eff1e1853f29fdULL,   // 5^-172
    0xf7549530e188c128ULL, 0xd12bee59e68ef47cULL,   // 5^-171
    0x9a94dd3e8cf578b9ULL, 0x82bb74f8301958ceULL,   // 5^-170
    0xc13a148e3032d6e7ULL, 0xe36a52363c1faf01ULL,   // 5^-169
    0xf18899b1bc3f8ca1ULL, 0xdc44e6c3cb279ac1ULL,   // 5^-168
    0x96f5600f15a7b7e5ULL, 0x29ab103a5ef8c0b9ULL,   // 5^-167
    0xbcb2b812db11a5deULL, 0x7415d448f6b6f0e7ULL,   // 5^-166
    0xebdf661791d60f56ULL, 0x111b495b3464ad21ULL,   // 5^-165
    0x936b9fcebb25c995ULL, 0xcab10dd900beec34ULL,   // 5^-164
    0xb84687c269ef3bfbULL, 0x3d5d514f40eea742ULL,   // 5^-163
    0xe65829b3046b0afaULL, 0x0cb4a5a3112a5112ULL,   // 5^-162
    0x8ff71a0fe2c2e6dcULL, 0x47f0e785eaba72abULL,   // 5^-161
    0xb3f4e093db73a093ULL, 0x59ed216765690f56ULL,   // 5^-160
    0xe0f218b8d25088b8ULL, 0x306869c13ec3532cULL,   // 5^-159
    0x8c974f7383725573ULL, 0x1e414218c73a13fbULL,   // 5^-158
    0xafbd2350644eeacfULL, 0xe5d1929ef90898faULL,   // 5^-157
    0xdbac6c247d62a583ULL, 0xdf45f746b74abf39ULL,   // 5^-156
    0x894bc396ce5da772ULL, 0x6b8bba8c328eb783ULL,   // 5^-155
    0xab9eb47c81f5114fULL, 0x066ea92f3f326564ULL,   // 5^-154
    0xd686619ba27255a2ULL, 0xc80a537b0efefebdULL,   // 5^-153
    0x8613fd0145877585ULL, 0xbd06742ce95f5f36ULL,   // 5^-152
    0xa798fc4196e952e7ULL, 0x2c48113823b73704ULL,   // 5^-151
    0xd17f3b51fca3a7a0ULL, 0xf75a15862ca504c5ULL,   // 5^-150
    0x82ef85133de648c4ULL, 0x9a984d73dbe722fbULL,   // 5^-149
    0xa3ab66580d5fdaf5ULL, 0xc13e60d0d2e0ebbaULL,   // 5^-148
    0xcc963fee10b7d1b3ULL, 0x318df905079926a8ULL,   // 5^-147
    0xffbbcfe994e5c61fULL, 0xfdf17746497f7052ULL,   // 5^-146
    0x9fd561f1fd0f9bd3ULL, 0xfeb6ea8bedefa633ULL,   // 5^-145
    0xc7caba6e7c5382c8ULL, 0xfe64a52ee96b8fc0ULL,   // 5^-144
    0xf9bd690a1b68637bULL, 0x3dfdce7aa3c673b0ULL,   // 5^-143
    0x9c1661a651213e2dULL, 0x06bea10ca65c084eULL,   // 5^-142
    0xc31bfa0fe5698db8ULL, 0x486e494fcff30a62ULL,   // 5^-141
    0xf3e2f893dec3f126ULL, 0x5a89dba3c3efccfaULL,   // 5^-140
    0x986ddb5c6b3a76b7ULL, 0xf89629465a75e01cULL,   // 5^-139
    0xbe89523386091465ULL, 0xf6bbb397f1135823ULL,   // 5^-138
    0xee2ba6c0678b597fULL, 0x746aa07ded582e2cULL,   // 5^-137
    0x94db483840b717efULL, 0xa8c2a44eb4571cdcULL,   // 5^-136
    0xba121a4650e4ddebULL, 0x92f34d62616ce413ULL,   // 5^-135
    0xe896a0d7e51e1566ULL, 0x77b020baf9c81d17ULL,   // 5^-134
    0x915e2486ef32cd60ULL, 0x0ace1474dc1d122eULL,   // 5^-133
    0xb5b5ada8aaff80b8ULL, 0x0d819992132456baULL,   // 5^-132
    0xe3231912d5bf60e6ULL, 0x10e1fff697ed6c69ULL,   // 5^-131
    0x8df5efabc5979c8fULL, 0xca8d3ffa1ef463c1ULL,   // 5^-130
    0xb1736b96b6fd83b3ULL, 0xbd308ff8a6b17cb2ULL,   // 5^-129
    0xddd0467c64bce4a0ULL, 0xac7cb3f6d05ddbdeULL,   // 5^-128
    0x8aa22c0dbef60ee4ULL, 0x6bcdf07a423aa96bULL,   // 5^-127
    0xad4ab7112eb3929dULL, 0x86c16c98d2c953c6ULL,   // 5^-126
    0xd89d64d57a607744ULL, 0xe871c7bf077ba8b7ULL,   // 5^-125
    0x87625f056c7c4a8bULL, 0x11471cd764ad4972ULL,   // 5^-124
    0xa93af6c6c79b5d2dULL, 0xd598e40d3dd89bcfULL,   // 5^-123
    0xd389b47879823479ULL, 0x4aff1d108d4ec2c3ULL,   // 5^-122
    0x843610cb4bf160cbULL, 0xcedf722a585139baULL,   // 5^-121
    0xa54394fe1eedb8feULL, 0xc2974eb4ee658828ULL,   // 5^-120
    0xce947a3da6a9273eULL, 0x733d226229feea32ULL,   // 5^-119
    0x811ccc668829b887ULL, 0x0806357d5a3f525fULL,   // 5^-118
    0xa163ff802a3426a8ULL, 0xca07c2dcb0cf26f7ULL,   // 5^-117
    0xc9bcff6034c13052ULL, 0xfc89b393dd02f0b5ULL,   // 5^-116
    0xfc2c3f3841f17c67ULL, 0xbbac2078d443ace2ULL,   // 5^-115
    0x9d9ba7832936edc0ULL, 0xd54b944b84aa4c0dULL,   // 5^-114
    0xc5029163f384a931ULL, 0x0a9e795e65d4df11ULL,   // 5^-113
    0xf64335bcf065d37dULL, 0x4d4617b5ff4a16d5ULL,   // 5^-112
    0x99ea0196163fa42eULL, 0x504bced1bf8e4e45ULL,   // 5^-111
    0xc06481fb9bcf8d39ULL, 0xe45ec2862f71e1d6ULL,   // 5^-110
    0xf07da27a82c37088ULL, 0x5d767327bb4e5a4cULL,   // 5^-109
    0x964e858c91ba2655ULL, 0x3a6a07f8d510f86fULL,   // 5^-108
    0xbbe226efb628afeaULL, 0x890489f70a55368bULL,   // 5^-107
    0xeadab0aba3b2dbe5ULL, 0x2b45ac74ccea842eULL,   // 5^-106
    0x92c8ae6b464fc96fULL, 0x3b0b8bc90012929dULL,   // 5^-105
    0xb77ada0617e3bbcbULL, 0x09ce6ebb40173744ULL,   // 5^-104
    0xe55990879ddcaabdULL, 0xcc420a6a101d0515ULL,   // 5^-103
    0x8f57fa54c2a9eab6ULL, 0x9fa946824a12232dULL,   // 5^-102
    0xb32df8e9f3546564ULL, 0x47939822dc96abf9ULL,   // 5^-101
    0xdff9772470297ebdULL, 0x59787e2b93bc56f7ULL,   // 5^-100
    0x8bfbea76c619ef36ULL, 0x57eb4edb3c55b65aULL,   // 5^-99
    0xaefae51477a06b03ULL, 0xede622920b6b23f1ULL,   // 5^-98
    0xdab99e59958885c4ULL, 0xe95fab368e45ecedULL,   // 5^-97
    0x88b402f7fd75539bULL, 0x11dbcb0218ebb414ULL,   // 5^-96
    0xaae103b5fcd2a881ULL, 0xd652bdc29f26a119ULL,   // 5^-95
    0xd59944a37c0752a2ULL, 0x4be76d3346f0495fULL,   // 5^-94
    0x857fcae62d8493a5ULL, 0x6f70a4400c562ddbULL,   // 5^-93
    0xa6dfbd9fb8e5b88eULL, 0xcb4ccd500f6bb952ULL,   // 5^-92
    0xd097ad07a71f26b2ULL, 0x7e2000a41346a7a7ULL,   // 5^-91
    0x825ecc24c873782fULL, 0x8ed400668c0c28c8ULL,   // 5^-90
    0xa2f67f2dfa90563bULL, 0x728900802f0f32faULL,   // 5^-89
    0xcbb41ef979346bcaULL, 0x4f2b40a03ad2ffb9ULL,   // 5^-88
    0xfea126b7d78186bcULL, 0xe2f610c84987bfa8ULL,   // 5^-87
    0x9f24b832e6b0f436ULL, 0x0dd9ca7d2df4d7c9ULL,   // 5^-86
    0xc6ede63fa05d3143ULL, 0x91503d1c79720dbbULL,   // 5^-85
    0xf8a95fcf88747d94ULL, 0x75a44c6397ce912aULL,   // 5^-84
    0x9b69dbe1b548ce7cULL, 0xc986afbe3ee11abaULL,   // 5^-83
    0xc24452da229b021bULL, 0xfbe85badce996168ULL,   // 5^-82
    0xf2d56790ab41c2a2ULL, 0xfae27299423fb9c3ULL,   // 5^-81
    0x97c560ba6b0919a5ULL, 0xdccd879fc967d41aULL,   // 5^-80
    0xbdb6b8e905cb600fULL, 0x5400e987bbc1c920ULL,   // 5^-79
    0xed246723473e3813ULL, 0x290123e9aab23b68ULL,   // 5^-78
    0x9436c0760c86e30bULL, 0xf9a0b6720aaf6521ULL,   // 5^-77
    0xb94470938fa89bceULL, 0xf808e40e8d5b3e69ULL,   // 5^-76
    0xe7958cb87392c2c2ULL, 0xb60b1d1230b20e04ULL,   // 5^-75
    0x90bd77f3483bb9b9ULL, 0xb1c6f22b5e6f48c2ULL,   // 5^-74
    0xb4ecd5f01a4aa828ULL, 0x1e38aeb6360b1af3ULL,   // 5^-73
    0xe2280b6c20dd5232ULL, 0x25c6da63c38de1b0ULL,   // 5^-72
    0x8d590723948a535fULL, 0x579c487e5a38ad0eULL,   // 5^-71
    0xb0af48ec79ace837ULL, 0x2d835a9df0c6d851ULL,   // 5^-70
    0xdcdb1b2798182244ULL, 0xf8e431456cf88e65ULL,   // 5^-69
    0x8a08f0f8bf0f156bULL, 0x1b8e9ecb641b58ffULL,   // 5^-68
    0xac8b2d36eed2dac5ULL, 0xe272467e3d222f3fULL,   // 5^-67
    0xd7adf884aa879177ULL, 0x5b0ed81dcc6abb0fULL,   // 5^-66
    0x86ccbb52ea94baeaULL, 0x98e947129fc2b4e9ULL,   // 5^-65
    0xa87fea27a539e9a5ULL, 0x3f2398d747b36224ULL,   // 5^-64
    0xd29fe4b18e88640eULL, 0x8eec7f0d19a03aadULL,   // 5^-63
    0x83a3eeeef9153e89ULL, 0x1953cf68300424acULL,   // 5^-62
    0xa48ceaaab75a8e2bULL, 0x5fa8c3423c052dd7ULL,   // 5^-61
    0xcdb02555653131b6ULL, 0x3792f412cb06794dULL,   // 5^-60
    0x808e17555f3ebf11ULL, 0xe2bbd88bbee40bd0ULL,   // 5^-59
    0xa0b19d2ab70e6ed6ULL, 0x5b6aceaeae9d0ec4ULL,   // 5^-58
    0xc8de047564d20a8bULL, 0xf245825a5a445275ULL,   // 5^-57
    0xfb158592be068d2eULL, 0xeed6e2f0f0d56712ULL,   // 5^-56
    0x9ced737bb6c4183dULL, 0x55464dd69685606bULL,   // 5^-55
    0xc428d05aa4751e4cULL, 0xaa97e14c3c26b886ULL,   // 5^-54
    0xf53304714d9265dfULL, 0xd53dd99f4b3066a8ULL,   // 5^-53
    0x993fe2c6d07b7fabULL, 0xe546a8038efe4029ULL,   // 5^-52
    0xbf8fdb78849a5f96ULL, 0xde98520472bdd033ULL,   // 5^-51
    0xef73d256a5c0f77cULL, 0x963e66858f6d4440ULL,   // 5^-50
    0x95a8637627989aadULL, 0xdde7001379a44aa8ULL,   // 5^-49
    0xbb127c53b17ec159ULL, 0x5560c018580d5d52ULL,   // 5^-48
    0xe9d71b689dde71afULL, 0xaab8f01e6e10b4a6ULL,   // 5^-47
    0x9226712162ab070dULL, 0xcab3961304ca70e8ULL,   // 5^-46
    0xb6b00d69bb55c8d1ULL, 0x3d607b97c5fd0d22ULL,   // 5^-45
    0xe45c10c42a2b3b05ULL, 0x8cb89a7db77c506aULL,   // 5^-44
    0x8eb98a7a9a5b04e3ULL, 0x77f3608e92adb242ULL,   // 5^-43
    0xb267ed1940f1c61cULL, 0x55f038b237591ed3ULL,   // 5^-42
    0xdf01e85f912e37a3ULL, 0x6b6c46dec52f6688ULL,   // 5^-41
    0x8b61313bbabce2c6ULL, 0x2323ac4b3b3da015ULL,   // 5^-40
    0xae397d8aa96c1b77ULL, 0xabec975e0a0d081aULL,   // 5^-39
    0xd9c7dced53c72255ULL, 0x96e7bd358c904a21ULL,   // 5^-38
    0x881cea14545c7575ULL, 0x7e50d64177da2e54ULL,   // 5^-37
    0xaa242499697392d2ULL, 0xdde50bd1d5d0b9e9ULL,   // 5^-36
    0xd4ad2dbfc3d07787ULL, 0x955e4ec64b44e864ULL,   // 5^-35
    0x84ec3c97da624ab4ULL, 0xbd5af13bef0b113eULL,   // 5^-34
    0xa6274bbdd0fadd61ULL, 0xecb1ad8aeacdd58eULL,   // 5^-33
    0xcfb11ead453994baULL, 0x67de18eda5814af2ULL,   // 5^-32
    0x81ceb32c4b43fcf4ULL, 0x80eacf948770ced7ULL,   // 5^-31
    0xa2425ff75e14fc31ULL, 0xa1258379a94d028dULL,   // 5^-30
    0xcad2f7f5359a3b3eULL, 0x096ee45813a04330ULL,   // 5^-29
    0xfd87b5f28300ca0dULL, 0x8bca9d6e188853fcULL,   // 5^-28
    0x9e74d1b791e07e48ULL, 0x775ea264cf55347eULL,   // 5^-27
    0xc612062576589ddaULL, 0x95364afe032a819eULL,   // 5^-26
    0xf79687aed3eec551ULL, 0x3a83ddbd83f52205ULL,   // 5^-25
    0x9abe14cd44753b52ULL, 0xc4926a9672793543ULL,   // 5^-24
    0xc16d9a0095928a27ULL, 0x75b7053c0f178294ULL    // 5^-23
  };
  const int smallest_q = -342;
  std::uint64_t bits;
  if (k > -23) {
    return false;
  } else if (k < smallest_q) {
    bits = 0;   // below half the smallest subnormal number: zero
  } else {
    const int lz = cpp_leading_zeros_64(mant);
    const std::uint64_t w = mant << lz;
    const int index = 2 * (k - smallest_q);
    std::uint64_t hi, lo;
    cpp_mul_64x64_128(w, pow5[index], hi, lo);
    // 52 + 3 exact upper bits are needed; refine with the lower half of
    // the power of five if the bits below them are all ones
    const std::uint64_t precision_mask = 0xFFFFFFFFFFFFFFFFULL >> 55;
    if ((hi & precision_mask) == precision_mask) {
      std::uint64_t hi2, lo2;
      cpp_mul_64x64_128(w, pow5[index + 1], hi2, lo2);
      lo += hi2;
      if (hi2 > lo) hi++;
    }
    // the approximation of 5^k may not decide the result (impossible for
    // k >= -27 as in fast_float): left to std::strtod
    if (lo == 0xFFFFFFFFFFFFFFFFULL && k < -27) return false;
    const int upperbit = static_cast<int>(hi >> 63);
    const int shift = upperbit + 64 - 52 - 3;
    std::uint64_t m = hi >> shift;
    // -ceil(log2(5^-k)) + k + 63, without right-shifting a negative number
    const int power_k = (((152170 + 65536) * k + (2048 * 65536)) >> 16) - 2048 + 63;
    int power2 = power_k + upperbit - lz + 1023;
    if (power2 <= 0) {
      // subnormal number or zero
      if (-power2 + 1 >= 64) {
        bits = 0;
      } else {
        m >>= -power2 + 1;
        m += (m & 1);
        m >>= 1;
        // rounding up may give the smallest normal number
        power2 = (m < (1ULL << 52)) ? 0 : 1;
        bits = (m & ((1ULL << 52) - 1)) | (static_cast<std::uint64_t>(power2) << 52);
      }
    } else {
      m += (m & 1);
      m >>= 1;
      if (m >= (2ULL << 52)) {
        m = 1ULL << 52;
        power2++;
      }
      m &= ~(1ULL << 52);
      bits = m | (static_cast<std::uint64_t>(power2) << 52);
    }
  }
  if (neg) bits |= 0x8000000000000000ULL;
  std::memcpy(&result, &bits, sizeof(result));
  return true;
}


// The common last step of cpp_fast_decimal_to_double, cpp_fast_field_swar
// and cpp_fast_field_to_double: the double for the decimal significand
// mant (the digits of the number as an integer, at most 15 significant
// digits), the decimal exponent k (the exponent of the number minus the
// number of digits after the decimal point, so that the value is
// mant * 10^k) and the sign neg. A significand of at most 15 digits is
// below 2^53, and 10^|k| is exactly representable for |k| <= 22, so for
// -22 <= k <= 22 both operands are exact and the single IEEE
// multiplication or division gives the correctly rounded result, i.e. the
// same value as std::strtod. The sign is applied last, so that a negative
// zero gives -0.0. Decimal exponents below -22 are converted exactly with
// cpp_decimal_to_double_negexp. Returns false, leaving result unchanged,
// for k > 22 and in the rare cases cpp_decimal_to_double_negexp leaves to
// the general code path.
CPP_DECIMAL_FORCEINLINE bool cpp_decimal_finish(std::uint64_t mant, int k, bool neg, double &result) {
  static const double p10[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
  };
  double v = static_cast<double>(mant);
  if (mant != 0) {
    if (k < -22) return cpp_decimal_to_double_negexp(mant, k, neg, result);
    if (k > 22) return false;
    if (k > 0) v *= p10[k];
    else if (k < 0) v /= p10[-k];
  }
  result = neg ? -v : v;
  return true;
}


// Fast exact conversion of a plain decimal number of the form
// [+-]digits[.digits][(e|E)[+-]digits] (as assembled by endfstr2float)
// to double, the same value as std::strtod (see cpp_decimal_finish).
// Returns false for more than 15 significant digits, decimal exponents
// above 22, the rare cases cpp_decimal_to_double_negexp declines and
// anything else, in which case std::strtod must be used.
inline bool cpp_fast_decimal_to_double(const char* s, double &result) {
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
  return cpp_decimal_finish(mant, expo - nfrac, neg, result);
}


#if defined(__BYTE_ORDER__) && defined(__ORDER_LITTLE_ENDIAN__)
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define CPP_FIELD_SWAR_LE 1
#endif
#elif defined(_MSC_VER) && (defined(_M_X64) || defined(_M_IX86) || defined(_M_ARM64) || defined(_M_ARM))
#define CPP_FIELD_SWAR_LE 1
#endif

// First stage: the two layouts of almost all float fields in ENDF-6 files,
// " d.dddddd+d" and " d.ddddd+dd" (first character blank, '+' or '-';
// exponent sign '+' or '-'), checked and decoded with 64-bit integer
// operations on two overlapping loads of the 11 bytes of the field, and
// converted with cpp_decimal_finish. Returns 1 if converted, -1 if the
// field has one of these layouts but cpp_decimal_finish does not convert
// it (decimal exponent above 22, or left to std::strtod by
// cpp_decimal_to_double_negexp; the common path rejects it as well), and
// 0 for any other content.
inline int cpp_fast_field_swar(const char* str, double &result) {
#ifdef CPP_FIELD_SWAR_LE
  const std::uint64_t ones = 0x0101010101010101ULL;
  std::uint64_t a, b;
  std::memcpy(&a, str, 8);       // bytes 0..7
  std::memcpy(&b, str + 3, 8);   // bytes 3..10
  // digit value in each byte; high bit of nd* set where a byte is no digit
  const std::uint64_t ta = a ^ (0x30 * ones);
  const std::uint64_t tb = b ^ (0x30 * ones);
  const std::uint64_t nda = (ta | (ta + 0x76 * ones)) & (0x80 * ones);
  const std::uint64_t ndb = (tb | (tb + 0x76 * ones)) & (0x80 * ones);
  const unsigned c0 = static_cast<unsigned>(a & 0xff);
  // byte 0 blank or sign, byte 1 digit, byte 2 '.', bytes 3..7 digits
  if ((nda & 0x8080808080008000ULL) != 0
      || ((a >> 16) & 0xff) != '.'
      || ! (c0 == ' ' || c0 == '+' || c0 == '-')) {
    return 0;
  }
  const std::uint64_t d1 = (ta >> 8) & 0xff;
  const unsigned c8 = static_cast<unsigned>((b >> 40) & 0xff);
  const unsigned c9 = static_cast<unsigned>((b >> 48) & 0xff);
  std::uint64_t w;   // the significand digits, most significant first
  int expo, nfrac;
  bool eneg;
  if ((c9 == '+' || c9 == '-') && (ndb & 0x8000808080808080ULL) == 0) {
    // d.dddddd+d: digits at bytes 1, 3..8, exponent at byte 10
    w = (tb << 16) | (d1 << 8);
    expo = static_cast<int>(tb >> 56);
    nfrac = 6;
    eneg = (c9 == '-');
  } else if ((c8 == '+' || c8 == '-') && (ndb & 0x8080008080808080ULL) == 0) {
    // d.ddddd+dd: digits at bytes 1, 3..7, exponent at bytes 9, 10
    w = (tb << 24) | (d1 << 16);
    expo = static_cast<int>((tb >> 48) & 0xff) * 10 + static_cast<int>(tb >> 56);
    nfrac = 5;
    eneg = (c8 == '-');
  } else {
    return 0;
  }
  // eight digits to a number (most significant digit in the lowest byte)
  w = (w * 10) + (w >> 8);
  w = (((w & 0x000000FF000000FFULL) * 0x000F424000000064ULL)
       + (((w >> 16) & 0x000000FF000000FFULL) * 0x0000271000000001ULL)) >> 32;
  const unsigned long long mant = static_cast<std::uint32_t>(w);
  const bool neg = (c0 == '-');
  const int k = (eneg ? -expo : expo) - nfrac;
  return cpp_decimal_finish(mant, k, neg, result) ? 1 : -1;
#else
  (void) str;
  (void) result;
  return 0;
#endif
}


// Single-pass conversion of the 11 characters of a float field for the
// common case: leading spaces, a decimal number of the form
// [+-]digits[.digits] optionally followed by an exponent introduced by
// e/E (or d/D if accepted) or directly by its sign, and trailing spaces,
// converted with cpp_decimal_finish to the same value as std::strtod.
// Returns false for any other content of the field, more than 15
// significant digits, decimal exponents above 22 and the rare cases
// cpp_decimal_to_double_negexp leaves to std::strtod; these are then
// handled by the general code path. The two layouts of almost all fields
// are first tried with cpp_fast_field_swar, which gives the same result
// for them.
inline bool cpp_fast_field_to_double(const char* str, bool accept_d_exponent, double &result) {
  const int swar = cpp_fast_field_swar(str, result);
  if (swar != 0) return swar > 0;
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
  return cpp_decimal_finish(mant, expo - nfrac, neg, result);
}


// Row kernels: the float fields of a line converted in one call.
//
// A row kernel converts the fields j = 0..5 of a line that are selected
// by the bits of `want` and returns the mask of the fields it has
// converted, with their values in out[j]. It converts a field only if
// cpp_fast_field_to_double converts it, and to the same bits. The caller
// reads every field the kernel leaves (bit not set) with the per-field
// path (cpp_read_field), so that the results, and the errors for
// malformed fields, do not depend on the kernel. A kernel does not throw
// and only reads the first 75 columns of the line (every line is padded
// to 75 columns, see cpp_pad_short_line; the fields are in columns 1-66,
// the AVX2 tier loads 16 bytes per field, up to column 71). `flags` holds the parsing
// options that matter for the conversion (CPP_ROW_ACCEPT_D_EXPONENT).
//
// The kernels are the tiers of a small table (cpp_row_tiers): the scalar
// tier, cpp_fast_field_to_double applied field by field, is always
// present; optional tiers for vector instruction sets are only built for
// x86-64 with GCC and Clang (CPP_ROW_X86_64_GNU, which does not depend on
// the instruction set the module is compiled for, so that the code of
// such a tier has to be compiled with per-function target attributes)
// and with MSVC (CPP_ROW_X86_64_MSVC, which needs no such attributes)
// and only used if the CPU supports them (cpp_cpu_features), and for
// AArch64 (CPP_ROW_NEON: GCC, Clang and MSVC; NEON is part of the
// baseline instruction set there, so that this tier needs neither target
// attributes nor a detection at run time). One tier,
// or none, is selected once when the module is loaded
// (cpp_row_selected), as given by the environment variable
// ENDF_PARSERPY_CPP_BULK_BODIES:
//   auto (also if unset or empty): the first vector tier of the table
//     that is built and supported by the CPU and taken by the automatic
//     selection (all except the NEON tier of GCC builds, see
//     CPP_ROW_NEON_NOT_AUTO), otherwise the scalar tier;
//   off: none;
//   scalar, avx2, avx512, neon: this tier if it is built and supported by
//     the CPU, otherwise as auto (with a warning when the module is
//     loaded).
// Without a selected tier, the float values of the bodies of TAB1 and
// LIST records are read field by field (the per-field form, as before
// the kernels existed); with a selected tier, a TAB1 body is converted by
// one kernel call per line (cpp_read_pairs_bulk) and a LIST body is
// decoded as a whole into a buffer first (the bulk form, see
// CppListBody). The choice is made once per record.

#define CPP_ROW_ACCEPT_D_EXPONENT 1u

typedef unsigned (*cpp_row_kernel_fn)(
  const char* line, unsigned want, unsigned flags, double* out
);


// number of calls of cpp_row_kernel_scalar, for tests showing that the
// row form is used (the scalar tier is the reference and the vehicle for
// testing the row form, it is not selected automatically)
inline unsigned long long& cpp_row_scalar_lines() {
  static unsigned long long count = 0;
  return count;
}

// the reference: cpp_fast_field_to_double field by field
inline unsigned cpp_row_kernel_scalar(
  const char* line, unsigned want, unsigned flags, double* out
) {
  cpp_row_scalar_lines()++;
  const bool accept_d_exponent = (flags & CPP_ROW_ACCEPT_D_EXPONENT) != 0;
  unsigned done = 0;
  for (int j = 0; j < 6; j++) {
    if (((want >> j) & 1u) != 0
        && cpp_fast_field_to_double(line + 11*j, accept_d_exponent, out[j])) {
      done |= 1u << j;
    }
  }
  return done;
}


#if (defined(__x86_64__) || defined(_M_X64)) && (defined(__GNUC__) || defined(__clang__))
#define CPP_ROW_X86_64_GNU 1
#endif
// MSVC itself on x64: not clang-cl (which defines _MSC_VER and __clang__
// and is handled as Clang above, with target attributes) and not ARM64EC
// (which defines _M_X64 as well, but compiles for ARM64)
#if defined(_MSC_VER) && ! defined(__clang__) && ! defined(__GNUC__) \
    && defined(_M_X64) && ! defined(_M_ARM64EC)
#define CPP_ROW_X86_64_MSVC 1
#endif

// The vector tiers (AVX2, AVX-512, NEON) are only built with compilers
// known to support everything they use (CPP_ROW_SIMD_COMPILER), so that an
// older compiler builds the module with the scalar tier only instead of
// failing to compile it (which in setup.py's optional mode would install
// the package without C++ modules). Defining CPP_ROW_NO_VECTOR_TIERS
// disables them as well (setup.py retries with it if a build fails in
// optional mode). The minimum versions are conservative:
// - GCC 8 (x86-64 and AArch64): the target attribute and option
//   avx512vbmi and the AVX-512 BW/VL/DQ intrinsics exist since GCC 5
//   (GCC 5 release notes), but the AVX-512 intrinsics and the inlining
//   of always_inline functions with target attributes were extended in
//   later releases; GCC 8.4 compiles all tiers (checked for x86-64 and
//   AArch64), older versions were not checked;
// - Clang 8 (LLVM release numbering; AVX-512 VBMI since Clang 3.9 by the
//   LLVM 3.9 release notes, the AArch64 NEON intrinsics of arm_neon.h
//   since Clang 3.5): Clang 8.0 compiles all tiers (checked); Apple Clang
//   numbers its releases differently (__apple_build_version__): Apple
//   Clang 11 (Xcode 11, 2019), based on about LLVM 8;
// - MSVC 19.30 (Visual Studio 2022) for the NEON tier on ARM64 (the ACLE
//   intrinsics of <arm_neon.h> and _BitScanForward; earlier versions
//   provide ARM64 NEON intrinsics as well, but were not checked) and for
//   the AVX2 and AVX-512 tiers on x64: Microsoft's documentation of /arch
//   (x64) says that "limited support for /arch:AVX512 was added in Visual
//   Studio 2017, and expanded in Visual Studio 2019"; the minimum is
//   conservatively the release after that (the kernels use AVX-512 F, BW,
//   VL, DQ and VBMI intrinsics); earlier versions were not checked;
// - not the classic Intel compiler (__INTEL_COMPILER, which defines
//   __GNUC__ but has its own support of target attributes).
#if ! defined(CPP_ROW_NO_VECTOR_TIERS) && ! defined(__INTEL_COMPILER)
#if defined(__clang__)
#if defined(__apple_build_version__)
#if __clang_major__ >= 11
#define CPP_ROW_SIMD_COMPILER 1
#endif
#elif __clang_major__ >= 8
#define CPP_ROW_SIMD_COMPILER 1
#endif
#elif defined(__GNUC__)
#if __GNUC__ >= 8
#define CPP_ROW_SIMD_COMPILER 1
#endif
#elif defined(_MSC_VER)
#if _MSC_VER >= 1930
#define CPP_ROW_SIMD_COMPILER 1
#endif
#endif
#endif

// AArch64, where NEON (Advanced SIMD) is mandatory: the NEON tier is built
// with GCC, Clang and MSVC for little-endian AArch64 (Linux, macOS,
// Windows); not for ARM64EC (x64 code conventions on Windows) and not for
// 32-bit ARM, whose NEON lacks the instructions the kernel uses.
#if (defined(__aarch64__) || defined(_M_ARM64) || defined(_M_ARM64EC))
#define CPP_ROW_AARCH64 1
#endif
#if defined(CPP_ROW_AARCH64) && ! defined(_M_ARM64EC) && ! defined(__ARM_BIG_ENDIAN) \
    && ! defined(CPP_ROW_X86_64_GNU) && defined(CPP_ROW_SIMD_COMPILER)
#define CPP_ROW_NEON 1
#endif

// The NEON tier compiled by GCC (not Clang) is built but not selected by
// auto, only if requested (ENDF_PARSERPY_CPP_BULK_BODIES=neon): on a
// Neoverse-N2 CPU (Linux, GCC 13.3, the flags of setup.py), parsing with
// it was 2-5% slower than with the scalar tier compiled by GCC, while the
// same code compiled by Clang 18 on the same CPU was 10-13% faster than
// its scalar tier (numpy mode). Apple Clang and MSVC builds take it.
#if defined(CPP_ROW_NEON) && defined(__GNUC__) && ! defined(__clang__)
#define CPP_ROW_NEON_NOT_AUTO 1
#endif

// Features of the CPU relevant for the tiers, from cpuid and xgetbv (the
// operating system must save the ymm and zmm registers). Only queried
// on x86-64 with CPP_ROW_X86_64_GNU (GCC and Clang including MinGW and
// clang-cl), where the instructions are issued directly, as
// __builtin_cpu_supports needs runtime support that not every toolchain
// links, and with CPP_ROW_X86_64_MSVC, with the intrinsics __cpuidex
// (<intrin.h>) and _xgetbv (<immintrin.h>); otherwise all false. `neon`
// is true on AArch64 (not queried: NEON is mandatory there).
struct cpp_cpu_features {
  bool detected;
  bool os_ymm;
  bool os_zmm;
  bool fma;
  bool avx2;
  bool avx512f;
  bool avx512dq;
  bool avx512bw;
  bool avx512vl;
  bool avx512vbmi;
  bool neon;
};

#ifdef CPP_ROW_X86_64_GNU
inline void cpp_cpuid(unsigned leaf, unsigned subleaf, unsigned regs[4]) {
  __asm__ volatile("cpuid"
    : "=a"(regs[0]), "=b"(regs[1]), "=c"(regs[2]), "=d"(regs[3])
    : "a"(leaf), "c"(subleaf));
}
#endif

#ifdef CPP_ROW_X86_64_MSVC
#include <intrin.h>
#include <immintrin.h>
inline void cpp_cpuid(unsigned leaf, unsigned subleaf, unsigned regs[4]) {
  int r[4];
  __cpuidex(r, static_cast<int>(leaf), static_cast<int>(subleaf));
  for (int i = 0; i < 4; i++) regs[i] = static_cast<unsigned>(r[i]);
}

// the low 32 bits of XCR0 (only called if cpuid reports OSXSAVE; out of
// line, so that the instruction cannot be moved before that check)
CPP_DECIMAL_NOINLINE inline unsigned cpp_xgetbv0() {
  return static_cast<unsigned>(_xgetbv(0));
}
#endif

inline cpp_cpu_features cpp_detect_cpu_features() {
  cpp_cpu_features f = {false, false, false, false, false, false, false, false, false, false, false};
#ifdef CPP_ROW_AARCH64
  f.neon = true;
#endif
#if defined(CPP_ROW_X86_64_GNU) || defined(CPP_ROW_X86_64_MSVC)
  unsigned r[4];
  cpp_cpuid(0, 0, r);
  const unsigned max_leaf = r[0];
  if (max_leaf < 1) return f;
  f.detected = true;
  cpp_cpuid(1, 0, r);
  f.fma = ((r[2] >> 12) & 1u) != 0;
  const bool osxsave = ((r[2] >> 27) & 1u) != 0;
  const bool avx = ((r[2] >> 28) & 1u) != 0;
  if (osxsave && avx) {
#ifdef CPP_ROW_X86_64_GNU
    unsigned xcr0, xcr0_hi;
    __asm__ volatile("xgetbv" : "=a"(xcr0), "=d"(xcr0_hi) : "c"(0));
    (void) xcr0_hi;
#else
    const unsigned xcr0 = cpp_xgetbv0();
#endif
    f.os_ymm = (xcr0 & 0x6u) == 0x6u;
    f.os_zmm = (xcr0 & 0xE6u) == 0xE6u;
  }
  if (max_leaf >= 7) {
    cpp_cpuid(7, 0, r);
    f.avx2 = ((r[1] >> 5) & 1u) != 0;
    f.avx512f = ((r[1] >> 16) & 1u) != 0;
    f.avx512dq = ((r[1] >> 17) & 1u) != 0;
    f.avx512bw = ((r[1] >> 30) & 1u) != 0;
    f.avx512vl = ((r[1] >> 31) & 1u) != 0;
    f.avx512vbmi = ((r[2] >> 1) & 1u) != 0;
  }
#endif
  return f;
}


inline bool cpp_row_cpu_any(const cpp_cpu_features&) {
  return true;
}

inline bool cpp_row_cpu_avx2(const cpp_cpu_features& f) {
  return f.os_ymm && f.avx2 && f.fma;
}

inline bool cpp_row_cpu_avx512(const cpp_cpu_features& f) {
  return cpp_row_cpu_avx2(f) && f.os_zmm && f.avx512f && f.avx512dq
    && f.avx512bw && f.avx512vl && f.avx512vbmi;
}

inline bool cpp_row_cpu_neon(const cpp_cpu_features& f) {
  return f.neon;
}


// The vector tiers (AVX2 and AVX-512), only built with CPP_ROW_VECTOR_TIERS:
// GCC and Clang on x86-64 (CPP_ROW_X86_64_GNU), and for clang-cl only if
// <immintrin.h> declares the intrinsics without the corresponding global
// compiler flags (older clang-cl versions declare them only with these
// flags; the two macros below are defined by the headers that do), and
// MSVC on x64 (CPP_ROW_X86_64_MSVC). The translation units are compiled
// for the baseline instruction set of the module; every function using
// these instructions is only executed if the CPU supports its tier
// (cpp_row_select). Such a function calls the scalar conversion only out
// of line (cpp_row_vector_fallback), so that this code is never compiled
// with the instruction set of a tier.
// - GCC and Clang: every function using these instructions carries a
//   target attribute (CPP_ROW_TARGET_AVX2, CPP_ROW_TARGET_AVX512), as the
//   compiler accepts the intrinsics of an instruction set only in
//   functions compiled for it; the parts of a kernel are always_inline
//   with the same attribute, and a function with a target attribute is
//   not inlined into a function without it.
// - MSVC accepts the intrinsics of every instruction set in every
//   function, without /arch: it emits the instruction of each intrinsic
//   and compiles all other code for the instruction set of /arch (SSE2
//   by default), so that no attribute is needed and the code around the
//   intrinsics (and every inline function shared with other translation
//   units) stays baseline code. The parts of a kernel are __forceinline;
//   the functions entered from outside a tier (the kernels and the LIST
//   loops of the tiers) are noinline (CPP_DECIMAL_NOINLINE,
//   CPP_ROW_VECTOR_ENTRY), so that their instructions stay behind the
//   call through the selected kernel and the comparison with it in
//   cpp_list_convert, and cannot be inlined into or scheduled before
//   these checks in a caller. (Compiling the tiers in translation units
//   of their own with /arch:AVX2 or /arch:AVX512 is not done: the inline
//   functions such units share with the others, e.g. those of the C++
//   library, would be compiled for that instruction set as well, and the
//   linker keeps one of the copies for the whole module.)
//
// The vector path of both kernels converts exactly the two layouts of
// cpp_fast_field_swar, " d.dddddd+d" and " d.ddddd+dd" (first character
// blank, '+' or '-', exponent sign '+' or '-'), with a decimal exponent
// k (of the significand as an integer) in -22..22: the significand m (an
// integer below 10^7, exact as a double) is multiplied by 10^k for k >= 0,
// which gives the correctly rounded product as the scalar code does; for
// k < 0 the quotient m / 10^-k is computed without a division as
// q0 = m * y, r = fma(-q0, b, m), q1 = fma(r, y, q0) with b = 10^-k and
// y = 10^k rounded, which equals the correctly rounded quotient computed
// by the scalar code (a division) for all m < 10^7 and -k = 1..22; the
// mode "exhaustive" of tests/cpp/float_kernel_equivalence.cpp checks every
// string of both layouts with every vector tier. The sign is applied
// last, so that "-0.000000+0" gives -0.0 as in the scalar code. Every other field (other layouts, exponents
// outside -22..22, among them those of cpp_decimal_to_double_negexp)
// is converted by cpp_fast_field_to_double, so that a kernel converts
// exactly the fields cpp_fast_field_to_double converts, to the same bits.
#if defined(CPP_ROW_X86_64_GNU) && defined(CPP_ROW_SIMD_COMPILER)
#include <immintrin.h>
#if ! defined(_MSC_VER) || defined(__GNUC__) \
    || (defined(_mm256_inserti128_si256) && defined(_mm512_cmple_epi64_mask))
#define CPP_ROW_VECTOR_TIERS 1
#endif
#elif defined(CPP_ROW_X86_64_MSVC) && defined(CPP_ROW_SIMD_COMPILER)
#include <immintrin.h>
#define CPP_ROW_VECTOR_TIERS 1
#endif

#if defined(CPP_ROW_VECTOR_TIERS) || defined(CPP_ROW_NEON)

// index of the lowest set bit of x != 0
inline int cpp_row_ctz(unsigned x) {
#if defined(__GNUC__) || defined(__clang__)
  return __builtin_ctz(x);
#elif defined(_MSC_VER)
  unsigned long j;
  _BitScanForward(&j, x);
  return static_cast<int>(j);
#else
  int j = 0;
  while (((x >> j) & 1u) == 0) j++;
  return j;
#endif
}

// The fields of `todo` converted by cpp_fast_field_to_double (the fields
// the vector path does not take); returns the mask of those converted.
CPP_DECIMAL_NOINLINE inline unsigned cpp_row_vector_fallback(
  const char* line, unsigned todo, bool accept_d_exponent, double* out
) {
  unsigned done = 0;
  while (todo != 0) {
    const int j = cpp_row_ctz(todo);
    todo &= todo - 1;
    if (cpp_fast_field_to_double(line + 11 * j, accept_d_exponent, out[j])) {
      done |= 1u << j;
    }
  }
  return done;
}

#endif

#ifdef CPP_ROW_VECTOR_TIERS

#ifdef CPP_ROW_X86_64_MSVC
#define CPP_ROW_TARGET_AVX2
#define CPP_ROW_TARGET_AVX512
// the parts of the kernels, inlined into the functions of their tier
#define CPP_ROW_INLINE_AVX2 __forceinline
#define CPP_ROW_INLINE_AVX512 __forceinline
// the LIST loops of the tiers
#define CPP_ROW_VECTOR_ENTRY CPP_DECIMAL_NOINLINE
#else
#define CPP_ROW_TARGET_AVX2 __attribute__((target("avx2,fma")))
#define CPP_ROW_TARGET_AVX512 \
  __attribute__((target("avx2,fma,avx512f,avx512bw,avx512vl,avx512dq,avx512vbmi")))
// the parts of the kernels, inlined into the functions of their tier
#define CPP_ROW_INLINE_AVX2 __attribute__((always_inline, target("avx2,fma"))) inline
#define CPP_ROW_INLINE_AVX512 __attribute__((always_inline, \
  target("avx2,fma,avx512f,avx512bw,avx512vl,avx512dq,avx512vbmi"))) inline
// the LIST loops of the tiers (not inlined into functions without the
// target attribute)
#define CPP_ROW_VECTOR_ENTRY
#endif

// tables of the vector kernels (constant-initialized, shared by the
// translation units of a module)
struct cpp_row_vector_tables {
  // AVX2: {10^q, 10^-q rounded} for q = 0..22, entry 23 neutral
  alignas(16) double pow2[24][2];
  // AVX-512: 10^q and 10^-q rounded for q = 0..22, entry 23 neutral
  alignas(64) double pow[24];
  alignas(64) double rpow[24];
  // AVX-512: the indices of the bytes of the line gathered into the eight
  // qwords (field j in qword j, qwords 6 and 7 repeat field 0): bytes 0-7
  // of the field, bytes 8-10, and the significand digits of the two
  // layouts (index 66: a byte '0')
  alignas(64) std::uint8_t idx1[64];
  alignas(64) std::uint8_t idx2[64];
  alignas(64) std::uint8_t idx3a[64];
  alignas(64) std::uint8_t idx3b[64];
};

inline const cpp_row_vector_tables& cpp_row_vector_tab() {
  static const cpp_row_vector_tables tab = {
    {
      {1e0, 1e-0}, {1e1, 1e-1}, {1e2, 1e-2}, {1e3, 1e-3}, {1e4, 1e-4}, {1e5, 1e-5},
      {1e6, 1e-6}, {1e7, 1e-7}, {1e8, 1e-8}, {1e9, 1e-9}, {1e10, 1e-10}, {1e11, 1e-11},
      {1e12, 1e-12}, {1e13, 1e-13}, {1e14, 1e-14}, {1e15, 1e-15}, {1e16, 1e-16},
      {1e17, 1e-17}, {1e18, 1e-18}, {1e19, 1e-19}, {1e20, 1e-20}, {1e21, 1e-21},
      {1e22, 1e-22}, {1.0, 1.0}
    },
    {
      1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11, 1e12, 1e13, 1e14, 1e15,
      1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22, 1.0
    },
    {
      1e-0, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10, 1e-11, 1e-12,
      1e-13, 1e-14, 1e-15, 1e-16, 1e-17, 1e-18, 1e-19, 1e-20, 1e-21, 1e-22, 1.0
    },
    {
      0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17, 18,
      22, 23, 24, 25, 26, 27, 28, 29, 33, 34, 35, 36, 37, 38, 39, 40,
      44, 45, 46, 47, 48, 49, 50, 51, 55, 56, 57, 58, 59, 60, 61, 62,
      0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6, 7
    },
    {
      8, 9, 10, 8, 8, 8, 8, 8, 19, 20, 21, 19, 19, 19, 19, 19,
      30, 31, 32, 30, 30, 30, 30, 30, 41, 42, 43, 41, 41, 41, 41, 41,
      52, 53, 54, 52, 52, 52, 52, 52, 63, 64, 65, 63, 63, 63, 63, 63,
      8, 9, 10, 8, 8, 8, 8, 8, 8, 9, 10, 8, 8, 8, 8, 8
    },
    {
      66, 1, 3, 4, 5, 6, 7, 8, 66, 12, 14, 15, 16, 17, 18, 19,
      66, 23, 25, 26, 27, 28, 29, 30, 66, 34, 36, 37, 38, 39, 40, 41,
      66, 45, 47, 48, 49, 50, 51, 52, 66, 56, 58, 59, 60, 61, 62, 63,
      66, 1, 3, 4, 5, 6, 7, 8, 66, 1, 3, 4, 5, 6, 7, 8
    },
    {
      66, 66, 1, 3, 4, 5, 6, 7, 66, 66, 12, 14, 15, 16, 17, 18,
      66, 66, 23, 25, 26, 27, 28, 29, 66, 66, 34, 36, 37, 38, 39, 40,
      66, 66, 45, 47, 48, 49, 50, 51, 66, 66, 56, 58, 59, 60, 61, 62,
      66, 66, 1, 3, 4, 5, 6, 7, 66, 66, 1, 3, 4, 5, 6, 7
    }
  };
  return tab;
}

// ---- AVX2: one ymm register holds two fields, each in a 128-bit lane
// (bytes 0..10 of the field; bytes 11..15 are ignored).

enum { CPP_ROW_C_D = 1, CPP_ROW_C_DOT = 2, CPP_ROW_C_S = 4, CPP_ROW_C_B = 8 };

CPP_ROW_INLINE_AVX2 __m256i cpp_row_avx2_load2(const char* p) {
  return _mm256_inserti128_si256(
    _mm256_castsi128_si256(_mm_loadu_si128(reinterpret_cast<const __m128i*>(p))),
    _mm_loadu_si128(reinterpret_cast<const __m128i*>(p + 11)), 1);
}

// Classification and digit reduction of two fields. Returns per lane the
// dwords [H, L, e, ld + 256*es]: significand = H*10^4 + L (layout B with
// an appended zero digit, i.e. ten times the significand), e the exponent
// digits, ld and es the first character and the exponent sign minus '0'
// (bit 2 set exactly for '-'). bad: movemask, a lane holds a field of one
// of the two layouts iff its 16 bits are zero.
CPP_ROW_INLINE_AVX2 __m256i cpp_row_avx2_prep(__m256i Y, unsigned& bad) {
  const __m256i lo_t = _mm256_setr_epi8(
    CPP_ROW_C_D | CPP_ROW_C_B, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D,
    CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, 0, CPP_ROW_C_S, 0,
    CPP_ROW_C_S, CPP_ROW_C_DOT, 0,
    CPP_ROW_C_D | CPP_ROW_C_B, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D,
    CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, 0, CPP_ROW_C_S, 0,
    CPP_ROW_C_S, CPP_ROW_C_DOT, 0);
  const __m256i hi_t = _mm256_setr_epi8(
    0, 0, CPP_ROW_C_DOT | CPP_ROW_C_S | CPP_ROW_C_B, CPP_ROW_C_D, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, CPP_ROW_C_DOT | CPP_ROW_C_S | CPP_ROW_C_B, CPP_ROW_C_D, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
  const __m256i nib = _mm256_set1_epi8(0x0F);
  const __m256i code = _mm256_and_si256(
    _mm256_shuffle_epi8(lo_t, _mm256_and_si256(Y, nib)),
    _mm256_shuffle_epi8(hi_t, _mm256_and_si256(_mm256_srli_epi16(Y, 4), nib)));
  // layout B iff byte 8 is a sign
  const __m256i isB = _mm256_cmpeq_epi8(
    _mm256_shuffle_epi8(code, _mm256_set1_epi8(8)), _mm256_set1_epi8(CPP_ROW_C_S));
#define CPP_ROW_PA CPP_ROW_C_S | CPP_ROW_C_B, CPP_ROW_C_D, CPP_ROW_C_DOT, CPP_ROW_C_D, \
  CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_S, CPP_ROW_C_D, \
  0, 0, 0, 0, 0
#define CPP_ROW_PB CPP_ROW_C_S | CPP_ROW_C_B, CPP_ROW_C_D, CPP_ROW_C_DOT, CPP_ROW_C_D, \
  CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_D, CPP_ROW_C_S, CPP_ROW_C_D, CPP_ROW_C_D, \
  0, 0, 0, 0, 0
  const __m256i patA = _mm256_setr_epi8(CPP_ROW_PA, CPP_ROW_PA);
  const __m256i patB = _mm256_setr_epi8(CPP_ROW_PB, CPP_ROW_PB);
#undef CPP_ROW_PA
#undef CPP_ROW_PB
  const __m256i dc = _mm256_setr_epi8(
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1);
  const __m256i pat = _mm256_blendv_epi8(patA, patB, isB);
  const __m256i ok = _mm256_or_si256(_mm256_and_si256(code, pat), dc);
  bad = static_cast<unsigned>(_mm256_movemask_epi8(_mm256_cmpeq_epi8(ok, _mm256_setzero_si256())));
  // digit gathering: A [Z,1,3,4,5,6,7,8, Z,10, Z,Z, 0,Z, 9,Z]
  //                  B [Z,1,3,4,5,6,7,Z, 9,10, Z,Z, 0,Z, 8,Z]
  const char Z = static_cast<char>(0x80);
#define CPP_ROW_CA Z, 1, 3, 4, 5, 6, 7, 8, Z, 10, Z, Z, 0, Z, 9, Z
#define CPP_ROW_CB Z, 1, 3, 4, 5, 6, 7, Z, 9, 10, Z, Z, 0, Z, 8, Z
  const __m256i ctrlA = _mm256_setr_epi8(CPP_ROW_CA, CPP_ROW_CA);
  const __m256i ctrlB = _mm256_setr_epi8(CPP_ROW_CB, CPP_ROW_CB);
#undef CPP_ROW_CA
#undef CPP_ROW_CB
  const __m256i ctrl = _mm256_blendv_epi8(ctrlA, ctrlB, isB);
  const __m256i dg = _mm256_sub_epi8(Y, _mm256_set1_epi8('0'));
  const __m256i sh = _mm256_shuffle_epi8(dg, ctrl);
  const __m256i W1 = _mm256_setr_epi8(
    10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 0, 0, 1, 0, 1, 0,
    10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 0, 0, 1, 0, 1, 0);
  const __m256i W2 = _mm256_setr_epi16(100, 1, 100, 1, 1, 0, 1, 256,
                                       100, 1, 100, 1, 1, 0, 1, 256);
  return _mm256_madd_epi16(_mm256_maddubs_epi16(sh, W1), W2);
}

// Floating-point stage for four fields: Pa holds the fields (a0, a1), Pb
// (b0, b1). Returns the values in the order (a0, a1, b0, b1); rmask: bit
// set where the exponent is in range, in the order (a0, b0, a1, b1).
CPP_ROW_INLINE_AVX2 __m256d cpp_row_avx2_fp4(__m256i Pa, __m256i Pb, unsigned& rmask) {
  const cpp_row_vector_tables& T = cpp_row_vector_tab();
  __m256i u = _mm256_unpacklo_epi32(Pa, Pb);   // lane: Ha Hb La Lb
  __m256i v = _mm256_unpackhi_epi32(Pa, Pb);   // lane: Ea Eb Da Db
  u = _mm256_permute4x64_epi64(u, 0xD8);       // Ha0 Hb0 Ha1 Hb1 | La0 Lb0 La1 Lb1
  v = _mm256_permute4x64_epi64(v, 0xD8);
  const __m128i H = _mm256_castsi256_si128(u), L = _mm256_extracti128_si256(u, 1);
  const __m128i E = _mm256_castsi256_si128(v), D = _mm256_extracti128_si256(v, 1);
  const __m256d m = _mm256_fmadd_pd(_mm256_cvtepi32_pd(H), _mm256_set1_pd(1e4), _mm256_cvtepi32_pd(L));
  const __m128i n = _mm_srai_epi32(_mm_slli_epi32(D, 21), 31);   // exponent sign
  const __m128i k = _mm_sub_epi32(_mm_sub_epi32(_mm_xor_si128(E, n), n), _mm_set1_epi32(6));
  // range of the decimal exponent of the (for B: scaled) significand
  const __m128i rok = _mm_andnot_si128(_mm_cmpgt_epi32(k, _mm_set1_epi32(21)),
                                       _mm_cmpgt_epi32(k, _mm_set1_epi32(-23)));
  rmask = static_cast<unsigned>(_mm_movemask_ps(_mm_castsi128_ps(rok)));
  const __m128i qi = _mm_min_epu32(_mm_abs_epi32(k), _mm_set1_epi32(23));
  alignas(16) int idx[4];
  _mm_store_si128(reinterpret_cast<__m128i*>(idx), qi);
  const __m256d X02 = _mm256_insertf128_pd(
    _mm256_castpd128_pd256(_mm_load_pd(T.pow2[idx[0]])), _mm_load_pd(T.pow2[idx[2]]), 1);
  const __m256d X13 = _mm256_insertf128_pd(
    _mm256_castpd128_pd256(_mm_load_pd(T.pow2[idx[1]])), _mm_load_pd(T.pow2[idx[3]]), 1);
  const __m256d B = _mm256_unpacklo_pd(X02, X13);
  const __m256d Yr = _mm256_unpackhi_pd(X02, X13);
  const __m256d rmul = _mm256_mul_pd(m, B);
  const __m256d q0 = _mm256_mul_pd(m, Yr);
  const __m256d r = _mm256_fnmadd_pd(q0, B, m);
  const __m256d q1 = _mm256_fmadd_pd(r, Yr, q0);
  __m256d res = _mm256_blendv_pd(rmul, q1, _mm256_castsi256_pd(_mm256_cvtepi32_epi64(k)));
  const __m256i sg = _mm256_and_si256(_mm256_cvtepi32_epi64(_mm_slli_epi32(D, 29)),
                                      _mm256_set1_epi64x(static_cast<long long>(0x8000000000000000ULL)));
  res = _mm256_xor_pd(res, _mm256_castsi256_pd(sg));
  return _mm256_permute4x64_pd(res, 0xD8);
}

// Floating-point stage for the two fields (a0, a1) of Pa, with 128-bit
// vectors. rmask: bits 0 and 1.
CPP_ROW_INLINE_AVX2 __m128d cpp_row_avx2_fp2(__m256i Pa, unsigned& rmask) {
  const cpp_row_vector_tables& T = cpp_row_vector_tab();
  const __m128i lo = _mm256_castsi256_si128(Pa), hi = _mm256_extracti128_si256(Pa, 1);
  const __m128i u = _mm_unpacklo_epi32(lo, hi);   // H0 H1 L0 L1
  const __m128i v = _mm_unpackhi_epi32(lo, hi);   // E0 E1 D0 D1
  const __m128d m = _mm_fmadd_pd(_mm_cvtepi32_pd(u), _mm_set1_pd(1e4), _mm_cvtepi32_pd(_mm_unpackhi_epi64(u, u)));
  const __m128i D = _mm_unpackhi_epi64(v, v);
  const __m128i n = _mm_srai_epi32(_mm_slli_epi32(D, 21), 31);
  const __m128i k = _mm_sub_epi32(_mm_sub_epi32(_mm_xor_si128(v, n), n), _mm_set1_epi32(6));
  const __m128i rok = _mm_andnot_si128(_mm_cmpgt_epi32(k, _mm_set1_epi32(21)),
                                       _mm_cmpgt_epi32(k, _mm_set1_epi32(-23)));
  rmask = static_cast<unsigned>(_mm_movemask_ps(_mm_castsi128_ps(rok))) & 3u;
  const __m128i qi = _mm_min_epu32(_mm_abs_epi32(k), _mm_set1_epi32(23));
  const __m128d X0 = _mm_load_pd(T.pow2[_mm_cvtsi128_si32(qi)]);
  const __m128d X1 = _mm_load_pd(T.pow2[_mm_extract_epi32(qi, 1)]);
  const __m128d B = _mm_unpacklo_pd(X0, X1);
  const __m128d Yr = _mm_unpackhi_pd(X0, X1);
  const __m128d rmul = _mm_mul_pd(m, B);
  const __m128d kn = _mm_castsi128_pd(_mm_cvtepi32_epi64(k));
  const __m128d q0 = _mm_mul_pd(m, Yr);
  const __m128d r = _mm_fnmadd_pd(q0, B, m);
  const __m128d res = _mm_blendv_pd(rmul, _mm_fmadd_pd(r, Yr, q0), kn);
  const __m128i sg = _mm_and_si128(_mm_cvtepi32_epi64(_mm_slli_epi32(D, 29)),
                                   _mm_set1_epi64x(static_cast<long long>(0x8000000000000000ULL)));
  return _mm_xor_pd(res, _mm_castsi128_pd(sg));
}

// The vector path of the AVX2 kernel: stores six values in out[0..5] and
// returns the mask of the fields it has converted (the other values are
// undefined).
CPP_ROW_INLINE_AVX2 unsigned cpp_row_avx2_fast(const char* s, double* out) {
  unsigned b0, b1, b2, r01, r2;
  const __m256i P0 = cpp_row_avx2_prep(cpp_row_avx2_load2(s), b0);
  const __m256i P1 = cpp_row_avx2_prep(cpp_row_avx2_load2(s + 22), b1);
  const __m256i P2 = cpp_row_avx2_prep(cpp_row_avx2_load2(s + 44), b2);
  _mm256_storeu_pd(out, cpp_row_avx2_fp4(P0, P1, r01));
  _mm_storeu_pd(out + 4, cpp_row_avx2_fp2(P2, r2));
  unsigned fast = (r01 & 9u) | ((r01 >> 1) & 2u) | ((r01 << 1) & 4u) | (r2 << 4);
  if ((b0 | b1 | b2) != 0) {
    const unsigned valid = static_cast<unsigned>((b0 & 0xFFFFu) == 0)
      | (static_cast<unsigned>((b0 >> 16) == 0) << 1)
      | (static_cast<unsigned>((b1 & 0xFFFFu) == 0) << 2)
      | (static_cast<unsigned>((b1 >> 16) == 0) << 3)
      | (static_cast<unsigned>((b2 & 0xFFFFu) == 0) << 4)
      | (static_cast<unsigned>((b2 >> 16) == 0) << 5);
    fast &= valid;
  }
  return fast;
}

// ---- AVX-512: one zmm register, field j in qword j (j = 0..5; qwords 6
// and 7 repeat field 0); the bytes are gathered from the line with
// vpermi2b (VBMI).

enum {
  CPP_ROW_C5_D = 1, CPP_ROW_C5_DOT = 2, CPP_ROW_C5_P = 4, CPP_ROW_C5_M = 8, CPP_ROW_C5_B = 16
};

CPP_ROW_INLINE_AVX512 __m512i cpp_row_avx512_code(__m512i G) {
  const __m512i lo_t = _mm512_broadcast_i32x4(_mm_setr_epi8(
    CPP_ROW_C5_D | CPP_ROW_C5_B, CPP_ROW_C5_D, CPP_ROW_C5_D, CPP_ROW_C5_D, CPP_ROW_C5_D,
    CPP_ROW_C5_D, CPP_ROW_C5_D, CPP_ROW_C5_D, CPP_ROW_C5_D, CPP_ROW_C5_D, 0, CPP_ROW_C5_P, 0,
    CPP_ROW_C5_M, CPP_ROW_C5_DOT, 0));
  const __m512i hi_t = _mm512_broadcast_i32x4(_mm_setr_epi8(
    0, 0, CPP_ROW_C5_DOT | CPP_ROW_C5_P | CPP_ROW_C5_M | CPP_ROW_C5_B, CPP_ROW_C5_D,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0));
  const __m512i nib = _mm512_set1_epi8(0x0F);
  return _mm512_and_si512(_mm512_shuffle_epi8(lo_t, _mm512_and_si512(G, nib)),
                          _mm512_shuffle_epi8(hi_t, _mm512_and_si512(_mm512_srli_epi16(G, 4), nib)));
}

// The vector path of the AVX-512 kernel, as cpp_row_avx2_fast. The
// patterns per qword: the classes of bytes 0-7 (sign or blank, digit,
// '.', digits) and of bytes 8-10 for the layouts A (digit, exponent sign,
// digit) and B (exponent sign, digits), and the weights of the exponent
// digits for A and B.
CPP_ROW_INLINE_AVX512 unsigned cpp_row_avx512_fast(const char* s, double* out) {
  const cpp_row_vector_tables& T = cpp_row_vector_tab();
  const __m512i pat1 = _mm512_set1_epi64(0x010101010102011CLL);
  const __m512i pat2a = _mm512_set1_epi64(static_cast<long long>(0xFFFFFFFFFF010C01ULL));
  const __m512i pat2b = _mm512_set1_epi64(static_cast<long long>(0xFFFFFFFFFF01010CULL));
  const __m512i wea = _mm512_set1_epi64(0x0000000000010000LL);
  const __m512i web = _mm512_set1_epi64(0x0000000000010A00LL);
  const __m512i L0 = _mm512_loadu_si512(s);
  const __m512i L1 = _mm512_mask_loadu_epi8(_mm512_set1_epi8('0'), 0x3, s + 64);
  const __m512i G1 = _mm512_permutex2var_epi8(L0, _mm512_load_si512(T.idx1), L1);
  const __m512i G2 = _mm512_permutex2var_epi8(L0, _mm512_load_si512(T.idx2), L1);
  const __m512i C1 = cpp_row_avx512_code(G1), C2 = cpp_row_avx512_code(G2);
  const __mmask8 kB = _mm512_test_epi64_mask(C2, _mm512_set1_epi64(CPP_ROW_C5_P | CPP_ROW_C5_M));
  const __m512i pat2 = _mm512_mask_blend_epi64(kB, pat2a, pat2b);
  const __mmask64 t = _mm512_test_epi8_mask(C1, pat1) & _mm512_test_epi8_mask(C2, pat2);
  const __mmask8 kval = _mm512_cmpeq_epi64_mask(_mm512_movm_epi8(t), _mm512_set1_epi64(-1));
  const __mmask8 keneg = _mm512_test_epi64_mask(
    C2, _mm512_set1_epi64(CPP_ROW_C5_M | (CPP_ROW_C5_M << 8)));
  const __mmask8 klneg = _mm512_test_epi64_mask(C1, _mm512_set1_epi64(CPP_ROW_C5_M));
  const __m512i G3 = _mm512_permutex2var_epi8(
    L0, _mm512_mask_blend_epi64(kB, _mm512_load_si512(T.idx3a), _mm512_load_si512(T.idx3b)), L1);
  const __m512i zero = _mm512_setzero_si512();
  const __m512i x = _mm512_madd_epi16(
    _mm512_maddubs_epi16(_mm512_sub_epi8(G3, _mm512_set1_epi8('0')), _mm512_set1_epi16(0x010A)),
    _mm512_set1_epi32(0x00010064));
  const __m512i mant = _mm512_add_epi64(
    _mm512_mul_epu32(x, _mm512_set1_epi64(10000)), _mm512_srli_epi64(x, 32));
  const __m512d m = _mm512_cvtepi64_pd(mant);
  const __m512i ex = _mm512_madd_epi16(
    _mm512_maddubs_epi16(_mm512_sub_epi8(G2, _mm512_set1_epi8('0')),
                         _mm512_mask_blend_epi64(kB, wea, web)),
    _mm512_set1_epi64(0x0000000000010001LL));
  __m512i k = _mm512_mask_sub_epi64(ex, keneg, zero, ex);
  k = _mm512_sub_epi64(k, _mm512_set1_epi64(6));
  k = _mm512_mask_add_epi64(k, kB, k, _mm512_set1_epi64(1));
  const __mmask8 kr = _mm512_mask_cmple_epi64_mask(
    _mm512_cmpge_epi64_mask(k, _mm512_set1_epi64(-22)), k, _mm512_set1_epi64(22));
  const __mmask8 kneg = _mm512_movepi64_mask(k);
  const __m512i q = _mm512_abs_epi64(k);
  const __mmask8 k16 = _mm512_test_epi64_mask(q, _mm512_set1_epi64(16));
  const __m512d B = _mm512_mask_permutexvar_pd(
    _mm512_permutex2var_pd(_mm512_load_pd(T.pow), q, _mm512_load_pd(T.pow + 8)),
    k16, q, _mm512_load_pd(T.pow + 16));
  const __m512d Yr = _mm512_mask_permutexvar_pd(
    _mm512_permutex2var_pd(_mm512_load_pd(T.rpow), q, _mm512_load_pd(T.rpow + 8)),
    k16, q, _mm512_load_pd(T.rpow + 16));
  const __m512d q0 = _mm512_mul_pd(m, Yr);
  const __m512d r = _mm512_fnmadd_pd(q0, B, m);
  const __m512d q1 = _mm512_fmadd_pd(r, Yr, q0);
  __m512d res = _mm512_mask_mul_pd(q1, static_cast<__mmask8>(~kneg), m, B);
  res = _mm512_mask_xor_pd(res, klneg, res, _mm512_set1_pd(-0.0));
  _mm512_mask_storeu_pd(out, 0x3F, res);
  return static_cast<unsigned>(kval & kr) & 0x3Fu;
}

// the row kernels of the two tiers (called through cpp_row_kernel_fn by
// the line-by-line readers)
CPP_ROW_TARGET_AVX2 CPP_DECIMAL_NOINLINE inline unsigned cpp_row_kernel_avx2(
  const char* line, unsigned want, unsigned flags, double* out
) {
  const unsigned fast = cpp_row_avx2_fast(line, out) & want;
  if (fast == want) return fast;
  return fast | cpp_row_vector_fallback(
    line, want & ~fast, (flags & CPP_ROW_ACCEPT_D_EXPONENT) != 0, out);
}

CPP_ROW_TARGET_AVX512 CPP_DECIMAL_NOINLINE inline unsigned cpp_row_kernel_avx512(
  const char* line, unsigned want, unsigned flags, double* out
) {
  const unsigned fast = cpp_row_avx512_fast(line, out) & want;
  if (fast == want) return fast;
  return fast | cpp_row_vector_fallback(
    line, want & ~fast, (flags & CPP_ROW_ACCEPT_D_EXPONENT) != 0, out);
}

#endif  // CPP_ROW_VECTOR_TIERS


// The NEON tier (AArch64), only built with CPP_ROW_NEON. NEON is part of
// the baseline instruction set of AArch64, so that the module and this
// tier are compiled for the same instructions and the tier is always
// supported.
//
// The vector path converts the same two layouts as the x86 tiers (see
// above) and takes a field only if it has one of them: each field is
// loaded into its own register (bytes 0..10 of the field, bytes 11..15
// ignored) and its bytes are classified with a nibble lookup (vqtbl1q);
// a field is taken if all 11 bytes have the classes of layout A
// (" d.dddddd+d") or of layout B (" d.ddddd+dd"), and if its decimal
// exponent is in range (see below). The arithmetic does not depend on the
// layout:
// - significand: the digits of bytes 1, 3..7 and of byte 8 if it is a
//   digit (layout A), else 0 (layout B), i.e. m = the significand for A
//   and ten times the significand for B, an integer below 10^7 computed
//   exactly with integer operations and converted exactly to a double;
// - exponent: e = (10 * byte 9 if it is a digit) + byte 10, negative if
//   byte 8 or byte 9 is '-' (only one of them is a sign), and
//   k = +-e - 6: the decimal exponent of m (for B one less than that of
//   the significand, so that m * 10^k is the same number). The field is
//   taken if k is in -22..21: for A, k is in -15..3; for B this is the
//   range -21..22 of the exponent of the significand, of which the
//   scalar code converts -22..22, so that the rare B fields with exponent
//   -22 go to the fallback (as in the AVX2 tier);
// - value: for k >= 0, m * 10^k, one IEEE multiplication with the exact
//   power of ten as in the scalar code (for B, the exact real number
//   (10 m') * 10^(k'-1) of the scalar code's m' * 10^k', hence the same
//   rounding). For k < 0, the quotient m / 10^-k as in the x86 tiers,
//   without a division: q0 = m * y, r = fma(-q0, b, m), q1 = fma(r, y,
//   q0) with b = 10^-k and y = 10^k rounded (vfmsq_f64, vfmaq_f64: fused,
//   one rounding, as the FMA instructions of the x86 tiers, so the same
//   bits), which equals the correctly rounded quotient that the scalar
//   code computes by division for all m < 10^7 and -k = 1..22. Both cases
//   are one sequence with three numbers per k from a table, {y1, b, y2}:
//   {10^k, 0, 0} for k >= 0 (then q0 = m * 10^k rounded, r = m and
//   q1 = q0 + r * 0 = q0 exactly) and {y, b, y} for k < 0. The table
//   also holds the sign (+0.0 or -0.0 per entry, the index includes the
//   first character), applied last by XOR, so that "-0.000000+0" gives
//   -0.0 as in the scalar code.
// No other floating-point operation is involved, and the multiplication
// q0 = m * y1 cannot be contracted with another operation (its result is
// a factor of the fused multiply-subtract), so -ffp-contract does not
// change the result. The mode "exhaustive" of
// tests/cpp/float_kernel_equivalence.cpp checks every string of both
// layouts with this tier as with the x86 tiers.
#ifdef CPP_ROW_NEON

#include <arm_neon.h>

#if defined(_MSC_VER) && ! defined(__clang__)
#define CPP_ROW_INLINE_NEON __forceinline
#else
#define CPP_ROW_INLINE_NEON __attribute__((always_inline)) inline
#endif

// k = -22..21, as {y1, b, y2, sign} (see above)
#define CPP_ROW_NEON_NEG(y, b, s) {y, b, y, s}
#define CPP_ROW_NEON_POS(p, s) {p, 0.0, 0.0, s}
#define CPP_ROW_NEON_POW(s) \
  CPP_ROW_NEON_NEG(1e-22, 1e22, s), CPP_ROW_NEON_NEG(1e-21, 1e21, s), \
  CPP_ROW_NEON_NEG(1e-20, 1e20, s), CPP_ROW_NEON_NEG(1e-19, 1e19, s), \
  CPP_ROW_NEON_NEG(1e-18, 1e18, s), CPP_ROW_NEON_NEG(1e-17, 1e17, s), \
  CPP_ROW_NEON_NEG(1e-16, 1e16, s), CPP_ROW_NEON_NEG(1e-15, 1e15, s), \
  CPP_ROW_NEON_NEG(1e-14, 1e14, s), CPP_ROW_NEON_NEG(1e-13, 1e13, s), \
  CPP_ROW_NEON_NEG(1e-12, 1e12, s), CPP_ROW_NEON_NEG(1e-11, 1e11, s), \
  CPP_ROW_NEON_NEG(1e-10, 1e10, s), CPP_ROW_NEON_NEG(1e-9, 1e9, s), \
  CPP_ROW_NEON_NEG(1e-8, 1e8, s), CPP_ROW_NEON_NEG(1e-7, 1e7, s), \
  CPP_ROW_NEON_NEG(1e-6, 1e6, s), CPP_ROW_NEON_NEG(1e-5, 1e5, s), \
  CPP_ROW_NEON_NEG(1e-4, 1e4, s), CPP_ROW_NEON_NEG(1e-3, 1e3, s), \
  CPP_ROW_NEON_NEG(1e-2, 1e2, s), CPP_ROW_NEON_NEG(1e-1, 1e1, s), \
  CPP_ROW_NEON_POS(1e0, s), CPP_ROW_NEON_POS(1e1, s), CPP_ROW_NEON_POS(1e2, s), \
  CPP_ROW_NEON_POS(1e3, s), CPP_ROW_NEON_POS(1e4, s), CPP_ROW_NEON_POS(1e5, s), \
  CPP_ROW_NEON_POS(1e6, s), CPP_ROW_NEON_POS(1e7, s), CPP_ROW_NEON_POS(1e8, s), \
  CPP_ROW_NEON_POS(1e9, s), CPP_ROW_NEON_POS(1e10, s), CPP_ROW_NEON_POS(1e11, s), \
  CPP_ROW_NEON_POS(1e12, s), CPP_ROW_NEON_POS(1e13, s), CPP_ROW_NEON_POS(1e14, s), \
  CPP_ROW_NEON_POS(1e15, s), CPP_ROW_NEON_POS(1e16, s), CPP_ROW_NEON_POS(1e17, s), \
  CPP_ROW_NEON_POS(1e18, s), CPP_ROW_NEON_POS(1e19, s), CPP_ROW_NEON_POS(1e20, s), \
  CPP_ROW_NEON_POS(1e21, s)

// classes of the bytes (bit 0x80 is set in every code, so that the
// patterns accept any byte at the positions 11..15 of a register)
enum {
  CPP_ROW_N_D = 1, CPP_ROW_N_DOT = 2, CPP_ROW_N_S = 4, CPP_ROW_N_B = 8, CPP_ROW_N_ANY = 0x80
};

// tables of the NEON kernel (constant-initialized, shared by the
// translation units of a module). The table object is not declared const,
// so that the compiler loads the vectors from it instead of folding them
// into constants: GCC at -O1 (the optimization level of the module
// builds) turns each use of a folded vector into a load from the
// constant pool with its own address computation, inside the loop of
// cpp_list_convert_neon (about 35 instructions per line). The kernel
// never writes to the table.
struct cpp_row_neon_tables {
  // index 44 * (first character is '-') + k + 22
  alignas(16) double pow[88][4];
  // class of a byte: lo[byte & 15] & hi[byte >> 4]
  alignas(16) std::uint8_t lo[16];
  alignas(16) std::uint8_t hi[16];
  // the classes of the bytes 0..10 of the layouts A and B
  alignas(16) std::uint8_t pat_a[16];
  alignas(16) std::uint8_t pat_b[16];
  // significand digits of two fields, one field per 64-bit lane, most
  // significant first: 0, bytes 1, 3..8 (the first field in lane 0, the
  // second in lane 1)
  alignas(16) std::uint8_t idx_m0[16];
  alignas(16) std::uint8_t idx_m1[16];
  // bytes 9 and 10 (exponent) and bytes 8 and 0 (signs) of the six
  // fields, two bytes per field, from the registers loaded at the bytes 8,
  // 30 and 52 of the line (and at byte 0 for byte 0 of field 0), see
  // cpp_row_neon_fast
  alignas(16) std::uint8_t idx_e[3][16];
  alignas(16) std::uint8_t idx_s[4][16];
  // the bit of a field in the mask of the converted fields (for the
  // layouts A and B of each field, see cpp_row_neon_fast)
  alignas(16) std::uint8_t bit8[16];
  alignas(16) std::uint16_t bit16[8];
  // the multipliers that combine digits into pairs, four and eight
  // digits (cpp_row_neon_mant; mul8 also for the exponents), here
  // rather than as vector literals for the same reason
  alignas(16) std::uint8_t mul8[16];
  alignas(16) std::uint16_t mul16[8];
  alignas(16) std::uint32_t mul32[4];
};

inline const cpp_row_neon_tables& cpp_row_neon_tab() {
  static cpp_row_neon_tables tab = {
    {CPP_ROW_NEON_POW(0.0), CPP_ROW_NEON_POW(-0.0)},
    {
      CPP_ROW_N_ANY | CPP_ROW_N_D | CPP_ROW_N_B, CPP_ROW_N_ANY | CPP_ROW_N_D,
      CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY | CPP_ROW_N_D,
      CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY | CPP_ROW_N_D,
      CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY | CPP_ROW_N_D, CPP_ROW_N_ANY,
      CPP_ROW_N_ANY | CPP_ROW_N_S, CPP_ROW_N_ANY, CPP_ROW_N_ANY | CPP_ROW_N_S,
      CPP_ROW_N_ANY | CPP_ROW_N_DOT, CPP_ROW_N_ANY
    },
    {
      CPP_ROW_N_ANY, CPP_ROW_N_ANY,
      CPP_ROW_N_ANY | CPP_ROW_N_DOT | CPP_ROW_N_S | CPP_ROW_N_B, CPP_ROW_N_ANY | CPP_ROW_N_D,
      CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY,
      CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY,
      CPP_ROW_N_ANY, CPP_ROW_N_ANY
    },
    {
      CPP_ROW_N_S | CPP_ROW_N_B, CPP_ROW_N_D, CPP_ROW_N_DOT, CPP_ROW_N_D, CPP_ROW_N_D,
      CPP_ROW_N_D, CPP_ROW_N_D, CPP_ROW_N_D, CPP_ROW_N_D, CPP_ROW_N_S, CPP_ROW_N_D,
      CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY
    },
    {
      CPP_ROW_N_S | CPP_ROW_N_B, CPP_ROW_N_D, CPP_ROW_N_DOT, CPP_ROW_N_D, CPP_ROW_N_D,
      CPP_ROW_N_D, CPP_ROW_N_D, CPP_ROW_N_D, CPP_ROW_N_S, CPP_ROW_N_D, CPP_ROW_N_D,
      CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY, CPP_ROW_N_ANY
    },
    {0xFF, 1, 3, 4, 5, 6, 7, 8, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
    {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 1, 3, 4, 5, 6, 7, 8},
    {
      {1, 2, 12, 13, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
      {0xFF, 0xFF, 0xFF, 0xFF, 1, 2, 12, 13, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
      {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 1, 2, 12, 13, 0xFF, 0xFF, 0xFF, 0xFF}
    },
    {
      {0, 0xFF, 11, 3, 0xFF, 14, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
      {0xFF, 0xFF, 0xFF, 0xFF, 0, 0xFF, 11, 3, 0xFF, 14, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
      {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0xFF, 11, 3, 0xFF, 0xFF, 0xFF, 0xFF},
      {0xFF, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}
    },
    {1, 2, 4, 8, 16, 32, 1, 2, 4, 8, 16, 32, 0, 0, 0, 0},
    {1, 2, 4, 8, 16, 32, 0, 0},
    {10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1},
    {100, 1, 100, 1, 100, 1, 100, 1},
    {10000, 1, 10000, 1}
  };
  return tab;
}

#undef CPP_ROW_NEON_NEG
#undef CPP_ROW_NEON_POS
#undef CPP_ROW_NEON_POW

// the classes of the bytes of field f compared with the patterns of the
// two layouts: 0xFF where a byte has the class of the layout
CPP_ROW_INLINE_NEON void cpp_row_neon_class(
  uint8x16_t f, uint8x16_t lo, uint8x16_t hi, uint8x16_t pat_a, uint8x16_t pat_b,
  uint8x16_t& ta, uint8x16_t& tb
) {
  const uint8x16_t code = vandq_u8(vqtbl1q_u8(lo, vandq_u8(f, vdupq_n_u8(0x0F))),
                                   vqtbl1q_u8(hi, vshrq_n_u8(f, 4)));
  ta = vtstq_u8(code, pat_a);
  tb = vtstq_u8(code, pat_b);
}

// the digits of fa and fb gathered by i0 and i1 (see idx_m0, idx_m1) as
// two integers, converted to doubles (c8, c16, c32: mul8, mul16, mul32)
CPP_ROW_INLINE_NEON float64x2_t cpp_row_neon_mant(
  uint8x16_t fa, uint8x16_t fb, uint8x16_t i0, uint8x16_t i1,
  uint8x16_t c8, uint16x8_t c16, uint32x4_t c32
) {
  uint8x16_t g = vsubq_u8(vqtbx1q_u8(vqtbl1q_u8(fa, i0), fb, i1), vdupq_n_u8('0'));
  // bytes that are not digits (byte 8 of layout B, the lane start) as 0
  g = vandq_u8(g, vcltq_u8(g, vdupq_n_u8(10)));
  // pairs of digits, then four digits, then eight
  const uint16x8_t d2 = vpaddlq_u8(vmulq_u8(g, c8));
  const uint32x4_t d4 = vpaddlq_u16(vmulq_u16(d2, c16));
  const uint64x2_t d8 = vpaddlq_u32(vmulq_u32(d4, c32));
  return vcvtq_f64_u64(d8);
}

// the floating-point stage of two fields with significands m and the
// table entries pa, pb (see above)
CPP_ROW_INLINE_NEON float64x2_t cpp_row_neon_fp(float64x2_t m, const double* pa, const double* pb) {
  const float64x2_t a0 = vld1q_f64(pa), a1 = vld1q_f64(pa + 2);
  const float64x2_t b0 = vld1q_f64(pb), b1 = vld1q_f64(pb + 2);
  const float64x2_t y1 = vzip1q_f64(a0, b0);
  const float64x2_t b = vzip2q_f64(a0, b0);
  const float64x2_t y2 = vzip1q_f64(a1, b1);
  const uint64x2_t sg = vreinterpretq_u64_f64(vzip2q_f64(a1, b1));
  const float64x2_t q0 = vmulq_f64(m, y1);
  const float64x2_t r = vfmsq_f64(m, q0, b);
  const float64x2_t q1 = vfmaq_f64(q0, r, y2);
  return vreinterpretq_f64_u64(veorq_u64(vreinterpretq_u64_f64(q1), sg));
}

// The vector path of the NEON kernel: stores six values in out[0..5] and
// returns the mask of the fields it has converted (the other values are
// undefined). Reads bytes 0..70 of the line. All table lookups are on
// one register (vqtbl1q_u8, vqtbx1q_u8): GCC passes the register tuples
// of the lookups on two or four registers through the stack at -O1, the
// optimization level of the module builds.
CPP_ROW_INLINE_NEON unsigned cpp_row_neon_fast(const char* s, double* out) {
  const cpp_row_neon_tables& T = cpp_row_neon_tab();
  const std::uint8_t* u = reinterpret_cast<const std::uint8_t*>(s);
  const uint8x16_t f0 = vld1q_u8(u), f1 = vld1q_u8(u + 11), f2 = vld1q_u8(u + 22);
  const uint8x16_t f3 = vld1q_u8(u + 33), f4 = vld1q_u8(u + 44), f5 = vld1q_u8(u + 55);
  // the layouts
  const uint8x16_t lo = vld1q_u8(T.lo), hi = vld1q_u8(T.hi);
  const uint8x16_t pat_a = vld1q_u8(T.pat_a), pat_b = vld1q_u8(T.pat_b);
  // the multipliers, loaded once (the stores to out may alias the table)
  const uint8x16_t c8 = vld1q_u8(T.mul8);
  const uint16x8_t c16 = vld1q_u16(T.mul16);
  const uint32x4_t c32 = vld1q_u32(T.mul32);
  uint8x16_t a0, a1, a2, a3, a4, a5, b0, b1, b2, b3, b4, b5;
  cpp_row_neon_class(f0, lo, hi, pat_a, pat_b, a0, b0);
  cpp_row_neon_class(f1, lo, hi, pat_a, pat_b, a1, b1);
  cpp_row_neon_class(f2, lo, hi, pat_a, pat_b, a2, b2);
  cpp_row_neon_class(f3, lo, hi, pat_a, pat_b, a3, b3);
  cpp_row_neon_class(f4, lo, hi, pat_a, pat_b, a4, b4);
  cpp_row_neon_class(f5, lo, hi, pat_a, pat_b, a5, b5);
  // minimum over the 16 bytes of each of the 12 results by pairwise
  // minima: one byte each, in the order A0..A5, B0..B5 (then B2..B5 again)
  const uint8x16_t x1 = vpminq_u8(vpminq_u8(a0, a1), vpminq_u8(a2, a3));
  const uint8x16_t x2 = vpminq_u8(vpminq_u8(a4, a5), vpminq_u8(b0, b1));
  const uint8x16_t x3 = vpminq_u8(vpminq_u8(b2, b3), vpminq_u8(b4, b5));
  const uint8x16_t v = vpminq_u8(vpminq_u8(x1, x2), vpminq_u8(x3, x3));
  // a byte cannot have the classes of both layouts at byte 8, so at most
  // one of A_j, B_j is set and the sum is the mask of the valid fields
  const unsigned valid = vaddvq_u8(vandq_u8(v, vld1q_u8(T.bit8)));
  // the exponents: e = 10 * byte 9 (if a digit) + byte 10, per field in a
  // 16-bit lane. Bytes 8..10 of field j and byte 0 of field j+1 are the
  // bytes 11j+8..11j+11 of the line: those of the fields 0, 1 are in the
  // register loaded at byte 8, of 2, 3 at byte 30, of 4, 5 at byte 52
  // (bytes 0..3 and 11..14 of each); byte 0 of field 0 is taken from f0.
  const uint8x16_t g8 = vld1q_u8(u + 8), g30 = vld1q_u8(u + 30), g52 = vld1q_u8(u + 52);
  const uint8x16_t ee = vqtbx1q_u8(vqtbx1q_u8(vqtbl1q_u8(g8, vld1q_u8(T.idx_e[0])),
                                              g30, vld1q_u8(T.idx_e[1])),
                                   g52, vld1q_u8(T.idx_e[2]));
  const uint8x16_t es = vqtbx1q_u8(vqtbx1q_u8(vqtbx1q_u8(vqtbl1q_u8(g8, vld1q_u8(T.idx_s[0])),
                                                         g30, vld1q_u8(T.idx_s[1])),
                                              g52, vld1q_u8(T.idx_s[2])),
                                   f0, vld1q_u8(T.idx_s[3]));
  uint8x16_t ed = vsubq_u8(ee, vdupq_n_u8('0'));
  ed = vandq_u8(ed, vcltq_u8(ed, vdupq_n_u8(10)));
  const int16x8_t e = vreinterpretq_s16_u16(
    vpaddlq_u8(vmulq_u8(ed, c8)));
  // signs: exponent negative if byte 8 or 9 is '-', value if byte 0 is
  const uint16x8_t m9 = vreinterpretq_u16_u8(vceqq_u8(ee, vdupq_n_u8('-')));
  const uint16x8_t m80 = vreinterpretq_u16_u8(vceqq_u8(es, vdupq_n_u8('-')));
  const int16x8_t eneg = vreinterpretq_s16_u16(vtstq_u16(vorrq_u16(m9, m80), vdupq_n_u16(0x00FF)));
  const uint16x8_t vneg = vtstq_u16(m80, vdupq_n_u16(0xFF00));
  const int16x8_t k = vsubq_s16(vsubq_s16(veorq_s16(e, eneg), eneg), vdupq_n_s16(6));
  const uint16x8_t rok = vandq_u16(vcgeq_s16(k, vdupq_n_s16(-22)), vcleq_s16(k, vdupq_n_s16(21)));
  const unsigned inrange = vaddvq_u16(vandq_u16(rok, vld1q_u16(T.bit16)));
  // the table index (0 for the fields out of range)
  const uint16x8_t idx = vandq_u16(
    vaddq_u16(vreinterpretq_u16_s16(vaddq_s16(k, vdupq_n_s16(22))),
              vandq_u16(vneg, vdupq_n_u16(44))),
    rok);
  const std::uint64_t i03 = vgetq_lane_u64(vreinterpretq_u64_u16(idx), 0);
  const std::uint32_t i45 = vgetq_lane_u32(vreinterpretq_u32_u16(idx), 2);
  // the significands and values
  const uint8x16_t im0 = vld1q_u8(T.idx_m0), im1 = vld1q_u8(T.idx_m1);
  vst1q_f64(out, cpp_row_neon_fp(cpp_row_neon_mant(f0, f1, im0, im1, c8, c16, c32),
                                 T.pow[i03 & 0xFFFFu], T.pow[(i03 >> 16) & 0xFFFFu]));
  vst1q_f64(out + 2, cpp_row_neon_fp(cpp_row_neon_mant(f2, f3, im0, im1, c8, c16, c32),
                                     T.pow[(i03 >> 32) & 0xFFFFu], T.pow[i03 >> 48]));
  vst1q_f64(out + 4, cpp_row_neon_fp(cpp_row_neon_mant(f4, f5, im0, im1, c8, c16, c32),
                                     T.pow[i45 & 0xFFFFu], T.pow[i45 >> 16]));
  return valid & inrange;
}

// the row kernel of the tier (called through cpp_row_kernel_fn by the
// line-by-line readers)
CPP_DECIMAL_NOINLINE inline unsigned cpp_row_kernel_neon(
  const char* line, unsigned want, unsigned flags, double* out
) {
  const unsigned fast = cpp_row_neon_fast(line, out) & want;
  if (fast == want) return fast;
  return fast | cpp_row_vector_fallback(
    line, want & ~fast, (flags & CPP_ROW_ACCEPT_D_EXPONENT) != 0, out);
}

#endif  // CPP_ROW_NEON



// Conversion of the float fields of the body of a LIST record read as
// one byte range (see cpp_list_body_range and CppListBody): the first npl
// fields of the nlines = (npl-1)/6+1 lines p, p + stride, ... into out
// (all 6*nlines values may be written). Each function returns the number
// of leading values converted (npl if all), i.e. the position of the
// first field the kernel of its tier does not convert, exactly as one
// call of that kernel per line would give. The tier is chosen once per
// body (cpp_list_convert).

// The scalar tier: one loop with the SWAR stage of cpp_fast_field_to_double
// inline; a field the SWAR stage does not take goes to
// cpp_fast_field_to_double (which tries the SWAR stage again and then its
// general fast path), as in cpp_row_kernel_scalar.
#if defined(__GNUC__) || defined(__clang__)
__attribute__((flatten))
#endif
inline int cpp_list_convert_scalar(
  const char* p, std::size_t stride, int npl, bool accept_d_exponent, double* out
) {
  int i = 0;
  const int full = npl / 6;
  for (int l = 0; l < full; l++) {
    const char* q = p + static_cast<std::size_t>(l) * stride;
    for (int j = 0; j < 6; j++, i++) {
      const int r = cpp_fast_field_swar(q + 11 * j, out[i]);
      if (r > 0) continue;
      if (r < 0 || ! cpp_fast_field_to_double(q + 11 * j, accept_d_exponent, out[i])) return i;
    }
  }
  const char* q = p + static_cast<std::size_t>(full) * stride;
  for (int j = 0; i < npl; j++, i++) {
    const int r = cpp_fast_field_swar(q + 11 * j, out[i]);
    if (r > 0) continue;
    if (r < 0 || ! cpp_fast_field_to_double(q + 11 * j, accept_d_exponent, out[i])) return i;
  }
  return npl;
}

// Any other kernel: one call through the pointer per line.
inline int cpp_list_convert_rows(
  const char* p, std::size_t stride, int npl, cpp_row_kernel_fn kernel,
  unsigned flags, double* out
) {
  const int nlines = (npl - 1) / 6 + 1;
  for (int l = 0; l < nlines; l++) {
    const int pos = 6 * l;
    const int remaining = npl - pos;
    const unsigned want = remaining >= 6 ? 0x3Fu : (1u << remaining) - 1u;
    const unsigned done = kernel(p + static_cast<std::size_t>(l) * stride, want, flags, out + pos);
    if (done != want) {
      int j = 0;
      while ((done >> j) & 1u) j++;
      return pos + j;
    }
  }
  return npl;
}

#ifdef CPP_ROW_VECTOR_TIERS

// The vector tiers: one loop per tier with the vector path of its kernel
// inline, one step per line; the fields it leaves go to
// cpp_row_vector_fallback (out of line), as in cpp_row_kernel_avx2 and
// cpp_row_kernel_avx512.
CPP_ROW_TARGET_AVX2 CPP_ROW_VECTOR_ENTRY inline int cpp_list_convert_avx2(
  const char* p, std::size_t stride, int npl, bool accept_d_exponent, double* out
) {
  const int nlines = (npl - 1) / 6 + 1;
  for (int l = 0; l < nlines; l++) {
    const char* q = p + static_cast<std::size_t>(l) * stride;
    const int pos = 6 * l;
    const int remaining = npl - pos;
    const unsigned want = remaining >= 6 ? 0x3Fu : (1u << remaining) - 1u;
    const unsigned fast = cpp_row_avx2_fast(q, out + pos) & want;
    if (fast != want) {
      const unsigned done = fast | cpp_row_vector_fallback(q, want & ~fast, accept_d_exponent, out + pos);
      if (done != want) return pos + cpp_row_ctz(~done);
    }
  }
  return npl;
}

CPP_ROW_TARGET_AVX512 CPP_ROW_VECTOR_ENTRY inline int cpp_list_convert_avx512(
  const char* p, std::size_t stride, int npl, bool accept_d_exponent, double* out
) {
  const int nlines = (npl - 1) / 6 + 1;
  for (int l = 0; l < nlines; l++) {
    const char* q = p + static_cast<std::size_t>(l) * stride;
    const int pos = 6 * l;
    const int remaining = npl - pos;
    const unsigned want = remaining >= 6 ? 0x3Fu : (1u << remaining) - 1u;
    const unsigned fast = cpp_row_avx512_fast(q, out + pos) & want;
    if (fast != want) {
      const unsigned done = fast | cpp_row_vector_fallback(q, want & ~fast, accept_d_exponent, out + pos);
      if (done != want) return pos + cpp_row_ctz(~done);
    }
  }
  return npl;
}

#endif  // CPP_ROW_VECTOR_TIERS

#ifdef CPP_ROW_NEON

// The NEON tier: one loop with the vector path of its kernel inline, as
// for the x86 tiers.
inline int cpp_list_convert_neon(
  const char* p, std::size_t stride, int npl, bool accept_d_exponent, double* out
) {
  const int nlines = (npl - 1) / 6 + 1;
  for (int l = 0; l < nlines; l++) {
    const char* q = p + static_cast<std::size_t>(l) * stride;
    const int pos = 6 * l;
    const int remaining = npl - pos;
    const unsigned want = remaining >= 6 ? 0x3Fu : (1u << remaining) - 1u;
    const unsigned fast = cpp_row_neon_fast(q, out + pos) & want;
    if (fast != want) {
      const unsigned done = fast | cpp_row_vector_fallback(q, want & ~fast, accept_d_exponent, out + pos);
      if (done != want) return pos + cpp_row_ctz(~done);
    }
  }
  return npl;
}

#endif  // CPP_ROW_NEON


struct cpp_row_tier {
  const char* name;
  // nullptr if the tier is not built (e.g. for another architecture)
  cpp_row_kernel_fn kernel;
  // whether the tier is a vector tier, a candidate of the automatic
  // selection (see cpp_row_tier_auto)
  bool vector;
  bool (*supported)(const cpp_cpu_features&);
};

#define CPP_ROW_NUM_TIERS 4

// in the order of preference of the automatic selection, which takes the
// scalar tier (the last one) if no vector tier is built and supported;
// the x86 vector tiers are only built with CPP_ROW_VECTOR_TIERS, the NEON
// tier with CPP_ROW_NEON
inline const cpp_row_tier* cpp_row_tiers() {
  static const cpp_row_tier tiers[CPP_ROW_NUM_TIERS] = {
#ifdef CPP_ROW_VECTOR_TIERS
    {"avx512", cpp_row_kernel_avx512, true, cpp_row_cpu_avx512},
    {"avx2", cpp_row_kernel_avx2, true, cpp_row_cpu_avx2},
#else
    {"avx512", nullptr, true, cpp_row_cpu_avx512},
    {"avx2", nullptr, true, cpp_row_cpu_avx2},
#endif
#ifdef CPP_ROW_NEON
    {"neon", cpp_row_kernel_neon, true, cpp_row_cpu_neon},
#else
    {"neon", nullptr, true, cpp_row_cpu_neon},
#endif
    {"scalar", cpp_row_kernel_scalar, false, cpp_row_cpu_any},
  };
  return tiers;
}

// whether the automatic selection takes tier i of the table (of
// cpp_row_tiers) if it is built and supported: the vector tiers (except
// the NEON tier with CPP_ROW_NEON_NOT_AUTO) and the scalar tier, the last
// one
inline bool cpp_row_tier_auto(const cpp_row_tier* tiers, int i) {
#ifdef CPP_ROW_NEON_NOT_AUTO
  if (tiers[i].kernel == cpp_row_kernel_neon) return false;
#endif
  return tiers[i].vector || i == CPP_ROW_NUM_TIERS - 1;
}

// the compiler of the module, for diagnostics: clang-cl (Clang with
// _MSC_VER, which takes the GCC/Clang branch of the x86 tiers) and Apple
// Clang are told apart from Clang, MSVC itself from both
inline const char* cpp_row_compiler() {
#if defined(__clang__) && defined(_MSC_VER)
  return "clang-cl";
#elif defined(__clang__) && defined(__apple_build_version__)
  return "apple-clang";
#elif defined(__clang__)
  return "clang";
#elif defined(__GNUC__)
  return "gcc";
#elif defined(_MSC_VER)
  return "msvc";
#else
  return "other";
#endif
}

struct cpp_row_selection {
  // the kernel of the selected tier, nullptr for the per-field form
  cpp_row_kernel_fn kernel;
  // the name of the selected tier, "off" if none
  const char* tier;
  // the value of the environment variable (at most 15 characters), and
  // whether it is set
  char requested[16];
  bool requested_set;
  // nullptr, or why the requested tier is not used
  const char* warning;
  cpp_cpu_features cpu;
  // whether all LIST bodies with a loop are read in the bulk form, also
  // those delivered by the code of the per-field form (see cpp_list_bulk):
  // with a vector tier and with a tier given by the variable, not with
  // the scalar tier selected automatically
  bool list_all;
};

// The selection for the value `value` (nullptr if unset) of the
// environment variable ENDF_PARSERPY_CPP_BULK_BODIES on a CPU with the
// features `cpu`. A tier is never selected if it is not built or the CPU
// does not support it.
inline cpp_row_selection cpp_row_select(const char* value, const cpp_cpu_features& cpu) {
  cpp_row_selection sel;
  sel.kernel = nullptr;
  sel.tier = "off";
  sel.requested[0] = '\0';
  sel.requested_set = value != nullptr;
  sel.warning = nullptr;
  sel.cpu = cpu;
  sel.list_all = false;
  char name[16];
  bool too_long = false;
  if (value != nullptr) {
    std::size_t n = 0;
    for (; value[n] != '\0' && n < 15; n++) {
      sel.requested[n] = value[n];
      name[n] = static_cast<char>(std::tolower(static_cast<unsigned char>(value[n])));
    }
    sel.requested[n] = '\0';
    name[n] = '\0';
    too_long = value[n] != '\0';
  } else {
    name[0] = '\0';
  }
  const cpp_row_tier* tiers = cpp_row_tiers();
  bool automatic = name[0] == '\0' || std::strcmp(name, "auto") == 0;
  if (! automatic && ! too_long && std::strcmp(name, "off") == 0) {
    return sel;
  }
  if (! automatic) {
    const cpp_row_tier* tier = nullptr;
    for (int i = 0; i < CPP_ROW_NUM_TIERS; i++) {
      if (! too_long && std::strcmp(name, tiers[i].name) == 0) tier = &tiers[i];
    }
    if (tier == nullptr) {
      sel.warning = "unknown value (expected auto, off, scalar, avx2, avx512 or neon); using auto";
    } else if (tier->kernel == nullptr) {
      sel.warning = "this tier is not built in this module; using auto";
    } else if (! tier->supported(cpu)) {
      sel.warning = "the CPU does not support this tier; using auto";
    } else {
      sel.kernel = tier->kernel;
      sel.tier = tier->name;
      sel.list_all = true;
      return sel;
    }
  }
  for (int i = 0; i < CPP_ROW_NUM_TIERS; i++) {
    // as cpp_row_tier_auto
#ifdef CPP_ROW_NEON_NOT_AUTO
    if (tiers[i].kernel == cpp_row_kernel_neon) continue;
#endif
    if ((tiers[i].vector || i == CPP_ROW_NUM_TIERS - 1)
        && tiers[i].kernel != nullptr && tiers[i].supported(cpu)) {
      sel.kernel = tiers[i].kernel;
      sel.tier = tiers[i].name;
      sel.list_all = tiers[i].vector;
      break;
    }
  }
  return sel;
}

// The kernel for the bodies of TAB1 and LIST records, nullptr for the
// per-field form: a variable without dynamic initialization (shared by
// the translation units of a module as a static member of a class
// template), so that reading it at every record is a plain load.
template<typename T = void>
struct cpp_row_state {
  static cpp_row_kernel_fn kernel;
  static bool list_all;
};

template<typename T>
cpp_row_kernel_fn cpp_row_state<T>::kernel = nullptr;

template<typename T>
bool cpp_row_state<T>::list_all = false;

// The selection made when the module is loaded (the first call, see
// register_reading_options in cpp_boilerplate_reading.py), which also
// sets the kernel used by the parse functions.
inline const cpp_row_selection& cpp_row_selected() {
  static const cpp_row_selection sel = cpp_row_select(
    std::getenv("ENDF_PARSERPY_CPP_BULK_BODIES"), cpp_detect_cpu_features()
  );
  cpp_row_state<>::kernel = sel.kernel;
  cpp_row_state<>::list_all = sel.list_all;
  return sel;
}

inline cpp_row_kernel_fn cpp_float_row_kernel() {
  return cpp_row_state<>::kernel;
}

// The conversion of a LIST body read as one byte range (see
// cpp_list_convert_scalar) with the kernel `kernel`: the loop of its tier,
// chosen once per body.
inline int cpp_list_convert(
  const char* p, std::size_t stride, int npl, cpp_row_kernel_fn kernel,
  bool accept_d_exponent, double* out
) {
  if (kernel == cpp_row_kernel_scalar) {
    return cpp_list_convert_scalar(p, stride, npl, accept_d_exponent, out);
  }
#ifdef CPP_ROW_VECTOR_TIERS
  if (kernel == cpp_row_kernel_avx512) {
    return cpp_list_convert_avx512(p, stride, npl, accept_d_exponent, out);
  }
  if (kernel == cpp_row_kernel_avx2) {
    return cpp_list_convert_avx2(p, stride, npl, accept_d_exponent, out);
  }
#endif
#ifdef CPP_ROW_NEON
  if (kernel == cpp_row_kernel_neon) {
    return cpp_list_convert_neon(p, stride, npl, accept_d_exponent, out);
  }
#endif
  return cpp_list_convert_rows(
    p, stride, npl, kernel, accept_d_exponent ? CPP_ROW_ACCEPT_D_EXPONENT : 0u, out);
}

// End of the row kernels.


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


// The integer in the length columns of str starting at start_pos (counting
// from 0) as the MAT/MF/MT numbers and the fields of INTG records are
// read: a blank field reads as zero, otherwise the field must hold an
// integer with an optional sign, preceded and followed by blanks only
// (e.g. " 3", "-1  ", "+12"), as read_ctrl and read_fort_int of
// EndfParserPy read it. Returns false for anything else (e.g. "ab", "8x",
// "1 2", a tab, "1_0"), and for a number outside the range of int.
inline bool cpp_int_columns_to_int(const char* str, int start_pos, int length, int& value) {
  const char* p = str + start_pos;
  const char* const e = p + length;
  while (p < e && *p == ' ') p++;
  if (p == e) {
    value = 0;
    return true;
  }
  bool neg = false;
  if (*p == '+' || *p == '-') {
    neg = (*p == '-');
    p++;
  }
  const char* const d = p;
  long long v = 0;
  for (; p < e && static_cast<unsigned char>(*p - '0') < 10; p++) {
    // beyond the range of int (also with more digits), but no overflow
    if (v < 10000000000LL) v = v * 10 + (*p - '0');
  }
  if (p == d) return false;
  while (p < e && *p == ' ') p++;
  if (p != e) return false;
  if (neg) v = -v;
  if (v < INT_MIN || v > INT_MAX) return false;
  value = static_cast<int>(v);
  return true;
}


// Raise the error for an invalid number field: the message is
// what + the field in quotes + a description of the field (see
// cpp_field_description) if fieldnum (counting from 0) is not negative
// + after. Kept out of line, so that the error path does not add code
// to the conversion functions.
[[noreturn]] CPP_DECIMAL_NOINLINE inline void cpp_throw_field_error(
  const char* what, const char* str, int fieldnum, const ParsingOptions& parse_opts,
  const char* after = ""
) {
  std::stringstream errmsg;
  errmsg << what << "\"" << std::string(str, 11) << "\"";
  if (fieldnum >= 0) {
    errmsg << " (" << cpp_field_description(fieldnum, parse_opts) << ")";
  }
  errmsg << after << std::endl;
  throw std::runtime_error(errmsg.str());
}


// str points to the field, fieldnum (counting from 0) is its position
// in the line, which is only used for error messages (-1 if unknown).
inline double endfstr2float(const char* str, ParsingOptions &parse_opts, int fieldnum = -1) {
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
    // a tab or another control character is not part of a number (as in
    // EndfParserPy); std::strtod would skip it before the number and stop
    // at a NUL character after it
    if (static_cast<unsigned char>(c) < 0x20 || c == 0x7f) {
      cpp_throw_field_error("malformed number field: ", str, fieldnum, parse_opts);
    }
    if (c == ' ') {
      if (parse_opts.accept_spaces || ! in_number) {
        continue;
      } else {
        cpp_throw_field_error("encountered number with spaces: ", str, fieldnum, parse_opts);
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
      // any other character than a blank starts the number (also a
      // letter, e.g. of "nan"), so that a blank within it is an error
      // without accept_spaces, as in EndfParserPy
      in_number = true;
    }
    // std::strtod also reads hexadecimal numbers ("0x10", "0x1p3") and
    // "nan" with a payload ("nan(1)"), which float() of EndfParserPy
    // does not; neither has a place in a number field
    if (c == 'x' || c == 'X' || c == '(') {
      cpp_throw_field_error("malformed number field: ", str, fieldnum, parse_opts);
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
  v = cpp_strtod_c(tbuf, &end);
  if (end == tbuf || *end != '\0') {
    cpp_throw_field_error("malformed number field: ", str, fieldnum, parse_opts);
  }
  if (!parse_opts.accept_nan_inf && !std::isfinite(v)) {
    cpp_throw_field_error(
      "non-finite value (overflow / inf / NaN) in field: ", str, fieldnum, parse_opts,
      ". Set `accept_nan_inf=true` to allow non-finite values."
    );
  }
  return v;
}


// See endfstr2float for the arguments. The field is read as the MAT/MF/MT
// numbers (see cpp_int_columns_to_int): blank (zero), or an integer with
// an optional sign, preceded and followed by blanks only; anything else
// (e.g. "0.000000+0", "4x", a tab or an underscore) is an error, as for
// read_fort_int of EndfParserPy. The fast path covers up to 9 digits.
inline int endfstr2int(const char* str, ParsingOptions &parse_opts, int fieldnum = -1) {
  int value;
  if (cpp_fast_field_to_int(str, value)) {
    return value;
  }
  if (! cpp_int_columns_to_int(str, 0, 11, value)) {
    cpp_throw_field_error("invalid integer in field: ", str, fieldnum, parse_opts, ".");
  }
  return value;
}

// case for EndfFloatCpp
inline EndfFloatCpp cpp_read_field_EndfFloatCpp(
  const char *str, const char fieldnum, ParsingOptions &parse_opts
) {
  double float_value = endfstr2float(str+fieldnum*11, parse_opts, fieldnum);
  if (parse_opts.preserve_value_strings) {
    return EndfFloatCpp(float_value, str+fieldnum*11, 11);
  } else {
    return EndfFloatCpp(float_value);
  }
}


// One specialization per type T instead of branches on std::is_same in
// one function: the branches for the other types would be instantiated as
// well, with conversions that are never executed, e.g. of the double of
// endfstr2float to int (undefined behaviour outside the range of int).
template<typename T>
inline T cpp_read_field(const char *str, const char fieldnum, ParsingOptions &parse_opts) {
  static_assert(sizeof(T) == 0, "T must be int, double or EndfFloatCpp");
}


template<>
inline double cpp_read_field<double>(
  const char *str, const char fieldnum, ParsingOptions &parse_opts
) {
  return endfstr2float(str+fieldnum*11, parse_opts, fieldnum);
}


template<>
inline EndfFloatCpp cpp_read_field<EndfFloatCpp>(
  const char *str, const char fieldnum, ParsingOptions &parse_opts
) {
  return cpp_read_field_EndfFloatCpp(str, fieldnum, parse_opts);
}


template<>
inline int cpp_read_field<int>(
  const char *str, const char fieldnum, ParsingOptions &parse_opts
) {
  return endfstr2int(str+fieldnum*11, parse_opts, fieldnum);
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


// A mismatch tolerated by the options ignore_zero_mismatch,
// ignore_number_mismatch and ignore_varspec_mismatch (see
// cpp_validate_field): the kind ('z', 'n' or 'v'), the field of the line
// (0 to 5, -1 if unknown), whether the value is one of the body of a
// record, the expression of the field in the recipe, the expected and the
// actual value (as double, and whether they are integers) and the
// position in the input after the line holding the value. The line and
// the MAT/MF/MT numbers are determined from the position when the
// mismatches are reported (see cpp_report_tolerated).
struct cpp_tolerated_mismatch {
  char kind = 0;
  int fieldnum;
  bool in_body;
  const char* exprstr;
  double expected;
  double actual;
  bool expected_int;
  bool actual_int;
  std::streamoff end_pos;
  // for a value of a LIST body delivered by CppListBody: the beginning of
  // the body in the memory of the input and the index of the value, which
  // identify the value if it is checked again (see cpp_record_tolerated)
  const char* body_start;
  int body_index;
};


// The mismatches tolerated in a call from Python, created by the function
// called (see generate_cpp_parsefun_wrappers_string), which sets
// ParsingOptions::tolerated. stream is the stream being parsed.
struct cpp_tolerated_log {
  std::istream* stream;
  // the input held in memory, if the stream reads from it
  const cpp_memory_streambuf* memory;
  std::vector<cpp_tolerated_mismatch> entries;
};


// Defined after CppListBody.
CPP_TOLERATED_COLD void cpp_record_tolerated(
  ParsingOptions& parse_opts, char kind, int fieldnum, const char* exprstr,
  double expected, bool expected_int, double actual, bool actual_int,
  const CppListBody* body, int body_index
);


// The value of a mismatch as a double and whether it is an integer, for
// cpp_record_tolerated.
template<typename T>
inline double cpp_tolerated_number(const T& value) { return static_cast<double>(value); }

template<typename T>
inline bool cpp_tolerated_is_int(const T&) { return std::is_integral<T>::value; }

inline bool cpp_tolerated_is_int(const EndfRational& value) { return value.is_integer(); }


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
  const char* exprstr,
  int fieldnum,
  ParsingOptions &parse_opts,
  const CppListBody* body = nullptr,
  int body_index = -1
) {
  std::stringstream errmsg;
  errmsg << "Both the expected and actual value are vectors --- "
         << "not implemented at the moment" << std::endl;
  throw std::runtime_error(errmsg.str());
}


// The handling of a field whose value (actual_value) differs from the
// value given by the recipe (expected_value), see cpp_validate_field:
// either the mismatch is tolerated by the options and recorded (see
// cpp_record_tolerated), or an error is raised. Kept out of line, so that
// a check adds only the comparison and one call to the reading functions.
template<typename U, typename V>
CPP_TOLERATED_COLD void cpp_field_mismatch(
  const U& expected_value,
  const V& actual_value,
  bool contains_variable,
  bool contains_desired_number,
  bool contains_inconsistent_varspec,
  const char* exprstr,
  int fieldnum,
  ParsingOptions &parse_opts,
  const CppListBody* body,
  int body_index
) {
  char kind;
  if (! contains_variable) {
    // dealing with a number
    // ignore zero mismatch only active for scalar data types
    if (is_zero_check(expected_value) && parse_opts.ignore_zero_mismatch) {
      kind = 'z';
    } else if (contains_desired_number && parse_opts.ignore_number_mismatch) {
      kind = 'n';
    } else {
      throw_number_mismatch_error(expected_value, actual_value, fieldnum, parse_opts);
      return;
    }
  } else {
    // dealing with an expression with variables
    if (contains_inconsistent_varspec && parse_opts.ignore_varspec_mismatch) {
      kind = 'v';
    } else {
      throw_mismatch_error(exprstr, expected_value, actual_value);
      return;
    }
  }
  cpp_record_tolerated(
    parse_opts, kind, fieldnum, exprstr,
    cpp_tolerated_number(expected_value), cpp_tolerated_is_int(expected_value),
    cpp_tolerated_number(actual_value), cpp_tolerated_is_int(actual_value),
    body, body_index
  );
}


// The value of a field (actual_value) is checked against the value given
// by the recipe (expected_value); a mismatch is handled by
// cpp_field_mismatch. For a value of the body of a LIST record delivered
// by CppListBody (whose lines have all been read), body is the object and
// body_index the index of the value in the body, otherwise body is
// nullptr and body_index the index of a value of a LIST body (-1 for a
// field of another kind).
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
  const char* exprstr,
  int fieldnum,
  ParsingOptions &parse_opts,
  const CppListBody* body = nullptr,
  int body_index = -1
) {
  if (cpp_values_equal(expected_value, actual_value)) return;
  cpp_field_mismatch(
    expected_value, actual_value, contains_variable, contains_desired_number,
    contains_inconsistent_varspec, exprstr, fieldnum, parse_opts, body, body_index
  );
}

// we are done with the cpp_validate_field related functionality

// The message of the error for a field that cpp_int_columns_to_int does
// not accept, e.g. `invalid MF number field: "8x" (columns 71-72)`; what
// names the field.
CPP_DECIMAL_NOINLINE inline std::string cpp_int_columns_error_message(
  const char* what, const char* str, int start_pos, int length
) {
  std::ostringstream errmsg;
  errmsg << "invalid " << what << " field: \""
         << std::string(str + start_pos, static_cast<std::size_t>(length))
         << "\" (columns " << start_pos + 1 << "-" << start_pos + length << ")";
  return errmsg.str();
}


// Raise the error for a field that cpp_int_columns_to_int does not
// accept while parsing; the template of the record and the line are
// added to the message by cpp_rethrow_parse_error. Kept out of line, so
// that the error path does not add code to the reading functions.
[[noreturn]] CPP_DECIMAL_NOINLINE inline void cpp_throw_int_columns_error(
  const char* what, const char* str, int start_pos, int length
) {
  throw std::runtime_error(
    cpp_int_columns_error_message(what, str, start_pos, length) + "\n"
  );
}


// The integer in the field of the given length starting at start_pos
// (see cpp_int_columns_to_int); used for the fields of INTG records.
// Raises an error if the field holds anything else than a blank field
// or an integer.
inline int cpp_read_custom_int_field(const char *str, int start_pos, int length) {
  int value;
  if (! cpp_int_columns_to_int(str, start_pos, length, value)) {
    cpp_throw_int_columns_error("integer", str, start_pos, length);
  }
  return value;
}


// The MAT, MF and MT numbers of a line (columns 67-70, 71-72 and 73-75),
// see cpp_int_columns_to_int. Raise an error for a field holding
// anything else than a blank field or an integer, as EndfParserPy.
inline int cpp_read_mat_number(const char *str) {
  int value;
  if (! cpp_int_columns_to_int(str, 66, 4, value)) {
    cpp_throw_int_columns_error("MAT number", str, 66, 4);
  }
  return value;
}


inline int cpp_read_mf_number(const char *str) {
  int value;
  if (! cpp_int_columns_to_int(str, 70, 2, value)) {
    cpp_throw_int_columns_error("MF number", str, 70, 2);
  }
  return value;
}


inline int cpp_read_mt_number(const char *str) {
  int value;
  if (! cpp_int_columns_to_int(str, 72, 3, value)) {
    cpp_throw_int_columns_error("MT number", str, 72, 3);
  }
  return value;
}


// Raise an error if one of the MAT, MF and MT fields of a line is not
// accepted by cpp_int_columns_to_int (see cpp_read_mat_number), for a
// line whose numbers are not needed otherwise.
inline void cpp_check_control_fields(const char *str) {
  cpp_read_mat_number(str);
  cpp_read_mf_number(str);
  cpp_read_mt_number(str);
}


// The leading integer of a field as std::atoi reads it (0 if there is
// none), only for the MAT/MF/MT numbers in the message of an error about
// another problem of the line (see cpp_check_line_ascii), as
// _lenient_int of EndfParserPy.
inline int cpp_read_lenient_int_field(const char *str, int start_pos, int length) {
  char buf[32];
  if (length >= static_cast<int>(sizeof(buf))) length = sizeof(buf) - 1;
  std::memcpy(buf, str + start_pos, length);
  buf[length] = '\0';
  return std::atoi(buf);
}


inline bool cpp_is_blank_line(const char* line, std::size_t size) {
  // scanning from the end exits early for regular lines, which end
  // with the MAT/MF/MT numbers (and possibly a line number)
  for (std::size_t i = size; i > 0; i--) {
    if (line[i-1] != ' ' && line[i-1] != '\t') return false;
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
inline std::istream& cpp_getline_with_cr(std::istream& is, std::string& line) {
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


// A line without the line terminator: the newline and, for a file with
// CRLF line endings (e.g. written on Windows), the carriage return before
// it, so that every reader sees the same line (blank lines included) as
// EndfParserPy, which reads the file in text mode.
inline std::istream& cpp_getline(std::istream& is, std::string& line) {
  cpp_getline_with_cr(is, line);
  if (! line.empty() && line.back() == '\r') line.pop_back();
  return is;
}


// The data to be parsed by `parse`: a Python string, whose characters
// are mapped to the bytes with the same codes (see cpp_bytes_to_pystr),
// or bytes. The bytes are not copied; they belong to `cont`, which
// must remain alive while they are used.
inline void cpp_parse_input_bytes(
  const py::object& cont, const char*& data, std::size_t& size, py::object& holder
) {
  PyObject* obj = cont.ptr();
  if (PyUnicode_Check(obj)) {
    if (cpp_pystr_bytes(obj, data, size)) return;
    PyObject* bytes = PyUnicode_AsLatin1String(obj);
    if (bytes == nullptr) {
      PyErr_Clear();
      // raises the error (a character above U+00FF)
      cpp_text_encoding_function("raise_input_error")(cont);
      throw std::logic_error("unexpected string conversion failure");
    }
    holder = py::reinterpret_steal<py::object>(bytes);
    obj = bytes;
  }
  if (PyBytes_Check(obj)) {
    data = PyBytes_AS_STRING(obj);
    size = static_cast<std::size_t>(PyBytes_GET_SIZE(obj));
    return;
  }
  throw py::type_error("the data to be parsed must be given as str or bytes");
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
// The get area always spans the whole memory, which is not changed while
// the stream buffer exists, so that the lines read from it can be views
// into the memory (see CppLine).
class cpp_memory_streambuf final : public std::streambuf {
public:
  cpp_memory_streambuf(const char* data, std::size_t size) {
    // the get area is only read from, never written to
    char* begin = const_cast<char*>(data);
    setg(begin, begin, begin + size);
  }

  // the beginning, the read position and the end of the memory
  const char* begin() const { return eback(); }
  const char* current() const { return gptr(); }
  const char* end() const { return egptr(); }

  // move the read position to pos (between current() and end())
  void move_to(const char* pos) {
    setg(eback(), const_cast<char*>(pos), egptr());
  }

  // The columns 67 to 75 of the lines of the section MAT/MF/MT as they
  // are written ("%4d%2d%3d", 9 characters), or nullptr if the numbers
  // do not fit into these columns; formatted once for each section read
  // from the memory (see cpp_list_body_range).
  const char* control_columns(int mat, int mf, int mt) {
    if (! cc_valid_ || mat != cc_mat_ || mf != cc_mf_ || mt != cc_mt_) {
      cc_mat_ = mat;
      cc_mf_ = mf;
      cc_mt_ = mt;
      cc_ok_ = std::snprintf(cc_, sizeof(cc_), "%4d%2d%3d", mat, mf, mt) == 9;
      cc_valid_ = true;
    }
    return cc_ok_ ? cc_ : nullptr;
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

private:
  // the cache of control_columns
  bool cc_valid_ = false;
  bool cc_ok_ = false;
  int cc_mat_ = 0;
  int cc_mf_ = 0;
  int cc_mt_ = 0;
  char cc_[16] = {0};
};


// The complete content of a file, read into memory. The memory is
// allocated once for the size of the file and the file is read into it
// with std::fread, without initializing the memory first (as resizing a
// std::string would) and without copying the data through the buffer
// of a file stream. A file whose size cannot be determined (e.g. a pipe)
// or that is larger than its size determined before reading is read
// in chunks into memory that grows as needed. As for a file stream, a
// read error ends the content, i.e. only the bytes read before the error
// are parsed.
class cpp_file_content {
  private:
    struct closer {
      void operator()(std::FILE* file) const { std::fclose(file); }
    };

  public:
    explicit cpp_file_content(const std::string& filename) {
      std::FILE* file = std::fopen(filename.c_str(), "rb");
      if (file == nullptr) {
        throw std::ifstream::failure("failed to open file " + filename);
      }
      std::unique_ptr<std::FILE, closer> file_guard(file);
      // one more byte than the size of the file, so that the end of the
      // file is detected by the first read
      std::size_t capacity = 64 * 1024;
      if (std::fseek(file, 0, SEEK_END) == 0) {
        long end = std::ftell(file);
        if (end >= 0) capacity = static_cast<std::size_t>(end) + 1;
      }
      std::rewind(file);
      buf_.reset(new char[capacity]);
      while (true) {
        size_ += std::fread(buf_.get() + size_, 1, capacity - size_, file);
        if (size_ < capacity) break;
        std::unique_ptr<char[]> larger(new char[2 * capacity]);
        std::memcpy(larger.get(), buf_.get(), size_);
        buf_.swap(larger);
        capacity *= 2;
      }
    }

    const char* data() const { return buf_.get(); }
    std::size_t size() const { return size_; }

  private:
    std::unique_ptr<char[]> buf_;
    std::size_t size_ = 0;
};


// Numbers of lines read as views and as copies (see CppLine), only for
// tests checking that lines are read as views where intended.
struct cpp_line_read_counts {
  unsigned long long views;
  unsigned long long copies;
};

inline cpp_line_read_counts& cpp_line_read_counter() {
  static cpp_line_read_counts counts = {0, 0};
  return counts;
}


// A line read from the input, without the line ending (see cpp_getline).
// If the input is held in memory by a cpp_memory_streambuf (`parse` and
// `parsefile` with load_file_into_memory=true), the line is a view into
// that memory, which is neither changed nor moved while it is parsed
// (repositioning the stream only moves the read pointer), so that the
// line is not copied. The stream buffer is given explicitly by the
// function that creates it (parse_opts.memory_input), and a line is only
// read as a view if the stream reads from that stream buffer. Otherwise
// the line is read into a string held by the object, whose memory is
// reused for the next line. A line to be
// modified, i.e. a short line padded with blanks (see pad_short), is
// also copied into this string.
// Unlike std::string::c_str, data() is not terminated by a NUL
// character; the readers only access the columns before size(), which
// is at least 75 after pad_short.
class CppLine {
  public:
    CppLine() : data_(""), size_(0), owned_(false), membuf_(nullptr) {}

    // a line read as a view from the stream buffer parse_opts.memory_input
    // (if not nullptr) and as a copy from any other stream buffer
    explicit CppLine(const ParsingOptions& parse_opts)
      : data_(""), size_(0), owned_(false),
        membuf_(parse_opts.memory_input) {}

    const char* data() const { return data_; }
    std::size_t size() const { return size_; }
    bool empty() const { return size_ == 0; }
    char operator[](std::size_t i) const { return data_[i]; }
    std::string str() const { return std::string(data_, size_); }

    // as std::string::substr
    std::string substr(std::size_t pos, std::size_t len = std::string::npos) const {
      if (pos > size_) throw std::out_of_range("CppLine::substr");
      std::size_t n = size_ - pos;
      if (len < n) n = len;
      return std::string(data_ + pos, n);
    }

    void clear() {
      own_.clear();
      set_owned();
    }

    // Equivalent of cpp_getline(is, line) for a std::string line,
    // including the state flags set on the stream and an unchanged
    // line if the stream is not good before the read.
    std::istream& getline(std::istream& is) {
      if (membuf_ == nullptr || is.rdbuf() != membuf_) {
        cpp_getline(is, own_);
        set_owned();
        cpp_line_read_counter().copies++;
        return is;
      }
      if (! is.good()) {
        // as std::istream::sentry
        is.setstate(std::ios_base::failbit);
        return is;
      }
      const char* p = membuf_->current();
      const char* e = membuf_->end();
      if (p == e) {
        clear();
        is.setstate(std::ios_base::eofbit | std::ios_base::failbit);
        return is;
      }
      const char* nl = static_cast<const char*>(std::memchr(p, '\n', e - p));
      std::size_t len;
      if (nl != nullptr) {
        len = nl - p;
        membuf_->move_to(nl + 1);
      } else {
        len = e - p;
        membuf_->move_to(e);
        is.setstate(std::ios_base::eofbit);
      }
      // the carriage return of a CRLF line ending
      if (len > 0 && p[len-1] == '\r') len--;
      data_ = p;
      size_ = len;
      owned_ = false;
      cpp_line_read_counter().views++;
      return is;
    }

    // The line as getline leaves a line of n characters (n >= 75, no line
    // ending) at p, a position in the memory of the input, which is read
    // without getline (see CppListBody::fast_body).
    void set_view(const char* p, std::size_t n) {
      data_ = p;
      size_ = n;
      owned_ = false;
    }

    // The fields and the MAT/MF/MT numbers are read at fixed columns up
    // to column 75. Columns missing from a shorter line are blanks (as
    // for EndfParserPy, which reads the columns of a line by slicing), so
    // that the readers never read past the end of the line.
    // Returns the length of the line content before the padding.
    std::size_t pad_short() {
      const std::size_t min_size = 75;
      std::size_t content_size = size_;
      if (content_size >= min_size) return content_size;
      if (! owned_) own_.assign(data_, size_);
      own_.append(min_size - content_size, ' ');
      set_owned();
      return content_size;
    }

  private:
    void set_owned() {
      data_ = own_.data();
      size_ = own_.size();
      owned_ = true;
    }

    const char* data_;
    std::size_t size_;
    // whether data_ is the content of own_
    bool owned_;
    std::string own_;
    // the stream buffer the line is a view into, if any
    cpp_memory_streambuf* membuf_;

    // a view must not outlive the input, and copies are not needed
    CppLine(const CppLine&) = delete;
    CppLine& operator=(const CppLine&) = delete;
};


inline std::string cpp_line_str(const CppLine& line) {
  return line.str();
}


inline std::istream& cpp_getline(std::istream& is, CppLine& line) {
  return line.getline(is);
}


inline bool cpp_is_blank_line(const CppLine& line) {
  return cpp_is_blank_line(line.data(), line.size());
}


// See CppLine::pad_short.
inline std::size_t cpp_pad_short_line(CppLine& line) {
  return line.pad_short();
}


// The number (counting from 1), the length and the content (both
// without the line ending) of the last line read from a stream, i.e. of
// the line that ends before the current position. The stream is read
// again from its beginning, which is only done for error messages; the
// position is restored. Returns false if the stream cannot be
// repositioned.
inline bool cpp_last_line_info(
  std::istream& cont, long& lineno, std::size_t& length, std::string* content = nullptr
) {
  cont.clear();
  std::streampos pos = cont.tellg();
  if (pos == std::streampos(-1)) return false;
  cont.seekg(0);
  if (! cont) {
    cont.clear();
    cont.seekg(pos);
    return false;
  }
  lineno = 0;
  length = 0;
  std::string line;
  while (true) {
    std::streampos start = cont.tellg();
    if (start == std::streampos(-1) || start >= pos) break;
    if (! cpp_getline(cont, line)) break;
    lineno++;
    length = line.size();
    if (content != nullptr) content->swap(line);
  }
  cont.clear();
  cont.seekg(pos);
  return lineno > 0;
}


// A hint for an error message if a line (the line number lineno counting
// from 1) is longer than 80 columns (length), otherwise empty.
inline std::string cpp_long_line_hint(long lineno, std::size_t length) {
  if (length <= 80) return "";
  std::ostringstream oss;
  oss << "Hint: line " << lineno << " is longer than 80 columns (" << length
      << " columns; non-ASCII multi-byte characters or text beyond column 80?)";
  return oss.str();
}


// To be called in a catch block for a std::runtime_error raised while
// parsing the data in cont: rethrows it with the context of the error
// added to the message, i.e. the template of the record being read (see
// ParsingOptions::current_template), the number and the content of the
// last line read (see cpp_last_line_info) and a hint if this line is
// longer than 80 columns. The message is escaped (see
// cpp_escape_message). Exceptions of derived classes, e.g. failures to
// open a file, are rethrown unchanged.
[[noreturn]] inline void cpp_rethrow_parse_error(
  const std::runtime_error& e, std::istream& cont, const ParsingOptions& parse_opts
) {
  if (typeid(e) != typeid(std::runtime_error)) throw;
  // a failed read at the end of the data (e.g. of a truncated file)
  bool past_end = cont.eof() && cont.fail();
  std::string msg = e.what();
  if (! msg.empty() && msg[msg.size()-1] != '\n') msg += "\n";
  const char* tmpl = cpp_template_text(parse_opts.current_template);
  if (tmpl != nullptr) {
    msg += "Template: ";
    msg += tmpl;
    msg += "\n";
  }
  long lineno;
  std::size_t length;
  std::string content;
  if (cpp_last_line_info(cont, lineno, length, &content)) {
    std::ostringstream oss;
    if (past_end) {
      oss << "End of the data reached after line " << lineno << "\n";
    } else {
      oss << "Line " << lineno << ": \"" << content << "\"\n";
      std::string hint = cpp_long_line_hint(lineno, length);
      if (! hint.empty()) oss << hint << "\n";
    }
    msg += oss.str();
  }
  if (! msg.empty() && msg[msg.size()-1] == '\n') msg.erase(msg.size()-1);
  throw std::runtime_error(cpp_escape_message(msg.c_str()));
}


// With accept_non_ascii=false, raise an error at the first character of
// a line outside printable ASCII (codes 32 to 126). size is the length
// of the line content (without the line ending and without the blanks
// added to a short line, see cpp_pad_short_line), which has just been
// read from cont. The error is raised by the Python function shared
// with EndfParserPy, so that both parsers give the same message.
inline void cpp_check_line_ascii(
  const CppLine& line, std::size_t size, std::istream& cont, ParsingOptions &parse_opts
) {
  if (parse_opts.accept_non_ascii) return;
  for (std::size_t i = 0; i < size; i++) {
    unsigned char c = static_cast<unsigned char>(line[i]);
    if (c >= 32 && c <= 126) continue;
    long lineno = 0;
    std::size_t length;
    cpp_last_line_info(cont, lineno, length);
    // the MAT/MF/MT columns (the line is at least 75 characters long)
    // (read leniently: the error is about the character)
    int mat = cpp_read_lenient_int_field(line.data(), 66, 4);
    int mf = cpp_read_lenient_int_field(line.data(), 70, 2);
    int mt = cpp_read_lenient_int_field(line.data(), 72, 3);
    cpp_text_encoding_function("raise_non_ascii_line_error")(
      lineno, i + 1, mat, mf, mt, static_cast<int>(c)
    );
    throw std::logic_error("unexpected return from raise_non_ascii_line_error");
  }
}


// The line is cleared first so that a failed read leaves an empty line.
inline void cpp_read_raw_line(CppLine& line, std::istream& cont) {
  line.clear();
  cpp_getline(cont, line);
  cpp_pad_short_line(line);
}


inline std::string cpp_read_raw_line(std::istream& cont) {
  CppLine line;
  cpp_read_raw_line(line, cont);
  return line.str();
}


// content_size (if given) receives the length of the line before the
// padding of a short line (see cpp_pad_short_line).
// The MAT/MF/MT fields of every line must hold numbers (see
// cpp_read_mat_number). The MAT/MF/MT numbers of a line are compared
// with mat, mf and mt with validate_control_records=true and, if check_long_line is true, for a
// line longer than 80 columns: such a line is not valid, and a non-ASCII
// character that occupies several bytes (e.g. in UTF-8) in a TEXT record
// shifts the MAT/MF/MT columns, which EndfParserPy, which divides a file
// into sections by these columns, also detects.
inline void cpp_read_line(
  CppLine& line, std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts,
  std::size_t* content_size = nullptr, bool check_long_line = true
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
  std::size_t size = cpp_pad_short_line(line);
  if (content_size != nullptr) *content_size = size;
  cpp_check_line_ascii(line, size, cont, parse_opts);

  if (parse_opts.validate_control_records || (check_long_line && size > 80)) {
    int curmat = cpp_read_mat_number(line.data());
    int curmf = cpp_read_mf_number(line.data());
    int curmt = cpp_read_mt_number(line.data());
    if (curmat != mat)
      throw_mismatch_error("MAT", mat, curmat);
    if (curmf != mf)
      throw_mismatch_error("MF", mf, curmf);
    if (curmt != mt)
      throw_mismatch_error("MT", mt, curmt);
  } else {
    // the MAT/MF/MT fields must hold numbers also if they are not
    // compared, as EndfParserPy reads them for every line
    cpp_check_control_fields(line.data());
  }
}


inline std::string cpp_read_line(
  std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts
) {
  CppLine line(parse_opts);
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  return line.str();
}


// Whether the next line of the stream is a SEND record by its control
// fields (MF not 0, MT 0); blank lines before it are skipped with
// ignore_blank_lines. A blank line otherwise counts as a SEND record, so
// that its reading reports it. The position of the stream is not changed.
inline bool cpp_next_is_send(std::istream& cont, ParsingOptions &parse_opts) {
  std::streampos pos = cont.tellg();
  CppLine line(parse_opts);
  bool is_send = false;
  while (cpp_getline(cont, line)) {
    if (cpp_is_blank_line(line)) {
      if (parse_opts.ignore_blank_lines) continue;
      is_send = true;
      break;
    }
    cpp_pad_short_line(line);
    is_send = (cpp_read_mt_number(line.data()) == 0 && cpp_read_mf_number(line.data()) != 0);
    break;
  }
  cont.clear();
  cont.seekg(pos);
  return is_send;
}


// With ignore_send_records, a section need not end with a SEND record:
// if the next line is not one (e.g. the first line of the next section,
// a FEND record or the end of the data), it is not read. A SEND record
// is checked as without this option.
inline void cpp_read_send(std::istream& cont, int mat, int mf, ParsingOptions &parse_opts) {
  if (parse_opts.ignore_send_records && ! cpp_next_is_send(cont, parse_opts)) {
    return;
  }
  CppLine line(parse_opts);
  cpp_read_line(line, cont, mat, mf, 0, parse_opts);
  int mtnum = cpp_read_mt_number(line.data());
  if (cpp_read_field<DOUBLE_TYPE>(line.data(), 0, parse_opts) != 0.0 ||
    cpp_read_field<DOUBLE_TYPE>(line.data(), 1, parse_opts) != 0.0 ||
    cpp_read_field<int>(line.data(), 2, parse_opts) != 0 ||
    cpp_read_field<int>(line.data(), 3, parse_opts) != 0 ||
    cpp_read_field<int>(line.data(), 4, parse_opts) != 0 ||
    cpp_read_field<int>(line.data(), 5, parse_opts) != 0 ||
    mtnum != 0) {

    // the line is added by cpp_rethrow_parse_error
    throw std::runtime_error("Expected SEND record does not contain one!\n");
  }
  if (parse_opts.validate_control_records) {
    int curmat = cpp_read_mat_number(line.data());
    int curmf = cpp_read_mf_number(line.data());
    if (curmat != mat)
      throw_mismatch_error("MAT", mat, curmat);
    if (curmf != mf)
      throw_mismatch_error("MF", mf, curmf);
  }
}


inline bool cpp_is_fend_record(const CppLine& line, int mat, ParsingOptions &parse_opts) {
  int curmat = cpp_read_mat_number(line.data());
  if (mat != curmat && parse_opts.validate_control_records) {
      throw_mismatch_error("MAT", mat, curmat);
  }
  int mf = cpp_read_mf_number(line.data());
  int mt = cpp_read_mt_number(line.data());
  double c1 = cpp_read_field<DOUBLE_TYPE>(line.data(), 0, parse_opts);
  double c2 = cpp_read_field<DOUBLE_TYPE>(line.data(), 1, parse_opts);
  int n1 = cpp_read_field<int>(line.data(), 2, parse_opts);
  int n2 = cpp_read_field<int>(line.data(), 3, parse_opts);
  int l1 = cpp_read_field<int>(line.data(), 4, parse_opts);
  int l2 = cpp_read_field<int>(line.data(), 5, parse_opts);
  bool cond = (c1 == 0.0 && c2 == 0.0 && n1 == 0 && n2 == 0);
  cond &= (l1 == 0 && l2 == 0 && mf == 0 && mt == 0);
  return cond;
}


// A SEND record outside a section, which is accepted with
// ignore_send_records: MF not 0, MT 0 and the fields 1-6 zero.
inline bool cpp_is_send_record(const CppLine& line, ParsingOptions &parse_opts) {
  int mf = cpp_read_mf_number(line.data());
  int mt = cpp_read_mt_number(line.data());
  if (mf == 0 || mt != 0) return false;
  double c1 = cpp_read_field<DOUBLE_TYPE>(line.data(), 0, parse_opts);
  double c2 = cpp_read_field<DOUBLE_TYPE>(line.data(), 1, parse_opts);
  int n1 = cpp_read_field<int>(line.data(), 2, parse_opts);
  int n2 = cpp_read_field<int>(line.data(), 3, parse_opts);
  int l1 = cpp_read_field<int>(line.data(), 4, parse_opts);
  int l2 = cpp_read_field<int>(line.data(), 5, parse_opts);
  return (c1 == 0.0 && c2 == 0.0 && n1 == 0 && n2 == 0 && l1 == 0 && l2 == 0);
}


inline bool cpp_is_mend_record(const CppLine& line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.data());
  bool cond = cpp_is_fend_record(line, 0, parse_opts);
  cond &= (mat == 0);
  return cond;
}


inline bool cpp_is_tend_record(const CppLine& line, ParsingOptions &parse_opts) {
  int mat = cpp_read_mat_number(line.data());
  bool cond = cpp_is_fend_record(line, -1, parse_opts);
  cond &= (mat == -1);
  return cond;
}


// The bulk form of the reading of the body of a LIST record (see the row
// kernels above and ListBulkForm in endf2cpp_aux.py). The body is read
// in two steps:
//
// 1. CppListBody, constructed with the number of values NPL of the body,
//    reads the lines of the body (cpp_read_line, i.e. with all checks of
//    a line) and converts their fields with the selected row kernel into
//    a buffer of NPL doubles. It stops at the first field the kernel
//    does not convert (e.g. a malformed field, or a form that only the
//    general path of endfstr2float handles) and at the first line whose
//    reading fails, whose exception is kept. nconv() values are
//    converted, which are those of the first nconv() fields of the body
//    (the value of field j of line l of the body is the value 6*l+j).
//    A body of at least two lines whose lines cpp_read_line would read
//    without error and without changing them, under any options, is read
//    as one byte range instead (see cpp_list_body_range and fast_body):
//    the lines are checked together, the fields are converted at fixed
//    offsets in one loop, and the stream, the line and the state of the
//    object are left exactly as by the line-by-line reading. Any other
//    body is read line by line, which gives today's errors.
//
// 2. The values are delivered from the buffer, either by strided copies
//    into the variables (if the code generator has proven the layout of
//    the body regular, all NPL values are converted and the number of
//    values given by the layout is NPL, see ListBulkForm), or by the code
//    of the per-field form, in which each reading of a field of the body
//    takes the value from the buffer if it is converted (field) and the
//    reading of the next line only reads a line not read in step 1
//    (next_line), where it raises the kept exception for the line whose
//    reading failed. Thus the values, and the order of the checks and
//    errors, are those of the per-field form.
//
// An error raised while the values are delivered must be reported for
// the line of the field being read, as by the per-field form, which
// reads the lines one after the other, whereas step 1 has read all lines:
// the error message adds the line last read from the stream (see
// cpp_rethrow_parse_error). Before such an error is propagated,
// reposition() therefore reads the lines of the body again from its
// beginning up to the line of the field. This is only done for errors, so
// the beginning of the body is kept (as a position in the memory of the
// input, as the bulk form is only used for input held in memory, see
// cpp_list_bulk).
//
// The lines are read as views, as in the per-field form; their lengths
// may differ (the reading of a line does not assume a fixed length).
//
// A switch from a vector tier to the scalar loop within a body, for
// bodies whose fields the vector path mostly leaves (e.g. decimals
// without exponent), was measured and not taken: it gave no gain on the
// files concerned (see the description of the change).

// Whether the body of a LIST record is read in the bulk form: a row
// kernel is selected, the input is held in memory (see CppLine), and the
// original strings of the values are not kept (preserve_value_strings,
// which needs the strings of the fields). `strided` tells whether the
// code generator has found a regular layout of the body (strided copies):
// a body without one is only read in the bulk form if all bodies are
// (list_all of cpp_row_selection), as its delivery by the code of the
// per-field form is not faster than the per-field form with the scalar
// row kernel.
inline bool cpp_list_bulk(const std::istream& cont, const ParsingOptions& parse_opts, bool strided) {
  return cpp_float_row_kernel() != nullptr
    && (strided || cpp_row_state<>::list_all)
    && ! parse_opts.preserve_value_strings
    && parse_opts.memory_input != nullptr
    && cont.rdbuf() == parse_opts.memory_input;
}


// Numbers of LIST bodies read in the bulk form, delivered by strided
// copies and by the code of the per-field form, the number of bodies
// whose conversion stopped before the end, and the numbers of bodies of
// at least two lines read as one byte range and line by line (see
// CppListBody), only for tests.
struct cpp_list_bulk_counts {
  unsigned long long strided;
  unsigned long long looped;
  unsigned long long stopped;
  unsigned long long byte_range;
  unsigned long long line_by_line;
  // of the strided bodies, those with row loops (one copy per row), their
  // values and the iterations of their row loops
  unsigned long long row_bodies;
  unsigned long long row_values;
  unsigned long long row_rows;
};

inline cpp_list_bulk_counts& cpp_list_bulk_counter() {
  static cpp_list_bulk_counts counts = {0, 0, 0, 0, 0, 0, 0, 0};
  return counts;
}


// thrown (and caught) when a strided delivery cannot be done; the values
// are then delivered by the code of the per-field form
struct cpp_list_bulk_fallback {};


// The memory for the values of a LIST body longer than the buffer of
// CppListBody, kept for the following bodies (one per module), so that
// it is not allocated (and its pages not faulted in) for each body. It
// is used by one CppListBody at a time (busy); a body read while it is
// in use (not the case when parsing, which holds the GIL and reads one
// body after the other) gets memory of its own.
struct cpp_list_body_store {
  std::unique_ptr<double[]> data;
  std::size_t capacity = 0;
  std::atomic<bool> busy{false};
};

inline cpp_list_body_store& cpp_list_body_shared_store() {
  static cpp_list_body_store store;
  return store;
}


// Whether the nlines lines at p (the read position of the input held in
// memory, which ends at e) are lines that cpp_read_line reads without
// error and without changing them under any options, as the lines of
// the body of a LIST record of the section with the control columns cc
// (see cpp_memory_streambuf::control_columns): the first line has a
// length L of 75 to 80 characters without its line ending, which is
// "\n" or "\r\n"; every line has this length and line ending and lies
// completely before e; all characters of the lines are printable ASCII
// (32 to 126: no blank line, no other line break or carriage return in
// a line, nothing accept_non_ascii=False would reject); and columns 67
// to 75 of every line are cc (the MAT/MF/MT numbers in the form in
// which they are written; validate_control_records and lines longer
// than 80 characters check them). Sets L and the stride of the lines (L
// plus the line ending). A body in any other form is read line by line.
inline bool cpp_list_body_range(
  const char* p, const char* e, int nlines, const char* cc,
  std::size_t& len, std::size_t& stride
) {
  const std::size_t avail = static_cast<std::size_t>(e - p);
  const char* nl = static_cast<const char*>(std::memchr(p, '\n', avail < 82 ? avail : 82));
  if (nl == nullptr) return false;
  const std::size_t raw = static_cast<std::size_t>(nl - p);
  const bool crlf = raw > 0 && p[raw - 1] == '\r';
  len = crlf ? raw - 1 : raw;
  if (len < 75 || len > 80) return false;
  stride = raw + 1;
  if (avail / stride < static_cast<std::size_t>(nlines)) return false;
  // 8 bytes at a time: a byte below 32 or above 126 sets the high bit of
  // its byte in acc (and possibly of other bytes, which is no matter)
  const std::uint64_t ones = 0x0101010101010101ULL;
  const std::uint64_t high = 0x8080808080808080ULL;
  std::uint64_t ref;
  std::memcpy(&ref, cc, 8);
  const char ref8 = cc[8];
  const char end0 = crlf ? '\r' : '\n';
  const std::size_t last = len - 8;
  std::uint64_t bad = 0;
  for (int l = 0; l < nlines; l++) {
    const char* q = p + static_cast<std::size_t>(l) * stride;
    std::uint64_t w, acc = 0;
    for (std::size_t k = 0; k < 72; k += 8) {
      std::memcpy(&w, q + k, 8);
      acc |= ((w - 0x20 * ones) & ~w) | (w + ones) | w;
    }
    std::memcpy(&w, q + last, 8);
    acc |= ((w - 0x20 * ones) & ~w) | (w + ones) | w;
    std::uint64_t c;
    std::memcpy(&c, q + 66, 8);
    bad |= (acc & high) | (c ^ ref)
      | static_cast<std::uint64_t>(q[74] != ref8)
      | static_cast<std::uint64_t>(q[len] != end0)
      | static_cast<std::uint64_t>(crlf && q[len + 1] != '\n');
  }
  return bad == 0;
}


class CppListBody {
  public:
    CppListBody(
      CppLine& line, std::istream& cont, int npl,
      int mat, int mf, int mt, ParsingOptions& parse_opts
    ) : buf_(small_), cap_(small_size), store_(nullptr), npl_(npl), nconv_(0),
        good_(0), visited_(0), failed_(false),
        start_(parse_opts.memory_input->current()), state_(cont.rdstate()) {
      if (npl <= 0) return;
      const cpp_row_kernel_fn kernel = cpp_float_row_kernel();
      const unsigned flags = parse_opts.accept_d_exponent ? CPP_ROW_ACCEPT_D_EXPONENT : 0u;
      const int nlines = (npl - 1) / 6 + 1;
      // a body of one line is read by the loop (as one range, it would
      // only add the checks of the range)
      if (nlines >= 2) {
        if (fast_body(line, cont, npl, nlines, mat, mf, mt, parse_opts, kernel)) {
          cpp_list_bulk_counter().byte_range++;
          return;
        }
        cpp_list_bulk_counter().line_by_line++;
      }
      for (int l = 0; l < nlines; l++) {
        try {
          cpp_read_line(line, cont, mat, mf, mt, parse_opts);
        } catch (...) {
          // raised by next_line when the line is read in the per-field form
          failed_ = true;
          error_ = std::current_exception();
          cpp_list_bulk_counter().stopped++;
          return;
        }
        good_ = l + 1;
        const int pos = 6 * l;
        if (static_cast<std::size_t>(pos) + 6 > cap_) grow(pos + 6);
        const int remaining = npl - pos;
        const unsigned want = remaining >= 6 ? 0x3Fu : (1u << remaining) - 1u;
        const unsigned done = kernel(line.data(), want, flags, buf_ + pos);
        if (done != want) {
          int j = 0;
          while ((done >> j) & 1u) j++;
          nconv_ = pos + j;
          cpp_list_bulk_counter().stopped++;
          return;
        }
        nconv_ = pos + (remaining >= 6 ? 6 : remaining);
      }
    }

    ~CppListBody() {
      if (store_ != nullptr) store_->busy.store(false);
    }

    // whether all values of the body are converted (also if NPL <= 0)
    bool complete() const { return ! failed_ && nconv_ == (npl_ > 0 ? npl_ : 0); }

    // the beginning of the body in the memory of the input
    const char* start() const { return start_; }

    int nconv() const { return nconv_; }

    const double* values() const { return buf_; }

    // the converted value i (i < nconv())
    template<typename T>
    T value(long long i) const { return T(buf_[i]); }

    // the value i of the body, the field fieldnum of the line str, as
    // cpp_read_field reads it (the field is only read if not converted)
    template<typename T>
    T field(int i, const char* str, const char fieldnum, ParsingOptions& parse_opts) const {
      if (i < nconv_) return T(buf_[i]);
      return cpp_read_field<T>(str, fieldnum, parse_opts);
    }

    // the reading of the next line of the body by the per-field form
    void next_line(
      CppLine& line, std::istream& cont, int mat, int mf, int mt, ParsingOptions& parse_opts
    ) {
      const int l = visited_++;
      if (l < good_) return;
      if (failed_ && l == good_) std::rethrow_exception(error_);
      cpp_read_line(line, cont, mat, mf, mt, parse_opts);
    }

    // To be called for an error raised while the per-field form has
    // consumed `consumed` values: the stream is positioned after the line
    // of the next value, as the per-field form has read it, unless this
    // is already the case (the line is the last one read in step 1, the
    // one whose reading failed, or a line read by next_line).
    void reposition(
      int consumed, CppLine& line, std::istream& cont, int mat, int mf, int mt,
      ParsingOptions& parse_opts
    ) {
      if (npl_ <= 0) return;
      const int target = (consumed < npl_ ? consumed : npl_ - 1) / 6;
      if (target + (failed_ ? 0 : 1) >= good_) return;
      try {
        parse_opts.memory_input->move_to(start_);
        cont.clear(state_);
        for (int l = 0; l <= target; l++) {
          cpp_read_line(line, cont, mat, mf, mt, parse_opts);
        }
      } catch (...) {
        // not raised: these lines have been read without error before
      }
    }

  private:
    enum { small_size = 48 };

    // Reads the body as one byte range of the input held in memory if
    // cpp_list_body_range accepts it (otherwise returns false, nothing is
    // changed), and leaves the stream, the line, good_ and nconv_ as the
    // line-by-line loop of the constructor leaves them: the position is
    // after the last line read by the loop (the last line of the body, or
    // the line with the first value not converted), the line is a view of
    // it, and the stream is good (each line has a line ending).
    bool fast_body(
      CppLine& line, std::istream& cont, int npl, int nlines, int mat, int mf, int mt,
      ParsingOptions& parse_opts, cpp_row_kernel_fn kernel
    ) {
      if (! cont.good()) return false;
      cpp_memory_streambuf* mb = parse_opts.memory_input;
      const char* cc = mb->control_columns(mat, mf, mt);
      if (cc == nullptr) return false;
      const char* p = mb->current();
      std::size_t len, stride;
      if (! cpp_list_body_range(p, mb->end(), nlines, cc, len, stride)) return false;
      const std::size_t need = 6 * static_cast<std::size_t>(nlines);
      if (need > cap_) grow(need);
      const int n = cpp_list_convert(p, stride, npl, kernel, parse_opts.accept_d_exponent, buf_);
      nconv_ = n;
      const int stop_line = n >= npl ? nlines - 1 : n / 6;
      good_ = stop_line + 1;
      mb->move_to(p + static_cast<std::size_t>(good_) * stride);
      line.set_view(p + static_cast<std::size_t>(stop_line) * stride, len);
      cpp_line_read_counter().views += static_cast<unsigned long long>(good_);
      if (n < npl) cpp_list_bulk_counter().stopped++;
      return true;
    }

    void grow(std::size_t needed) {
      // the buffer grows with the lines read, at first to the size of
      // the body or at most 2^20 values, so that a corrupt NPL does not
      // lead to a huge allocation
      std::size_t cap = cap_;
      const std::size_t first = std::min<std::size_t>(
        static_cast<std::size_t>(npl_) + 6, std::size_t(1) << 20);
      if (cap < first) cap = first;
      while (cap < needed) cap *= 2;
      if (store_ == nullptr && large_ == nullptr) {
        cpp_list_body_store& store = cpp_list_body_shared_store();
        if (! store.busy.exchange(true)) store_ = &store;
      }
      double* target;
      if (store_ != nullptr) {
        if (store_->capacity < cap) {
          std::unique_ptr<double[]> larger(new double[cap]);
          if (buf_ == store_->data.get()) {
            std::memcpy(larger.get(), buf_, sizeof(double) * static_cast<std::size_t>(nconv_));
          }
          store_->data.swap(larger);
          store_->capacity = cap;
        }
        target = store_->data.get();
        cap = store_->capacity;
      } else {
        std::unique_ptr<double[]> larger(new double[cap]);
        if (buf_ == large_.get()) {
          std::memcpy(larger.get(), buf_, sizeof(double) * static_cast<std::size_t>(nconv_));
        }
        large_.swap(larger);
        target = large_.get();
      }
      if (buf_ == small_) {
        std::memcpy(target, small_, sizeof(double) * static_cast<std::size_t>(nconv_));
      }
      buf_ = target;
      cap_ = cap;
    }

    double small_[small_size];
    // the memory of a longer body: the shared store, or memory of its own
    std::unique_ptr<double[]> large_;
    double* buf_;
    std::size_t cap_;
    cpp_list_body_store* store_;
    int npl_;
    int nconv_;
    // the number of lines read without error in step 1, and whether the
    // reading of the next line failed (with the exception error_)
    int good_;
    // the number of lines of the body read by the per-field form
    int visited_;
    bool failed_;
    std::exception_ptr error_;
    // the beginning of the body in the memory of the input, and the
    // state of the stream there
    const char* start_;
    std::ios_base::iostate state_;

    CppListBody(const CppListBody&) = delete;
    CppListBody& operator=(const CppListBody&) = delete;
};


// The position in the input after the line of the body of a LIST record
// read by CppListBody (whose lines have all been read) that holds the
// value with the given index; the lines are counted as cpp_read_line
// reads them, i.e. without the blank lines skipped with
// ignore_blank_lines.
inline std::streamoff cpp_body_value_end(
  const CppListBody& body, int index, const ParsingOptions& parse_opts
) {
  const cpp_memory_streambuf* mb = parse_opts.memory_input;
  const char* p = body.start();
  const char* e = mb->end();
  const int target = index / 6;
  int l = 0;
  while (p < e) {
    const char* nl = static_cast<const char*>(std::memchr(p, '\n', e - p));
    const char* line_end = nl != nullptr ? nl : e;
    std::size_t len = static_cast<std::size_t>(line_end - p);
    if (len > 0 && p[len-1] == '\r') len--;
    const bool blank = cpp_is_blank_line(p, len);
    p = nl != nullptr ? nl + 1 : e;
    if (blank && parse_opts.ignore_blank_lines) continue;
    if (l == target) break;
    l++;
  }
  return static_cast<std::streamoff>(p - mb->begin());
}


// The position of the stream being parsed (after the line last read).
inline std::streamoff cpp_tolerated_stream_offset(
  std::istream& cont, const ParsingOptions& parse_opts
) {
  const cpp_memory_streambuf* mb = parse_opts.memory_input;
  if (mb != nullptr && cont.rdbuf() == mb) {
    return static_cast<std::streamoff>(mb->current() - mb->begin());
  }
  // tellg fails if a flag is set, e.g. eofbit after the last line
  std::ios_base::iostate state = cont.rdstate();
  cont.clear();
  std::streamoff pos = static_cast<std::streamoff>(cont.tellg());
  cont.clear(state);
  return pos;
}


CPP_TOLERATED_COLD void cpp_record_tolerated(
  ParsingOptions& parse_opts, char kind, int fieldnum, const char* exprstr,
  double expected, bool expected_int, double actual, bool actual_int,
  const CppListBody* body, int body_index
) {
  cpp_tolerated_log* log = parse_opts.tolerated;
  if (log == nullptr) return;
  cpp_tolerated_mismatch m;
  m.kind = kind;
  m.fieldnum = fieldnum;
  m.in_body = body_index >= 0;
  m.exprstr = exprstr;
  m.expected = expected;
  m.actual = actual;
  m.expected_int = expected_int;
  m.actual_int = actual_int;
  m.body_start = nullptr;
  m.body_index = body_index;
  if (body != nullptr) {
    // A value delivered by CppListBody is checked again by the code of
    // the per-field form if the strided delivery is given up after the
    // checks (see ListBulkForm in endf2cpp_aux.py); it is recorded once.
    // The mismatches of a body are the last ones recorded.
    const char* start = body->start();
    for (auto it = log->entries.rbegin();
         it != log->entries.rend() && it->body_start == start; ++it) {
      if (it->body_index == body_index && it->exprstr == exprstr) return;
    }
    m.body_start = start;
    m.end_pos = cpp_body_value_end(*body, body_index, parse_opts);
  } else {
    m.end_pos = cpp_tolerated_stream_offset(*log->stream, parse_opts);
  }
  log->entries.push_back(m);
}


inline py::object cpp_tolerated_pyvalue(double value, bool is_int) {
  if (is_int) return py::int_(static_cast<long long>(value));
  return py::float_(value);
}


// Append the mismatches recorded in log while parsing cont (see
// cpp_record_tolerated) to the Python list `tolerated`, as tuples (MAT,
// MF, MT, field (0 to 5, -1 if unknown), whether in the body of a
// record, expression of the field, kind ('zero', 'number' or 'varspec'),
// line (counting from 1), expected value, actual value), in the order of
// their positions in the input and, within a line, of the fields (as
// EndfParserPy finds them; the checks of the strided delivery of a LIST
// body visit the values in another order). The line and the MAT/MF/MT
// numbers of a
// mismatch are those of the line holding the value, determined in one
// pass over the input, which is only read for this if there are
// mismatches.
inline void cpp_report_tolerated(
  cpp_tolerated_log& log, std::istream& cont, py::object tolerated
) {
  if (log.entries.empty() || tolerated.is_none()) return;
  const std::size_t n = log.entries.size();
  std::vector<std::size_t> order(n);
  for (std::size_t i = 0; i < n; i++) order[i] = i;
  std::stable_sort(order.begin(), order.end(), [&log](std::size_t a, std::size_t b) {
    const cpp_tolerated_mismatch& x = log.entries[a];
    const cpp_tolerated_mismatch& y = log.entries[b];
    if (x.end_pos != y.end_pos) return x.end_pos < y.end_pos;
    return x.body_index < y.body_index;
  });
  // the line holding the value ends before end_pos: its number is one
  // more than the number of line breaks before its last character, and
  // it starts after the last of them
  std::vector<long> line_numbers(n);
  std::vector<std::streamoff> line_starts(n);
  // the input in memory is read directly, a file in chunks
  const cpp_memory_streambuf* mb = log.memory;
  const bool in_memory = mb != nullptr && cont.rdbuf() == mb;
  cont.clear();
  cont.seekg(0);
  std::vector<char> buf(in_memory ? 0 : 1 << 16);
  std::streamoff done = 0;
  long breaks = 0;
  std::streamoff last_start = 0;
  for (std::size_t k = 0; k < n; k++) {
    const std::size_t i = order[k];
    const std::streamoff target = log.entries[i].end_pos - 1;
    while (done < target) {
      const char* chunk;
      std::streamoff got = target - done;
      if (in_memory) {
        const std::streamoff avail = mb->end() - mb->begin() - done;
        if (got > avail) got = avail;
        chunk = mb->begin() + done;
      } else {
        if (! cont) break;
        if (got > static_cast<std::streamoff>(buf.size())) got = buf.size();
        cont.read(buf.data(), static_cast<std::streamsize>(got));
        got = cont.gcount();
        chunk = buf.data();
      }
      if (got <= 0) break;
      const char* p = chunk;
      const char* e = chunk + got;
      while ((p = static_cast<const char*>(std::memchr(p, '\n', e - p))) != nullptr) {
        breaks++;
        p++;
        last_start = done + (p - chunk);
      }
      done += got;
    }
    line_numbers[i] = breaks + 1;
    line_starts[i] = last_start;
  }
  static const char* kinds[] = {"zero", "number", "varspec"};
  py::list result = tolerated.cast<py::list>();
  std::string line;
  for (std::size_t k = 0; k < n; k++) {
    const std::size_t i = order[k];
    const cpp_tolerated_mismatch& m = log.entries[i];
    cont.clear();
    cont.seekg(line_starts[i]);
    line.clear();
    std::getline(cont, line);
    if (! line.empty() && line[line.size()-1] == '\r') line.erase(line.size()-1);
    if (line.size() < 75) line.append(75 - line.size(), ' ');
    const int mat = cpp_read_lenient_int_field(line.data(), 66, 4);
    const int mf = cpp_read_lenient_int_field(line.data(), 70, 2);
    const int mt = cpp_read_lenient_int_field(line.data(), 72, 3);
    const char* kind = kinds[m.kind == 'z' ? 0 : (m.kind == 'n' ? 1 : 2)];
    result.append(py::make_tuple(
      mat, mf, mt, m.fieldnum, m.in_body, m.exprstr, kind, line_numbers[i],
      cpp_tolerated_pyvalue(m.expected, m.expected_int),
      cpp_tolerated_pyvalue(m.actual, m.actual_int)
    ));
  }
}


// The number of iterations of a loop over the indices a to b, and the
// number of values of n iterations of z values each, for the layout of
// the body of a LIST record (see ListBulkForm in endf2cpp_aux.py); the
// latter saturates at 2^40, so that the sums of these numbers, which are
// compared with NPL, do not overflow for any bounds.
inline long long cpp_list_loop_count(int a, int b) {
  return b >= a ? static_cast<long long>(b) - a + 1 : 0;
}

inline long long cpp_list_size(long long n, long long z) {
  const long long cap = 1LL << 40;
  if (n == 0 || z == 0) return 0;
  if (n >= cap || z >= cap || n > cap / z) return cap;
  return n * z;
}


// The strided copy of values of the body of a LIST record into an array:
// the values src[sum_k i_k * src_step[k]] for 0 <= i_k < count[k] go to
// dst[sum_k i_k * dst_step[k]], k = 0 .. rank-1.
template<typename T>
inline void cpp_copy_strided(
  T* dst, const double* src, int rank,
  const long long* count, const long long* dst_step, const long long* src_step
) {
  if (rank == 1) {
    const long long n = count[0], ds = dst_step[0], ss = src_step[0];
    for (long long i = 0; i < n; i++) dst[i * ds] = T(src[i * ss]);
    return;
  }
  for (long long i = 0; i < count[0]; i++) {
    cpp_copy_strided(
      dst + i * dst_step[0], src + i * src_step[0], rank - 1,
      count + 1, dst_step + 1, src_step + 1
    );
  }
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
  CppLine line(parse_opts);
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i += 2) {
    a.push_back(cpp_read_field<T>(line.data(), j++, parse_opts));
    b.push_back(cpp_read_field<T>(line.data(), j++, parse_opts));
    if (j > 5 && i+2 < numel) {
      cpp_read_line(line, cont, mat, mf, mt, parse_opts);
      j = 0;
    }
  }
}


// cpp_read_pairs for float values with the row kernel `kernel` (the
// bulk form of the body of a TAB1 record): one kernel call per line
// converts its fields, and a field the kernel leaves is read with
// cpp_read_field; the same lines are consumed in the same order, and the
// same values and errors result. Not for preserve_value_strings.
template<typename T>
inline void cpp_read_pairs_bulk(
  std::istream& cont, const int n, std::vector<T>& a, std::vector<T>& b,
  int mat, int mf, int mt, ParsingOptions &parse_opts, cpp_row_kernel_fn kernel
) {
  const int numel = 2*n;
  if (numel <= 0) return;
  a.reserve(cpp_reserve_size(n));
  b.reserve(cpp_reserve_size(n));
  const unsigned flags = parse_opts.accept_d_exponent ? CPP_ROW_ACCEPT_D_EXPONENT : 0u;
  CppLine line(parse_opts);
  double v[6];
  for (int i=0; i < numel; i += 6) {
    cpp_read_line(line, cont, mat, mf, mt, parse_opts);
    const int m = numel - i < 6 ? numel - i : 6;
    const unsigned want = (1u << m) - 1u;
    const unsigned done = kernel(line.data(), want, flags, v);
    if (done == want) {
      for (int j=0; j < m; j += 2) {
        a.push_back(T(v[j]));
        b.push_back(T(v[j+1]));
      }
    } else {
      for (int j=0; j < m; j += 2) {
        a.push_back(((done >> j) & 1u) ? T(v[j]) : cpp_read_field<T>(line.data(), j, parse_opts));
        b.push_back(((done >> (j+1)) & 1u) ? T(v[j+1]) : cpp_read_field<T>(line.data(), j+1, parse_opts));
      }
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
  CppLine line(parse_opts);
  cpp_read_line(line, cont, mat, mf, mt, parse_opts);
  for (int i=0; i < numel; i++) {
    res.push_back(cpp_read_field<T>(line.data(), j++, parse_opts));
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
  // the form of the reading of the float values is chosen once per record
  const cpp_row_kernel_fn row_kernel = cpp_float_row_kernel();
  if (row_kernel == nullptr || parse_opts.preserve_value_strings) {
    cpp_read_pairs<DOUBLE_TYPE>(cont, np, tab_body.X, tab_body.Y, mat, mf, mt, parse_opts);
  } else {
    cpp_read_pairs_bulk<DOUBLE_TYPE>(
      cont, np, tab_body.X, tab_body.Y, mat, mf, mt, parse_opts, row_kernel
    );
  }
  return tab_body;
}


// Whether a line that is not blank follows in the stream (blank lines
// are skipped with ignore_blank_lines). The position of the stream is
// not changed.
inline bool cpp_lines_follow(std::istream& cont, ParsingOptions &parse_opts) {
  std::streampos pos = cont.tellg();
  CppLine line(parse_opts);
  bool found = false;
  while (cpp_getline(cont, line)) {
    if (! cpp_is_blank_line(line) || ! parse_opts.ignore_blank_lines) {
      found = true;
      break;
    }
  }
  cont.clear();
  cont.seekg(pos);
  return found;
}


// The lines of a section are returned as Python strings (see
// cpp_bytes_to_pystr).
inline py::list read_section_verbatim(
    int mat, int mf, int mt, std::istream& cont, bool is_first, ParsingOptions &parse_opts
) {
  std::streampos curpos;
  CppLine line(parse_opts);
  std::string verbatim_line;
  py::list secvec;
  int curmf;
  int curmt;
  std::size_t content_size;
  // with ignore_send_records, the section need not end with a SEND
  // record (see cpp_read_send), also at the end of the data
  const bool send_optional = parse_opts.ignore_send_records && ! is_first;
  bool at_end = false;
  while (! cont.eof()) {
    if (send_optional && ! cpp_lines_follow(cont, parse_opts)) {
      at_end = true;
      break;
    }
    // the MF/MT numbers of every line are checked below
    cpp_read_line(line, cont, mat, mf, mt, parse_opts, &content_size, false);
    // a blank MF/MT field (e.g. of a tape header) reads as zero, as in
    // EndfParserPy and everywhere else in this parser
    curmf = cpp_read_mf_number(line.data());
    curmt = cpp_read_mt_number(line.data());
    if (curmf != mf || curmt != mt) break;
    // the line as read (without the blanks added to a short line), with
    // the newline for compatibility with the Python parser
    verbatim_line.assign(line.data(), content_size);
    verbatim_line.push_back('\n');
    secvec.append(cpp_bytes_to_pystr(verbatim_line));
    curpos = cont.tellg();
  }
  if (send_optional) {
    // a line that is not a SEND record (MF not 0, MT 0) is not read
    if (! at_end && (curmf == 0 || curmt != 0)) {
      cont.clear();
      cont.seekg(curpos);
    }
  } else if (! is_first && (curmf != mf || curmt != 0)) {
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
