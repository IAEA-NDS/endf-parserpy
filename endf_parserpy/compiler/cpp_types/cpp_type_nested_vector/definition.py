############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/25
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


definition_code = """
template<typename T>
class NestedVector : public std::vector<T> {
  private:
    int startIndex;
    int lastIndex;

  public:
    // default constructor
    NestedVector() : startIndex(0), lastIndex(-1) {}

    // copy and move construction/assignment are the implicitly
    // generated ones (member-wise); the implicit move operations
    // avoid deep copies when a std::vector of NestedVector grows

    void set_start_index(int start) {
      this->startIndex = start;
    }

    int get_start_index() const {
      return this->startIndex;
    }

    void set_last_index(int lastIndex) {
      this->lastIndex = lastIndex;
    }

    int get_last_index() const {
      return this->lastIndex;
    }

    T& operator[](int index) {
      if (! contains(index)) {
        throw std::out_of_range("index out of range 1");
      }
      return std::vector<T>::operator[](index - startIndex);
    }

    T& at(int index) {
      return std::vector<T>::at(index - startIndex);
    }

    T* prepare(int index) {
      if (contains(index)) return &((*this)[index]);
      T cpp_curel;
      set(index, cpp_curel);
      return &(*this)[index];
    }

    void set(int index, const T& value) {
      bool is_first = false;
      if (this->lastIndex == -1) {
        this->startIndex = index;
        this->lastIndex = index;
        is_first = true;
      }
      if (index == startIndex + (int)this->size()) {
        std::vector<T>::push_back(value);
        if (! is_first) {
          this->lastIndex++;
        }
      } else if (index >= startIndex && index < startIndex + (int)this->size())  {
        std::vector<T>::operator[](index - startIndex) = value;
      } else {
        throw std::out_of_range("index out of range 2");
      }
    }

    bool contains(int index) {
      return (this->startIndex <= index && index <= this->lastIndex);
    }

    py::object to_pyobj(bool list_mode) {
      if (list_mode) {
        py::list ret;
        to_pylist(ret, (*this));
        return ret;
      } else {
        py::dict ret;
        to_pydict(ret, (*this));
        return ret;
      }
    }

    // with array_type="numpy" (numpy_ints, numpy_floats, see
    // cpp_numpy_export_enabled), the innermost arrays of numbers are
    // numpy arrays and the enclosing levels lists
    py::object to_pyobj(bool list_mode, bool numpy_ints, bool numpy_floats) {
      if (numpy_ints || numpy_floats) {
        return to_pyobj_numpy((*this), numpy_ints, numpy_floats);
      }
      return to_pyobj(list_mode);
    }

    template <typename U>
    py::object to_pyobj_numpy(const NestedVector<NestedVector<U>>& curvec, bool numpy_ints, bool numpy_floats) {
      py::list ret;
      for (const auto& elem : curvec) {
        ret.append(to_pyobj_numpy(elem, numpy_ints, numpy_floats));
      }
      return ret;
    }

    template <typename U>
    py::object to_pyobj_numpy(const NestedVector<std::vector<U>>& curvec, bool numpy_ints, bool numpy_floats) {
      py::list ret;
      for (const auto& elem : curvec) {
        ret.append(cpp_vector_to_pyobj(elem, numpy_ints, numpy_floats));
      }
      return ret;
    }

    template <typename U>
    py::object to_pyobj_numpy(const NestedVector<U>& curvec, bool numpy_ints, bool numpy_floats) {
      if (cpp_numpy_export_enabled(curvec.data(), numpy_ints, numpy_floats)) {
        return cpp_numeric_ndarray(curvec.data(), curvec.size(), 0, false);
      }
      py::list ret;
      to_pylist(ret, curvec);
      return ret;
    }

    template <typename U>
    void to_pylist(py::list cur, const NestedVector<NestedVector<U>>& curvec) {
      for (const auto& elem : curvec) {
        py::list sublist;
        to_pylist(sublist, elem);
        cur.append(sublist);
      }
    }

    template <typename U>
    void to_pylist(py::list cur, const NestedVector<U>& curvec) {
      for (const auto& elem : curvec) {
          cur.append(py::cast(elem));
      }
    }

    template <typename U>
    void to_pydict(py::dict cur, const NestedVector<NestedVector<U>>& curvec) {
      int cnt = curvec.get_start_index();
      for (const auto& elem : curvec) {
        py::dict subdict;
        to_pydict(subdict, elem);
        cur[py::cast(cnt++)] = subdict;
      }
    }

    template <typename U>
    void to_pydict(py::dict cur, const NestedVector<U>& curvec) {
      int cnt = curvec.get_start_index();
      for (const auto& elem : curvec) {
        cur[py::cast(cnt++)] = py::cast(elem);
      }
    }

};
"""
