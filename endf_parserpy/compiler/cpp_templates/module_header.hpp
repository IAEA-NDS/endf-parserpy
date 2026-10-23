#ifndef MODULE_HEADER_HPP
#define MODULE_HEADER_HPP


#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Necessary for STL containers like std::map
#include <pybind11/numpy.h> // numpy arrays for array_type="numpy", imported on first use

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
#include <cstdio>     // for std::snprintf
#include <cstring>    // for std::memcpy / std::memchr
#include <cmath>      // for std::isfinite
#include <cerrno>     // for errno (ERANGE)
#include <climits>    // for INT_MIN / INT_MAX
#include <cstdint>    // for std::int64_t
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


// number of correlation values KIJ per INTG record for NDIGIT=2..6, from
// the formats 2I5,1X,18I3,1X / 2I5,1X,13I4,3X / 2I5,1X,11I5 /
// 2I5,1X,9I6,1X / 2I5,8I7 of ENDF-102 (Section 0.6.4.9)
inline int cpp_intg_num_values(int ndigit) {
  static const int num_values[] = {18, 13, 11, 9, 8};
  return num_values[ndigit - 2];
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


// Export of parsed arrays as numpy arrays (array_type="numpy").
// Arrays of floats (EndfFloatCpp) become float64 arrays if numpy_floats is
// true, which is not the case with preserve_value_strings=True, as the
// original strings cannot be stored in a numpy array. Arrays of integers
// become int64 arrays if numpy_ints is true. Arrays of all other element
// types are exported as lists, as with array_type="list".

inline bool cpp_numpy_export_enabled(const EndfFloatCpp*, bool numpy_ints, bool numpy_floats) {
  return numpy_floats;
}

inline bool cpp_numpy_export_enabled(const int*, bool numpy_ints, bool numpy_floats) {
  return numpy_ints;
}

template<typename T>
inline bool cpp_numpy_export_enabled(const T*, bool numpy_ints, bool numpy_floats) {
  return false;
}

// New uninitialized C-contiguous numpy array with elements of type T,
// created with the numpy C API (as in the constructor of py::array_t,
// without its intermediate containers); data receives the address of
// its elements
template<typename T>
inline py::object cpp_new_ndarray(int ndim, py::ssize_t* dims, T*& data) {
  static const int typenum = py::dtype::of<T>().num();
  py::detail::npy_api& api = py::detail::npy_api::get();
  PyObject* descr = api.PyArray_DescrFromType_(typenum);
  if (descr == nullptr) throw py::error_already_set();
  // PyArray_NewFromDescr steals the reference to descr
  PyObject* arr = api.PyArray_NewFromDescr_(
    api.PyArray_Type_, descr, ndim, reinterpret_cast<Py_intptr_t*>(dims),
    nullptr, nullptr, 0, nullptr
  );
  if (arr == nullptr) throw py::error_already_set();
  data = reinterpret_cast<T*>(py::detail::array_proxy(arr)->data);
  return py::reinterpret_steal<py::object>(arr);
}

// numpy array of the given shape filled with the row-major elements
// starting at src, converted in a single loop
inline py::object cpp_numeric_ndarray(const EndfFloatCpp* src, int ndim, py::ssize_t* dims) {
  double* dst;
  py::object arr = cpp_new_ndarray<double>(ndim, dims, dst);
  std::size_t n = 1;
  for (int d = 0; d < ndim; d++) n *= dims[d];
  for (std::size_t i = 0; i < n; i++) {
    dst[i] = static_cast<double>(src[i]);
  }
  return arr;
}

inline py::object cpp_numeric_ndarray(const int* src, int ndim, py::ssize_t* dims) {
  std::int64_t* dst;
  py::object arr = cpp_new_ndarray<std::int64_t>(ndim, dims, dst);
  std::size_t n = 1;
  for (int d = 0; d < ndim; d++) n *= dims[d];
  for (std::size_t i = 0; i < n; i++) {
    dst[i] = static_cast<std::int64_t>(src[i]);
  }
  return arr;
}

template<typename T>
inline py::object cpp_numeric_ndarray(const T*, int, py::ssize_t*) {
  // not reached: cpp_numpy_export_enabled is false for other element types
  throw std::logic_error("no numpy export for this element type");
}

// std::vector holding a TAB1/TAB2 table column or a list of integers
template<typename T>
inline py::object cpp_vector_to_pyobj(const std::vector<T>& vec, bool numpy_ints, bool numpy_floats) {
  if (cpp_numpy_export_enabled(vec.data(), numpy_ints, numpy_floats)) {
    py::ssize_t dim = static_cast<py::ssize_t>(vec.size());
    return cpp_numeric_ndarray(vec.data(), 1, &dim);
  }
  return py::cast(vec);
}


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
