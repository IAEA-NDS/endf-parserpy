// Equivalence test of the float fields written by EndfParserCpp.
//
// cpp_write_field_double_at in
// endf_parserpy/compiler/cpp_templates/module_header_writing.hpp writes
// the 11 characters of a float field into a line. This program compares
// the characters it writes with those of a frozen copy of the iostream
// based conversion (ref_float2endfstr below), which the writer produced
// before its formatting was reimplemented without iostreams, for every
// combination of the options abuse_signpos, keep_E, skip_intzero and
// prefer_noexp. The other characters of the line must stay unchanged.
//
// The functions under test are not copied here: the test driver
// (tests/test_cpp_float_field_writing.py) extracts them from the template
// into the header "float_field_under_test.hpp", which is included below,
// so that the test always checks the code that ships.
//
// usage: float_field_writing_equivalence sampled
//        float_field_writing_equivalence random <number of values> <seed>
// The exit status is 0 if no mismatch was found.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "float_field_under_test.hpp"


// FROZEN REFERENCE -- DO NOT UPDATE THESE FUNCTIONS TOGETHER WITH THE
// WRITER. They are verbatim copies of the iostream based conversion of
// module_header_writing.hpp (normalize_exponent, get_scientific_numstr,
// is_carried_mantissa, float2endfstr_helper, float2endfstr_decimal_helper,
// float2endfstr; only the names differ).

