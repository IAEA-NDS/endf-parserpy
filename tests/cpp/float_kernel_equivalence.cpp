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
// The only intended difference: fields with a decimal exponent
// k = exponent - digits after the decimal point below -22, which the
// reference leaves to std::strtod, are now converted exactly
// (cpp_decimal_to_double_negexp). For the fields that the reference does
// not convert, the expectation comes from ref_parse_field, the reference
// up to the point where it computes the value, and std::strtod: the
// field must be converted if and only if the reference accepts its form
// and k < -22, and with the bits of the std::strtod result. cpp_fast_decimal_to_double
// is checked in the same way on the string that endfstr2float passes to
// it, and cpp_decimal_to_double_negexp directly on significands up to 2^64
// and decimal exponents from -360 to 30 (mode "negexp") and on near-halfway
// cases computed with exact arithmetic by the test driver (mode "list").
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
//        float_kernel_equivalence exhaustive3 <first character index 0..2>
//        float_kernel_equivalence negexp <number of random significands per k> <seed>
//        float_kernel_equivalence list <file>
// The exit status is 0 if no mismatch was found.

#include <cmath>
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


// The reference above up to the point where it computes the value, with
// the sign, the significand and the exponents as outputs: it accepts
// exactly the fields that the reference converts or rejects only because
// of the range of k.
struct ParsedField {
  bool neg;
  unsigned long long mant;
  int expo;
  int k;
};

