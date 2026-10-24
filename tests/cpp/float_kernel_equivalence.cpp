// Equivalence test of the conversion of float fields in EndfParserCpp.
//
// The conversion of the 11 characters of a float field,
// cpp_fast_field_to_double in
// endf_parserpy/compiler/cpp_templates/module_header_reading.hpp, starts
// with a first stage (cpp_fast_field_swar) for the two most common
// layouts of float fields, " d.dddddd+d" and " d.ddddd+dd". This program
// compares the function as it ships with a frozen copy of the function
// before the first stage was added (ref_fast_field_to_double below): the
// decision whether the field is converted or left to the general path
// (std::strtod) and the bits of the double must agree for every field,
// with accept_d_exponent false and true. In addition, the first stage
// must handle exactly the fields of its two layouts.
//
// The kernel is not copied here: the test driver
// (tests/test_cpp_float_kernel_equivalence.py) extracts it from the
// template into the header "float_kernel_under_test.hpp", which is
// included below, so that the test always checks the code that ships.
//
// usage: float_kernel_equivalence sampled
//        float_kernel_equivalence exhaustive <first character index 0..2>
//        float_kernel_equivalence boundary <number of fields>
//        float_kernel_equivalence random <number of fields> <seed>
//        float_kernel_equivalence explicit
// The exit status is 0 if no mismatch was found.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "float_kernel_under_test.hpp"


