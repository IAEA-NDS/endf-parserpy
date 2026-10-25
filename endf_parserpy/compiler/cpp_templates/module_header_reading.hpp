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
  bool accept_non_ascii;
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
    true,   // accept_non_ascii
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


// Exact conversion of mant * 10^k for decimal exponents k below -22, the
// range of the single division used below, i.e. of values below about
// 1e-16, which occur in many ENDF-6 files (14% of the float fields of
// tsl-HinH2O of ENDF/B-VIII.0). It uses the algorithm of Eisel and Lemire
// as in the fast_float library (D. Lemire, "Number parsing at a gigabyte
// per second", Software: Practice and Experience 51(8), 2021): the
// significand, shifted so that its most significant bit is set, is
// multiplied with a 128-bit approximation of 5^k; the upper bits of the
// product give the significand of the double, its exponent follows from
// k and the shift. The result is the correctly rounded double (round half
// to even), subnormal numbers and underflow to zero included, i.e. the
// same value as std::strtod. The algorithm is valid for any significand
// below 2^64; the callers pass at most 15 decimal digits (an ENDF-6 field
// of 11 characters holds at most 10). An exact tie between two doubles is
// impossible for k < -22, as its decimal significand would need more
// than 20 digits.
//
// The table holds the entries of fast_float for 5^q, q = -342 ... -23:
// 2^b / 5^-q rounded down, incremented by one, and truncated to 128 bits
// with the most significant bit set. A significand below 2^64 times 10^q
// is below half the smallest subnormal number for q < -342, hence zero.
// Decimal exponents above 22 (values above about 1e22) are not covered:
// they do not occur in the ENDF/B-VIII.0 and VIII.1 libraries and are
// left to std::strtod.

#if defined(_MSC_VER) && ! defined(__clang__) && (defined(_M_X64) || defined(_M_ARM64)) && ! defined(_M_ARM64EC)
#include <intrin.h>
#endif

#if defined(__GNUC__) || defined(__clang__)
#define CPP_DECIMAL_NOINLINE __attribute__((noinline))
#elif defined(_MSC_VER)
#define CPP_DECIMAL_NOINLINE __declspec(noinline)
#else
#define CPP_DECIMAL_NOINLINE
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

// Sets result to the double nearest to mant * 10^k (ties to even),
// negated if neg, for 0 < mant < 2^64 and k < -22. Returns false, leaving
// result unchanged, for k >= -22 and in the rare cases in which the
// 128-bit product does not determine the rounding; these are left to the
// general code path (std::strtod).
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


// Fast exact conversion of a plain decimal number of the form
// [+-]digits[.digits][(e|E)[+-]digits] (as assembled by endfstr2float)
// to double. If the significand has at most 15 digits and the decimal
// exponent is at most 22 in magnitude, both the significand and the
// power of ten are exactly representable and a single IEEE multiplication
// or division yields the correctly rounded result, i.e. the same value as
// std::strtod; decimal exponents below -22 are converted exactly with
// cpp_decimal_to_double_negexp. Returns false for anything else, in which
// case std::strtod must be used.
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
    if (k < -22) return cpp_decimal_to_double_negexp(mant, k, neg, result);
    if (k > 22) return false;
    if (k > 0) v *= p10[k];
    else if (k < 0) v /= p10[-k];
  }
  result = neg ? -v : v;
  return true;
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
// operations on two overlapping loads of the 11 bytes of the field.
// Decimal exponents below -22 are converted with
// cpp_decimal_to_double_negexp. Returns 1 if converted, -1 if the field
// has one of these layouts but its decimal exponent is above 22 or
// cpp_decimal_to_double_negexp leaves it to std::strtod (the common path
// rejects it as well), and 0 for any other content.
inline int cpp_fast_field_swar(const char* str, double &result) {
#ifdef CPP_FIELD_SWAR_LE
  static const double p10[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
  };
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
  double v = static_cast<double>(mant);
  if (mant != 0) {
    if (k < -22) return cpp_decimal_to_double_negexp(mant, k, neg, result) ? 1 : -1;
    if (k > 22) return -1;
    if (k > 0) v *= p10[k];
    else if (k < 0) v /= p10[-k];
  }
  result = neg ? -v : v;
  return 1;
#else
  (void) str;
  (void) result;
  return 0;
#endif
}


