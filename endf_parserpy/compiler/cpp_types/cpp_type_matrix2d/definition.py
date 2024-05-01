############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/20
# Last modified:   2024/05/01
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


definition_code = """
template<typename T>
class Matrix2d {

  private:
    std::vector<T> data;
    size_t num_rows;
    size_t num_cols;
    size_t row_start;
    size_t col_start;
    bool initialized;
    bool accessed;
    bool triagonal;
    bool lower;

  public:

    Matrix2d() : initialized(false), accessed(false),
                 triagonal(false), lower(false) {};

    void init(size_t first_row_idx, size_t last_row_idx,
              size_t first_col_idx, size_t last_col_idx,
              bool triagonal=false, bool lower=false) {
      this->num_rows = last_row_idx - first_row_idx + 1;
      this->num_cols = last_col_idx - first_col_idx + 1;
      this->row_start = first_row_idx;
      this->col_start = first_col_idx;
      this->data.resize(this->num_rows * this->num_cols);
      this->initialized = true;
      this->triagonal = triagonal;
      this->lower = lower;
    }

    bool is_initialized() {
      return initialized;
    }

    bool did_read() {
      return accessed;
    }

    T& operator()(size_t i, size_t j) {
      accessed = true;
      return data.at((i-row_start)*num_cols + (j-col_start));
    }

    int get_row_start_index() {
      return row_start;
    }

    int get_row_last_index() {
      return row_start + num_rows - 1;
    }

    int get_col_start_index() {
      return col_start;
    }

    int get_col_start_index(int i) {
      if (! triagonal || lower) {
        return col_start;
      } else {
        return col_start + (i - row_start);
      }
    }

    int get_col_last_index() {
      return col_start + num_cols - 1;
    }

    int get_col_last_index(int i) {
      if (! triagonal || ! lower) {
        return col_start + num_cols - 1;
      } else {
        return col_start + (i - row_start);
      }
    }
};
"""