// FROZEN REFERENCE -- DO NOT UPDATE THIS FUNCTION TOGETHER WITH THE KERNEL.
// It is a verbatim copy of cpp_fast_field_to_double as it was before the
// first stage was added (only its name differs). It is the reference
// that makes this test a guarantee that the results did not change;
// changing it along with the kernel would defeat the purpose of the test.
inline bool ref_fast_field_to_double(const char* str, bool accept_d_exponent, double &result) {
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


static long nchk = 0, nfail = 0, nfirst = 0;

static bool isdig(unsigned char c) { return c >= '0' && c <= '9'; }
static bool issgn(unsigned char c) { return c == '+' || c == '-'; }

// independent check of the two layouts of the first stage
static int layout_of(const char* f) {
  const unsigned char* u = reinterpret_cast<const unsigned char*>(f);
  if (! (u[0] == ' ' || issgn(u[0])) || ! isdig(u[1]) || u[2] != '.') return 0;
  for (int i = 3; i <= 7; i++) if (! isdig(u[i])) return 0;
  if (isdig(u[8]) && issgn(u[9]) && isdig(u[10])) return 1;
  if (issgn(u[8]) && isdig(u[9]) && isdig(u[10])) return 2;
  return 0;
}

static void print_field(const char* f) {
  for (int i = 0; i < 11; i++) {
    unsigned char c = static_cast<unsigned char>(f[i]);
    if (c >= 32 && c < 127) std::printf("%c", c); else std::printf("\\x%02x", c);
  }
}

// the field must consist of exactly 11 readable bytes
static void check(const char* f) {
  double r_first = 0;
  const int s = cpp_fast_field_swar(f, r_first);
  const int lay = layout_of(f);
#ifdef CPP_FIELD_SWAR_LE
  const bool layout_ok = (s != 0) == (lay != 0);
#else
  const bool layout_ok = (s == 0);
#endif
  if (s != 0) nfirst++;
  for (int d = 0; d < 2; d++) {
    double r_ref = 0, r_new = 0;
    const bool a = ref_fast_field_to_double(f, d == 1, r_ref);
    const bool b = cpp_fast_field_to_double(f, d == 1, r_new);
    nchk++;
    bool ok = layout_ok && a == b && (! a || std::memcmp(&r_ref, &r_new, 8) == 0);
    if (s != 0) ok = ok && ((s > 0) == a) && (s < 0 || std::memcmp(&r_ref, &r_first, 8) == 0);
    if (! ok && nfail++ < 20) {
      std::printf("MISMATCH accept_d_exponent=%d [", d);
      print_field(f);
      std::printf("] reference=%d %.17g new=%d %.17g first_stage=%d layout=%d\n",
                  a, r_ref, b, r_new, s, lay);
    }
  }
}

static std::uint64_t rs = 88172645463325252ULL;
static inline std::uint64_t xr() { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }

static void make_valid(char* f) {
  const char s0[] = " +-";
  const bool lay1 = (xr() & 1) != 0;
  f[0] = s0[xr() % 3];
  f[1] = static_cast<char>('0' + xr() % 10);
  f[2] = '.';
  for (int i = 3; i <= 7; i++) f[i] = static_cast<char>('0' + xr() % 10);
  if (lay1) {
    f[8] = static_cast<char>('0' + xr() % 10);
    f[9] = (xr() & 1) ? '+' : '-';
    f[10] = static_cast<char>('0' + xr() % 10);
  } else {
    f[8] = (xr() & 1) ? '+' : '-';
    f[9] = static_cast<char>('0' + xr() % 10);
    f[10] = static_cast<char>('0' + xr() % 10);
  }
}

// all strings of both layouts with the given first character
static void run_exhaustive(char c0) {
  char f[12];
  f[11] = '\0';
  for (int lay = 1; lay <= 2; lay++) {
    const long nm = (lay == 1) ? 10000000L : 1000000L;
    const int nd = (lay == 1) ? 7 : 6;
    const int ne = (lay == 1) ? 10 : 100;
    for (long m = 0; m < nm; m++) {
      char dg[8];
      long x = m;
      for (int i = nd - 1; i >= 0; i--) { dg[i] = static_cast<char>('0' + x % 10); x /= 10; }
      f[0] = c0;
      f[1] = dg[0];
      f[2] = '.';
      for (int i = 1; i < nd; i++) f[2 + i] = dg[i];
      for (int es = 0; es < 2; es++) {
        for (int e = 0; e < ne; e++) {
          if (lay == 1) {
            f[9] = es ? '-' : '+';
            f[10] = static_cast<char>('0' + e);
          } else {
            f[8] = es ? '-' : '+';
            f[9] = static_cast<char>('0' + e / 10);
            f[10] = static_cast<char>('0' + e % 10);
          }
          check(f);
        }
      }
    }
  }
}

// every byte value at every position of valid fields
static void run_boundary(long n) {
  char g[12], f[12];
  g[11] = f[11] = '\0';
  for (long r = 0; r < n; r++) {
    make_valid(g);
    for (int pos = 0; pos < 11; pos++) {
      for (int c = 0; c < 256; c++) {
        std::memcpy(f, g, 11);
        f[pos] = static_cast<char>(c);
        check(f);
      }
    }
  }
}

// random fields: valid layouts with up to three substitutions, fields
// over the alphabet of number fields, and arbitrary bytes
static void run_random(long n) {
  const char alpha[] = "  0123456789+-.eEdD";
  const int na = sizeof(alpha) - 1;
  char f[12];
  f[11] = '\0';
  for (long r = 0; r < n; r++) {
    std::uint64_t a = xr();
    int m = static_cast<int>(a & 7);
    if (m < 4) {
      make_valid(f);
      int ns = static_cast<int>((a >> 3) & 3);
      for (int k = 0; k < ns; k++) {
        std::uint64_t b = xr();
        f[b % 11] = ((b >> 8) & 1) ? alpha[(b >> 9) % na] : static_cast<char>((b >> 9) & 0xff);
      }
    } else if (m < 7) {
      std::uint64_t b = xr();
      for (int i = 0; i < 11; i++) f[i] = alpha[(b >> (5 * i)) % na];
    } else {
      std::uint64_t b = xr(), c = xr();
      std::memcpy(f, &b, 8);
      std::memcpy(f + 8, &c, 3);
    }
    check(f);
  }
}

static void run_explicit() {
  // negative zero, limits of the power of ten (k = +-22, +-23) with one-
  // and two-digit exponents, other exponent characters, blanks inside the
  // field, a digit at position 0, bytes >= 0x80 and other characters
  static const char* const cases[] = {
    "-0.000000+0", "-0.000000-9", "+0.000000+0", " 0.000000-0", "-0.00000-99",
    "-0.00000+99", " 0.00000+99", " 1.23456+27", " 1.23456+28", " 1.23456-17",
    " 1.23456-18", "-9.99999+27", "-9.99999-17", " 9.99999-18", " 1.234567+9",
    " 1.234567-9", "-9.999999-9", " 1.00000+22", " 1.00000-22", " 0.00001+27",
    " 0.00001-17", " 1.23456D+5", " 1.23456d-5", " 1.234567D5", " 1.23456E+5",
    " 1.23456e-5", " 1.234567E5", " 1.234 67+8", " 1.234567 8", " 1.2345 7-8",
    "  .234567+8", " 1 234567+8", " 1.23456+ 8", " 1.23456 +8", "12.34567+8 ",
    "12.34567+80", "1.2345678+9", "1.234567+89", "1.2345678-9", "\x80" "1.234567+8",
    " \xb1.234567+8", " 1.\xb3" "4567+8", " 1.234567\xab" "8", " 1.234567+\xb8",
    " 1.23456\xad" "99", " 1.234567+8", "-1.234567-8", "+1.234567+8", " 1.23456+12",
    "-1.23456-12", "*1.234567+8", " 1,234567+8", "           ", " 1.234567+8\xff",
  };
  char f[12];
  f[11] = '\0';
  for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
    std::memset(f, ' ', 11);
    std::size_t len = std::strlen(cases[i]);
    std::memcpy(f, cases[i], len < 11 ? len : 11);
    check(f);
  }
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s sampled|exhaustive|boundary|random|explicit ...\n", argv[0]);
    return 2;
  }
  const char* mode = argv[1];
  if (std::strcmp(mode, "sampled") == 0) {
    run_explicit();
    run_boundary(300);
    run_random(3000000);
  } else if (std::strcmp(mode, "exhaustive") == 0 && argc > 2) {
    const char s0[] = " +-";
    run_exhaustive(s0[std::atoi(argv[2]) % 3]);
  } else if (std::strcmp(mode, "boundary") == 0 && argc > 2) {
    run_boundary(std::atol(argv[2]));
  } else if (std::strcmp(mode, "random") == 0 && argc > 3) {
    rs ^= static_cast<std::uint64_t>(std::atol(argv[3])) * 0x9E3779B97F4A7C15ULL;
    run_random(std::atol(argv[2]));
  } else if (std::strcmp(mode, "explicit") == 0) {
    run_explicit();
  } else {
    std::fprintf(stderr, "invalid arguments\n");
    return 2;
  }
  std::printf("%s: checks=%ld first_stage=%ld mismatches=%ld\n", mode, nchk, nfirst, nfail);
  return nfail == 0 ? 0 : 1;
}
