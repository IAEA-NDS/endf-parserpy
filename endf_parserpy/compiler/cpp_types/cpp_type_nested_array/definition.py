############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/22
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################


definition_code = """
// Arrays of the variables with N indices.
//
// A NestedArray<T, N> is either a list of elements NestedArray<T, N-1>
// (list form) or, for N >= 2, a regular block (block form): a rectangular
// array whose index ranges are fixed when it is created (make_block),
// with the elements in row-major order. A list starts at the index of
// its first element and grows by appending elements (prepare); a
// NestedArray<T, 1> is a list of values (set). The capacity of a list
// of values filled by a loop is reserved before the loop (reserve) if
// the code generator can determine the list and the loop (see
// _filling_loop in assign.py). The code generator creates
// a block for the trailing indices of a variable if it can prove that
// they form a rectangular array that no other code of the recipe writes
// to and that is created only once (see find_block in assign.py); the
// logic_error exceptions below are therefore not raised for any recipe.
//
// Export (to_pyobj): with array_type="numpy", a block of numbers is one
// numpy array with N dimensions, a list of values a one-dimensional
// numpy array and the other lists Python lists; with array_type="list"
// and "dict", a block gives the same nested lists or dictionaries as the
// list form with the same elements.
//
// The values of an INTG record are a row: the variable of the values
// with N indices is a NestedArray<int, N+1> whose innermost level holds
// the rows. A row is a list of values set at once (set_row) or, in a
// block created with make_row_block, the last dimension of the block
// (set_block_row), whose length is fixed before the records are read.
// With array_type="dict", a row is exported as a list, not as a
// dictionary.

template<typename T, int N>
class NestedArray;

// whether the row with the given indices exists and its values, for an
// array of rows (see set_row); the indices of the rows of a
// NestedArray<T, N> are its first N-1 indices
template<typename T>
inline bool cpp_has_row(const NestedArray<T, 1>&) {
  return true;
}

template<typename T, int M, typename... I>
inline bool cpp_has_row(const NestedArray<T, M>& arr, I... indices) {
  return arr.contains(indices...);
}

template<typename T>
inline std::vector<T> cpp_get_row(const NestedArray<T, 1>& arr) {
  return arr.values();
}

template<typename T, int M, typename... I>
inline std::vector<T> cpp_get_row(const NestedArray<T, M>& arr, I... indices) {
  return arr(indices...);
}

// upper limit of the number of elements reserved by NestedArray::reserve
const long long cpp_max_reserved_elements = 65536;
// capacity of a list of values without reserved capacity when its first
// element is set
const std::size_t cpp_initial_list_capacity = 4;


// export of a sequence of values
template<typename T>
inline py::object cpp_values_to_pyobj(const T* vals, std::size_t n, int start, bool list_mode, bool numpy_ints, bool numpy_floats) {
  if (cpp_numpy_export_enabled(vals, numpy_ints, numpy_floats)) {
    py::ssize_t dim = static_cast<py::ssize_t>(n);
    return cpp_numeric_ndarray(vals, 1, &dim);
  }
  if (list_mode || numpy_ints || numpy_floats) {
    py::list ret = cpp_new_pylist(n);
    for (std::size_t i = 0; i < n; i++) cpp_pylist_set(ret, i, cpp_value_to_pyobj(vals[i]));
    return ret;
  }
  py::dict ret = cpp_new_pydict(n);
  for (std::size_t i = 0; i < n; i++) cpp_pydict_set(ret, start + (int)i, cpp_value_to_pyobj(vals[i]));
  return ret;
}

// columns of TAB1/TAB2 records and integers of INTG records
template<typename U>
inline py::object cpp_values_to_pyobj(const std::vector<U>* vals, std::size_t n, int start, bool list_mode, bool numpy_ints, bool numpy_floats) {
  if (list_mode || numpy_ints || numpy_floats) {
    py::list ret = cpp_new_pylist(n);
    for (std::size_t i = 0; i < n; i++) cpp_pylist_set(ret, i, cpp_vector_to_pyobj(vals[i], numpy_ints, numpy_floats));
    return ret;
  }
  py::dict ret = cpp_new_pydict(n);
  for (std::size_t i = 0; i < n; i++) cpp_pydict_set(ret, start + (int)i, py::cast(vals[i]));
  return ret;
}


template<typename T>
class NestedArray<T, 1> {
  private:
    int start = 0;
    std::vector<T> items;
    // the values of a record set at once (see set_row)
    bool row = false;

  public:
    bool empty() const {
      return items.empty();
    }

    bool contains(int index) const {
      return index >= start && index < start + (int)items.size();
    }

    T& operator()(int index) {
      if (! contains(index)) {
        throw std::out_of_range("index out of range");
      }
      return items[index - start];
    }

    // capacity for the elements with the indices up to last, if they are
    // set in the order of their indices from first on, so that the
    // elements are not moved while they are added; at most
    // cpp_max_reserved_elements elements are reserved (the loop bounds
    // of a damaged file may be huge). The elements are not changed.
    void reserve(int first, int last) {
      long long begin = items.empty() ? first : start;
      long long num = (long long)last - begin + 1;
      if (num > cpp_max_reserved_elements) {
        num = cpp_max_reserved_elements;
      }
      if (num > (long long)items.capacity()) {
        items.reserve((std::size_t)num);
      }
    }

    void set(int index, const T& value) {
      if (items.empty()) {
        start = index;
        // a list without reserved capacity starts with room for a few
        // elements, which saves the first reallocations of short lists
        if (items.capacity() == 0) {
          items.reserve(cpp_initial_list_capacity);
        }
      }
      if (index == start + (int)items.size()) {
        items.push_back(value);
      } else if (contains(index)) {
        items[index - start] = value;
      } else {
        throw std::out_of_range("index out of range");
      }
    }

    const std::vector<T>& values() const {
      return items;
    }

    // the values of a record as a row
    void assign_row(std::vector<T> values) {
      items = std::move(values);
      start = 0;
      row = true;
    }

    py::object to_pyobj(bool list_mode, bool numpy_ints, bool numpy_floats) const {
      return cpp_values_to_pyobj(items.data(), items.size(), start, list_mode || row, numpy_ints, numpy_floats);
    }
};


template<typename T, int N>
class NestedArray {
  private:
    // list form
    int start = 0;
    std::vector<NestedArray<T, N-1>> items;
    // block form
    bool is_block = false;
    // the last dimension of the block holds rows (see make_row_block)
    bool row_block = false;
    int first[N];
    int dims[N];
    std::vector<T> data;

    template<typename... I>
    std::size_t offset(int d, std::size_t pos, int index, I... rest) const {
      int i = index - first[d];
      if (i < 0 || i >= dims[d]) {
        throw std::out_of_range("index out of range");
      }
      return offset(d + 1, pos * dims[d] + i, rest...);
    }

    std::size_t offset(int, std::size_t pos) const {
      return pos;
    }

    template<typename... I>
    bool in_block(int d, int index, I... rest) const {
      return index >= first[d] && index < first[d] + dims[d] && in_block(d + 1, rest...);
    }

    bool in_block(int) const {
      return true;
    }

    // nested lists or dictionaries of the block elements of dimension d
    // and following, starting at the element ptr
    py::object block_to_pyobj(int d, const T* ptr, std::size_t stride, bool list_mode, bool numpy_ints, bool numpy_floats) const {
      std::size_t substride = stride / (dims[d] > 0 ? dims[d] : 1);
      if (d == N - 1) {
        return cpp_values_to_pyobj(ptr, dims[d], first[d], list_mode || row_block, false, false);
      }
      if (list_mode) {
        py::list ret = cpp_new_pylist(dims[d]);
        for (int i = 0; i < dims[d]; i++) {
          cpp_pylist_set(ret, i, block_to_pyobj(d + 1, ptr + i * substride, substride, list_mode, false, false));
        }
        return ret;
      }
      py::dict ret = cpp_new_pydict(dims[d]);
      for (int i = 0; i < dims[d]; i++) {
        cpp_pydict_set(ret, first[d] + i, block_to_pyobj(d + 1, ptr + i * substride, substride, list_mode, false, false));
      }
      return ret;
    }

  public:
    bool empty() const {
      return is_block ? data.empty() : items.empty();
    }

    // element of the list form with the given index; a new element is
    // appended if the index follows the last one
    NestedArray<T, N-1>* prepare(int index) {
      if (is_block) {
        throw std::logic_error("element of a regular block prepared");
      }
      if (items.empty()) {
        start = index;
      }
      int pos = index - start;
      if (pos == (int)items.size()) {
        items.emplace_back();
      } else if (pos < 0 || pos > (int)items.size()) {
        throw std::out_of_range("index out of range");
      }
      return &items[pos];
    }

    // capacity of the list form for the elements with the indices up to
    // last, see NestedArray<T, 1>::reserve
    void reserve(int first, int last) {
      if (is_block) return;
      long long begin = items.empty() ? first : start;
      long long num = (long long)last - begin + 1;
      if (num > cpp_max_reserved_elements) {
        num = cpp_max_reserved_elements;
      }
      if (num > (long long)items.capacity()) {
        items.reserve((std::size_t)num);
      }
    }

    // row of values of the list form with the given index, set as
    // NestedArray<T, 1>::set sets a value
    void set_row(int index, std::vector<T> values) {
      static_assert(N == 2, "rows are the elements of an array with two levels");
      if (is_block) {
        throw std::logic_error("row of a regular block set as element");
      }
      if (items.empty()) {
        start = index;
      }
      int pos = index - start;
      if (pos == (int)items.size()) {
        items.emplace_back();
      } else if (pos < 0 || pos > (int)items.size()) {
        throw std::out_of_range("index out of range");
      }
      items[pos].assign_row(std::move(values));
    }

    // turn the array into a regular block whose last dimension holds
    // rows (see set_block_row), with the limits of make_block
    template<typename... L>
    void make_row_block(L... limits) {
      make_block(limits...);
      row_block = true;
    }

    // the values of the row of a block with the given leading indices
    template<typename... I>
    void set_block_row(const std::vector<T>& values, I... indices) {
      static_assert(sizeof...(I) == N - 1, "wrong number of indices");
      if (! is_block) {
        throw std::logic_error("row of a list set as row of a regular block");
      }
      if ((int)values.size() != dims[N-1]) {
        throw std::runtime_error("number of values differs from the length of the rows of the block");
      }
      std::size_t pos = offset(0, 0, indices..., first[N-1]);
      std::copy(values.begin(), values.end(), data.begin() + pos);
    }

    // turn the array into a regular block whose indices range from
    // limits[2*d] to limits[2*d+1] (both inclusive) in dimension d
    template<typename... L>
    void make_block(L... limits) {
      static_assert(sizeof...(L) == 2 * N, "two limits per index expected");
      const int lims[2 * N] = {static_cast<int>(limits)...};
      std::size_t size = 1;
      bool same = is_block;
      for (int d = 0; d < N; d++) {
        int dim = std::max(0, lims[2*d+1] - lims[2*d] + 1);
        same = same && first[d] == lims[2*d] && dims[d] == dim;
        first[d] = lims[2*d];
        dims[d] = dim;
        size *= dim;
      }
      if (same) return;
      if (is_block || ! items.empty()) {
        throw std::logic_error("regular block created again with a different shape");
      }
      is_block = true;
      data.resize(size);
    }

    template<typename... I, typename std::enable_if<sizeof...(I) == N - 1, int>::type = 0>
    bool contains(int index, I... rest) const {
      if (is_block) {
        return in_block(0, index, rest...);
      }
      int pos = index - start;
      return pos >= 0 && pos < (int)items.size() && items[pos].contains(rest...);
    }

    template<typename... I, typename std::enable_if<sizeof...(I) == N - 1, int>::type = 0>
    T& operator()(int index, I... rest) {
      if (is_block) {
        return data[offset(0, 0, index, rest...)];
      }
      int pos = index - start;
      if (pos < 0 || pos >= (int)items.size()) {
        throw std::out_of_range("index out of range");
      }
      return items[pos](rest...);
    }

    // an array of rows (see set_row and set_block_row) indexed by the
    // indices of its rows: whether the row exists, and a copy of its values
    template<typename... I, typename std::enable_if<sizeof...(I) == N - 2, int>::type = 0>
    bool contains(int index, I... rest) const {
      if (is_block) {
        return in_block(0, index, rest...);
      }
      int pos = index - start;
      return pos >= 0 && pos < (int)items.size() && cpp_has_row(items[pos], rest...);
    }

    template<typename... I, typename std::enable_if<sizeof...(I) == N - 2, int>::type = 0>
    std::vector<T> operator()(int index, I... rest) const {
      if (is_block) {
        std::size_t pos = offset(0, 0, index, rest..., first[N-1]);
        return std::vector<T>(data.begin() + pos, data.begin() + pos + dims[N-1]);
      }
      int pos = index - start;
      if (pos < 0 || pos >= (int)items.size()) {
        throw std::out_of_range("index out of range");
      }
      return cpp_get_row(items[pos], rest...);
    }

    py::object to_pyobj(bool list_mode, bool numpy_ints, bool numpy_floats) const {
      if (is_block) {
        if (cpp_numpy_export_enabled(data.data(), numpy_ints, numpy_floats)) {
          py::ssize_t shape[N];
          for (int d = 0; d < N; d++) shape[d] = dims[d];
          return cpp_numeric_ndarray(data.data(), N, shape);
        }
        list_mode = list_mode || numpy_ints || numpy_floats;
        return block_to_pyobj(0, data.data(), data.size(), list_mode, false, false);
      }
      if (list_mode || numpy_ints || numpy_floats) {
        py::list ret = cpp_new_pylist(items.size());
        for (std::size_t i = 0; i < items.size(); i++) {
          cpp_pylist_set(ret, i, items[i].to_pyobj(list_mode, numpy_ints, numpy_floats));
        }
        return ret;
      }
      py::dict ret = cpp_new_pydict(items.size());
      for (std::size_t i = 0; i < items.size(); i++) {
        cpp_pydict_set(ret, start + (int)i, items[i].to_pyobj(list_mode, numpy_ints, numpy_floats));
      }
      return ret;
    }
};
"""
