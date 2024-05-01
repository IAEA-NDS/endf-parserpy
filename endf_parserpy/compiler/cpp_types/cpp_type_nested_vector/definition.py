############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/25
# Last modified:   2024/05/01
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

    // copy constructor
    NestedVector(const NestedVector<T>& other) :
      std::vector<T>(other), startIndex(other.startIndex),
      lastIndex(other.lastIndex) {}

    // assignment constructor
    NestedVector<T>& operator=(const NestedVector<T>& other) {
      if (this != &other) {
        std::vector<T>::operator=(other);
        startIndex = other.startIndex;
        lastIndex = other.lastIndex;
      }
      return *this;
    }

    void set_start_index(int start) {
      this->startIndex = start;
    }

    int get_start_index() {
      return this->startIndex;
    }

    void set_last_index(int lastIndex) {
      this->lastIndex = lastIndex;
    }

    int get_last_index() {
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
};
"""
