#ifndef MODULE_HEADER_HPP
#define MODULE_HEADER_HPP


#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Necessary for STL containers like std::map

#include <stdexcept>
#include <iostream>
#include <sstream>
#include <fstream>
#include <iomanip>
#include <vector>
#include <string>
#include <cassert>
#include <algorithm>  // for std::sort
#include <cstddef>
#include <cstdlib>    // for std::strtod / std::strtol
#include <cmath>      // for std::isfinite
#include <cerrno>     // for errno (ERANGE)
#include <climits>    // for INT_MIN / INT_MAX
#include <limits>     // for std::numeric_limits

// When Python merges the various
// C++ files, there is no need
// to include them here
#ifndef PYTHON_COMPILE
#include "endf_rational.hpp"
#include "endf_float_cpp.hpp"
#include "index_shifter.hpp"
#endif

namespace py = pybind11;


#ifndef DOUBLE_TYPE
#define DOUBLE_TYPE double
#endif


// Arithmetic of ENDF recipe expressions.
// The generated code calls these functions instead of using the C++
// operators `/` and `%` directly, so that the results agree with those
// of the Python parser (see `endf_parserpy.interpreter.endf_mapping_utils`):
// - a division of two integers gives an exact fraction (EndfRational),
//   e.g. 13/6; only where an integer is needed must the value be an
//   integer (see the conversion of EndfRational to int),
// - the result of the modulo operation has the sign of the divisor
//   (as in Python), e.g. (5-7)%6 == 4,
// - a value of a float field (EndfFloatCpp) enters arithmetic as a
//   double; EndfFloatCpp also converts implicitly to int, which would
//   otherwise truncate it.

template<typename T, typename U>
inline auto cpp_div(T x, U y) -> decltype(x / y) {
  return x / y;
}


inline EndfRational cpp_div(int x, int y) {
  return EndfRational(x) / EndfRational(y);
}


template<typename U>
inline auto cpp_div(const EndfFloatCpp& x, U y)
    -> decltype(static_cast<double>(x) / y) {
  return static_cast<double>(x) / y;
}


template<typename T>
inline auto cpp_div(T x, const EndfFloatCpp& y)
    -> decltype(x / static_cast<double>(y)) {
  return x / static_cast<double>(y);
}


inline double cpp_div(const EndfFloatCpp& x, const EndfFloatCpp& y) {
  return static_cast<double>(x) / static_cast<double>(y);
}


inline int cpp_mod(int x, int y) {
  if (y == 0) {
    throw std::runtime_error("modulo by zero in expression " +
      std::to_string(x) + "%" + std::to_string(y));
  }
  int res = x % y;
  if (res != 0 && ((res < 0) != (y < 0))) {
    res += y;
  }
  return res;
}


inline long long cpp_floor_div(long long num, long long den) {
  // den > 0
  return num >= 0 ? num / den : -((-num + den - 1) / den);
}


inline EndfRational cpp_mod(const EndfRational& x, const EndfRational& y) {
  // x - y*floor(x/y), the result has the sign of y (as in Python)
  if (y.numerator() == 0) {
    throw std::runtime_error("modulo by zero in expression");
  }
  EndfRational q = x / y;
  EndfRational fq(cpp_floor_div(q.numerator(), q.denominator()));
  return x - y * fq;
}


inline EndfRational cpp_mod(const EndfRational& x, int y) {
  return cpp_mod(x, EndfRational(y));
}


inline EndfRational cpp_mod(int x, const EndfRational& y) {
  return cpp_mod(EndfRational(x), y);
}


inline double cpp_mod(double x, double y) {
  if (y == 0.0) {
    throw std::runtime_error("modulo by zero in expression");
  }
  double res = std::fmod(x, y);
  if (res != 0.0 && ((res < 0.0) != (y < 0.0))) {
    res += y;
  }
  return res;
}