inline void ref_normalize_exponent(std::string& numstr) {
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


inline std::string ref_get_scientific_numstr(double value, int precision, bool abuse_signpos) {
  std::ostringstream oss;
  oss << std::scientific << std::setprecision(precision) << value;
  std::string numstr = oss.str();
  ref_normalize_exponent(numstr);
  if (! abuse_signpos && value >= 0) {
    numstr.insert(0, " ");
  }
  return numstr;
}


inline bool ref_is_carried_mantissa(const std::string& numstr) {
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


inline std::string ref_float2endfstr_helper(double value, size_t width, WritingOptions &write_opts)
{
  std::string numstr = ref_get_scientific_numstr(value, 6, write_opts.abuse_signpos);
  // re-calculate precision to match width specification
  int prec = 6 - (static_cast<int>(numstr.size()) - static_cast<int>(width));
  if (prec < 0) {
    prec = 0;
  }
  numstr = ref_get_scientific_numstr(value, prec, write_opts.abuse_signpos);
  while (numstr.size() > width && prec > 0) {
    numstr = ref_get_scientific_numstr(value, --prec, write_opts.abuse_signpos);
  }
  while (prec < 20 && ref_is_carried_mantissa(numstr)) {
    std::string candidate = ref_get_scientific_numstr(
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


inline std::string ref_float2endfstr_decimal_helper(
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


inline std::string ref_float2endfstr(double value, WritingOptions &write_opts) {
  std::ostringstream oss;
  std::string numstr;
  int width = 11;
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
  numstr = ref_float2endfstr_helper(
    value, effwidth, write_opts
  );
  if (write_opts.prefer_noexp) {
    std::string numstr_noexp = ref_float2endfstr_decimal_helper(
      value, width, write_opts
    );
    if (numstr_noexp.size() <= width) {
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

// END OF FROZEN REFERENCE


static long nchk = 0, nfail = 0, nfast = 0, nfinite = 0;
static WritingOptions opts_all[16];

static void check(double v, int first_opt, int last_opt) {
  if (first_opt == 0 && std::isfinite(v)) {
    // how often the fast path applies (default options)
    char buf[16];
    nfinite++;
    if (cpp_float_field_fast(buf, v, false, false)) nfast++;
  }
  for (int k = first_opt; k <= last_opt; k++) {
    WritingOptions& opts = opts_all[k];
    std::string ref = ref_float2endfstr(v, opts);
    // the field in the middle of a line whose other characters must stay
    std::string line(81, '#');
    std::string got_err;
    try {
      cpp_write_field_double_at(line, 22, v, opts);
    } catch (const std::exception& e) {
      got_err = e.what();
    }
    nchk++;
    bool ok = ref.size() == 11 && got_err.empty()
      && line.compare(22, 11, ref) == 0
      && line.size() == 81
      && line.compare(0, 22, std::string(22, '#')) == 0
      && line.compare(33, 48, std::string(48, '#')) == 0;
    if (! ok) {
      if (nfail < 20) {
        std::printf(
          "MISMATCH value=%.17g opts=%d%d%d%d ref=[%s] got=[%s] err=[%s]\n", v,
          opts.abuse_signpos, opts.keep_E, opts.skip_intzero, opts.prefer_noexp,
          ref.c_str(), line.size() >= 33 ? line.substr(22, 11).c_str() : line.c_str(),
          got_err.c_str());
      }
      nfail++;
    }
  }
}

// default options and the formatting options that use the same code path
// (all combinations without prefer_noexp) come first
static void init_opts() {
  int k = 0;
  for (int noexp = 0; noexp < 2; noexp++)
    for (int bits = 0; bits < 8; bits++) {
      WritingOptions& o = opts_all[k++];
      o.abuse_signpos = bits & 1;
      o.keep_E = (bits >> 1) & 1;
      o.skip_intzero = (bits >> 2) & 1;
      o.prefer_noexp = noexp;
      o.preserve_value_strings = false;
      o.include_linenum = true;
      o.accept_non_ascii = true;
      o.array_type = "dict";
    }
}

static void check_both_signs(double v, int first_opt, int last_opt) {
  check(v, first_opt, last_opt);
  check(-v, first_opt, last_opt);
}

static uint64_t rng_state = 1;
static uint64_t next_rand() {
  // splitmix64
  uint64_t z = (rng_state += 0x9E3779B97F4A7C15ULL);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}

static double from_bits(uint64_t b) { double d; std::memcpy(&d, &b, 8); return d; }
static uint64_t to_bits(double d) { uint64_t b; std::memcpy(&b, &d, 8); return b; }

static double pow10i(int e) {
  return std::strtod(("1e" + std::to_string(e)).c_str(), nullptr);
}

// values whose rounding to nsig digits is a tie or carries into the next
// decade, the values of the decades boundaries, and their neighbours
static void special_values(std::vector<double>& out, int emin, int emax) {
  for (int e = emin; e <= emax; e++) {
    std::vector<double> base;
    base.push_back(pow10i(e));
    for (int nsig = 1; nsig <= 10; nsig++) {
      // 9.99...95 * 10^e (carry), 9.99...949 and 1.00...05
      std::string nines(nsig, '9');
      std::string s1 = "9." + nines.substr(1) + "5e" + std::to_string(e);
      std::string s2 = "9." + nines.substr(1) + "49e" + std::to_string(e);
      std::string s3 = "1." + std::string(nsig - 1, '0') + "5e" + std::to_string(e);
      if (nsig == 1) { s1 = "9.5e" + std::to_string(e); s2 = "9.49e" + std::to_string(e); s3 = "1.5e" + std::to_string(e); }
      base.push_back(std::strtod(s1.c_str(), nullptr));
      base.push_back(std::strtod(s2.c_str(), nullptr));
      base.push_back(std::strtod(s3.c_str(), nullptr));
    }
    for (double b : base) {
      if (! std::isfinite(b) || b == 0) continue;
      uint64_t bits = to_bits(b);
      for (int d = -1; d <= 1; d++) out.push_back(from_bits(bits + d));
    }
  }
}

static void run_sampled() {
  std::vector<double> vals;
  vals.push_back(0.0);
  vals.push_back(-0.0);
  vals.push_back(std::numeric_limits<double>::quiet_NaN());
  vals.push_back(std::numeric_limits<double>::infinity());
  vals.push_back(std::numeric_limits<double>::denorm_min());
  vals.push_back(std::numeric_limits<double>::min());
  vals.push_back(std::numeric_limits<double>::max());
  special_values(vals, -324, 308);
  // random decimal numbers with 1 to 12 significant digits
  for (int i = 0; i < 20000; i++) {
    int nsig = 1 + next_rand() % 12;
    uint64_t lo = 1, hi;
    for (int k = 1; k < nsig; k++) lo *= 10;
    hi = lo * 10;
    uint64_t m = lo + next_rand() % (hi - lo);
    int e = static_cast<int>(next_rand() % 640) - 330;
    std::string s = std::to_string(m) + "e" + std::to_string(e);
    vals.push_back(std::strtod(s.c_str(), nullptr));
  }
  // random bit patterns
  for (int i = 0; i < 20000; i++) {
    vals.push_back(from_bits(next_rand() & 0x7fffffffffffffffULL));
  }
  // skip_intzero only matters with prefer_noexp: the combinations with
  // it (options 4 to 7) on a sample; prefer_noexp (options 8 to 15), whose
  // reference is slow for large magnitudes, on a sample of the values with
  // magnitudes up to 1e25
  long n = 0;
  for (double v : vals) {
    check_both_signs(v, 0, 3);
    if (n % 8 == 0) check_both_signs(v, 4, 7);
    if (n % 16 == 0 && std::fabs(v) < 1e25) check_both_signs(v, 8, 15);
    n++;
  }
  for (int e = -12; e <= 12; e++) {
    for (int i = 0; i < 500; i++) {
      double v = (1.0 + (next_rand() % 1000000000ULL) / 1e8) * pow10i(e);
      check_both_signs(v, 0, 15);
    }
  }
}

// random values; most of them with magnitudes between 1e-50 and 1e50,
// where the digits are computed with double arithmetic
static void run_random(long n) {
  for (long i = 0; i < n; i++) {
    uint64_t r = next_rand();
    double v;
    if ((r & 3) == 0) {
      v = from_bits(next_rand());
    } else if ((r & 3) == 1) {
      // binary exponent between -166 and 166
      uint64_t mant = next_rand() & 0xFFFFFFFFFFFFFULL;
      uint64_t bexp = 1023 - 166 + next_rand() % 333;
      v = from_bits((bexp << 52) | mant | ((r & 4) ? 0x8000000000000000ULL : 0));
    } else {
      int nsig = 1 + next_rand() % 10;
      uint64_t lo = 1;
      for (int k = 1; k < nsig; k++) lo *= 10;
      uint64_t m = lo + next_rand() % (9 * lo);
      int e = ((r & 3) == 2) ? static_cast<int>(next_rand() % 640) - 330
                             : static_cast<int>(next_rand() % 100) - 55;
      v = std::strtod((std::to_string(m) + "e" + std::to_string(e)).c_str(), nullptr);
      if (r & 4) v = -v;
    }
    check(v, 0, 7);
    if (r % 16 == 3) check(v, 8, 15);
  }
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s sampled|random ...\n", argv[0]);
    return 2;
  }
  init_opts();
  const char* mode = argv[1];
  if (std::strcmp(mode, "sampled") == 0) {
    run_sampled();
  } else if (std::strcmp(mode, "random") == 0 && argc > 3) {
    rng_state = std::strtoull(argv[3], nullptr, 10);
    run_random(std::atol(argv[2]));
  } else {
    std::fprintf(stderr, "unknown mode\n");
    return 2;
  }
  std::printf("checked=%ld mismatches=%ld finite=%ld fast=%ld\n", nchk, nfail, nfinite, nfast);
  return nfail == 0 ? 0 : 1;
}