// Single-pass conversion of the 11 characters of a float field for the
// common case: leading spaces, a decimal number of the form
// [+-]digits[.digits] optionally followed by an exponent introduced by
// e/E (or d/D if accepted) or directly by its sign, and trailing spaces.
// If the significand has at most 15 significant digits and the decimal
// exponent is at most 22 in magnitude, both the significand and the
// power of ten are exactly representable and a single IEEE multiplication
// or division gives the correctly rounded result, i.e. the same value as
// std::strtod; decimal exponents below -22 are converted exactly with
// cpp_decimal_to_double_negexp (same value as std::strtod). Returns false
// for any other content of the field, more significant digits, decimal
// exponents above 22 and the rare cases cpp_decimal_to_double_negexp
// leaves to std::strtod; these are then handled by the general code path. The two layouts of almost
// all fields are first tried with cpp_fast_field_swar, which gives the
// same result for them.
inline bool cpp_fast_field_to_double(const char* str, bool accept_d_exponent, double &result) {
  const int swar = cpp_fast_field_swar(str, result);
  if (swar != 0) return swar > 0;
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
    if (k < -22) return cpp_decimal_to_double_negexp(mant, k, neg, result);
    if (k > 22) return false;
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

// The integer in the field of the given length starting at start_pos,
// converted by std::atoi, or 0 if the field is blank. The field is
// copied into a terminated buffer for std::atoi; the fields read with
// this function (MAT/MF/MT numbers and the fields of INTG records) are
// short, so the buffer is on the stack and only longer fields need a
// heap allocation.
inline int cpp_read_custom_int_field(const char *str, int start_pos, int length) {
  const char* field = str + start_pos;
  int i = 0;
  while (i < length && field[i] == ' ') i++;
  if (i >= length) return 0;
  char buf[32];
  if (length < static_cast<int>(sizeof(buf))) {
    std::memcpy(buf, field, length);
    buf[length] = '\0';
    return std::atoi(buf);
  }
  std::string longfield(field, static_cast<std::size_t>(length));
  return std::atoi(longfield.c_str());
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


// The functions reading a line into an existing string reuse its
// allocated memory; the line is cleared first so that a failed read
// leaves an empty line.
// The fields and the MAT/MF/MT numbers are read at fixed columns up to
// column 75. Columns missing from a shorter line are blanks (as for
// EndfParserPy, which reads the columns of a line by slicing), so that the
// readers never read past the end of the line.
// Returns the length of the line content before the padding.
inline std::size_t cpp_pad_short_line(std::string& line) {
  const std::size_t min_size = 75;
  if (line.size() >= min_size) return line.size();
  std::size_t content_size = line.size();
  line.append(min_size - content_size, ' ');
  return content_size;
}


// The number (counting from 1) and the length (without the line
// ending) of the last line read from a stream, i.e. of the line that ends
// before the current position. The stream is read again from its
// beginning, which is only done for error messages; the position is
// restored. Returns false if the stream cannot be repositioned.
inline bool cpp_last_line_info(std::istream& cont, long& lineno, std::size_t& length) {
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
  }
  cont.clear();
  cont.seekg(pos);
  return lineno > 0;
}


// A hint for an error message if the last line read from the stream
// (see cpp_last_line_info) is longer than 80 columns, otherwise empty.
inline std::string cpp_long_line_hint(std::istream& cont) {
  long lineno;
  std::size_t length;
  if (! cpp_last_line_info(cont, lineno, length) || length <= 80) return "";
  std::ostringstream oss;
  oss << "Hint: line " << lineno << " is longer than 80 columns (" << length
      << " columns; non-ASCII multi-byte characters or text beyond column 80?)";
  return oss.str();
}


// To be called in a catch block for a std::runtime_error raised while
// parsing the data in cont: rethrows it with the message escaped (see
// cpp_escape_message) and with a hint if the last line read is longer
// than 80 columns. Exceptions of derived classes, e.g. failures to open
// a file, are rethrown unchanged.
[[noreturn]] inline void cpp_rethrow_parse_error(const std::runtime_error& e, std::istream& cont) {
  if (typeid(e) != typeid(std::runtime_error)) throw;
  std::string msg = cpp_escape_message(e.what());
  std::string hint = cpp_long_line_hint(cont);
  if (! hint.empty()) {
    if (msg.empty() || msg[msg.size()-1] != '\n') msg += "\n";
    msg += hint;
  }
  throw std::runtime_error(msg);
}


// With accept_non_ascii=false, raise an error at the first character of
// a line outside printable ASCII (codes 32 to 126). size is the length
// of the line content (without the line ending and without the blanks
// added to a short line, see cpp_pad_short_line), which has just been
// read from cont. The error is raised by the Python function shared
// with EndfParserPy, so that both parsers give the same message.
inline void cpp_check_line_ascii(
  const std::string& line, std::size_t size, std::istream& cont, ParsingOptions &parse_opts
) {
  if (parse_opts.accept_non_ascii) return;
  for (std::size_t i = 0; i < size; i++) {
    unsigned char c = static_cast<unsigned char>(line[i]);
    if (c >= 32 && c <= 126) continue;
    long lineno = 0;
    std::size_t length;
    cpp_last_line_info(cont, lineno, length);
    // the MAT/MF/MT columns (the line is at least 75 characters long)
    int mat = cpp_read_custom_int_field(line.c_str(), 66, 4);
    int mf = cpp_read_custom_int_field(line.c_str(), 70, 2);
    int mt = cpp_read_custom_int_field(line.c_str(), 72, 3);
    cpp_text_encoding_function("raise_non_ascii_line_error")(
      lineno, i + 1, mat, mf, mt, static_cast<int>(c)
    );
    throw std::logic_error("unexpected return from raise_non_ascii_line_error");
  }
}


inline void cpp_read_raw_line(std::string& line, std::istream& cont) {
  line.clear();
  cpp_getline(cont, line);
  cpp_pad_short_line(line);
}


inline std::string cpp_read_raw_line(std::istream& cont) {
  std::string line;
  cpp_read_raw_line(line, cont);
  return line;
}


// content_size (if given) receives the length of the line before the
// padding of a short line (see cpp_pad_short_line).
// The MAT/MF/MT numbers of a line are checked with
// validate_control_records=true and, if check_long_line is true, for a
// line longer than 80 columns: such a line is not valid, and a non-ASCII
// character that occupies several bytes (e.g. in UTF-8) in a TEXT record
// shifts the MAT/MF/MT columns, which EndfParserPy, which divides a file
// into sections by these columns, also detects.
inline void cpp_read_line(
  std::string& line, std::istream& cont, int mat, int mf, int mt, ParsingOptions &parse_opts,
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


// The lines of a section are returned as Python strings (see
// cpp_bytes_to_pystr).
inline py::list read_section_verbatim(
    int mat, int mf, int mt, std::istream& cont, bool is_first, ParsingOptions &parse_opts
) {
  std::streampos curpos;
  std::string line;
  py::list secvec;
  int curmf;
  int curmt;
  std::size_t content_size;
  while (! cont.eof()) {
    // the MF/MT numbers of every line are checked below
    cpp_read_line(line, cont, mat, mf, mt, parse_opts, &content_size, false);
    curmf = std::stoi(line.substr(70, 2));
    curmt = std::stoi(line.substr(72, 3));
    if (curmf != mf || curmt != mt) break;
    // the line as read (without the blanks added to a short line), with
    // the newline for compatibility with the Python parser
    line.resize(content_size);
    line.push_back('\n');
    secvec.append(cpp_bytes_to_pystr(line));
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