inline double cpp_mod(double x, int y) { return cpp_mod(x, static_cast<double>(y)); }
inline double cpp_mod(int x, double y) { return cpp_mod(static_cast<double>(x), y); }
inline double cpp_mod(const EndfRational& x, double y) { return cpp_mod(static_cast<double>(x), y); }
inline double cpp_mod(double x, const EndfRational& y) { return cpp_mod(x, static_cast<double>(y)); }


template<typename U>
inline auto cpp_mod(const EndfFloatCpp& x, U y)
    -> decltype(cpp_mod(static_cast<double>(x), static_cast<double>(y))) {
  return cpp_mod(static_cast<double>(x), static_cast<double>(y));
}


template<typename T>
inline auto cpp_mod(T x, const EndfFloatCpp& y)
    -> decltype(cpp_mod(static_cast<double>(x), static_cast<double>(y))) {
  return cpp_mod(static_cast<double>(x), static_cast<double>(y));
}


// Conversion of the value of an expression to the value of a float field
// or a float variable

inline double cpp_to_double(int x) { return static_cast<double>(x); }
inline double cpp_to_double(double x) { return x; }
inline double cpp_to_double(const EndfRational& x) { return static_cast<double>(x); }
inline double cpp_to_double(const EndfFloatCpp& x) { return static_cast<double>(x); }


// Conversion of the value of an expression to the value of an integer
// field or an integer variable. The value must be an integer. A
// floating-point value (arising from a float field) may deviate from an
// integer by rounding errors.

inline int cpp_to_integer(int x) {
  return x;
}


inline int cpp_to_integer(const EndfRational& x) {
  return static_cast<int>(x);
}


inline int cpp_to_integer(double x) {
  double rounded = std::round(x);
  double tolerance = std::max(1e-6, 1e-12 * std::fabs(x));
  if (std::fabs(x - rounded) > tolerance) {
    std::ostringstream oss;
    oss << std::setprecision(17) << x;
    throw std::runtime_error("the value " + oss.str() + " is not an integer");
  }
  return static_cast<int>(rounded);
}


inline int cpp_to_integer(const EndfFloatCpp& x) {
  return cpp_to_integer(static_cast<double>(x));
}


// Lenient conversion to an integer, used for the solution of a field
// equation within a lookahead: the records are only read there to decide
// whether a branch applies, so the value need not be an integer.

inline int cpp_round_to_int(int x) { return x; }
inline int cpp_round_to_int(double x) { return static_cast<int>(std::round(x)); }
inline int cpp_round_to_int(const EndfRational& x) {
  return static_cast<int>(std::round(static_cast<double>(x)));
}


struct Tab1Body {
  std::vector<int> INT;
  std::vector<int> NBT;
  std::vector<DOUBLE_TYPE> X;
  std::vector<DOUBLE_TYPE> Y;
};


struct Tab2Body {
  std::vector<int> INT;
  std::vector<int> NBT;
};


inline bool seq_contains(py::sequence seq, py::object value) {
  int i = 0;
  for (const auto& item : seq) {
    if (py::cast<py::object>(item).equal(value)) {
      return true;
    }
  }
  return false;
}


inline bool should_parse_section(int mf, int mt, py::object& exclude, py::object& include) {
  py::tuple mf_mt_tup = py::make_tuple(mf, mt);
  if (! exclude.is_none()) {
    if (! py::isinstance<py::sequence>(exclude)) {
      throw std::runtime_error("`exclude` argument must be of sequence type");
    }
    if (seq_contains(exclude, py::int_(mf)) || seq_contains(exclude, mf_mt_tup)) {
      return false;
    } else {
      return true;
    }
  } else if (! include.is_none()) {
    if (! py::isinstance<py::sequence>(include)) {
      throw std::runtime_error("`include` argument must be of sequence type");
    }
    if (seq_contains(include, py::int_(mf)) || seq_contains(include, mf_mt_tup)) {
      return true;
    } else {
      return false;
    }
  } else {
    return true;
  }
}

#endif // MODULE_HEADER_HPP
