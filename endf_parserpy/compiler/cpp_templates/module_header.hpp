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

// When Python merges the various
// C++ files, there is no need
// to include them here
#ifndef PYTHON_COMPILE
#include "endf_float_cpp.hpp"
#include "index_shifter.hpp"
#endif

namespace py = pybind11;


#ifndef DOUBLE_TYPE
#define DOUBLE_TYPE double
#endif


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


bool seq_contains(py::sequence seq, py::object value) {
  int i = 0;
  for (const auto& item : seq) {
    if (py::cast<py::object>(item).equal(value)) {
      return true;
    }
  }
  return false;
}


bool should_parse_section(int mf, int mt, py::object& exclude, py::object& include) {
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