inline bool ref_parse_field(const char* str, bool accept_d_exponent, ParsedField &out) {
  const char* p = str;
  const char* const e = str + 11;
  while (p < e && *p == ' ') p++;
  if (p == e) {
    out.neg = false; out.mant = 0; out.expo = 0; out.k = 0;
    return true;
  }
  bool neg = false;
  if (*p == '+' || *p == '-') {
    neg = (*p == '-');
    p++;
  }
  unsigned long long mant = 0;
  int ndig = 0;
  int nfrac = 0;
  bool any_digit = false;
  for (; p < e && *p >= '0' && *p <= '9'; p++) {
    any_digit = true;
    if (mant == 0 && *p == '0') continue;
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
  out.neg = neg;
  out.mant = mant;
  out.expo = expo;
  out.k = expo - nfrac;
  return true;
}

// std::strtod of [-]mant e k
static double strtod_of(bool neg, unsigned long long mant, long k) {
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%s%llue%ld", neg ? "-" : "", mant, k);
  return std::strtod(buf, nullptr);
}

// the string that endfstr2float passes to cpp_fast_decimal_to_double and
// std::strtod for a non-blank field without blanks inside the number
// (copy of its loop)
static void endf_tbuf(const char* str, bool accept_d_exponent, char* tbuf) {
  int j = 0;
  bool in_number = false;
  bool in_exponent = false;
  int last_nonspace_pos = -1;
  for (int i = 10; i >= 0; i--) {
    if (str[i] != ' ') {
      last_nonspace_pos = i;
      break;
    }
  }
  for (int i = 0; i <= last_nonspace_pos; i++) {
    char c = str[i];
    if (c == ' ') continue;
    if (in_number) {
      if (! in_exponent) {
        if (c == '+' || c == '-') {
          tbuf[j++] = 'e';
          in_exponent = true;
        } else if (c == 'e' || c == 'E') {
          in_exponent = true;
        } else if ((c == 'd' || c == 'D') && accept_d_exponent) {
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
  if (j == 0) tbuf[j++] = '0';
  tbuf[j++] = '\0';
}


static long nchk = 0, nfail = 0, nfirst = 0, nneg = 0, nleft = 0, ndec = 0;

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

static bool same_bits(double x, double y) { return std::memcmp(&x, &y, 8) == 0; }

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
    // expected decision and value
    bool expect = a;
    double r_exp = r_ref;
    ParsedField pf;
    const bool parsed = ref_parse_field(f, d == 1, pf);
    if (! a && parsed) {
      // left to std::strtod by the reference only because of k
      r_exp = strtod_of(pf.neg, pf.mant, pf.k);
      expect = pf.k < -22;
      if (expect) nneg++; else nleft++;
    }
    bool ok = layout_ok && b == expect && (! b || same_bits(r_exp, r_new));
    if (s != 0) ok = ok && ((s > 0) == b) && (s < 0 || same_bits(r_new, r_first));
    // cpp_fast_decimal_to_double on the string assembled by endfstr2float
    bool ok_dec = true;
    double r_dec = 0, r_std = 0;
    bool c = false;
    if (parsed && std::memcmp(f, "           ", 11) != 0) {
      char tbuf[16];
      endf_tbuf(f, d == 1, tbuf);
      c = cpp_fast_decimal_to_double(tbuf, r_dec);
      char* end = nullptr;
      r_std = std::strtod(tbuf, &end);
      ndec++;
      ok_dec = (! c || (*end == '\0' && same_bits(r_dec, r_std)))
               && (! b || pf.expo > 1000 || pf.expo < -1000 || c);
    }
    if ((! ok || ! ok_dec) && nfail++ < 20) {
      std::printf("MISMATCH accept_d_exponent=%d [", d);
      print_field(f);
      std::printf("] reference=%d %.17g expected=%d %.17g new=%d %.17g first_stage=%d layout=%d"
                  " decimal=%d %.17g strtod=%.17g\n",
                  a, r_ref, expect, r_exp, b, r_new, s, lay, c, r_dec, r_std);
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

// random fields of the general form accepted by the conversion: blanks,
// an optional sign, digits with or without a decimal point, an exponent
// introduced by e/E/d/D or directly by its sign with up to three digits
// (mostly negative), blanks; mostly with |k| > 22
static void make_general(char* f) {
  static const char ech[] = "eEdD";
  char buf[32];
  int n = 0;
  std::uint64_t a = xr();
  const int sg = static_cast<int>(a % 4);
  if (sg == 1) buf[n++] = '+';
  else if (sg == 2) buf[n++] = '-';
  const int nint = static_cast<int>((a >> 2) % 4);           // 0..3 digits before the point
  const bool point = ((a >> 4) & 7) != 0 || nint == 0;
  const int nfr = static_cast<int>((a >> 7) % 8);            // 0..7 digits after it
  const int ne = 1 + static_cast<int>((a >> 10) % 3);        // 1..3 exponent digits
  const int ek = static_cast<int>((a >> 12) % 5);            // 0: sign only, else e/E/d/D
  const bool eneg = ((a >> 15) % 8) != 0;
  for (int i = 0; i < nint; i++) buf[n++] = static_cast<char>('0' + xr() % 10);
  if (point) buf[n++] = '.';
  for (int i = 0; i < nfr; i++) buf[n++] = static_cast<char>('0' + xr() % 10);
  if (nint + nfr == 0) buf[n++] = static_cast<char>('0' + xr() % 10);
  if (ek > 0) buf[n++] = ech[ek - 1];
  if (ek == 0 || ((a >> 18) & 3) != 0) buf[n++] = eneg ? '-' : '+';
  for (int i = 0; i < ne; i++) buf[n++] = static_cast<char>('0' + xr() % 10);
  if (n > 11) {
    // too long for a field
    make_valid(f);
    return;
  }
  const int lead = static_cast<int>(xr() % (12 - n));
  std::memset(f, ' ', 11);
  std::memcpy(f + lead, buf, n);
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

// random fields: valid fields (the two layouts of the first stage or
// make_general) with up to three substitutions, fields
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
      if ((a >> 5) & 1) make_valid(f); else make_general(f);
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
    // decimal exponents beyond 22 in magnitude: the tie 1e23 (rounded to
    // even, left to std::strtod), limits of the subnormal range, underflow
    // to zero, overflow (left to std::strtod)
    " 1.00000+23", "-1.00000+23", " 1.000000+23", " 2.00000+23", " 1.00000-23",
    " 9.99999-23", " 4.9407-324", "-4.9407-324", " 4.9406-324", " 2.4703-324",
    " 2.4704-324", "-2.4702-324", " 9.8813-324", " 2.2251-308", " 2.2250-308",
    " 2.2250738-308", " 1.0000-400", "-1.0000-999", " 1.7976+308", " 1.7977+308",
    "-1.7977+308", " 1.0000+309", " 9.99999+99", " 1.2345E-50", " 1.2345d-50",
    " 1.2345D-50", "1.2345e-300", "12345678-99", "1234567-330", " .12345-320",
    " 0.0000-320", "-0.0000-999", "0.00001-320", "1e999999999", "1e-99999999",
    "-1e-9999999", " 1.234567-23", " 1.23456-23", "-9.99999+29",
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

// all strings " d.dddd+ddd" / " d.dddd-ddd" with the given first character
static void run_exhaustive3(char c0) {
  char f[12];
  f[11] = '\0';
  f[0] = c0;
  f[2] = '.';
  for (long m = 0; m < 100000L; m++) {
    long x = m;
    for (int i = 6; i >= 3; i--) { f[i] = static_cast<char>('0' + x % 10); x /= 10; }
    f[1] = static_cast<char>('0' + x);
    for (int es = 0; es < 2; es++) {
      f[7] = es ? '-' : '+';
      for (int e = 0; e < 1000; e++) {
        f[8] = static_cast<char>('0' + e / 100);
        f[9] = static_cast<char>('0' + (e / 10) % 10);
        f[10] = static_cast<char>('0' + e % 10);
        check(f);
      }
    }
  }
}

static long nnchk = 0;

// cpp_decimal_to_double_negexp against std::strtod and, if given, the bits
// of the correctly rounded positive value computed by the test driver
static void check_negexp(unsigned long long mant, int k, bool neg,
                       bool have_bits = false, std::uint64_t bits = 0) {
  if (mant == 0) return;
  double r_new = 0;
  const bool b = cpp_decimal_to_double_negexp(mant, k, neg, r_new);
  const double r_exp = strtod_of(neg, mant, k);
  nnchk++;
  const bool expect = k < -22;
  bool ok = b == expect && (! b || same_bits(r_new, r_exp));
  if (have_bits) {
    std::uint64_t ebits;
    std::memcpy(&ebits, &r_exp, 8);
    ok = ok && (ebits & 0x7FFFFFFFFFFFFFFFULL) == bits && (ebits >> 63) == (neg ? 1u : 0u);
  }
  if (! ok) {
    if (nfail++ < 20) {
      std::printf("MISMATCH negexp %s%llue%d: expected=%d %.17g new=%d %.17g\n",
                  neg ? "-" : "", mant, k, expect, r_exp, b, r_new);
    }
  }
}

// significands 1..300, 10^n and 2^n and 5^n with their neighbours,
// 10-digit limits and nrand random significands with 1 to 20 digits
// for all decimal exponents k from -360 to 30 (converted only for k < -22)
static void run_negexp(long nrand) {
  unsigned long long fixed[1024];
  int nf = 0;
  for (unsigned long long m = 1; m <= 300; m++) fixed[nf++] = m;
  unsigned long long p = 1;
  for (int n = 0; n <= 19; n++) {
    if (n > 0) p *= 10;
    fixed[nf++] = p - 1; fixed[nf++] = p; fixed[nf++] = p + 1;
  }
  for (int n = 0; n <= 63; n++) {
    p = 1ULL << n;
    fixed[nf++] = p - 1; fixed[nf++] = p; fixed[nf++] = p + 1;
  }
  fixed[nf++] = 0xFFFFFFFFFFFFFFFFULL;
  p = 1;
  for (int n = 0; n <= 27; n++) {
    if (n > 0) p *= 5;
    fixed[nf++] = p - 1; fixed[nf++] = p; fixed[nf++] = p + 1;
  }
  fixed[nf++] = 9999999999ULL; fixed[nf++] = 999999999999999ULL;
  fixed[nf++] = 4294967295ULL; fixed[nf++] = 4294967296ULL;
  // neighbours of the smallest normal number 2.2250738585072014e-308,
  // of the largest subnormal 2.225073858507201e-308 and of the smallest
  // subnormal 4.9406564584124654e-324 and half of it
  // (with k = -324 for 17 digits; also tried with all other k)
  fixed[nf++] = 22250738585072014ULL; fixed[nf++] = 22250738585072013ULL;
  fixed[nf++] = 22250738585072012ULL; fixed[nf++] = 22250738585072011ULL;
  fixed[nf++] = 22250738585072010ULL; fixed[nf++] = 22250738585072009ULL;
  fixed[nf++] = 22250738585072008ULL; fixed[nf++] = 49406564584124654ULL;
  fixed[nf++] = 24703282292062327ULL; fixed[nf++] = 24703282292062328ULL;
  fixed[nf++] = 17976931348623157ULL; fixed[nf++] = 17976931348623158ULL;
  fixed[nf++] = 17976931348623159ULL;
  for (int k = -360; k <= 30; k++) {
    for (int i = 0; i < nf; i++) check_negexp(fixed[i], k, (i & 1) != 0);
    for (long r = 0; r < nrand; r++) {
      const std::uint64_t a = xr();
      const int nd = 1 + static_cast<int>(a % 20);
      unsigned long long m;
      if (nd == 20) {
        m = xr();
      } else {
        unsigned long long lim = 1;
        for (int i = 0; i < nd; i++) lim *= 10;
        m = xr() % lim;
      }
      check_negexp(m, k, ((a >> 8) & 1) != 0);
    }
  }
}

// lines "W <significand> <k> <bits of the correctly rounded value in hex>"
// (cpp_decimal_to_double_negexp, both signs) and "F <11 characters>" (a
// field)
static bool run_list(const char* path) {
  std::FILE* fp = std::fopen(path, "r");
  if (! fp) return false;
  char line[256];
  while (std::fgets(line, sizeof(line), fp)) {
    if (line[0] == 'W') {
      unsigned long long m, bits;
      int k;
      if (std::sscanf(line + 1, "%llu %d %llx", &m, &k, &bits) == 3) {
        check_negexp(m, k, false, true, bits);
        check_negexp(m, k, true, true, bits);
      } else if (nfail++ < 20) {
        std::printf("invalid line %s", line);
      }
    } else if (line[0] == 'F' && std::strlen(line) >= 13) {
      char f[12];
      std::memcpy(f, line + 2, 11);
      f[11] = '\0';
      check(f);
    }
  }
  std::fclose(fp);
  return true;
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s sampled|exhaustive|boundary|random|explicit|exhaustive3|negexp|list ...\n", argv[0]);
    return 2;
  }
  const char* mode = argv[1];
  if (std::strcmp(mode, "sampled") == 0) {
    run_explicit();
    run_boundary(300);
    run_random(3000000);
    run_negexp(1000);
  } else if (std::strcmp(mode, "exhaustive3") == 0 && argc > 2) {
    const char s0[] = " +-";
    run_exhaustive3(s0[std::atoi(argv[2]) % 3]);
  } else if (std::strcmp(mode, "negexp") == 0 && argc > 3) {
    rs ^= static_cast<std::uint64_t>(std::atol(argv[3])) * 0x9E3779B97F4A7C15ULL;
    run_negexp(std::atol(argv[2]));
  } else if (std::strcmp(mode, "list") == 0 && argc > 2) {
    if (! run_list(argv[2])) {
      std::fprintf(stderr, "cannot read %s\n", argv[2]);
      return 2;
    }
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
  std::printf("%s: checks=%ld first_stage=%ld negexp_converted=%ld not_converted=%ld decimal_checks=%ld"
              " negexp_direct=%ld mismatches=%ld\n",
              mode, nchk, nfirst, nneg, nleft, ndec, nnchk, nfail);
  return nfail == 0 ? 0 : 1;
}
